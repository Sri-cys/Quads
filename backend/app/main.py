import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Load environment variables
load_dotenv()

from app.api.health import router as health_router
from app.api.cases import router as cases_router
from app.api.analysis import router as analysis_router
from app.api.checkpoints import router as checkpoints_router
from app.api.recovery import router as recovery_router
from app.api.execution import router as execution_router
from app.dependencies import get_case_service, reset_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quads.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Quads Control Tower backend services...")
    get_case_service()  # Pre-warm LangGraph checkpointer and repository
    yield
    logger.info("Shutting down Quads Control Tower backend services...")
    reset_services()


app = FastAPI(
    title="Quads — Supply Chain Control Tower (Phase 1)",
    description=(
        "Agentic Supply Chain Disruption Detection, Impact Analysis & Recovery Orchestration.\n"
        "Phase 1: Ingestion, Triage, Agent 1 Impact Analysis, and Human Checkpoint 1."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
# Backend must allow the frontend's local origin(s) explicitly —
# do not use a wildcard "*" together with credentials.
default_origins = {"http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8080", "http://127.0.0.1:8080"}
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    default_origins.update(orig.strip() for orig in cors_origins_env.split(",") if orig.strip())
allowed_origins = list(default_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Consistent error handling format: {"error": "...", "message": "..."}
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    msg = first_error.get("msg", "Invalid request payload")
    detail_msg = f"Validation failed at '{loc}': {msg}" if loc else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "VALIDATION_ERROR", "message": detail_msg},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_SERVER_ERROR", "message": "An internal unexpected server error occurred"},
    )


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Register API routers
app.include_router(health_router)
app.include_router(cases_router)
app.include_router(analysis_router)
app.include_router(checkpoints_router)
app.include_router(recovery_router)
app.include_router(execution_router)


# Configure SAPUI5 Frontend Serving
# Priority 1: frontend/dist (built production bundle)
# Priority 2: frontend/webapp (development source fallback)
repo_root = Path(__file__).resolve().parents[2]
dist_dir = repo_root / "frontend" / "dist"
webapp_dir = repo_root / "frontend" / "webapp"

frontend_static_dir = dist_dir if dist_dir.exists() else webapp_dir

@app.get("/", include_in_schema=False)
async def serve_root():
    index_path = frontend_static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "FRONTEND_NOT_BUILT", "message": "Please run 'npm run build' inside frontend directory"},
    )

if frontend_static_dir.exists():
    logger.info(f"Serving SAPUI5 frontend from {frontend_static_dir}")
    app.mount("/", StaticFiles(directory=str(frontend_static_dir), html=True), name="frontend_static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
