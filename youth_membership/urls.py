from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from common_utils.views import SentryGraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("social_django.urls", namespace="social")),
    path("helusers_auth/", include("helusers.urls", namespace="helusers")),
    path(
        "graphql/",
        csrf_exempt(
            SentryGraphQLView.as_view(
                graphiql=settings.ENABLE_GRAPHIQL or settings.DEBUG
            )
        ),
    ),
    path("gdpr/", include("youths.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#
# Kubernetes liveness & readiness probes
#
def healthz(*args, **kwargs):
    return HttpResponse(status=200)


def readiness(*args, **kwargs):
    return HttpResponse(status=200)


urlpatterns += [path("healthz", healthz), path("readiness", readiness)]
