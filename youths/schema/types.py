import django_filters
import graphene
from django.core.exceptions import PermissionDenied
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphene_django.types import DjangoObjectType
from graphene_federation import extend, external
from graphql_jwt.decorators import login_required

from common_utils.graphql import CountConnection

from ..enums import MembershipStatus, YouthLanguage
from ..models import AdditionalContactPerson, YouthProfile
from ..utils import user_is_admin

with override("en"):
    LanguageAtHome = graphene.Enum.from_enum(
        YouthLanguage, description=lambda e: e.label if e else ""
    )


MembershipStatusEnum = graphene.Enum.from_enum(
    MembershipStatus, description=lambda e: e.label if e else ""
)


class AdditionalContactPersonNode(DjangoObjectType):
    class Meta:
        model = AdditionalContactPerson
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
        )
        interfaces = (relay.Node,)


class ProfileFilter(django_filters.FilterSet):
    class Meta:
        model = YouthProfile
        fields = ("membership_number",)

    membership_number = django_filters.CharFilter(lookup_expr="icontains")


class YouthProfileNode(DjangoObjectType):
    class Meta:
        model = YouthProfile
        fields = (
            "id",
            "membership_number",
            "birth_date",
            "school_name",
            "school_class",
            "expiration",
            "language_at_home",
            "approver_first_name",
            "approver_last_name",
            "approver_phone",
            "approver_email",
            "approval_notification_timestamp",
            "approved_time",
            "photo_usage_approved",
            "additional_contact_persons",
        )

        interfaces = (relay.Node,)
        filterset_class = ProfileFilter
        connection_class = CountConnection

    profile = graphene.Field(
        "youths.schema.types.ProfileNode",
        description="Profile related to the youth profile",
    )

    language_at_home = LanguageAtHome(
        description="The language which is spoken in the youth's home.", required=True
    )
    membership_status = MembershipStatusEnum(
        description="Membership status based on expiration and approved_time fields",
        required=True,
    )
    renewable = graphene.Boolean(
        description="Tells if the membership is currently renewable or not",
        required=True,
    )

    def resolve_profile(self: YouthProfile, info, **kwargs):
        return self

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        user = info.context.user
        if node and (user_is_admin(user) or node.user == user):
            return node
        return None


@extend(fields="id")
class ProfileNode(DjangoObjectType):
    class Meta:
        model = YouthProfile
        fields = ("id",)
        interfaces = (relay.Node,)
        filterset_class = ProfileFilter
        connection_class = CountConnection

    id = external(relay.GlobalID())
    youth_profile = graphene.Field(
        YouthProfileNode, description="Youth Profile related to the Profile"
    )

    def resolve_youth_profile(self: YouthProfile, info, **kwargs):
        return self

    @login_required
    def __resolve_reference(self, info, **kwargs):
        profile = graphene.Node.get_node_from_global_id(
            info, self.id, only_type=ProfileNode
        )
        if not profile:
            return None

        user = info.context.user
        if user == profile.user or user_is_admin(user):
            return profile
        else:
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        user = info.context.user
        if node and (user_is_admin(user) or node.user == user):
            return node
        return None
