from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Sum
from django_etebase.models import Collection
from loguru import logger
from ninja import Router
import stripe


from myauth.models import Tier, Team, Billing, TierAddons, User, UserProfile
from server.api.schemas import (
    CheckoutSessionIn,
    CheckoutSessionOut,
    Error,
    AddonIn,
    InvoicesOut,
    CurrentLimitsOut,
    CurrentPlanOut,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

router = Router()


# Filter a stripe subscription to get the IDs of prices already applied (so we can update them)
def get_user_price_id(price_id, subscription):
    return next(
        (item.id for item in subscription["items"]["data"] if item.price["id"] == price_id),
        None,
    )


def calculate_plan_total(base, addons):
    if base is None or addons is None:
        return base
    else:
        return base + addons


def calculate_plan(team):
    plan = dict(tier_name=team.tier.name, tier_id=team.tier.id)

    subscription = stripe.Subscription.retrieve(team.billing.subscription_id)

    plan["current_period_end"] = subscription.current_period_end
    plan["current_period_start"] = subscription.current_period_start

    items = stripe.SubscriptionItem.list(subscription=team.billing.subscription_id, expand=["data.price.tiers"])

    storage = [item for item in items if item.price["id"] == team.tier.stripe_storage_price_id]
    project = [item for item in items if item.price["id"] == team.tier.stripe_project_price_id]
    base = [item for item in items if item.price["id"] == team.tier.stripe_flat_price_id]
    user = [item for item in items if item.price["id"] == team.tier.stripe_user_price_id]
    collaborator = [item for item in items if item.price["id"] == team.tier.stripe_collaborator_price_id]

    plan["addons"] = dict()

    if len(base):
        plan["base_price"] = base[0].price["unit_amount"]

    if len(project):
        # this assumes tiers[0] is the included amount and tiers[1] is the ONLY charged graduation in Stripe
        # (this is for all addons)
        price_per_unit = project[0].price.tiers[1].unit_amount
        plan["addons"]["project"] = dict(
            quantity=project[0]["quantity"], name="Projects", price_per_unit=price_per_unit
        )

    if len(user):
        price_per_unit = user[0].price.tiers[1].unit_amount
        plan["addons"]["user"] = dict(quantity=user[0]["quantity"], name="Users", price_per_unit=price_per_unit)

    if len(collaborator):
        price_per_unit = collaborator[0].price.tiers[1].unit_amount
        plan["addons"]["collaborator"] = dict(
            quantity=collaborator[0]["quantity"], name="Collaborator", price_per_unit=price_per_unit
        )

    if len(storage):
        billed_usage = int(team.usage or 0) - (storage[0].price.tiers[0].up_to * 1000)
        if billed_usage >= 0:
            plan["billed_usage"] = billed_usage
        else:
            plan["billed_usage"] = 0

        plan["billed_usage_price"] = storage[0].price.tiers[0].unit_amount

    return plan


def calculate_limits(team):
    team_members = UserProfile.objects.filter(team__owner_id=team.owner).values_list("user_id", flat=True)
    users = User.objects.filter(userprofile__team__owner_id=team.owner, userprofile__is_collaborator=False).count()
    collaborators = User.objects.filter(
        userprofile__team__owner_id=team.owner, userprofile__is_collaborator=True
    ).count()
    storage = Team.objects.filter(id=team.id).values("usage")[0]
    projects = Collection.objects.filter(owner__in=team_members).count()

    plan = dict(
        tier_name=team.tier.name,
        tier_id=team.tier.id,
        users=users,
        storage=storage["usage"],
        collaborators=collaborators,
        projects=projects,
    )

    plan["storage_included_limit"] = team.tier.base_storage_limit

    # Add limits
    if not hasattr(team, "billing"):
        # Team is on the free plan so it's whatever those limits are
        plan["has_billing"] = False
        plan["projects_limit"] = team.tier.base_project_limit
        plan["users_limit"] = team.tier.base_user_limit
        plan["collaborators_limit"] = team.tier.base_collaborator_limit
        return plan

    plan["has_billing"] = True

    addons = TierAddons.objects.filter(team=team).aggregate(
        users=Sum("additional_user_count"),
        projects=Sum("additional_project_count"),
        collaborators=Sum("additional_collaborator_count"),
    )

    # None is "unlimited"
    plan["projects_limit"] = calculate_plan_total(team.tier.base_project_limit, addons["projects"])
    plan["users_limit"] = calculate_plan_total(team.tier.base_user_limit, addons["users"])
    plan["collaborators_limit"] = calculate_plan_total(team.tier.base_collaborator_limit, addons["collaborators"])

    return plan


@router.get(
    "/invoices",
    response={200: InvoicesOut, 403: Error, 500: Error},
)
def get_invoices(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id is not user.id:
            return 403, {"message": "Only owners can view invoices"}

        invoices = stripe.Invoice.list(customer=team.billing.stripe_customer_id)
        if invoices:
            return {"invoices": invoices.data}
        else:
            return {"invoices": list()}
    except Exception as e:
        logger.error(f"Error getting invoices for user {user.id} - {e}")
        return {"message": "There was an error retrieving your invoices"}


@router.get(
    "/limits",
    response={200: CurrentLimitsOut, 403: Error, 500: Error},
)
def get_plan_limits(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    return calculate_limits(team)


@router.get(
    "/plan",
    response={200: CurrentPlanOut, 403: Error, 500: Error},
)
def get_plan(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can view plan details"}

    return calculate_plan(team)


@router.post(
    "/addon",
    response={201: None, 422: Error, 403: Error, 500: Error},
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
        stripe.Subscription.modify(team.billing.subscription_id, items=items)

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


@router.post("/create-checkout-session", response={200: CheckoutSessionOut, 403: Error, 409: Error}, auth=None)
def create_checkout_session(request, payload: CheckoutSessionIn):
    try:
        user = User.objects.get(id__exact=payload.user_id)
        tier = Tier.objects.get(id__exact=payload.tier_id)
        team = Team.objects.get(owner_id=user.id)

        # This is a free plan, no need to bill them
        if tier.stripe_flat_price_id is None:
            logger.error("we shouldn't create_checkout_session for a free plan?!")
            return 409, {"message": "Can't pay for a free tier"}

        # Charge the flat rate and add storage, which is updated daily
        line_items = [
            {"price": tier.stripe_flat_price_id, "quantity": 1},
            {"price": tier.stripe_storage_price_id},
        ]

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            client_reference_id=user.id,
            # This doesn't HAVE to be the user account email
            customer_email=payload.user_email,
            line_items=line_items,
            mode="subscription",
            success_url=settings.SUCCESS_URL,
            cancel_url=settings.CANCEL_URL,
            metadata={"tier_id": tier.id, "tier_name": tier.name, "team_id": team.id},
        )
        return {"id": checkout_session.id}
    except Exception as e:
        logger.error(str(e))
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
