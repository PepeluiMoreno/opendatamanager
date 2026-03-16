"""
Schema principal de GraphQL.
"""
import strawberry
from app.graphql_api.queries import Query
from app.graphql_api.mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)
