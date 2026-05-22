from fastapi import FastAPI
from routes import accounts_router
from routes import profiles_router
app = FastAPI(title="Online Cinema API")


api_version_prefix = "/api/v1"

app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"])

@app.get("/")
def read_root():
    return {"status": "ok"}