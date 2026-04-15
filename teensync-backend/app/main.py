"""
TeenSync Backend – FastAPI Application Entrypoint

Startup sequence:
  1. Initialize database tables (SQLAlchemy / SQLite)
  2. Initialize RAG pipeline (load/build FAISS index from mental health docs)
  3. Register all API routers
  4. Apply CORS middleware

Run with:
  cd teensync-backend
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Application Lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Code before `yield` runs at startup; code after runs at shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("🚀 Starting TeenSync API v%s ...", settings.app_version)

    # 1. Initialize database tables
    logger.info("Initializing database...")
    await init_db()
    logger.info("✅ Database ready.")

    # 2. Initialize RAG pipeline (non-blocking graceful degradation)
    logger.info("Initializing RAG pipeline...")
    try:
        from app.services.rag_service import initialize_rag
        initialize_rag()  # Builds/loads FAISS index from mental health docs
    except Exception as exc:
        logger.warning(
            "⚠️  RAG initialization failed (chatbot will use rule-based fallback): %s", exc
        )

    logger.info("✅ TeenSync API is ready.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("TeenSync API shutting down...")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "TeenSync – AI-powered mental wellness platform for teenagers. "
        "Features RAG-augmented empathetic chatbot (Luna), mood tracking, "
        "journaling, burnout detection, and peer support."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ──────────────────────────────────────────────────────────

from app.routers import auth, mood, journal, chat  # noqa: E402

app.include_router(auth.router,    prefix="/api/v1")
app.include_router(mood.router,    prefix="/api/v1")
app.include_router(journal.router, prefix="/api/v1")
app.include_router(chat.router,    prefix="/api/v1")

# Optional: burnout router if it exists
try:
    from app.routers import burnout  # type: ignore
    app.include_router(burnout.router, prefix="/api/v1")
    logger.info("Burnout router registered.")
except ImportError:
    logger.debug("No burnout router found — skipping.")


# ── Root Health Check ─────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root health check."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check including RAG status."""
    from app.services.rag_service import get_rag_status
    rag = get_rag_status()
    return {
        "status": "ok",
        "version": settings.app_version,
        "rag": rag,
        "llm": {
            "openai_configured": settings.has_openai,
            "gemini_configured": settings.has_gemini,
        },
    }
