# GoaT Public API - Quick Reference

## 🚀 Getting Started (5 minutes)

```bash
cd src/public-api

# Option 1: Quick setup script
./setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload --port 8000
```

Open: http://localhost:8000

## 📊 Cost Summary

### Recommended for Academic Project

**Start**: GPT-4o mini ($15 for 10k queries)

- Test with beta users
- Measure accuracy
- Cheapest option

**Upgrade if needed**: Claude Haiku 3.5 ($64 for 10k queries)

- Better reasoning
- Still affordable
- Production-ready

### Scale Planning

| Monthly Queries | GPT-4o mini | Claude Haiku |
| --------------- | ----------- | ------------ |
| 1,000           | $1.50       | $6.40        |
| 10,000          | $15         | $64          |
| 50,000          | $75         | $320         |

## 🎯 Example API Calls

### Free Tier (No API Key)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many plant species have chromosome data?",
    "model": "gpt-4o-mini"
  }'
```

### Premium (User's Key)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-ant-your-key" \
  -d '{
    "question": "Complex genomics question",
    "model": "claude-sonnet-4-5-20241022"
  }'
```

## 🔑 BYOK (Bring Your Own Key) Setup

Users can provide their own API keys to:

- ✅ Use premium models (Sonnet, GPT-4o)
- ✅ No rate limits
- ✅ Control their own costs

### Web UI

1. Select premium model
2. Enter API key (stored locally)
3. Query unlimited

### API

- Header: `X-API-Key: your-key`
- Or body: `"user_api_key": "your-key"`

## 📁 Key Files

```
src/public-api/
├── app/main.py              # Main FastAPI app
├── app/api/endpoints.py     # API routes
├── app/services/llm_service.py  # Multi-provider LLM
├── public/index.html        # Web interface
├── .env.example             # Configuration template
├── docker-compose.yml       # Docker setup
└── README.md               # Full documentation
```

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List models
curl http://localhost:8000/api/v1/models

# Run test suite
python test_api.py
```

## 🐳 Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

## 💰 Budget Control

### Rate Limiting

- Free tier: 100 queries/day per IP
- BYOK: Unlimited

### Admin Dashboard

```bash
curl http://localhost:8000/api/v1/admin/usage?days=30 \
  -H "X-Admin-Key: your-admin-key"
```

Returns:

- Total queries
- Total cost
- Free tier vs BYOK breakdown
- Queries by model

## 🎨 Web Interface Features

- 🖱️ Click example questions
- 📝 Natural language input
- 🎛️ Model selector (free/premium)
- 🔐 API key input for BYOK
- 📊 Real-time token and cost display
- 💾 Local storage of keys

## 🚢 Production Deployment

### Railway (Recommended)

```bash
railway login
railway init
railway up
```

### Render

1. Connect GitHub repo
2. Select "Web Service"
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### DigitalOcean

$6/month droplet + Docker Compose

## 🔒 Security Checklist

- [x] Environment variables for API keys
- [x] Rate limiting enabled
- [x] Admin endpoint protected
- [x] CORS configured
- [x] HTTPS via reverse proxy
- [x] User API keys not logged

## 📈 Monitoring

### Check Usage

```bash
# Last 7 days
curl http://localhost:8000/api/v1/admin/usage?days=7 \
  -H "X-Admin-Key: your-key"
```

### View Logs

```bash
# Docker
docker-compose logs -f api

# Local
tail -f logs/api.log
```

## 🆘 Troubleshooting

### Rate Limit Error

```
"Rate limit exceeded: 100 per 1 day"
```

→ Use BYOK or wait for reset

### Premium Model Requires Key

```
"Premium model requires API key"
```

→ Provide X-API-Key header or use free model

### Database Issues

```bash
rm usage.db
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

## 📚 Next Steps

1. ✅ **Set up .env** with your API keys
2. ✅ **Run locally** and test with web UI
3. ✅ **Test accuracy** with GPT-4o mini (cheapest)
4. ⬜ **A/B test** Haiku vs GPT-4o mini if needed
5. ⬜ **Deploy** to Railway/Render
6. ⬜ **Share** with beta users
7. ⬜ **Monitor** costs via admin endpoint

## 💡 Tips

- Start with GPT-4o mini (~$0.0015/query)
- Upgrade to Haiku if accuracy < 85%
- Enable BYOK for power users
- Monitor usage via admin endpoint
- Set up alerts for budget thresholds

## 📞 Support

- **Docs**: http://localhost:8000/docs
- **GoaT**: https://goat.genomehubs.org
- **Issues**: GitHub Issues

---

**Total Setup Time**: ~5 minutes  
**Monthly Cost (10k queries)**: $15-64  
**BYOK**: Free (users pay their own)
