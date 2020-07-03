import graphene
from django.utils.translation import ugettext_lazy as _
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay.node.node import from_global_id

from ..models import YouthProfile
from .types import YouthProfileType


class Query(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    youth_profile = graphene.Field(
        YouthProfileType,
        profile_id=graphene.ID(),
        description="Get a youth profile by youth profile ID.\n\n**NOTE:** Currently this requires `superuser` "
        "credentials. This is going to be changed at one point so that service-specific staff "
        "credentials and service type are used, just like the rest of the admin-type queries.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    youth_profile_by_approval_token = graphene.Field(
        YouthProfileType,
        token=graphene.String(),
        description="Get a youth profile by approval token. \n\nDoesn't require authentication.\n\nPossible "
        "error codes:\n\n* `TODO`",
    )

    @login_required
    def resolve_youth_profile(self, info, **kwargs):
        profile_id = kwargs.get("profile_id")

        if profile_id is not None and not info.context.user.is_superuser:
            raise GraphQLError(_("Query by id not allowed for regular users."))

        if info.context.user.is_superuser:
            return YouthProfile.objects.get(pk=from_global_id(profile_id)[1])
        return YouthProfile.objects.get(user=info.context.user)

    def resolve_youth_profile_by_approval_token(self, info, **kwargs):
        return YouthProfile.objects.get(approval_token=kwargs.get("token"))
