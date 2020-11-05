import datetime
from functools import partial

import factory
from django.utils import timezone
from graphql_relay import to_global_id

from users.factories import UserFactory
from youths.models import AdditionalContactPerson, YouthProfile


class ProfileAPIResponse(factory.DictFactory):
    """Data returned from ProfileAPI.fetch_profile."""

    id = factory.Faker("uuid4", cast_to=partial(to_global_id, "ProfileNode"))


class MyProfileAPIResponse(ProfileAPIResponse):
    """Data returned from ProfileAPI.fetch_my_profile."""

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class ProfileAPITokenResponse(factory.DictFactory):
    """Data returned from ProfileAPI.create_temporary_access_token."""

    token = factory.Faker("uuid4", cast_to=str)
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + datetime.timedelta(days=2)
    )


class YouthProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    school_name = "Kontulan Alakoulu"
    school_class = "1A"
    approver_email = factory.Faker("email")
    birth_date = "2002-02-02"
    approval_token = factory.Faker("uuid4")

    class Meta:
        model = YouthProfile


class AdditionalContactPersonDictFactory(factory.DictFactory):
    firstName = factory.Faker("first_name")  # noqa: N815
    lastName = factory.Faker("last_name")  # noqa: N815
    phone = factory.Faker("phone_number")
    email = factory.Faker("email")


class AdditionalContactPersonFactory(factory.django.DjangoModelFactory):
    youth_profile = factory.SubFactory(YouthProfileFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = factory.Faker("phone_number")
    email = factory.Faker("email")

    class Meta:
        model = AdditionalContactPerson
