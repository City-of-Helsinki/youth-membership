import json
from pathlib import PurePath


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
