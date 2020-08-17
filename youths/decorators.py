from graphql_jwt.decorators import user_passes_test

from youths.utils import user_is_admin

staff_required = user_passes_test(lambda u: user_is_admin(u))
