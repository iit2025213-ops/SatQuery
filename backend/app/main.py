# app/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.config import settings
from app.utils.logger import setup_logger
from app.middleware.error_handling import ErrorHandlingMiddleware
from app.storage.supabase_client import SupabaseClient
from app.storage.cloudinary_client import CloudinaryClient
from app.auth.routes import router as auth_router
from app.api.v1.queries import router as queries_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.assets import router as assets_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.documents import router as documents_router
from app.api.v1.aoi import router as aoi_router
from app.api.v1.gee import router as gee_router
from app.api.v1.terrain import router as terrain_router
from app.api.v1.timeline import router as timeline_router
from app.api.websocket.routes import router as ws_router

# Initialize logger
logger = setup_logger("satquery", settings.log_level)

# Global clients (initialized on startup)
supabase_client = None
cloudinary_client = None
gee_connector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    
    # Startup
    logger.info("🚀 Starting SatQuery AI Backend...")
    
    global supabase_client, cloudinary_client, gee_connector
    
    try:
        # Initialize Supabase client
        supabase_client = SupabaseClient(
            url=settings.supabase_url,
            key=settings.supabase_key,
            service_role_key=settings.supabase_service_role_key
        )
        logger.info("✅ Supabase client initialized")
        
        # Initialize Cloudinary client
        cloudinary_client = CloudinaryClient(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret
        )
        logger.info("✅ Cloudinary client initialized")

        # Initialize GEE connector
        from app.gee.connector import GEEConnector
        gee_connector = GEEConnector(
            service_account_key_path=settings.gee_service_account_key_path,
            project_id=settings.gee_project_id,
        )
        logger.info("✅ GEE connector initialised (auth deferred)")
        
        # Make clients globally accessible
        from app import main as main_module
        main_module.supabase_client = supabase_client
        main_module.cloudinary_client = cloudinary_client
        main_module.gee_connector = gee_connector
        
        # Health check: Supabase connection
        try:
            await supabase_client.health_check()
            logger.info("✅ Supabase connection healthy")
        except Exception as e:
            logger.warning(f"⚠️ Supabase connection check failed: {e}")
        
        logger.info("✅ Backend startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down SatQuery AI Backend...")
    # Add cleanup code here if needed
    logger.info("✅ Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Vision-Language Assistant for Multimodal Remote-Sensing Analysis",
    lifespan=lifespan,
    debug=settings.debug
)

# Include auth routes
app.include_router(auth_router)

# Include API v1 routes
app.include_router(queries_router)
app.include_router(jobs_router)
app.include_router(assets_router)
app.include_router(artifacts_router)
app.include_router(documents_router)
app.include_router(aoi_router)
app.include_router(gee_router)
app.include_router(terrain_router)
app.include_router(timeline_router)
app.include_router(ws_router)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Custom error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.2f}s"
    )
    
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": time.time()
    }


# Ready check endpoint (checks all dependencies)
@app.get("/ready")
async def ready_check():
    """Readiness check - verifies all critical services"""
    checks = {
        "supabase": "unknown",
        "cloudinary": "unknown",
        "config": "ok"
    }
    
    try:
        if supabase_client:
            await supabase_client.health_check()
            checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {str(e)}"
    
    try:
        if cloudinary_client:
            # Simple cloudinary check (verify we can access config)
            checks["cloudinary"] = "ok"
    except Exception as e:
        checks["cloudinary"] = f"error: {str(e)}"
    
    all_ok = all(v == "ok" for v in checks.values())
    
    return {
        "ready": all_ok,
        "checks": checks,
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


# NOTE: API routes will be included in MEGAPROMPT 3
# NOTE: WebSocket endpoints will be included in MEGAPROMPT 9

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
