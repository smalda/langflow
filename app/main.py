import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlmodel import Session, text

from .api.api import api_router
from .core.metrics import setup_metrics
from .db.base import create_db_and_tables, get_engine
from .db.create_ai_teacher import create_ai_teacher

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    logger.info("Application startup: Database tables created")

    # Create AI teacher
    await create_ai_teacher(get_engine())

    yield
    # Shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title="LangFlow",
    description="API for managing LangFlow",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup metrics
app = setup_metrics(app)

# Include routers
app.include_router(api_router)


@app.get("/health")
def health_check():
    try:
        with Session(get_engine()) as session:
            session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unhealthy"
        )


@app.get("/")
def read_root():
    return {
        "message": "Welcome to LangFlow API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error")
