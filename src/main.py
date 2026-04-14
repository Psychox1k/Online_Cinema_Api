from fastapi import FastAPI

app = FastAPI(title="Online Cinema API")

@app.get("/")
def read_root():
    return {"status": "ok"}