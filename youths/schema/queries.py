import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required

from ..decorators import staff_required
from ..models import YouthProfile
from .types import ProfileNode


class Query(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    youth_profile = graphene.relay.Node.Field(
        ProfileNode,
        description="Get a youth profile by youth profile ID.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    youth_profile_by_approval_token = graphene.Field(
        ProfileNode,
        token=graphene.String(),
        description="Get a youth profile by approval token. \n\nDoesn't require authentication.\n\nPossible "
        "error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    youth_profiles = DjangoFilterConnectionField(
        ProfileNode,
        description="Search for profiles. The results are filtered based on the given parameters. The results are "
        "paged using Relay.\n\nRequires `staff` credentials for the service given in "
        "`serviceType`. The profiles must have an active connection to the given `serviceType`, otherwise "
        "they will not be returned.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    my_youth_profile = graphene.Field(
        ProfileNode,
        description="Get the youth profile belonging to the currently authenticated user.\n\n"
        "Requires authentication.\n\nPossible error codes:\n\n* `TODO`",
    )

    @login_required
    def resolve_my_youth_profile(self, info, **kwargs):
        return YouthProfile.objects.filter(user=info.context.user).first()

    @staff_required
    def resolve_youth_profiles(self, info, **kwargs):
        return YouthProfile.objects.all()

    def resolve_youth_profile_by_approval_token(self, info, **kwargs):
        return YouthProfile.objects.get(approval_token=kwargs.get("token"))
