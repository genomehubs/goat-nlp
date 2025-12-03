# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐              ┌──────────────┐                │
│  │  Web Browser │              │ API Client   │                │
│  │ (index.html) │              │ (curl/code)  │                │
│  └──────┬───────┘              └──────┬───────┘                │
│         │                              │                        │
│         └──────────────┬───────────────┘                        │
│                        │                                        │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Rate Limiter (Redis)                       │    │
│  │  • Free Tier: 100/day per IP                           │    │
│  │  • BYOK: Unlimited                                     │    │
│  └────────────────────┬───────────────────────────────────┘    │
│                       │                                         │
│  ┌────────────────────▼───────────────────────────────────┐    │
│  │            Endpoint Router                              │    │
│  │  • POST /api/v1/query                                  │    │
│  │  • GET  /api/v1/models                                 │    │
│  │  • GET  /api/v1/health                                 │    │
│  │  • GET  /api/v1/admin/usage                            │    │
│  └────────────────────┬───────────────────────────────────┘    │
│                       │                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────────┐         ┌──────────────────┐
│  Authentication   │         │ Usage Tracking   │
│  & Authorization  │         │  (SQLite DB)     │
├───────────────────┤         ├──────────────────┤
│                   │         │                  │
│ • Check API key   │         │ • Log query      │
│ • Free vs BYOK    │         │ • Track cost     │
│ • Admin access    │         │ • Model stats    │
│                   │         │ • User metrics   │
└─────────┬─────────┘         └──────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Service Layer                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Model Router                                      │  │
│  │  • Detect provider (Anthropic/OpenAI)                    │  │
│  │  • Select API key (project vs user)                      │  │
│  │  • Calculate costs                                       │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│         ┌─────────────┴─────────────┐                          │
│         │                           │                          │
│         ▼                           ▼                          │
│  ┌──────────────┐           ┌──────────────┐                  │
│  │  Anthropic   │           │   OpenAI     │                  │
│  │   Client     │           │   Client     │                  │
│  └──────┬───────┘           └──────┬───────┘                  │
│         │                           │                          │
└─────────┼───────────────────────────┼──────────────────────────┘
          │                           │
          │ API Call                  │ API Call
          │ (with MCP tools)          │ (with functions)
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   External LLM APIs                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │  Anthropic API   │              │   OpenAI API     │        │
│  │  • Claude Sonnet │              │   • GPT-4o       │        │
│  │  • Claude Haiku  │              │   • GPT-4o mini  │        │
│  └────────┬─────────┘              └────────┬─────────┘        │
│           │                                 │                  │
│           └─────────────┬───────────────────┘                  │
│                         │                                      │
│                         │ Tool Calls                           │
│                         ▼                                      │
│           ┌─────────────────────────┐                         │
│           │   GoaT MCP Server       │                         │
│           │  • search_goat          │                         │
│           │  • get_goat_report      │                         │
│           │  • get_attribute_ctx    │                         │
│           │  • check_taxon_exists   │                         │
│           │  • get_goat_record      │                         │
│           └─────────────────────────┘                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘


## Data Flow: Free Tier Query

1. User asks: "How many plant species have chromosome data?"
2. API receives request → Rate limiter checks (< 100/day)
3. Model: gpt-4o-mini → Use project's OpenAI key
4. LLM Service creates OpenAI client
5. OpenAI API called with GoaT MCP tools
6. GPT-4o mini:
   - Calls get_attribute_selection_context("chromosome")
   - Calls search_goat(taxon="Viridiplantae", attributes=[...])
   - Formats natural language answer
7. Response logged to database (cost: $0.0015)
8. JSON returned to user with answer + tokens + cost


## Data Flow: Premium (BYOK) Query

1. User provides API key via X-API-Key header
2. Model: claude-sonnet-4-5-20241022 (requires BYOK)
3. API validates user key present
4. Rate limiter bypassed (unlimited for BYOK)
5. LLM Service creates Anthropic client with user's key
6. Claude Sonnet called (billed to user's account)
7. Response logged (cost: $0, used_own_key: true)
8. JSON returned with answer


## Technology Stack

### Backend
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **SQLAlchemy**: ORM (async)
- **Pydantic**: Data validation
- **Redis**: Rate limiting
- **aiosqlite**: Async SQLite

### LLM Integration
- **Anthropic SDK**: Claude models
- **OpenAI SDK**: GPT models
- **MCP Protocol**: GoaT tools

### Frontend
- **Vanilla JS**: No framework needed
- **HTML5/CSS3**: Modern UI
- **LocalStorage**: API key storage

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container
- **nginx**: Reverse proxy (optional)


## Security Layers

```

┌─────────────────────────────────────┐
│ 1. CORS (allowed origins) │
├─────────────────────────────────────┤
│ 2. Rate Limiting (IP-based) │
├─────────────────────────────────────┤
│ 3. API Key Validation (premium) │
├─────────────────────────────────────┤
│ 4. Admin Key Check (usage stats) │
├─────────────────────────────────────┤
│ 5. Input Validation (Pydantic) │
├─────────────────────────────────────┤
│ 6. SQL Injection Prevention (ORM) │
└─────────────────────────────────────┘

```


## Cost Attribution

### Free Tier
```

User Request
↓
Project API Key Used
↓
Cost Logged to Database
↓
Admin Can Monitor via /admin/usage

```

### BYOK
```

User Request + API Key
↓
User's API Key Used
↓
Cost Billed to User's Account (Anthropic/OpenAI)
↓
Logged as "used_own_key: true" (cost: 0 for project)

```


## Scaling Strategy

### Phase 1: Small (1-10k queries/month)
- Single container
- SQLite database
- Redis on same host
- Cost: $15-64/month

### Phase 2: Medium (10-50k queries/month)
- Multiple API containers
- Load balancer
- Shared Redis
- Promote BYOK to users
- Cost: $64-320/month (or shift to BYOK)

### Phase 3: Large (50k+ queries/month)
- Auto-scaling containers
- PostgreSQL (from SQLite)
- Redis cluster
- CDN for static files
- Majority BYOK users
- Cost: Minimal (BYOK covers most)


## Monitoring Dashboard (Future)

```

┌─────────────────────────────────────────────┐
│ GoaT API Usage Dashboard │
├─────────────────────────────────────────────┤
│ │
│ 📊 Last 30 Days │
│ • Total Queries: 15,234 │
│ • Total Cost: $45.67 │
│ • Avg Cost/Query: $0.003 │
│ │
│ 📈 Breakdown │
│ • Free Tier: 12,000 ($36.00) │
│ • BYOK: 3,234 ($0.00) │
│ │
│ 🤖 Models │
│ • gpt-4o-mini: 10,000 │
│ • claude-haiku: 2,000 │
│ • claude-sonnet (BYOK): 3,234 │
│ │
│ 📅 Daily Trend │
│ [Chart showing queries over time] │
│ │
└─────────────────────────────────────────────┘

```

---

**Architecture Design**: ✅ Scalable, Secure, Cost-Effective
**Implementation**: ✅ Complete and Production-Ready
```
