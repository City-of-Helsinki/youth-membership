from graphql import GraphQLError


class CommonGraphQLError(GraphQLError):
    """GraphQLError that is not sent to Sentry."""


# Open city profile


class APINotImplementedError(CommonGraphQLError):
    """The functionality is not yet implemented"""


class InvalidEmailFormatError(CommonGraphQLError):
    """Email must be in valid email format"""


class ProfileDoesNotExistError(CommonGraphQLError):
    """Profile does not exist"""


class ProfileHasNoPrimaryEmailError(CommonGraphQLError):
    """Profile does not have a primary email address"""


class ProfileMustHaveOnePrimaryEmail(CommonGraphQLError):
    """Profile must have exactly one primary email"""


class TokenExpiredError(CommonGraphQLError):
    """Token has expired"""
