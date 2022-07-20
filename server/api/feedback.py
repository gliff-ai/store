from myauth.models import UserFeedback
from .schemas import Error, UserFeedbackSchema, FieldCreatedSchema
from loguru import logger
from ninja import Router

router = Router()


@router.post("/", response={200: FieldCreatedSchema, 403: Error, 500: Error})
def create_userfeedback(request, payload: UserFeedbackSchema):
    user = request.auth

    try:
        userfeedback = UserFeedback.objects.create(rating=payload.rating, comment=payload.comment)
        return {"id": userfeedback.id}
    except Exception as e:
        logger.error(e)
