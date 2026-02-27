from fastapi import FastAPI

from api.routes import approvals, policies, trips
from db.database import init_db

app = FastAPI(title="Travel & Logistics Agentic Platform", version="0.3.0")

app.include_router(trips.router)
app.include_router(approvals.router)
app.include_router(policies.router)


@app.on_event("startup")
async def on_startup():
    await init_db()
