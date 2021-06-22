import requests
import json
from ninja import Router
from loguru import logger
from myauth.models import UserProfile, Tier, Team
from .schemas import UserProfileIn, UserProfileOut, Error

router = Router()


# Submit a Sentry event
@router.post("/", response={200: "", 409: Error})
def post_event(request):
    logger.info("POST request on Sentry tunnel endpoint")
    logger.debug(request.body.decode("utf-8").split("\n"))
    [envelopeHeader, itemHeader, item] = request.body.decode("utf-8").split("\n")
    envelopeHeader = json.loads(envelopeHeader)
    itemHeader = json.loads(itemHeader)
    item = json.loads(item)

    try:
        dsn = envelopeHeader["dsn"][:-8:]  # get dsn url
        project_id = envelopeHeader["dsn"][-7::]  # get project id
        url = f"{dsn}/api/{project_id}/envelope/"
        logger.info(f"Attempting to send event to {url}")
        r = requests.post(url, data=request.body)
        status_code = r.status_code
        if status_code >= 400 and status_code < 500:
            message = f"Failed to tunnel frontend sentry event - received {status_code}"
            logger.error(message)
        elif status_code >= 200 and status_code < 300:
            message = f"Successfully tunnelled frontend sentry event - received {status_code}"
            logger.success(message)
        else:
            message = f"Unknown outcome of tunnelling frontend sentry event - received {status_code}"
            logger.warning(message)
    except Exception as e:
        status_code = 400
        message = e
        logger.warning(f"Received Exception {e}")

    return status_code, {"message": message}
