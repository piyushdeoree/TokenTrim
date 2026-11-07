from fastapi import APIRouter, Depends

from app.api.routers import analysis, api_keys, auth, dashboard, models, projects, teams, usage
from app.core.rate_limit import general_limit

api_router = APIRouter(dependencies=[Depends(general_limit)])
for r in (auth.router, projects.router, analysis.router, usage.router, dashboard.router, api_keys.router,
          teams.router, models.router):
    api_router.include_router(r)
