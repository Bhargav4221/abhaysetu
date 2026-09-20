import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as public_health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.redis import close_redis, init_redis
from app.db.base import Base
from app.db.session import engine
from app.services.bootstrap import bootstrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("abhaysetu")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    import app.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    await bootstrap()
    logger.info("AbhaySetu backend started")
    yield
    await close_redis()


app = FastAPI(
    title="AbhaySetu",
    description="Emergency communication and response platform. Delivery states always reflect actual acknowledgements.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_health)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {
        "product": "AbhaySetu",
        "tagline": "One Emergency Message. Through Any Available Communication Path.",
        "api": settings.api_v1_prefix,
    }
