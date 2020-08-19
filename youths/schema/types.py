from datetime import date

import graphene
from django.utils import timezone
from django.utils.translation import override
from graphene import relay
from graphene_django.types import DjangoObjectType

from ..enums import YouthLanguage
from ..models import AdditionalContactPerson, calculate_expiration, YouthProfile

with override("en"):
    LanguageAtHome = graphene.Enum.from_enum(
        YouthLanguage, description=lambda e: e.label if e else ""
    )


class MembershipStatus(graphene.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    RENEWING = "renewing"


# @extend(fields="id")
# TODO Add separete ProfileNode with id for extending the open-city-profile profile (like in berth-reservations)


class YouthProfileType(DjangoObjectType):

    membership_number = graphene.String(
        source="membership_number", description="Youth's membership number"
    )

    language_at_home = LanguageAtHome(
        source="language_at_home",
        description="The language which is spoken in the youth's home.",
    )
    membership_status = MembershipStatus(
        description="Membership status based on expiration and approved_time fields"
    )
    renewable = graphene.Boolean(
        description="Tells if the membership is currently renewable or not"
    )

    class Meta:
        model = YouthProfile
        exclude = ("approval_token", "language_at_home")

    def resolve_renewable(self, info, **kwargs):
        return bool(self.approved_time) and self.expiration != calculate_expiration(
            date.today()
        )

    def resolve_membership_status(self, info, **kwargs):
        if self.expiration <= date.today():
            return MembershipStatus.EXPIRED
        elif self.approved_time and self.approved_time <= timezone.now():
            # Status RENEWING implemented naively. Calculates the expiration for the existing approval time and checks
            # if expiration is set explicitly => status == EXPIRED. If expiration is greater than calculated expiration
            # for the current period, do one of the following:
            #
            # 1. If calculated expiration for approval time is in the past, membership is considered expired
            # 2. Otherwise status of the youth profile is RENEWING
            approved_period_expiration = calculate_expiration(self.approved_time.date())
            if self.expiration < approved_period_expiration:
                return MembershipStatus.EXPIRED
            elif self.expiration > approved_period_expiration:
                if date.today() <= approved_period_expiration:
                    return MembershipStatus.RENEWING
                else:
                    return MembershipStatus.EXPIRED
            return MembershipStatus.ACTIVE
        return MembershipStatus.PENDING


class AdditionalContactPersonNode(DjangoObjectType):
    class Meta:
        model = AdditionalContactPerson
        interfaces = (relay.Node,)
