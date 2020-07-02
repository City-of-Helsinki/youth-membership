import pytest


@pytest.fixture(autouse=True)
def autouse_db(db):
    pass
