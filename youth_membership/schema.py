import graphene
from graphene_federation import build_schema

import youths.schema


class Query(youths.schema.Query, graphene.ObjectType):
    pass


class Mutation(youths.schema.Mutation, graphene.ObjectType):
    pass


schema = build_schema(Query, Mutation)
