"""API models (request/response schemas)"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request to query GoaT via natural language"""

    question: str = Field(
        ...,
        description="Natural language question about genomic data",
        examples=["How many plant species have chromosome data?"],
    )
    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    user_api_key: Optional[str] = Field(
        None, description="User's API key for premium models (BYOK)"
    )


class TokenUsage(BaseModel):
    """Token usage information"""

    input: int
    output: int
    total: int


class QueryResponse(BaseModel):
    """Response from GoaT query"""

    answer: str
    tokens_used: TokenUsage
    cost_usd: float
    model: str
    used_own_key: bool


class ModelInfo(BaseModel):
    """Model information"""

    name: str
    provider: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    typical_3k_query_cost: float
    requires_user_key: bool


class ModelsResponse(BaseModel):
    """Available models"""

    free_tier: List[ModelInfo]
    premium: List[ModelInfo]
    usage_info: Dict[str, str]


class UsageStats(BaseModel):
    """Usage statistics"""

    total_queries: int
    total_cost_usd: float
    free_tier_queries: int
    byok_queries: int
    queries_by_model: Dict[str, int]
    date_range: Dict[str, str]


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    timestamp: datetime
    timestamp: datetime
