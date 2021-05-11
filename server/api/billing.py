from ninja import Router
import stripe

# from pydantic import typing

from myauth.models import Tier
from server.api.schemas import CheckoutSessionIn, CheckoutSessionOut, Error

stripe.api_key = "dadsfsr"  # Temp
endpoint_secret = "whsec_bN6gqLZhC1MP0aFOkMj22i6QOsrivE6I"  # Temp

router = Router()

YOUR_DOMAIN = "http://localhost:3000/signup"


@router.post(
    "/create-checkout-session",
    response={200: CheckoutSessionOut, 409: Error},
)
def create_checkout_session(request, payload: CheckoutSessionIn):
    tier = Tier.objects.get(id__exact=payload.tier_id)
    user = request.auth

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            client_reference_id=user.id,
            customer_email=user.email,
            line_items=[
                {"price": tier.stripe_price_id},
            ],
            mode="subscription",
            success_url=YOUR_DOMAIN + "?paid=true",
            cancel_url=YOUR_DOMAIN + "?canceled=true",
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

    print("Got valid webhook")
    print(event)
    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Fulfill the purchase...
        print(session)

    # Passed signature verification
    return 200
