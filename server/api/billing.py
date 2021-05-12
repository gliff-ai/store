from datetime import datetime, timezone
from django.conf import settings

from ninja import Router
import stripe

from myauth.models import Tier, Team, Billing
from server.api.schemas import CheckoutSessionIn, CheckoutSessionOut, Error

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

router = Router()


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
            print("we shouldn't create_checkout_session for a free plan?!")
            return 409, {"message": "Can't pay for a free tier"}

        # By default, just charge the flat rate
        line_items = [{"price": tier.stripe_flat_price_id, "quantity": 1}]

        # We can also add a Storage price
        if tier.stripe_storage_price_id is not None:
            line_items.append({"price": tier.stripe_storage_price_id})

        # And seats
        if tier.stripe_seat_price_id is not None:
            line_items.append({"price": tier.stripe_seat_price_id})

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
        return 400, {"message": "Invalid Payload"}
    except KeyError as e:
        return 400, {"message": "No Signature"}
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
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
            start_date=datetime.fromtimestamp(
                subscription["current_period_start"], timezone.utc
            ),
            renewal_date=datetime.fromtimestamp(
                subscription["current_period_end"], timezone.utc
            ),
            team_id=metatdata.team_id,
            subscription_id=subscription["id"],
        )

        billing.save()

        return True
    except Exception as e:
        print(e)
        return False
