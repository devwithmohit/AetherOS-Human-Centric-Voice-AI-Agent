# Memory Service (Module 10)

**Memory management service for AetherOS with short-term, long-term, and episodic memory.**

Part of the critical path: M2 (STT) → **M10 (Memory)** → M4 (Intent) → M5 (Orchestration)

## 🎯 Overview

The Memory Service provides comprehensive memory management with three storage tiers:

1. **Short-Term Memory (Redis)**: Active conversations, temporary context
2. **Long-Term Memory (PostgreSQL)**: User preferences, consent, execution history, knowledge base
3. **Episodic Memory (ChromaDB)**: Semantic search over conversation history with embeddings

### Key Features

- ✅ **Multi-tier storage** with appropriate backends for each memory type
- ✅ **Privacy controls** with encryption, anonymization, and consent management
- ✅ **Semantic search** using vector embeddings for context retrieval
- ✅ **GDPR/CCPA compliant** consent tracking and data retention policies
- ✅ **RESTful API** with FastAPI and async support
- ✅ **Docker Compose** for easy deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for infrastructure)
- PostgreSQL 15+
- Redis 7+

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
cd memory-service

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Create .env file
cp .env.example .env
# Edit .env and set ENCRYPTION_KEY and SECRET_KEY

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8001/health
```

#### Option 2: Local Development

```bash
cd memory-service

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (via Docker)
docker-compose up -d postgres redis

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://aetheros:password@localhost:5432/aetheros_memory"
export REDIS_URL="redis://localhost:6379/0"

# Run service
python -m app.main
```

### Verify Installation

```bash
# Health check
curl http://localhost:8001/health

# Should return:
# {
#   "status": "healthy",
#   "timestamp": "2024-02-07T10:00:00",
#   "services": {
#     "redis": "healthy",
#     "chromadb": "healthy",
#     "postgresql": "healthy"
#   }
# }
```

## 📦 API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### Example Usage

#### Short-Term Memory (Redis)

```python
import httpx

# Store conversation context
response = httpx.post(
    "http://localhost:8001/short-term/conversation/session-123",
    json={
        "current_intent": "weather_query",
        "location": "San Francisco",
        "message_count": 3
    }
)

# Retrieve context
response = httpx.get("http://localhost:8001/short-term/conversation/session-123")
context = response.json()
```

#### Long-Term Memory (PostgreSQL)

```python
# Store user preferences
response = httpx.post(
    "http://localhost:8001/long-term/preferences",
    json={
        "user_id": "user-456",
        "preferences": {
            "wake_word": "Hey Aether",
            "voice_speed": 1.2,
            "language": "en-US"
        },
        "language": "en",
        "timezone": "America/Los_Angeles"
    }
)

# Log command execution
response = httpx.post(
    "http://localhost:8001/long-term/execution",
    json={
        "user_id": "user-456",
        "session_id": "session-123",
        "command": "What's the weather in San Francisco?",
        "tool_name": "weather_api",
        "parameters": {"city": "San Francisco"},
        "result": "Sunny, 72°F",
        "success": true,
        "execution_time_ms": 245
    }
)
```

#### Episodic Memory (ChromaDB)

```python
# Store episodic memory
response = httpx.post(
    "http://localhost:8001/episodic/store",
    json={
        "user_id": "user-456",
        "session_id": "session-123",
        "content": "User asked about weather in San Francisco. Responded with current conditions.",
        "metadata": {
            "intent": "weather_query",
            "entities": ["San Francisco"]
        }
    }
)

# Semantic search
response = httpx.post(
    "http://localhost:8001/episodic/query",
    json={
        "user_id": "user-456",
        "query_text": "What was the weather like last time?",
        "n_results": 5
    }
)

episodes = response.json()
# Returns semantically similar episodes with distance scores
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│          Memory Service (Module 10)              │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│
│  │Short-Term   │  │ Long-Term   │  │ Episodic ││
│  │  (Redis)    │  │(PostgreSQL) │  │(ChromaDB)││
│  │             │  │             │  │          ││
│  │• Context    │  │• Preferences│  │• Semantic││
│  │• Sessions   │  │• Consent    │  │  Search  ││
│  │• Cache      │  │• History    │  │• Vectors ││
│  │• TTL: 1h    │  │• Knowledge  │  │• 90 days ││
│  └─────────────┘  └─────────────┘  └──────────┘│
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │       Privacy Controller                  │   │
│  │  • Encryption (Fernet)                    │   │
│  │  • Anonymization (PII redaction)          │   │
│  │  • Consent validation                     │   │
│  │  • Retention policies                     │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         ▲                           │
         │ gRPC/HTTP                 │ gRPC/HTTP
         │                           ▼
    ┌────────┐              ┌─────────────────┐
    │STT (M2)│              │Intent Class (M4)│
    └────────┘              └─────────────────┘
