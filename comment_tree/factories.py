from types import NoneType
from typing import NewType

import sqlalchemy.ext.asyncio as sa
from fastapi import FastAPI

from comment_tree.api.root_router import root_router
from comment_tree.authorization.authorization_service import AuthorizationService
from comment_tree.authorization.jwt_service import JwtService
from comment_tree.env import Env
from comment_tree.exceptions import add_exception_handler
from comment_tree.postgres.storage import Storage
from comment_tree.scopes.guest_scope import GuestService
from comment_tree.service_provider.fastapi_helpers import app_set_service_provider
from comment_tree.service_provider.service_factory import ServiceFactories
from comment_tree.service_provider.service_provider import ServiceProvider

CreateTablesFlag = NewType("CreateTablesFlag", NoneType)

factories = ServiceFactories()


@factories.add(Env)
def parse_env() -> Env:
    return Env()


@factories.add(FastAPI)
def build_fastapi(service_provider: ServiceProvider) -> FastAPI:
    async def on_startup():
        await service_provider.solve_all_async()

    app = FastAPI(on_startup=[on_startup])
    app_set_service_provider(app, service_provider)
    app.include_router(root_router)
    add_exception_handler(app)

    return app


@factories.add(Storage)
def build_storage(env: Env) -> Storage:
    return Storage(
        sa.create_async_engine(
            env.postgres_uri,
            echo=env.debug,
            future=True,
        )
    )


@factories.add(JwtService)
def build_jwt_token_service(env: Env) -> JwtService:
    return JwtService(env.jwt_secret_key)


@factories.add(AuthorizationService)
def build_authorizer(storage: Storage, jwt_service: JwtService) -> AuthorizationService:
    return AuthorizationService(storage, jwt_service)


@factories.add(GuestService)
def build_guesthouse(
    authorizer: AuthorizationService, storage: Storage
) -> GuestService:
    return GuestService(authorizer, storage)


@factories.add(CreateTablesFlag)
async def create_tables(storage: Storage):
    await storage.create_all()
