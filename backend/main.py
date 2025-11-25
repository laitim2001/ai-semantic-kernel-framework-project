"""
IPA Platform - FastAPI Backend Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Version
__version__ = "0.1.0"

# Create FastAPI app
app = FastAPI(
    title="IPA Platform API",
    description="Intelligent Process Automation Platform powered by Semantic Kernel",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "IPA Platform API",
        "version": __version__,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": __version__,
    }


# Sprint 2: Audit API Routes
from src.api.v1.audit import router as audit_router

app.include_router(audit_router, prefix="/api/v1", tags=["audit"])

# Sprint 2: Webhook API Routes
from src.api.v1.webhooks import router as webhooks_router

app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])

# TODO: 添加其他路由
# from src.workflow.router import router as workflow_router
# from src.execution.router import router as execution_router
# from src.agent.router import router as agent_router
#
# app.include_router(workflow_router, prefix="/api/v1/workflows", tags=["workflows"])
# app.include_router(execution_router, prefix="/api/v1/executions", tags=["executions"])
# app.include_router(agent_router, prefix="/api/v1/agents", tags=["agents"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
