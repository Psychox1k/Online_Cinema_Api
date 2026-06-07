from fastapi import FastAPI, Depends
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from config.dependencies import get_current_username
from routes import accounts_router
from routes import profiles_router
from routes import movies_router
from routes import genres_router
from routes import stars_router
from routes import directors_router
from routes import notifications_router
from routes import orders_router
from routes import carts_router
app = FastAPI(
    title="Online Cinema API",
    description="REST API for managing movies, users, orders and shopping carts",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)


api_version_prefix = "/api/v1/cinema"

app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"])
app.include_router(movies_router, prefix=f"{api_version_prefix}/movies", tags=["movies"])
app.include_router(directors_router, prefix=f"{api_version_prefix}/directors", tags=["directors"])
app.include_router(stars_router, prefix=f"{api_version_prefix}/stars", tags=["stars"])
app.include_router(genres_router, prefix=f"{api_version_prefix}/genres", tags=["genres"])
app.include_router(notifications_router, prefix=f"{api_version_prefix}/notifications", tags=["notifications"])
app.include_router(carts_router, prefix=f"{api_version_prefix}/carts", tags=["carts"])
app.include_router(orders_router, prefix=f"{api_version_prefix}/orders", tags=["orders"])


@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Online Cinema API - Swagger UI"
    )

@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(get_current_username)):
    return get_openapi(
        title="Online Cinema API",
        version="1.0.0",
        routes=app.routes,
    )