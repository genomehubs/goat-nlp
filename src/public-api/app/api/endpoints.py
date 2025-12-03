"""Main API endpoints"""

from datetime import datetime, timedelta
from typing import Optional

from app.api.models import (
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    QueryRequest,
    QueryResponse,
    TokenUsage,
    UsageStats,
)
from app.core.config import settings
from app.core.database import QueryLog, get_session
from app.core.rate_limit import limiter, requires_user_key
from app.services.llm_service import LLMService
from app.services.mcp_client import get_mcp_client
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
@limiter.limit(settings.free_tier_rate_limit)
async def query_goat(
    request: Request,
    query_req: QueryRequest,
    db: AsyncSession = Depends(get_session),
    x_api_key: Optional[str] = Header(None),
):
    """
    Query GoaT using natural language

    **Free Tier**: Uses gpt-4o-mini or claude-haiku-3.5 (project API key)
    - Rate limit: 100 queries/day per IP
    - No API key required

    **Premium (BYOK)**: Any model with your own API key
    - No rate limits
    - Billed to your account
    - Provide key via X-API-Key header or user_api_key field
    """
    user_key = query_req.user_api_key or x_api_key
    model = query_req.model

    # Check if model requires user key
    if requires_user_key(model, settings.free_tier_models):
        if not user_key:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Premium model requires API key",
                    "model": model,
                    "message": (
                        "Provide your API key via X-API-Key header "
                        "or user_api_key field"
                    ),
                    "free_models": settings.free_tier_models,
                },
            )

    # Get client IP
    client_ip = request.client.host

    try:
        # Create LLM service
        llm = LLMService(model=model, user_api_key=user_key)

        # Get MCP client
        mcp_client = await get_mcp_client()

        # Execute query with MCP tools
        result = await llm.query(query_req.question, mcp_client=mcp_client)

        # Log query
        log = QueryLog(
            user_id=None,
            ip_address=client_ip,
            model=model,
            question=query_req.question,
            tokens_input=result["tokens"]["input"],
            tokens_output=result["tokens"]["output"],
            cost_usd=result["cost_usd"],
            used_own_key=bool(user_key),
            success=True,
        )
        db.add(log)
        await db.commit()

        return QueryResponse(
            answer=result["answer"],
            tokens_used=TokenUsage(**result["tokens"]),
            cost_usd=result["cost_usd"],
            model=model,
            used_own_key=bool(user_key),
        )

    except Exception as e:
        # Log error
        log = QueryLog(
            user_id=None,
            ip_address=client_ip,
            model=model,
            question=query_req.question,
            tokens_input=0,
            tokens_output=0,
            cost_usd=0.0,
            used_own_key=bool(user_key),
            success=False,
            error_message=str(e),
        )
        db.add(log)
        await db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available models and pricing"""
    free_models = [
        ModelInfo(
            name="gpt-4o-mini",
            provider="openai",
            cost_per_1m_input=0.15,
            cost_per_1m_output=0.60,
            typical_3k_query_cost=0.0015,
            requires_user_key=False,
        ),
        ModelInfo(
            name="claude-haiku-3-5-20241022",
            provider="anthropic",
            cost_per_1m_input=0.80,
            cost_per_1m_output=4.0,
            typical_3k_query_cost=0.0064,
            requires_user_key=False,
        ),
    ]

    premium_models = [
        ModelInfo(
            name="claude-sonnet-4-5-20241022",
            provider="anthropic",
            cost_per_1m_input=3.0,
            cost_per_1m_output=15.0,
            typical_3k_query_cost=0.024,
            requires_user_key=True,
        ),
        ModelInfo(
            name="claude-sonnet-3-5-20241022",
            provider="anthropic",
            cost_per_1m_input=3.0,
            cost_per_1m_output=15.0,
            typical_3k_query_cost=0.024,
            requires_user_key=True,
        ),
        ModelInfo(
            name="gpt-4o",
            provider="openai",
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.0,
            typical_3k_query_cost=0.0175,
            requires_user_key=True,
        ),
    ]

    # Dynamically discover Google models via REST API
    try:
        if settings.google_api_key:
            import httpx

            url = "https://generativelanguage.googleapis.com/v1beta/models"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url, params={"key": settings.google_api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    google_working = [
                        m
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]

            # Pick a small curated set if available (prefer 2.5, then 2.0)
            preferred_order = [
                "models/gemini-2.5-flash",
                "models/gemini-2.5-pro",
                "models/gemini-2.0-flash",
                "models/gemini-2.0-flash-exp",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-pro",
            ]
            names = [m.get("name", "") for m in google_working]
            selected = [n for n in preferred_order if n in names]
            if not selected:
                # Fallback to first few generate-capable names
                selected = names[:3]

            # Pricing approximations aligned with friendly names
            pricing = {
                "models/gemini-1.5-flash": (0.075, 0.30, 0.000525),
                "models/gemini-1.5-pro": (1.25, 5.0, 0.00875),
                "models/gemini-2.0-flash": (1.25, 5.0, 0.00875),
                "models/gemini-2.0-flash-exp": (0.0, 0.0, 0.0),
                "models/gemini-2.5-flash": (1.25, 5.0, 0.00875),
                "models/gemini-2.5-pro": (3.5, 14.0, 0.0245),
            }
            for name in selected:
                inp, outp, typical = pricing.get(name, (0.0, 0.0, 0.0))
                premium_models.append(
                    ModelInfo(
                        name=name,
                        provider="google",
                        cost_per_1m_input=inp,
                        cost_per_1m_output=outp,
                        typical_3k_query_cost=typical,
                        requires_user_key=True,
                    )
                )
    except Exception:
        # If discovery fails, keep current list without Google additions
        pass

    return ModelsResponse(
        free_tier=free_models,
        premium=premium_models,
        usage_info={
            "free_tier": "100 queries/day per IP, uses project API keys",
            "premium": "Unlimited with your API key (BYOK)",
            "header": "X-API-Key: your-key-here",
            "field": "user_api_key in request body",
        },
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy", version="1.0.0", timestamp=datetime.utcnow()
    )


@router.get("/admin/usage", response_model=UsageStats)
async def get_usage_stats(
    admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_session),
    days: int = 30,
):
    """Get usage statistics (admin only)"""
    if admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    # Date range
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total queries
    total_result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.timestamp >= start_date)
    )
    total_queries = total_result.scalar() or 0

    # Total cost
    cost_result = await db.execute(
        select(func.sum(QueryLog.cost_usd)).where(
            QueryLog.timestamp >= start_date, QueryLog.used_own_key is False
        )
    )
    total_cost = cost_result.scalar() or 0.0

    # Free tier vs BYOK
    free_result = await db.execute(
        select(func.count(QueryLog.id)).where(
            QueryLog.timestamp >= start_date, QueryLog.used_own_key is False
        )
    )
    free_queries = free_result.scalar() or 0

    # Queries by model
    model_result = await db.execute(
        select(QueryLog.model, func.count(QueryLog.id))
        .where(QueryLog.timestamp >= start_date)
        .group_by(QueryLog.model)
    )
    queries_by_model = {row[0]: row[1] for row in model_result.fetchall()}

    return UsageStats(
        total_queries=total_queries,
        total_cost_usd=round(total_cost, 2),
        free_tier_queries=free_queries,
        byok_queries=total_queries - free_queries,
        queries_by_model=queries_by_model,
        date_range={
            "start": start_date.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "days": str(days),
        },
    )


@router.get("/diagnostics/google-models")
async def google_models_diagnostics(x_api_key: Optional[str] = Header(None)):
    """List Google Gemini models via REST API."""
    import httpx

    api_key = x_api_key or settings.google_api_key
    if not api_key:
        raise HTTPException(
            status_code=400, detail="Google API key required via X-API-Key or settings"
        )

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"key": api_key})
            response.raise_for_status()
            data = response.json()

        results = []
        for m in data.get("models", []):
            name = m.get("name", "")
            gen_methods = m.get("supportedGenerationMethods", [])
            results.append(
                {
                    "name": name,
                    "supported_generation_methods": gen_methods,
                    "supports_generateContent": "generateContent" in gen_methods,
                }
            )
        return {"count": len(results), "models": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
