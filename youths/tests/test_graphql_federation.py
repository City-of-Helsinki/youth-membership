from graphql_relay.node.node import to_global_id

from youths.tests.factories import YouthProfileFactory

FEDERATED_SCHEMA_QUERY = """
    {
        _service {
            sdl
        }
    }
"""

FEDERATED_PROFILES_QUERY = """
query($_representations: [_Any!]!) {
    _entities(representations: $_representations) {
        ... on ProfileNode {
            id
            youthProfile {
                id
                membershipNumber
            }
        }
    }
}
"""


def test_profile_node_gets_extended_properly(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    executed = anon_user_gql_client.execute(FEDERATED_SCHEMA_QUERY, context=request)
    assert (
        "extend type ProfileNode  implements Node "
        ' @key(fields: "id") {   id: ID! @external '
        in executed["data"]["_service"]["sdl"]
    )


def test_youth_profile_connection_schema_matches_federated_schema(
    rf, anon_user_gql_client
):
    request = rf.post("/graphql")

    executed = anon_user_gql_client.execute(FEDERATED_SCHEMA_QUERY, context=request)

    assert (
        "type YouthProfileNodeConnection {   pageInfo: PageInfo!   "
        "edges: [YouthProfileNodeEdge]!   count: Int!   totalCount: Int! }"
        in executed["data"]["_service"]["sdl"]
    )


def test_query_extended_profile_nodes(rf, user_gql_client, youth_profile):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)

    youth_profile_id = to_global_id("YouthProfileNode", youth_profile.id)
    profile_id = to_global_id("ProfileNode", youth_profile.id)
    variables = {"_representations": [{"id": profile_id, "__typename": "ProfileNode"}]}

    executed = user_gql_client.execute(
        FEDERATED_PROFILES_QUERY, variables=variables, context=request
    )

    assert executed["data"]["_entities"][0] == {
        "id": profile_id,
        "youthProfile": {
            "id": youth_profile_id,
            "membershipNumber": youth_profile.membership_number,
        },
    }