```

### Data Flow

1. **STT → Memory**: Transcribed text stored in episodic memory
2. **Memory → Intent**: Context retrieved for intent classification
3. **Intent → Memory**: Execution results logged
4. **Memory → Orchestration**: Historical patterns inform decisions

## 🗄️ Database Schema

### PostgreSQL Tables

#### user_preferences

- User settings and personalization
- Voice preferences, language, timezone

#### consent_records

- GDPR/CCPA compliance
- Consent tracking with IP/user-agent

#### execution_history

- Command execution logs
- Tool usage patterns
- Performance metrics

#### conversations

- Session metadata
- Message counts
- Active/ended status

#### knowledge_base

- Learned facts
- Confidence scores
- Expiration timestamps

## 🔒 Privacy & Security

### Encryption

```python
from cryptography.fernet import Fernet

# Generate key
key = Fernet.generate_key()
print(key.decode())  # Add to .env as ENCRYPTION_KEY
```

All sensitive data can be encrypted at rest using Fernet symmetric encryption.

### PII Anonymization

Automatically redacts:

- Email addresses → `[EMAIL]`
- Phone numbers → `[PHONE]`
- SSN → `[SSN]`
- Credit cards → `[CREDIT_CARD]`
- IP addresses → `[IP_ADDRESS]`

### Consent Management

```python
# Record consent
POST /long-term/consent
{
    "user_id": "user-123",
    "consent_type": "data_collection",
    "granted": true,
    "ip_address": "192.168.1.1"
}

# Check consent
GET /long-term/consent/user-123/data_collection
# Returns: {"granted": true}
```

### Retention Policies

- **Short-term**: 1 hour (configurable)
- **Episodic**: 90 days (configurable)
- **Long-term**: Until user deletion or consent revocation

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Load testing
pytest tests/test_load.py -v
```

### Example Test

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_store_and_retrieve():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Store memory
        response = await client.post(
            "/short-term/set",
            json={"key": "test", "value": {"foo": "bar"}, "namespace": "test"}
        )
        assert response.status_code == 201

        # Retrieve memory
        response = await client.get("/short-term/get/test/test")
        assert response.status_code == 200
        assert response.json()["value"] == {"foo": "bar"}
```

## 📊 Performance

### Expected Metrics

| Operation       | Latency | Throughput   |
| --------------- | ------- | ------------ |
| Redis SET       | <5ms    | >10k ops/sec |
| Redis GET       | <3ms    | >15k ops/sec |
| Postgres INSERT | <20ms   | >1k ops/sec  |
| Postgres SELECT | <10ms   | >5k ops/sec  |
| ChromaDB Store  | <50ms   | >500 ops/sec |
| ChromaDB Query  | <100ms  | >200 ops/sec |

### Load Testing Results

Target: 1000 concurrent users

```bash
# Run load test
pytest tests/test_load.py
```

Expected: <200ms p95 latency, 0% error rate

## 🔧 Configuration

### Environment Variables

See `.env.example` for all configuration options.

Key settings:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0

# Security
ENCRYPTION_KEY=<fernet-key>
SECRET_KEY=<random-string>

# Retention
SHORT_TERM_TTL=3600        # 1 hour
EPISODIC_RETENTION_DAYS=90 # 90 days

# Privacy
ENABLE_ENCRYPTION=true
REQUIRE_CONSENT=true
ANONYMIZE_PII=true
```

## 🐛 Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Check memory usage
redis-cli info memory
```

### ChromaDB Issues

```bash
# Check persist directory
ls -la ./chroma_data

# Reset ChromaDB
rm -rf ./chroma_data
mkdir -p ./chroma_data
```

## 📈 Monitoring

### Health Endpoints

```bash
# Overall health
curl http://localhost:8001/health

