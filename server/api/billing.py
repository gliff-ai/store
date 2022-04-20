from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Sum
from django_etebase.models import Collection
from loguru import logger
from ninja import Router
import stripe
import ipaddress


from myauth.models import Tier, Team, Billing, TierAddons, User, UserProfile, CustomBilling, Invite
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
    UpdatePlanIn,
    AllPlans,
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


def create_team_billing(tier: Tier, team_id: int):
    Team.objects.filter(id=team_id).update(tier_id=tier.id)

    return [
        {"price": tier.stripe_flat_price_id, "quantity": 1},
        {"price": tier.stripe_storage_price_id},
    ]


def create_stripe_customer(email, name, user_id, team_id, ip):
    try:
        kwargs = {
            "email": email,
            "name": name,
            "metadata": {"user_id": user_id, "team_id": team_id},
            "expand": ["tax"],
        }

        if ip and not ipaddress.ip_address(ip).is_private:
            kwargs["tax"] = {"ip_address": ip}
        else:
            # Ideally we never get here, but if we do, default auto tax to UK for now
            # We can also get Cloudflare to add a geo header if we wish to help with this
            kwargs["address"] = {"country": "GB", "postal_code": "NE22DS"}

        return stripe.Customer.create(**kwargs)
    except Exception as e:
        logger.error(f"Error creating stripe customer for user {user_id} - {e}")
        return None


def create_stripe_subscription(email, name, user_id: int, team_id: int, tier: Tier, ip: str, trial=True):
    try:
        customer = create_stripe_customer(email, name, user_id, team_id, ip)

        line_items = create_team_billing(tier, team_id)

        # For a custom tier, we have a subscription ID already so no need to create
        if not tier.is_custom:
            subscription = stripe.Subscription.create(
                customer=customer,
                items=line_items,
                trial_period_days=30 if trial else None,
                automatic_tax={
                    "enabled": True,
                },
            )
        else:
            subscription = stripe.Subscription.retrieve(id=tier.custom_subscription_id)
            # Check if they've paid?

        billing = Billing.objects.create(
            stripe_customer_id=subscription["customer"],
            start_date=datetime.fromtimestamp(subscription["current_period_start"], timezone.utc),
            renewal_date=datetime.fromtimestamp(subscription["current_period_end"], timezone.utc),
            team_id=team_id,
            subscription_id=subscription["id"],
        )

        return subscription, billing
    except Exception as e:
        logger.error(f"Error creating stripe subscription for user {user_id} - {e}")
        return None


def calculate_plan_total(base, addons):
    if base is None or addons is None:
        return base
    else:
        return base + addons


def calculate_plan(team: Team):
    plan = dict(tier_name=team.tier.name, tier_id=team.tier.id)

    # If a team doesn't have billing information, that means they signed up on V1 so we should migrate them
    if not hasattr(team, "billing"):
        logger.info(f"Migrating {team.id} to billing 2.0")

        create_stripe_subscription(
            team.owner.email, team.owner.userprofile.name, team.owner.id, team.id, team.tier, "127.0.0.1", False
        )

    subscription = stripe.Subscription.retrieve(team.billing.subscription_id)

    plan["current_period_end"] = subscription.current_period_end
    plan["current_period_start"] = subscription.current_period_start
    plan["trial_end"] = subscription.trial_end
    plan["trial_start"] = subscription.trial_start

    items = stripe.SubscriptionItem.list(subscription=team.billing.subscription_id, expand=["data.price.tiers"])

    storage = [item for item in items if item.price["id"] == team.tier.stripe_storage_price_id]
    project = [item for item in items if item.price["id"] == team.tier.stripe_project_price_id]
    base = [item for item in items if item.price["id"] == team.tier.stripe_flat_price_id]
    user = [item for item in items if item.price["id"] == team.tier.stripe_user_price_id]
    collaborator = [item for item in items if item.price["id"] == team.tier.stripe_collaborator_price_id]

    plan["addons"] = dict()

    if len(base):
        plan["base_price"] = base[0].price["unit_amount"] if base[0].price["unit_amount"] is not None else 0
    else:
        plan["base_price"] = 0

    # No addons on free or custom plans
    if team.tier.id != 1 and not team.tier.is_custom:
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

    else:
        plan["billed_usage"] = 0
        plan["billed_usage_gb_price"] = 0

    plan["is_custom"] = team.tier.is_custom

    if plan["trial_end"] and datetime.fromtimestamp(plan["trial_end"], timezone.utc) > datetime.now(tz=timezone.utc):
        plan["is_trial"] = True
    else:
        plan["is_trial"] = False

    if team.billing.cancel_date:
        plan["cancel_date"] = datetime.timestamp(team.billing.cancel_date)

    return plan


