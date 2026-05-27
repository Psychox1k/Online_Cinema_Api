from fastapi import FastAPI
from routes import accounts_router
from routes import profiles_router
from routes import movies_router
from routes import genres_router
from routes import stars_router
from routes import directors_router
app = FastAPI(title="Online Cinema API")


api_version_prefix = "/api/v1/cinema"

app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"])
app.include_router(movies_router, prefix=f"{api_version_prefix}/movies", tags=["movies"])
app.include_router(directors_router, prefix=f"{api_version_prefix}/directors", tags=["directors"])
app.include_router(stars_router, prefix=f"{api_version_prefix}/stars", tags=["stars"])
app.include_router(genres_router, prefix=f"{api_version_prefix}/genres", tags=["genres"])


@app.get("/")
def read_root():
    return {"status": "ok"}