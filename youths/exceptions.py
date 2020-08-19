# Youth Profile
from common_utils.exceptions import CommonGraphQLError


class ApproverEmailCannotBeEmptyForMinorsError(CommonGraphQLError):
    """Approver email is required for youth under 18 years old"""


class CannotCreateYouthProfileIfUnder13YearsOldError(CommonGraphQLError):
    """Under 13 years old cannot create youth profile"""


class CannotRenewYouthProfileError(CommonGraphQLError):
    """Youth profile is already renewed or not yet in the next renew window"""


class CannotSetPhotoUsagePermissionIfUnder15YearsError(CommonGraphQLError):
    """A youth cannot set photo usage permission by himself if he is under 15 years old"""
