from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers import automation, keys, admin
from app.db import init_db
from fastapi.middleware.cors import CORSMiddleware
import os

# API Base URL for OpenAPI docs
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

app = FastAPI(
    title="Anvesh API",
    description="Lead generation engine that hunts for high-value businesses with zero online presence.",
    version="1.0.0",
    servers=[
        {"url": API_BASE_URL, "description": "API Server"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler to make Pydantic validation errors 
    consistent with our standard API response format.
    """
    # Extract error messages
    errors = []
    for error in exc.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{location}: {error['msg']}")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "data": {
                "errors": errors,
                "details": exc.errors()
            },
            "error": True
        }
    )


# Initialize Database
init_db()

# Include Routers
app.include_router(automation.router)
app.include_router(keys.router)
app.include_router(admin.router)