# Detailed metrics (if enabled)
curl http://localhost:8001/metrics
```

### Logging

Logs are structured with timestamp, logger name, level, and message:

```
2024-02-07 10:00:00 - app.stores.short_term - INFO - Connected to Redis successfully
2024-02-07 10:00:01 - app.database - INFO - Database tables initialized successfully
2024-02-07 10:00:02 - app.stores.episodic - INFO - Connected to ChromaDB successfully
```

Set `LOG_LEVEL=DEBUG` for verbose logging.

## 🚀 Deployment

### Production Checklist

- [ ] Generate strong `ENCRYPTION_KEY` and `SECRET_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS for specific origins
- [ ] Enable HTTPS/TLS
- [ ] Set up database backups
- [ ] Configure monitoring/alerting
- [ ] Set resource limits in Docker
- [ ] Enable authentication middleware
- [ ] Review retention policies
- [ ] Test disaster recovery

### Kubernetes Deployment

See `kubernetes/` directory for manifests (TODO).

## 🔗 Integration with Other Modules

### Module 2 (STT Processor)

```python
# After transcription, store in episodic memory
transcription = stt_processor.transcribe(audio)

memory_client.post(
    "/episodic/store",
    json={
        "user_id": user_id,
        "session_id": session_id,
        "content": transcription.text,
        "metadata": {
            "confidence": transcription.confidence,
            "timestamp": datetime.now().isoformat()
        }
    }
)
```

### Module 4 (Intent Classifier)

```python
# Retrieve context for intent classification
context = memory_client.get(
    f"/short-term/conversation/{session_id}"
).json()

# Get relevant episodic memories
episodes = memory_client.post(
    "/episodic/query",
    json={
        "user_id": user_id,
        "query_text": current_utterance,
        "n_results": 5
    }
).json()

# Combine for intent classification
intent = classify_intent(current_utterance, context, episodes)
```

## 📝 API Reference

Full API documentation available at `/docs` when service is running.

### Endpoints Summary

**Short-Term Memory**

- `POST /short-term/set` - Store memory
- `GET /short-term/get/{namespace}/{key}` - Retrieve memory
- `DELETE /short-term/delete/{namespace}/{key}` - Delete memory
- `GET /short-term/conversation/{session_id}` - Get conversation context
- `POST /short-term/conversation/{session_id}` - Set conversation context

**Long-Term Memory**

- `POST /long-term/preferences` - Create/update preferences
- `GET /long-term/preferences/{user_id}` - Get preferences
- `POST /long-term/consent` - Record consent
- `GET /long-term/consent/{user_id}/{type}` - Check consent
- `POST /long-term/execution` - Log execution
- `GET /long-term/execution/{user_id}` - Get execution history
- `POST /long-term/conversation` - Create conversation
- `GET /long-term/conversation/{session_id}` - Get conversation
- `PATCH /long-term/conversation/{session_id}` - Update conversation
- `DELETE /long-term/conversation/{session_id}` - End conversation
- `POST /long-term/knowledge` - Store knowledge
- `GET /long-term/knowledge/{user_id}` - Get knowledge
- `DELETE /long-term/knowledge/{user_id}` - Delete knowledge

**Episodic Memory**

- `POST /episodic/store` - Store episode
- `POST /episodic/query` - Semantic search
- `GET /episodic/episode/{id}` - Get episode
- `GET /episodic/recent/{user_id}` - Get recent episodes
- `DELETE /episodic/episode/{id}` - Delete episode
- `DELETE /episodic/user/{user_id}` - Delete user episodes
- `GET /episodic/count/{user_id}` - Count episodes

## 📄 License

Part of the AetherOS project.

## 👥 Contributing

Module 10 is critical for the AetherOS critical path. Changes must maintain:

- **Performance**: <100ms p95 latency for memory operations
- **Reliability**: >99.9% uptime
- **Privacy**: GDPR/CCPA compliance
- **API Stability**: Backward compatibility

## 📧 Support

See main AetherOS project documentation.

## 🔄 Next Steps

Once Module 10 is complete:

1. **Module 4** (Intent Classifier): Use memory for context-aware intent detection
2. **Integration Testing**: M2 → M10 → M4 pipeline validation
3. **Load Testing**: Verify 1000 concurrent user target
4. **Production Deployment**: Deploy to staging environment
