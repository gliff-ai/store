from ninja import Schema
from ninja.orm import create_schema
from myauth.models import User, UserProfile, Tier, Team

TierSchema = create_schema(Tier)


class Error(Schema):
    message: str


class UserProfileIn(Schema):
    name: str
    team_id: int = None
    recovery_key: str = "TEMP"


class TeamSchema(Schema):
    id: int
    owner_id: int
    tier: TierSchema


class UserProfileOut(Schema):
    id: int
    name: str
    team: TeamSchema


class CheckoutSessionIn(Schema):
    tier_id: int


class CheckoutSessionOut(Schema):
    id: str
