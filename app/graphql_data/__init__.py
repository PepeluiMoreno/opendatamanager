# app/graphql_data — Dynamic GraphQL API for datasets
#
# Exposes a second GraphQL endpoint at /graphql/data (separate from the
# management API at /graphql which uses Strawberry).
#
# This module uses graphql-core directly, which gives full control over
# runtime schema construction — something Strawberry cannot do cleanly
# because it resolves types at import time via Python decorators.
#
# Entry points:
#   engine.rebuild(db)  — rebuild the live schema from current datasets in DB
#   router.router       — FastAPI router to mount at /graphql/data
