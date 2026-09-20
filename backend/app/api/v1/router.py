from fastapi import APIRouter

from app.api.v1 import auth, health, ops, responders, sos, sync, volunteers, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sos.router)
api_router.include_router(ops.router)
api_router.include_router(sync.router)
api_router.include_router(health.router)
api_router.include_router(volunteers.router)
api_router.include_router(responders.router)
api_router.include_router(ws.router)
