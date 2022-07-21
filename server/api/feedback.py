from django.utils import timezone
from myauth.models import UserFeedback
from django.db.models import Q
from .schemas import Error, CreateUserFeedbackSchema, FieldCreatedSchema
from loguru import logger
from ninja import Router

router = Router()


@router.post("/", response={200: FieldCreatedSchema, 403: Error, 500: Error})
def create_feedback(request, payload: CreateUserFeedbackSchema):
    user = request.auth

    try:
        userfeedback = UserFeedback.objects.create(user=user, rating=payload.rating, comment=payload.comment)
        return {"id": userfeedback.id}
    except Exception as e:
        logger.error(e)


@router.get("/", response={200: bool, 403: Error, 500: Error})
def can_request_feedback(request):
    user = request.auth

    try:
        # feedback collected in the last 30 days
        feedback = UserFeedback.objects.filter(
            Q(user_id=user.id) & Q(date__gte=timezone.now() + timezone.timedelta(days=30))
        )
        if len(feedback) == 0:
            return True
    except Exception as e:
        logger.error(e)
    return False
