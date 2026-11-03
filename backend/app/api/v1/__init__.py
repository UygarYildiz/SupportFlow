from fastapi import APIRouter

from app.api.v1 import auth, orders, proposals, runs, setup, tickets, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tickets.router)
api_router.include_router(orders.router)
api_router.include_router(runs.router)
api_router.include_router(proposals.router)
