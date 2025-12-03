"""Rate limiting utilities"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on user authentication"""
    # Check if user has their own API key (BYOK)
    user_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")

    if user_key:
        # BYOK users get separate, higher limits
        return f"byok_{user_key[:8]}"

    # Free tier users limited by IP
    return get_remote_address(request)


def requires_user_key(model: str, free_tier_models: list) -> bool:
    """Check if model requires user's own API key"""
    return model not in free_tier_models
