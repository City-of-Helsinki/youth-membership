from common_utils.views import GDPRAPIView
from youths.models import YouthProfile


class YouthProfileGDPRAPIView(GDPRAPIView):
    model = YouthProfile
