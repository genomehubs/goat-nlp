# GoaT Public API

Natural Language Query Interface for Genomes on a Tree (GoaT) - enabling researchers to query genomic metadata using plain English.

## Features

- 🆓 **Free Tier**: GPT-4o mini / Claude Haiku with project API keys
- 🔑 **BYOK (Bring Your Own Key)**: Use premium models with your API key
- 📊 **Rich Queries**: Ask complex questions about genomic data
- 🚀 **Fast & Async**: Built on FastAPI with async I/O
- 📈 **Usage Tracking**: Monitor costs and query statistics
- 🔒 **Rate Limited**: Prevent abuse with IP-based limiting

## Quick Start

### 1. Installation

```bash
cd src/public-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required settings:

- `ANTHROPIC_API_KEY`: Your Anthropic API key (for free tier)
- `OPENAI_API_KEY`: Your OpenAI API key (for free tier)
- `ADMIN_API_KEY`: Admin key for usage stats
- `SECRET_KEY`: Generate with `openssl rand -hex 32`

### 3. Run Locally

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access at: http://localhost:8000

### 4. Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

## API Usage

### Free Tier Query

No API key required - uses project's API keys:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many plant species have chromosome data?",
    "model": "gpt-4o-mini"
  }'
```

Response:

```json
{
  "answer": "247,404 plant species in GoaT have chromosome number data...",
  "tokens_used": {
    "input": 3200,
    "output": 850,
    "total": 4050
  },
  "cost_usd": 0.0015,
  "model": "gpt-4o-mini",
  "used_own_key": false
}
```

### Premium (BYOK) Query

Provide your API key for better models:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-ant-your-anthropic-key" \
  -d '{
    "question": "Give me a detailed analysis of chromosome evolution in mammals",
    "model": "claude-sonnet-4-5-20241022"
  }'
```

### List Available Models

```bash
curl http://localhost:8000/api/v1/models
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Admin: Usage Statistics

```bash
curl http://localhost:8000/api/v1/admin/usage?days=30 \
  -H "X-Admin-Key: your-admin-key"
```

## Pricing

### Free Tier (Your Project API Keys)

| Model            | Cost per Query\* | 10k Queries/mo |
| ---------------- | ---------------- | -------------- |
| GPT-4o mini      | $0.0015          | **$15**        |
| Claude Haiku 3.5 | $0.0064          | **$64**        |

\*Based on typical 3k input + 1k output tokens

### Premium (User's API Keys)

Users pay directly to Anthropic/OpenAI:

| Model             | Cost per Query | Notes         |
| ----------------- | -------------- | ------------- |
| Claude Sonnet 4.5 | $0.024         | Best quality  |
| Claude Sonnet 3.5 | $0.024         | Latest        |
| GPT-4o            | $0.0175        | Fast, capable |

## Project Structure

```
src/public-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   ├── endpoints.py     # API routes
│   │   └── models.py        # Request/response schemas
│   ├── core/
│   │   ├── config.py        # Settings
│   │   ├── database.py      # DB models
│   │   └── rate_limit.py    # Rate limiting
│   └── services/
│       ├── llm_service.py   # LLM integrations
│       └── goat_tools.py    # MCP tool definitions
├── public/
│   └── index.html           # Web UI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Budget Planning

### Academic Use Case (Free Tier)

**Start with GPT-4o mini** (~$15 for 10k queries):

- Test with beta users
- Measure accuracy on genomics questions
- If accuracy < 85%, upgrade to Haiku

**Claude Haiku 3.5** (~$64 for 10k queries):

- Better reasoning and tool use
- Still affordable for academic budgets
- Recommended for production

### Scale Estimates

| Monthly Queries | GPT-4o mini | Claude Haiku |
| --------------- | ----------- | ------------ |
| 1,000           | $1.50       | $6.40        |
| 5,000           | $7.50       | $32          |
| 10,000          | $15         | $64          |
| 50,000          | $75         | $320         |

## Rate Limiting

### Free Tier

- **100 queries/day per IP**
- Reset: Daily at midnight UTC
- Backend: Redis

### BYOK (Premium)

- **Unlimited** - you control costs
- Users provide their own API keys
- No rate limits applied

## Web Interface

Open browser to: http://localhost:8000

Features:

- Example questions to get started
- Model selector (free vs premium)
- API key input for BYOK
- Real-time token and cost display
- Local storage of API keys

## Development

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

### Adding New Models

Edit `app/core/config.py`:

```python
free_tier_models: List[str] = [
    "gpt-4o-mini",
    "claude-haiku-3-5-20241022",
    "new-model-here"  # Add here
]
```

Update pricing in `app/services/llm_service.py`:

```python
pricing = {
    "new-model-here": {"input": 0.5, "output": 2.0},
    ...
}
```

## Production Deployment

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Render

1. Connect GitHub repo
2. Select "Web Service"
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### AWS Lambda + API Gateway

Use Mangum adapter:

```python
from mangum import Mangum
handler = Mangum(app)
```

## Security Best Practices

1. **API Keys**: Never commit to git - use `.env`
2. **Admin Key**: Generate strong key for `/admin/usage`
3. **HTTPS**: Use reverse proxy (nginx) with SSL
4. **Rate Limits**: Adjust based on your budget
5. **CORS**: Restrict `allowed_origins` in production

## Monitoring

### View Logs

```bash
# Docker
docker-compose logs -f api

# Local
tail -f logs/api.log
```

### Usage Dashboard

Access admin endpoint:

```bash
curl http://localhost:8000/api/v1/admin/usage?days=7 \
  -H "X-Admin-Key: your-key"
```

## Troubleshooting

### Rate Limit Errors

```json
{
  "error": "Rate limit exceeded",
  "detail": "100 per 1 day"
}
```

Solution: Use BYOK or wait for reset

### Model Requires API Key

```json
{
  "error": "Premium model requires API key",
  "free_models": ["gpt-4o-mini", "claude-haiku-3-5-20241022"]
}
```

Solution: Provide `X-API-Key` header or switch to free model

### Database Locked

```bash
# Reset database
rm usage.db
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

## Support

- **Issues**: GitHub Issues
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **GoaT**: https://goat.genomehubs.org

## License

MIT License - see LICENSE file

## Citation

If you use this API in research, please cite:

```bibtex
@software{goat_api,
  title = {GoaT Public API: Natural Language Interface for Genomic Metadata},
  year = {2025},
  url = {https://github.com/your-repo/goat-api}
}
```
