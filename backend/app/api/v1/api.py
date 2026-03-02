from fastapi import APIRouter
from backend.app.api.v1.endpoints import items, login, users, queues, tickets, modules, operators, reports, config

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(queues.router, prefix="/queues", tags=["queues"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
api_router.include_router(operators.router, prefix="/operators", tags=["operators"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