def calculate_limits(team):
    team_members = UserProfile.objects.filter(team__owner_id=team.owner).values_list("user_id", flat=True)
    users = (
        User.objects.filter(
            userprofile__team__owner_id=team.owner,
            userprofile__is_collaborator=False,
            userprofile__is_trusted_service=False,
        ).count()
        + Invite.objects.filter(
            from_team__owner_id=team.owner, is_collaborator=False, accepted_date__isnull=True
        ).count()
    )

    collaborators = (
        User.objects.filter(
            userprofile__team__owner_id=team.owner,
            userprofile__is_collaborator=True,
            userprofile__is_trusted_service=False,
        ).count()
        + Invite.objects.filter(
            from_team__owner_id=team.owner, is_collaborator=True, accepted_date__isnull=True
        ).count()
    )

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
    response={200: PaymentOut, 204: None, 403: Error, 422: Error, 500: Error},
)
def get_payments(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if hasattr(team, "custombilling"):
        return 422, {"message": "Payment methods for custom plans cannot be shown here"}

    methods = stripe.Customer.list_payment_methods(team.billing.stripe_customer_id, type="card")

    if len(methods.data):
        payment_method = methods.data[0]
        payment = dict(
            number=f"**** **** **** **** {payment_method.card.last4}",
            expiry=f"{payment_method.card.exp_month}/{payment_method.card.exp_year}",
            brand=payment_method.card.brand,
            name=payment_method.billing_details.name,
        )
        return payment

    return 204, None


@router.get(
    "/invoices",
    response={200: InvoicesOut, 403: Error, 500: Error},
)
def get_invoices(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id != user.id:
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


@router.post(
    "/plan/",
    response={200: CurrentPlanOut, 403: Error, 422: Error, 500: Error},
)
def update_current_plan(request, payload: UpdatePlanIn):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)
    current_tier = Tier.objects.get(id__exact=team.tier.id)
    new_tier = Tier.objects.get(id__exact=payload.tier_id)

    if user.team.owner_id != user.id:
        return 403, {"message": "Only owners can upgrade plans"}

    if team.tier.is_custom:
        return 422, {"message": "You can't change to a custom plan, contact us"}

    subscription = stripe.Subscription.retrieve(team.billing.subscription_id)

    # TODO support invoice billing check here
    if not subscription.default_payment_method and new_tier.id != 1:
        return 422, {"message": "No valid payment method"}

    if current_tier.id == new_tier:
        return 422, {"message": "You can't change to the same tier"}

    # Check they haven't exceeded limits for downgrading
    limits = calculate_limits(team)

    if new_tier.base_user_limit is not None and limits["users"] > new_tier.base_user_limit:
        return 422, {"message": "Too many users to switch to this plan"}

    if new_tier.base_project_limit is not None and limits["projects"] > new_tier.base_project_limit:
        return 422, {"message": "Too many projects to switch to this plan"}

    if new_tier.base_collaborator_limit is not None and limits["collaborators"] > new_tier.base_collaborator_limit:
        return 422, {"message": "Too many collaborators to switch to this plan"}

    if not subscription.default_payment_method and limits["storage"] > limits["storage_included_limit"]:
        return 422, {"message": "Storage exceeds included amount, and not payment method registered"}

    items = stripe.SubscriptionItem.list(subscription=team.billing.subscription_id, expand=["data.price.tiers"])

    # Get the current Stripe price Ids so we can update them
    storage_id = next((item["id"] for item in items if item.price["id"] == current_tier.stripe_storage_price_id), None)
    project_id = next((item["id"] for item in items if item.price["id"] == current_tier.stripe_project_price_id), None)
    base_id = next((item["id"] for item in items if item.price["id"] == current_tier.stripe_flat_price_id), None)
    user_id = next((item["id"] for item in items if item.price["id"] == current_tier.stripe_user_price_id), None)
    collaborator_id = next(
        (item["id"] for item in items if item.price["id"] == current_tier.stripe_collaborator_price_id), None
    )

    items = [
        {"id": base_id, "price": new_tier.stripe_flat_price_id, "quantity": 1},
        {"id": storage_id, "price": new_tier.stripe_storage_price_id},
    ]

    # Remove addons
    if project_id:
        items.append({"id": project_id, "deleted": True})

    if user_id:
        items.append({"id": user_id, "deleted": True})

    if collaborator_id:
        items.append({"id": collaborator_id, "deleted": True})

    stripe.Subscription.modify(team.billing.subscription_id, items=items)

    team.tier = new_tier

    team.save()

    return calculate_plan(team)


@router.get(
    "/plan",
    response={200: CurrentPlanOut, 204: None, 403: Error, 500: Error},
)
def get_current_plan(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id != user.id:
        return 403, {"message": "Only owners can view plan details"}

    return calculate_plan(team)


@router.get(
    "/plans",
    response={200: AllPlans, 403: Error, 500: Error},
)
def get_all_plans(request):
    user = request.auth
    tiers = Tier.objects.filter(is_custom=False)
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id != user.id:
        return 403, {"message": "Only owners can view plan details"}

    limits = calculate_limits(team)
    prices = list()

    for tier in tiers:
        # Check they haven't exceeded limits for downgrading
        if (
            tier.id != team.tier_id
            and (tier.base_user_limit is None or limits["users"] <= tier.base_user_limit)
            and (tier.base_project_limit is None or limits["projects"] <= tier.base_project_limit)
            and (tier.base_collaborator_limit is None or limits["collaborators"] <= tier.base_collaborator_limit)
        ):
            if tier.stripe_flat_price_id:
                price = stripe.Price.retrieve(tier.stripe_flat_price_id, expand=["tiers"])
                prices.append({"id": tier.id, "name": tier.name, "price": price.unit_amount})
            else:
                prices.append({"id": tier.id, "name": tier.name, "price": 0})

    return {"tiers": prices}


@router.get(
    "/addon-prices",
    response={200: AddonPrices, 422: Error, 403: Error, 500: Error},
)
def addonPrice(request):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id != user.id:
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

    return prices


@router.post(
    "/cancel/",
    response={200: None, 422: Error, 403: Error, 500: Error},
)
def cancel(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        if user.team.owner_id != user.id:
            return 403, {"message": "Only owners can cancel plans"}

        if not hasattr(team, "billing"):
            return 422, {"message": "No valid subscription to cancel. Try changing your plan"}

        res = stripe.Subscription.delete(team.billing.subscription_id)

        if res.status != "canceled":
            return 500, {"message": "There was an error cancelling, contact us at contact@gliff.ai"}

        team.billing.cancel_date = datetime.fromtimestamp(res.canceled_at, timezone.utc)
        team.billing.save()

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

        if user.team.owner_id != user.id:
            return 403, {"message": "Only owners can upgrade plans"}

        if team.tier.is_custom:
            return 422, {"message": "You can't have addons on a custom plan"}

        items = []

        addons = TierAddons.objects.filter(team=team).aggregate(
            users=Sum("additional_user_count"),
            projects=Sum("additional_project_count"),
            collaborators=Sum("additional_collaborator_count"),
        )

        subscription = stripe.Subscription.retrieve(team.billing.subscription_id)

        methods = stripe.Customer.list_payment_methods(team.billing.stripe_customer_id, type="card")

        if not methods.data or len(methods.data) == 0:
            return 422, {"message": "No valid payment method"}

        if team.tier.base_project_limit is not None and payload.projects > 0:
            # the user doesn't have unlimited projects
            projects = (addons["projects"] or 0) + payload.projects
            items.append(
                {
                    "price": team.tier.stripe_project_price_id,
                    "quantity": projects,
                    "id": get_user_price_id(team.tier.stripe_project_price_id, subscription),
                }
            )

        if payload.collaborators > 0:
            collaborators = (addons["collaborators"] or 0) + payload.collaborators
            items.append(
                {
                    "price": team.tier.stripe_collaborator_price_id,
                    "quantity": collaborators,
                    "id": get_user_price_id(team.tier.stripe_collaborator_price_id, subscription),
                }
            )

        if payload.users > 0:
            users = (addons["users"] or 0) + payload.users
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


# TODO coupons are added to subscriptions outside of this process now
@router.post("/create-checkout-session/", response={200: CheckoutSessionOut, 403: Error, 422: Error, 500: Error})
def create_auth_checkout_session(request):
    try:
        user = request.auth
        team = Team.objects.get(owner_id=user.id)
        tier = Tier.objects.get(id__exact=team.tier.id)

        if user.team.owner_id != user.id:
            return 403, {"message": "Only owners can add a payment method"}

        if not hasattr(team, "billing"):
            logger.error("User doesn't have billing information (this shouldn't happen)")
            return 422, {"message": "No valid subscription to upgrade."}

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="setup",
            customer=team.billing.stripe_customer_id,
            setup_intent_data={
                "metadata": {
                    "subscription_id": team.billing.subscription_id,
                },
            },
            success_url=settings.BASE_URL + "/billing?card_status=success",
            cancel_url=settings.BASE_URL + "/billing?card_status=error",
            metadata={"tier_id": tier.id, "tier_name": tier.name, "team_id": team.id},
            billing_address_collection="required",
            # If we need these we either need to add them manually thro Stripe or add our own form elements _somewhere_
            # allow_promotion_codes=True,
            # tax_id_collection={"enabled": True},
        )

        return {"id": session.id}
    except Exception as e:
        logger.error(str(e))
        return 500, {"message": str(e)}


#
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

    # Handle them completing checkout.
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Fulfill the purchase...
        complete_payment_registration(session)

    # if event["type"] == "":
    # TODO Handle invoice payments to update expiry date
    # TODO Handle cancellation hook?

    return 200


# We've got a new payment method, make it the default for the customer
def complete_payment_registration(session):
    try:
        logger.info(session)

        intent = stripe.SetupIntent.retrieve(session["setup_intent"])

        stripe.Customer.modify(
            session["customer"],
            invoice_settings={"default_payment_method": intent["payment_method"]},
        )

        return True
    except Exception as e:
        logger.error(e)
        return False
