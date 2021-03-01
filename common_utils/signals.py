from django.dispatch import Signal

token_authentication_successful = Signal(providing_args=["user", "request"])
token_authentication_failed = Signal(providing_args=["error", "request"])
