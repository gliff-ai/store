from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Sum
from django_etebase.models import Collection
from loguru import logger
from ninja import Router
import stripe


from myauth.models import Tier, Team, Billing, TierAddons, User, UserProfile, CustomBilling
from server.api.schemas import (
    CheckoutSessionIn,
    CheckoutSessionOut,
    Error,
    AddonIn,
    InvoicesOut,
    CurrentLimitsOut,
    CurrentPlanOut,
    Addons,
    AddonPrices,
    PaymentOut,
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


# We use Mb they use Gb
def stripe_to_gliff_usage(usage):
    return usage * 1000


def gliff_to_stripe_usage(usage):
    return usage / 1000


def calculate_plan_total(base, addons):
    if base is None or addons is None:
        return base
    else:
        return base + addons


def calculate_plan(team):
    plan = dict(tier_name=team.tier.name, tier_id=team.tier.id)

    # They are either on the free plan or a custom plan
    # Either way, they can't have addons so just return the standard plan
    if not hasattr(team, "billing"):
        return plan

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
        billed_usage = int(team.usage or 0) - (stripe_to_gliff_usage(storage[0].price.tiers[0].up_to))
        if billed_usage >= 0:
            plan["billed_usage"] = billed_usage
        else:
            plan["billed_usage"] = 0

        plan["billed_usage_gb_price"] = storage[0].price.tiers[1].unit_amount

    return plan


def calculate_limits(team):
    team_members = UserProfile.objects.filter(team__owner_id=team.owner).values_list("user_id", flat=True)
    users = User.objects.filter(
        userprofile__team__owner_id=team.owner,
        userprofile__is_collaborator=False,
        userprofile__is_trusted_service=False,
    ).count()
    collaborators = User.objects.filter(
        userprofile__team__owner_id=team.owner,
        userprofile__is_collaborator=True,
        userprofile__is_trusted_service=False,
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
    if not hasattr(team, "billing") and not hasattr(team, "custombilling"):
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
    "/payment-method",
    response={200: PaymentOut, 403: Error, 422: Error, 500: Error},
)
def get_payments(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if hasattr(team, "custombilling"):
        return 422, {"message": "Payment methods for custom plans cannot be shown here"}

    subscription = stripe.Subscription.retrieve(team.billing.subscription_id)
    payment_method = stripe.PaymentMethod.retrieve(subscription["default_payment_method"])

    payment = dict(
        number=f"**** **** **** **** {payment_method.card.last4}",
        expiry=f"{payment_method.card.exp_month}/{payment_method.card.exp_year}",
        brand=payment_method.card.brand,
        name=payment_method.billing_details.name,
    )
    return payment


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

        if hasattr(team, "custombilling"):
            return 403, {"message": "Custom invoices cannot be shown here"}

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
    response={200: CurrentPlanOut, 204: None, 403: Error, 500: Error},
)
def get_plan(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can view plan details"}

    if hasattr(team, "custombilling"):
        return 204, None

    return calculate_plan(team)


@router.get(
    "/addon-prices",
    response={200: AddonPrices, 422: Error, 403: Error, 500: Error},
)
def addonPrice(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can upgrade plans"}

    if not hasattr(team, "billing"):
        return 422, {"message": "No valid subscription to upgrade. Try changing your plan"}

    prices = dict(project=None, user=None, collaborator=None)
    if team.tier.stripe_project_price_id:
        project = stripe.Price.retrieve(team.tier.stripe_project_price_id, expand=["tiers"])
        prices["project"] = project.tiers[1].unit_amount
    if team.tier.stripe_user_price_id:
        user = stripe.Price.retrieve(team.tier.stripe_user_price_id, expand=["tiers"])
        prices["user"] = user.tiers[1].unit_amount

    if team.tier.stripe_collaborator_price_id:
        collaborator = stripe.Price.retrieve(team.tier.stripe_collaborator_price_id, expand=["tiers"])
        prices["collaborator"] = collaborator.tiers[1].unit_amount

    print(user)

    return prices


@router.post(
    "/cancel/",
    response={200: None, 422: Error, 403: Error, 500: Error},
)
def cancel(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id is not user.id:
            return 403, {"message": "Only owners can cancel plans"}

        if not hasattr(team, "billing"):
            return 422, {"message": "No valid subscription to cancel. Try changing your plan"}

        res = stripe.Subscription.delete(team.billing.subscription_id)

        if res.status != "cancelled":
            return 500, {"message": "There was an error cancelling, contact us at contact@gliff.ai"}

        team.billing.cancel_date = res.cancelled_at
        team.save()

        users = User.objects.filter(team=team.id)
        users.update(is_active=False)

        return 200

    except Exception as e:
        logger.error(e)
        return 500, {"message": "There was an error cancelling, contact us at contact@gliff.ai"}


@router.post(
    "/addon/",
    response={201: None, 422: Error, 403: Error, 500: Error},
)
def addon(request, payload: AddonIn):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id is not user.id:
            return 403, {"message": "Only owners can upgrade plans"}

        if hasattr(team, "custombilling"):
            return 422, {"message": "You can't have addons on a custom plan"}

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


@router.post("/create-authd-checkout-session/", response={200: CheckoutSessionOut, 422: Error, 403: Error})
def create_auth_checkout_session(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id is not user.id:
            return 403, {"message": "Only owners can upgrade plans"}

        if hasattr(team, "custombilling"):
            return 422, {"message": "You can't upgrade a custom plan"}

        if not hasattr(team, "billing"):
            return 422, {"message": "No valid subscription to upgrade. Try changing your plan"}

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="setup",
            customer=team.billing.stripe_customer_id,
            setup_intent_data={
                "metadata": {
                    "subscription_id": team.billing.subscription_id,
                },
            },
            success_url=settings.BASE_URL + "/billing/success",
            cancel_url=settings.BASE_URL + "/billing/error",
        )

        return {"id": session.id}
    except Exception as e:
        logger.error(str(e))
        return 403, {"message": str(e)}


@router.post(
    "/create-checkout-session/", response={200: CheckoutSessionOut, 201: None, 403: Error, 409: Error}, auth=None
)
def create_checkout_session(request, payload: CheckoutSessionIn):
    try:
        user = User.objects.get(id__exact=payload.user_id)
        tier = Tier.objects.get(id__exact=payload.tier_id)
        team = Team.objects.get(owner_id=user.id)

        # This is a free plan, no need to bill them
        if tier.id == 1:
            logger.error(f"we shouldn't create_checkout_session for a free plan?! ({payload.tier_id})")
            return 409, {"message": "Can't pay for a free tier"}

        if tier.is_custom:
            # Has this plan already been used?
            if Team.objects.filter(tier_id=payload.tier_id):
                logger.error(f"Custom Tier already used - ({payload.tier_id})")
                return 409, {"message": "This tier is unavailable"}

            CustomBilling.objects.create(
                start_date=datetime.now(tz=timezone.utc),
                renewal_date=None,
                team_id=team.id,
            ).save()

            Team.objects.filter(id=team.id).update(tier_id=payload.tier_id)
            return 201, None

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
            allow_promotion_codes=True,
            automatic_tax={"enabled": True},
            tax_id_collection={"enabled": True},
            billing_address_collection="required",
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
        logger.info(session)

        subscription = stripe.Subscription.retrieve(session["subscription"])
        metadata = session["metadata"]

        billing = Billing.objects.create(
            stripe_customer_id=subscription["customer"],
            start_date=datetime.fromtimestamp(subscription["current_period_start"], timezone.utc),
            renewal_date=datetime.fromtimestamp(subscription["current_period_end"], timezone.utc),
            team_id=metadata.team_id,
            subscription_id=subscription["id"],
        )

        billing.save()

        Team.objects.filter(id=metadata.team_id).update(tier_id=metadata.tier_id)

        return True
    except Exception as e:
        logger.error(e)
        return False
