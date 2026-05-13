from fastapi import FastAPI

from src.internhunter.api.routes.demo_routes import router as demo_router

app = FastAPI(
    title="InternHunter MVP API",
    version="0.1.0",
    description="Minimal local demo API for job search and resume matching.",
)

app.include_router(demo_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "InternHunter MVP API"}
