from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Sum
from loguru import logger
from ninja import Router
import stripe

from myauth.models import Tier, Team, Billing, TierAddons
from server.api.schemas import CheckoutSessionIn, CheckoutSessionOut, Error, AddonIn, CurrentPlanOut

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

router = Router()


# Filter a stripe subscription to get the IDs of prices already applied (so we can update them)
def get_user_price_id(price_id, subscription):
    return next(
        (item.id for item in subscription["items"]["data"] if item.price["id"] == price_id),
        None,
    )


def calculatePlanTotal(base, addons):
    if base is None:
        return base
    else:
        return base + addons


@router.get(
    "/plan",
    response={200: CurrentPlanOut, 500: Error},
)
def get_plan_limits(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can view plan details"}  # is this true?

    plan = dict(tier_name=team.tier.name, tier_id=team.tier.id)

    if not hasattr(team, "billing"):
        # Team is on the free plan so it's whatever those limits are
        plan["has_billing"] = False
        plan["projects"] = team.tier.base_project_limit
        plan["users"] = team.tier.base_user_limit
        plan["collaborators"] = team.tier.base_collaborator_limit
        return plan

    plan["has_billing"] = True

    addons = TierAddons.objects.filter(team=team).aggregate(
        users=Sum("additional_user_count"),
        projects=Sum("additional_project_count"),
        collaborators=Sum("additional_collaborator_count"),
    )

    # None is "unlimited"
    plan["projects"] = calculatePlanTotal(team.tier.base_project_limit, addons["projects"])
    plan["users"] = calculatePlanTotal(team.tier.base_user_limit, addons["users"])
    plan["collaborators"] = calculatePlanTotal(team.tier.base_collaborator_limit, addons["collaborators"])

    return plan


@router.post(
    "/addon",
    response={201: None, 422: Error, 402: Error, 500: Error},
)
def addon(request, payload: AddonIn):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id is not user.id:
            return 403, {"message": "Only owners can upgrade plans"}

        if not hasattr(team, "billing"):
            return 422, {"message": "No valid subscription to upgrade. Try changing your plan"}

        items = []

        addons = TierAddons.objects.filter(team=team).aggregate(
            users=Sum("additional_user_count"),
            projects=Sum("additional_project_count"),
            collaborators=Sum("additional_collaborator_count"),
        )

        subscription = stripe.Subscription.retrieve(team.billing.subscription_id)

        if team.tier.base_project_limit is not None and payload.projects > 0:
            # the user doesn't have unlimited projects
            projects = addons["projects"] + payload.projects
            items.append(
                {
                    "price": team.tier.stripe_project_price_id,
                    "quantity": projects,
                    "id": get_user_price_id(team.tier.stripe_project_price_id, subscription),
                }
            )

        if payload.collaborators > 0:
            collaborators = addons["collaborators"] + payload.collaborators
            items.append(
                {
                    "price": team.tier.stripe_collaborator_price_id,
                    "quantity": collaborators,
                    "id": get_user_price_id(team.tier.stripe_collaborator_price_id, subscription),
                }
            )

        if payload.users > 0:
            users = addons["users"] + payload.users
            items.append(
                {
                    "price": team.tier.stripe_user_price_id,
                    "quantity": users,
                    "id": get_user_price_id(team.tier.stripe_user_price_id, subscription),
                }
            )

        # Update Stripe
        res = stripe.Subscription.modify(team.billing.subscription_id, items=items)

        # Update DB
        addons_row = TierAddons.objects.create(
            team_id=team.id,
            additional_user_count=payload.users,
            additional_project_count=payload.projects,
            additional_collaborator_count=payload.collaborators,
        )
        addons_row.save()

        return 201, None

    except Exception as e:
        logger.error(f"Unknown addon error {e}")
        return 500, {"message": "Unknown Error"}


@router.post(
    "/create-checkout-session",
    response={200: CheckoutSessionOut, 403: Error, 409: Error},
)
def create_checkout_session(request, payload: CheckoutSessionIn):
    try:
        user = request.auth
        tier = Tier.objects.get(id__exact=payload.tier_id)
        team = Team.objects.get(owner_id=user.id)

        # This is a free plan, no need to bill them
        if tier.stripe_flat_price_id is None:
            logger.error("we shouldn't create_checkout_session for a free plan?!")
            return 409, {"message": "Can't pay for a free tier"}

        # By default, just charge the flat rate
        line_items = [{"price": tier.stripe_flat_price_id, "quantity": 1}]

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            client_reference_id=user.id,
            # We may want different billing emails later, but this is fine for now
            customer_email=user.email,
            line_items=line_items,
            mode="subscription",
            success_url=settings.SUCCESS_URL,
            cancel_url=settings.CANCEL_URL,
            metadata={"tier_id": tier.id, "tier_name": tier.name, "team_id": team.id},
        )
        return {"id": checkout_session.id}
    except Exception as e:
        print(e)
        return 403, {"message": str(e)}


@router.post(
    "/webhook",
    response={200: None, 400: Error},
    auth=None,
)
def stripe_webhook(request):
    payload = request.body
    event = None
    try:
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        logger.warning(f"Received ValueError {e}")
        return 400, {"message": "Invalid Payload"}
    except KeyError as e:
        logger.warning(f"Received KeyError {e}")
        return 400, {"message": "No Signature"}
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.warning(f"Received VerificationError {e}")
        return 400, {"message": "Invalid Signature"}

    # Handle them completing checkout. Add the billling info and update the tier
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Fulfill the purchase...
        complete_payment(session)

    # if event["type"] == "": TODO Handle invoice payments to update expiry date

    return 200


def complete_payment(session):
    try:
        print(session)  # Log properly

        subscription = stripe.Subscription.retrieve(session["subscription"])
        metatdata = session["metadata"]

        billing = Billing.objects.create(
            stripe_customer_id=subscription["customer"],
            start_date=datetime.fromtimestamp(subscription["current_period_start"], timezone.utc),
            renewal_date=datetime.fromtimestamp(subscription["current_period_end"], timezone.utc),
            team_id=metatdata.team_id,
            subscription_id=subscription["id"],
        )

        billing.save()

        return True
    except Exception as e:
        print(e)
        return False
