import json
from pathlib import PurePath

from crum import get_current_request
from django.conf import settings


def read_json_file(main: str, *args: str) -> dict:
    """Read and return the JSON content from a file.

    :param main: Path to which the JSON is relatively located (e.g. `__file__`)
    :param args: Parts of the path ending with the file (e.g. `"response", "r.json"`)
    :return: Dict containing file's JSON content.
    """
    path = PurePath(main).parent.joinpath(*args)
    with open(path.as_posix(), "r") as f:
        content = json.loads(f.read())
    return content


def get_original_client_ip():
    client_ip = None

    request = get_current_request()
    if request:
        if settings.USE_X_FORWARDED_FOR:
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded_for.split(",")[0] or None

        if not client_ip:
            client_ip = request.META.get("REMOTE_ADDR")

    return client_ip
