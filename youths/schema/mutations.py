from datetime import date

import graphene
from django.db import transaction
from graphene import relay
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay.node.node import from_global_id, to_global_id

from common_utils.exceptions import ProfileDoesNotExistError
from common_utils.profile import ProfileAPI

from ..decorators import staff_required
from ..exceptions import (
    ApproverEmailCannotBeEmptyForMinorsError,
    CannotCreateYouthProfileIfUnder13YearsOldError,
    CannotRenewYouthProfileError,
    CannotSetPhotoUsagePermissionIfUnder15YearsError,
)
from ..models import calculate_expiration, YouthProfile
from ..utils import (
    calculate_age,
    create_or_update_contact_persons,
    delete_contact_persons,
)
from .types import LanguageAtHome, YouthProfileNode

# from django_ilmoitin.utils import send_notification
# from ..enums import NotificationType

# from profiles.decorators import staff_required
# from profiles.models import Email, Profile

# from common_utils.exceptions import ProfileHasNoPrimaryEmailError


def create_youth_profile(input, user, profile_id):
    contact_persons_to_create = input.pop("add_additional_contact_persons", [])

    youth_profile = YouthProfile.objects.create(user=user, id=profile_id, **input)
    create_or_update_contact_persons(youth_profile, contact_persons_to_create)

    return youth_profile


def update_youth_profile(input, youth_profile, manage_permission=False):
    """Update the given youth profile.

    :param manage_permission: Calling user has manage permission on youth membership service.
    """
    contact_persons_to_create = input.pop("add_additional_contact_persons", [])
    contact_persons_to_update = input.pop("update_additional_contact_persons", [])
    contact_persons_to_delete = input.pop("remove_additional_contact_persons", [])

    resend_request_notification = input.pop("resend_request_notification", False)

    if "photo_usage_approved" in input and not manage_permission:
        # Disable setting photo usage by themselves for youths under 15 years old (allowed for staff).
        # Check for birth date given in input or birth date persisted in the db.
        if (
            "birth_date" in input and calculate_age(input["birth_date"]) < 15
        ) or calculate_age(youth_profile.birth_date) < 15:
            raise CannotSetPhotoUsagePermissionIfUnder15YearsError(
                "Cannot set photo usage permission if under 15 years old"
            )

    for field, value in input.items():
        setattr(youth_profile, field, value)
    if resend_request_notification:
        youth_profile.make_approvable()

    youth_profile.save()

    create_or_update_contact_persons(youth_profile, contact_persons_to_create)
    create_or_update_contact_persons(youth_profile, contact_persons_to_update)
    delete_contact_persons(youth_profile, contact_persons_to_delete)

    return youth_profile


def cancel_youth_profile(youth_profile, input):
    expiration = input.get("expiration")

    youth_profile.expiration = expiration or date.today()
    youth_profile.save()

    return youth_profile


def renew_youth_profile(youth_profile):
    next_expiration = calculate_expiration(date.today())
    if youth_profile.expiration == next_expiration:
        raise CannotRenewYouthProfileError(
            "Cannot renew youth profile. Either youth profile is already renewed or not yet in the next "
            "renew window."
        )
    youth_profile.expiration = next_expiration

    if calculate_age(youth_profile.birth_date) >= 18:
        youth_profile.set_approved()
    else:
        youth_profile.make_approvable()

    youth_profile.save()
    return youth_profile


class CreateAdditionalContactPersonInput(graphene.InputObjectType):
    first_name = graphene.String(description="First name.", required=True)
    last_name = graphene.String(description="Last name.", required=True)
    phone = graphene.String(description="Phone number.", required=True)
    email = graphene.String(description="Email address.", required=True)


class UpdateAdditionalContactPersonInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    phone = graphene.String(description="Phone number.")
    email = graphene.String(description="Email address.")


# Abstract base fields
class YouthProfileFields(graphene.InputObjectType):
    school_name = graphene.String(description="The youth's school name.")
    school_class = graphene.String(description="The youth's school class.")
    language_at_home = LanguageAtHome(
        description="The language which is spoken in the youth's home."
    )
    approver_first_name = graphene.String(
        description="The youth's (supposed) guardian's first name."
    )
    approver_last_name = graphene.String(
        description="The youth's (supposed) guardian's last name."
    )
    approver_phone = graphene.String(
        description="The youth's (supposed) guardian's phone number."
    )
    approver_email = graphene.String(
        description=(
            "The youth's (supposed) guardian's email address which will be used to send approval requests."
            "This field is required for youth under 18 years old."
        )
    )
    birth_date = graphene.Date(
        required=False,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )
    photo_usage_approved = graphene.Boolean(
        description=(
            "`true` if the youth is allowed to be photographed. Only youth over 15 years old can set this."
            "For youth under 15 years old this is set by the (supposed) guardian in the approval phase"
        )
    )
    add_additional_contact_persons = graphene.List(
        CreateAdditionalContactPersonInput,
        description="Add additional contact persons to youth profile.",
    )
    update_additional_contact_persons = graphene.List(
        UpdateAdditionalContactPersonInput,
        description="Update youth profile's additional contact persons.",
    )
    remove_additional_contact_persons = graphene.List(
        graphene.ID, description="Remove additional contact persons from youth profile."
    )


