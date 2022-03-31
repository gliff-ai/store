from typing import List, Optional
from ninja import Schema
from ninja.orm import create_schema
from pydantic import validator, typing, conint

from myauth.models import Tier

TierSchema = create_schema(Tier)


class PluginSchema(Schema):
    type: str
    name: str
    url: str
    products: str
    enabled: bool
    collection_uids: Optional[List[str]] = None


class PluginCreated(Schema):
    id: int


class TrustedServiceSchema(PluginSchema):
    username: str


class TrustedServiceCreated(Schema):
    id: int


class Error(Schema):
    message: str


class UserProfileIn(Schema):
    name: str
    team_id: int = None
    recovery_key: str
    invite_id: str = None
    accepted_terms_and_conditions: bool = False
    tier_id: int = None


class TeamSchema(Schema):
    id: int
    name: str
    owner_id: int
    tier: TierSchema
    usage: int


class UserProfileOut(Schema):
    @validator("email_verified")
    def cast_verified_date_to_bool(cls, verified_date):
        return verified_date is not None

    id: int
    name: str
    email: str
    email_verified: typing.Any  # we cast this to a bool
    is_collaborator: bool
    is_trusted_service: bool
    team: TeamSchema


class InvitedProfileOut(Schema):
    email: str
    sent_date: typing.Any  # Date?!
    is_collaborator: bool


class TeamsOut(Schema):
    profiles: List[UserProfileOut]
    pending_invites: List[InvitedProfileOut]


class CheckoutSessionIn(Schema):
    tier_id: int
    user_id: int
    user_email: str


class CheckoutSessionOut(Schema):
    id: str


class InviteCreated(Schema):
    id: str


class InviteOut(Schema):
    email: str
    team_id: str


class CreateInvite(Schema):
    email: str


class AccountRecovery(Schema):
    email: str


class AccountRecoveryOut(Schema):
    recovery_key: str


class AddonIn(Schema):
    users: conint(ge=0) = 0
    projects: conint(ge=0) = 0
    collaborators: conint(ge=0) = 0


class Addon(Schema):
    quantity: int = 0
    name: str = None
    price_per_unit: int


class Addons(Schema):
    project: Addon = None
    user: Addon = None
    collaborator: Addon = None


class AddonPrices(Schema):
    project: int = None
    user: int = None
    collaborator: int = None


class CurrentPlanOut(Schema):
    tier_name: str
    tier_id: int
    current_period_end: int
    current_period_start: int
    cancel_date: int = None
    trial_end: int = None
    base_price: int = None
    addons: Addons
    billed_usage: int
    billed_usage_gb_price: int
    is_custom: bool
    is_trial: bool


class Plan(Schema):
    id: int
    name: str
    price: int


class AllPlans(Schema):
    tiers: List[Plan]


class UpdatePlanIn(Schema):
    tier_id: int


class CurrentLimitsOut(Schema):
    has_billing: bool
    tier_name: str
    tier_id: int
    users_limit: Optional[conint(ge=0)] = 0
    projects_limit: Optional[conint(ge=0)] = 0
    collaborators_limit: Optional[conint(ge=0)] = 0
    users: Optional[conint(ge=0)] = 0
    projects: Optional[conint(ge=0)] = 0
    collaborators: Optional[conint(ge=0)] = 0
    storage: Optional[conint(ge=0)] = 0
    storage_included_limit: Optional[conint(ge=0)] = 0


class Invoice(Schema):
    id: str
    amount_due: int
    amount_paid: int
    created: int
    invoice_pdf: str
    number: str
    paid: bool
    status: str


class InvoicesOut(Schema):
    invoices: List[Invoice]


class PaymentOut(Schema):
    number: str
    expiry: str
    brand: str
    name: str
