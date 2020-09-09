FEDERATED_SCHEMA_QUERY = """
    {
        _service {
            sdl
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


def test_profile_connection_schema_matches_federated_schema(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    executed = anon_user_gql_client.execute(FEDERATED_SCHEMA_QUERY, context=request)

    assert (
        "type ProfileNodeConnection {   pageInfo: PageInfo!   "
        "edges: [ProfileNodeEdge]!   count: Int!   totalCount: Int! }"
        in executed["data"]["_service"]["sdl"]
    )