# Subset of abstract fields are required for creation
class CreateYouthProfileInput(YouthProfileFields):
    birth_date = graphene.Date(
        required=True,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )


class UpdateYouthProfileInput(YouthProfileFields):
    resend_request_notification = graphene.Boolean(
        description="If set to `true`, a new approval token is generated and a new email notification is sent to the"
        "approver's email address."
    )


class CreateYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.Argument(graphene.ID, required=True)
        youth_profile = CreateYouthProfileInput(required=True)
        profile_api_token = graphene.String(
            required=True, description="API token for Helsinki profile GraphQL API."
        )

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @staff_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")
        profile_api_token = input.get("profile_api_token")
        profile_id = from_global_id(input.get("id"))[1]
        profile_node_id = to_global_id("ProfileNode", profile_id)

        profile_api = ProfileAPI()
        profile_data = profile_api.fetch_profile(profile_api_token, profile_node_id)

        if not profile_data["id"]:
            raise ProfileDoesNotExistError("Profile does not exist")

        youth_profile = create_youth_profile(input_data, None, profile_id)
        youth_profile.set_approved(save=True)

        return CreateYouthProfileMutation(youth_profile=youth_profile)


class CreateMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        youth_profile = CreateYouthProfileInput(required=True)
        profile_api_token = graphene.String(
            required=True, description="API token for Helsinki profile GraphQL API."
        )

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")
        profile_api_token = input.get("profile_api_token")
        profile_api = ProfileAPI()

        if calculate_age(input_data["birth_date"]) < 13:
            raise CannotCreateYouthProfileIfUnder13YearsOldError(
                "Under 13 years old cannot create youth profile"
            )

        if "photo_usage_approved" in input_data:
            # Disable setting photo usage by themselves for youths under 15 years old
            if calculate_age(input_data["birth_date"]) < 15:
                raise CannotSetPhotoUsagePermissionIfUnder15YearsError(
                    "Cannot set photo usage permission if under 15 years old"
                )

        profile_data = profile_api.fetch_my_profile(profile_api_token)

        if not profile_data["id"]:
            raise ProfileDoesNotExistError("Profile does not exist")

        youth_profile = create_youth_profile(
            input_data, info.context.user, from_global_id(profile_data["id"])[1]
        )

        if calculate_age(youth_profile.birth_date) >= 18:
            youth_profile.set_approved()
        else:
            if not youth_profile.approver_email:
                raise ApproverEmailCannotBeEmptyForMinorsError(
                    "Approver email is required for youth under 18 years old"
                )

            # Create and save a temporary Helsinki profile access token for later use.
            temp_token = profile_api.create_temporary_access_token(profile_api_token)
            youth_profile.profile_access_token = temp_token["token"]
            youth_profile.profile_access_token_expiration = temp_token["expires_at"]
            youth_profile.save(
                update_fields=[
                    "profile_access_token",
                    "profile_access_token_expiration",
                ]
            )

            youth_profile.make_approvable()
        youth_profile.save()

        return CreateMyYouthProfileMutation(youth_profile=youth_profile)


class UpdateYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.Argument(graphene.ID, required=True)
        youth_profile = UpdateYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @staff_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")

        youth_profile = YouthProfile.objects.get(pk=from_global_id(input.get("id"))[1])
        youth_profile = update_youth_profile(
            input_data, youth_profile, manage_permission=True
        )
        return UpdateYouthProfileMutation(youth_profile=youth_profile)


class UpdateMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        youth_profile = UpdateYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")

        youth_profile = YouthProfile.objects.get(user=info.context.user)
        youth_profile = update_youth_profile(input_data, youth_profile)
        return UpdateMyYouthProfileMutation(youth_profile=youth_profile)


class RenewYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.Argument(graphene.ID, required=True)

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @staff_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_profile = YouthProfile.objects.get(pk=from_global_id(input.get("id"))[1])
        youth_profile = renew_youth_profile(youth_profile)

        return RenewYouthProfileMutation(youth_profile=youth_profile)


class RenewMyYouthProfileMutation(relay.ClientIDMutation):
    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_profile = YouthProfile.objects.get(user=info.context.user)
        youth_profile = renew_youth_profile(youth_profile)
        return RenewMyYouthProfileMutation(youth_profile=youth_profile)


class ApproveYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        approval_token = graphene.String(
            required=True,
            description="This is the token with which a youth profile may be fetched for approval purposes.",
        )
        approval_data = YouthProfileFields(
            required=True,
            description="The youth profile data to approve. This may contain modifications done by the approver.",
        )

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_data = input.get("approval_data")
        token = input.get("approval_token")

        if not token:
            raise GraphQLError("Approval token cannot be empty.")

        contact_persons_to_create = youth_data.pop("add_additional_contact_persons", [])
        contact_persons_to_update = youth_data.pop(
            "update_additional_contact_persons", []
        )
        contact_persons_to_delete = youth_data.pop(
            "remove_additional_contact_persons", []
        )

        youth_profile = YouthProfile.objects.get(approval_token=token)

        for field, value in youth_data.items():
            setattr(youth_profile, field, value)

        # Additional contact persons
        create_or_update_contact_persons(youth_profile, contact_persons_to_create)
        create_or_update_contact_persons(youth_profile, contact_persons_to_update)
        delete_contact_persons(youth_profile, contact_persons_to_delete)

        # try:
        #     # TODO Should get the profile email through other methods
        #     email = youth_profile.profile.get_primary_email()
        # except Email.DoesNotExist:
        #     raise ProfileHasNoPrimaryEmailError(
        #         "Cannot send email confirmation, youth profile has no primary email address."
        #     )

        youth_profile.set_approved()
        youth_profile.save()
        # send_notification(
        #     email=email.email,
        #     notification_type=NotificationType.YOUTH_PROFILE_CONFIRMED.value,
        #     context={"youth_profile": youth_profile},
        #     language=youth_profile.profile.language if youth_profile.profile else "fi",
        #     # TODO Refactor should get the language of profile through other methods
        # )
        return ApproveYouthProfileMutation(youth_profile=youth_profile)


class CancelYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.Argument(
            graphene.ID, required=True, description="Profile id of the youth profile"
        )
        expiration = graphene.Date(
            description="Optional value for expiration. If missing or blank, current date will be used"
        )

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @staff_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_profile = YouthProfile.objects.get(pk=from_global_id(input.get("id"))[1])
        youth_profile = cancel_youth_profile(youth_profile, input)

        return CancelYouthProfileMutation(youth_profile=youth_profile)


class CancelMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        expiration = graphene.Date(
            description="Optional value for expiration. If missing or blank, current date will be used"
        )

    youth_profile = graphene.Field(YouthProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_profile = cancel_youth_profile(
            YouthProfile.objects.get(user=info.context.user), input,
        )

        return CancelMyYouthProfileMutation(youth_profile=youth_profile)


class Mutation(graphene.ObjectType):
    # TODO: Complete the description
    create_youth_profile = CreateYouthProfileMutation.Field(
        description="Creates a new youth profile and links it to the profile specified with the id argument.\n\n"
        "When the youth profile has been created, a notification is sent to the youth profile's approver "
        "whose contact information is given in the input.\n\nRequires elevated privileges.\n\nPossible error "
        "codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    create_my_youth_profile = CreateMyYouthProfileMutation.Field(
        description="Creates a new youth profile and links it to the currently authenticated user's profile.\n\n"
        "When the youth profile has been created, a notification is sent to the youth profile's approver "
        "whose contact information is given in the input.\n\nRequires authentication.\n\nPossible error "
        "codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    update_youth_profile = UpdateYouthProfileMutation.Field(
        description="Updates the youth profile which belongs to the profile specified in the id argument.\n\n"
        "The `resend_request_notification` parameter may be used to send a notification to the youth "
        "profile's approver whose contact information is in the youth profile.\n\nRequires elevated privileges."
        "\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    update_my_youth_profile = UpdateMyYouthProfileMutation.Field(
        description="Updates the youth profile which belongs to the profile of the currently authenticated user.\n\n"
        "The `resend_request_notification` parameter may be used to send a notification to the youth "
        "profile's approver whose contact information is in the youth profile.\n\nRequires authentication."
        "\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Update the description when we support the draft/published model for the youth profiles
    # TODO: Add the complete list of error codes
    renew_youth_profile = RenewYouthProfileMutation.Field(
        description="Renews the youth profile. Renewing can only be done once per season.\n\nRequires Authentication."
        "\n\nPossible error codes:\n\n* `CANNOT_RENEW_YOUTH_PROFILE_ERROR`: Returned if the youth profile is already "
        "renewed or not in the renew window\n\n* `TODO`"
    )
    # TODO: Update the description when we support the draft/published model for the youth profiles
    # TODO: Add the complete list of error codes
    renew_my_youth_profile = RenewMyYouthProfileMutation.Field(
        description="Renews the youth profile. Renewing can only be done once per season.\n\nRequires Authentication."
        "\n\nPossible error codes:\n\n* `CANNOT_RENEW_YOUTH_PROFILE_ERROR`: Returned if the youth profile is already "
        "renewed or not in the renew window\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    approve_youth_profile = ApproveYouthProfileMutation.Field(
        description="Fetches a youth profile using the given token, updates the data based on the given input data and"
        " approves the youth profile so that it is considered active. A confirmation is sent to the youth "
        "profile's email address after a successful approval.\n\nThe token is no longer valid after "
        "it's been used to approve the youth profile.\n\nRequires authentication.\n\nPossible error "
        "codes:\n\n* `PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR`: Returned if the youth profile doesn't have a "
        "primary email address.\n\n* `TODO`"
    )
    cancel_youth_profile = CancelYouthProfileMutation.Field(
        description="Cancels youth profile of given profile\n\nRequires Authentication."
    )
    cancel_my_youth_profile = CancelMyYouthProfileMutation.Field(
        description="Cancels youth profile for current user\n\nRequires Authentication."
    )
