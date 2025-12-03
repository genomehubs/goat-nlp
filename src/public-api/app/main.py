"""Main FastAPI application"""

from contextlib import asynccontextmanager

from app.api.endpoints import router
from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import limiter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="GoaT Public API",
    description="""
Natural Language Query Interface for Genomes on a Tree (GoaT)

## Features
- 🆓 Free tier with GPT-4o mini / Claude Haiku
- 🔑 Bring Your Own Key (BYOK) for premium models
- 📊 Query genomic metadata with natural language
- 🚀 Fast, async API built on FastAPI

## Usage

### Free Tier (No API Key)
```bash
curl -X POST https://api.goat.edu/query \\
  -H "Content-Type: application/json" \\
  -d '{"question": "How many mammal species?", "model": "gpt-4o-mini"}'
```

### Premium (Your API Key)
```bash
curl -X POST https://api.goat.edu/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-anthropic-key" \\
  -d '{"question": "Complex query", "model": "claude-sonnet-4-5-20241022"}'
```
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["queries"])

# Serve static files (for web UI)
try:
    app.mount("/", StaticFiles(directory="public", html=True), name="public")
except RuntimeError:
    # Public directory doesn't exist yet
    pass


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GoaT Public API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "query": "/api/v1/query",
            "models": "/api/v1/models",
            "health": "/api/v1/health",
        },
    }
