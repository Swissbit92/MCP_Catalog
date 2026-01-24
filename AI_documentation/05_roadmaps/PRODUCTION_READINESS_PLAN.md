# Kubernetes Production Readiness Plan

**Status**: Planning Phase
**Last Updated**: December 24, 2025
**Author**: Production Architecture Assessment

---

## Executive Summary

**Current State**: Development-ready codebase with excellent code quality (10/10 hygiene score) but critical infrastructure gaps for production deployment.

**Production Readiness Score**: **4/10**
- ✅ Code Quality: 10/10
- ✅ Security: 8/10
- ✅ Configuration: 9/10
- ⚠️ Testing: 7/10
- ❌ Database: 2/10
- ❌ Scalability: 1/10
- ❌ Observability: 3/10
- ❌ Deployment: 0/10

**Recommendation**: **Do NOT deploy to Kubernetes yet**. Follow 3-phase migration plan below.

---

## Table of Contents

1. [Production Readiness Assessment](#production-readiness-assessment)
2. [Critical Gaps Analysis](#critical-gaps-analysis)
3. [Recommended Approach](#recommended-approach)
4. [Phase 1: Docker-First Migration](#phase-1-docker-first-migration-2-3-weeks)
5. [Phase 2: Cloud-Native Refactoring](#phase-2-cloud-native-refactoring-3-4-weeks)
6. [Phase 3: Kubernetes Deployment](#phase-3-kubernetes-deployment-2-3-weeks)
7. [Decision Matrix](#decision-matrix)
8. [Next Steps](#next-steps)

---

## Production Readiness Assessment

### ✅ Strengths (Production-Ready)

#### 1. Code Quality (10/10)
- ✅ **Modular Architecture**: 95% reduction in server.py (1,645 → 85 lines)
- ✅ **Type Safety**: Pydantic schemas throughout entire codebase
- ✅ **Technical Debt**: Only 1 TODO comment (performance optimization note)
- ✅ **Test Coverage**: 41 test files organized across backend/integration/exploration
- ✅ **Error Handling**: 82+ exception handlers for resilience
- ✅ **Clean Codebase**: Zero unused imports, zero dead code

#### 2. Security (8/10)
- ✅ **Secrets Management**: `.env` properly gitignored, no hardcoded API keys
- ✅ **Input Validation**: Pydantic models validate all user input
- ✅ **CORS Configuration**: Configured (though hardcoded for localhost)
- ✅ **Dependencies**: Minimal npm vulnerabilities (dev dependencies only)
- ✅ **SQL Injection**: Protected via parameterized queries

#### 3. Testing (6/10)
- ✅ **Test Coverage**: Backend unit tests + integration tests + frontend tests
- ✅ **Build Verification**: Production build validated manually
- ✅ **Security Scanning**: npm audit (run manually)

#### 4. Configuration Management (9/10)
- ✅ **Centralized Config**: Pydantic-based settings in `config.py`
- ✅ **Environment-Driven**: All settings from `.env` with validation
- ✅ **Type-Safe**: Field validators and defaults
- ✅ **Backward Compatible**: Function-based API alongside class-based

---

## Critical Gaps Analysis

### ❌ 1. Database Architecture (BLOCKER)

**Current State**: SQLite with local file storage (`chats.db`)

**Issues**:
- ❌ **Single-Instance Only**: No concurrent write support across multiple processes
- ❌ **File-Based**: Pod restarts in Kubernetes = complete data loss
- ❌ **No Replication**: Zero fault tolerance or backups
- ❌ **Filesystem Coupling**: Persona summaries stored in `personas/_summaries/`
- ❌ **Phase 3 RAG**: FAISS vector index stored in-memory (lost on restart)

**Impact**:
- Cannot scale horizontally
- Data loss risk in containerized environments
- Cannot run multiple backend replicas
- Load balancing causes inconsistent user experience

**Location in Codebase**:
```python
# src/coordinator/startup.py (line 45)
_DB_PATH = os.environ.get("COORDINATOR_DB_PATH", "chats.db")

# repositories/base_repository.py
conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
```

---

### ❌ 2. External Service Dependencies (MAJOR)

**Current State**: Tightly coupled to local Ollama server

**Issues**:
- ❌ **Hardcoded Localhost**: Default config points to `http://127.0.0.1:11434`
- ❌ **No Service Discovery**: Cannot dynamically discover Ollama instances
- ❌ **Single Point of Failure**: If Ollama crashes, entire app fails
- ❌ **STDIO MCP Clients**: Brave/MongoDB use subprocess spawning (not cloud-native)

**Impact**:
- Cannot deploy backend separately from LLM inference
- MCP integrations break in distributed systems
- No load balancing for LLM requests
- Cannot scale Ollama independently

**Location in Codebase**:
```python
# src/coordinator/config.py (line 29)
base: str = Field(
    default="http://127.0.0.1:11434",  # ← Hardcoded localhost
    description="Ollama API base URL",
    alias="OLLAMA_BASE"
)

# src/coordinator/server.py (line 40)
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]  # ← Hardcoded CORS
```

---

### ❌ 3. State Management (MAJOR)

**Current State**: In-memory global state and caches

**Issues**:
```python
# src/coordinator/startup.py (lines 48-60)
_brave_client: Optional[BraveMCPClient] = None           # ← Process-local
_mongodb_cache: Optional[MongoDBCache] = None            # ← Not shared across pods
_memory_manager: Optional[MemoryManager] = None          # ← Lost on restart
_episodic_memory_rag: Optional[EpisodicMemoryRAG] = None # ← FAISS in-memory
```

- ❌ **Process-Local State**: Each Kubernetes pod has different state
- ❌ **No Shared Cache**: MongoDB cache not distributed across replicas
- ❌ **RAG Vector Store**: FAISS index stored in-memory (8000+ vectors lost on pod restart)
- ❌ **Session Affinity Required**: Load balancer must route same user to same pod

**Impact**:
- Horizontal scaling impossible without major refactoring
- Cache stampede on pod restarts (all caches cold simultaneously)
- User experience breaks if load balancer switches pods
- Cannot do rolling deployments without service disruption

---

### ❌ 4. CORS & Network Configuration (MINOR)

**Current State**: Hardcoded localhost origins

**Issues**:
```python
# src/coordinator/server.py (line 40)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # ← Problem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- ❌ Won't work with production frontend domains
- ❌ No environment-driven CORS configuration
- ❌ Hardcoded port numbers

**Impact**: Frontend cannot connect to backend in production

---

### ⚠️ 5. Logging & Observability (MODERATE)

**Current State**: Basic Python logging to stdout

**Missing**:
- ⚠️ **Structured Logging**: Using standard Python `logging` (not JSON)
- ⚠️ **Distributed Tracing**: No OpenTelemetry/Jaeger integration
- ⚠️ **Metrics Export**: No Prometheus `/metrics` endpoint
- ⚠️ **Log Aggregation**: Logs to stdout (good) but no centralized collection
- ⚠️ **Request IDs**: No correlation IDs for tracing requests across services

**Impact**:
- Difficult to debug issues in production
- No visibility into system performance
- Cannot trace requests across microservices
- No alerting on errors or performance degradation

**Example Current Logging**:
```python
logger.info("[Brave] Web search workflow starting...")
logger.error(f"Failed to initialize Brave MCP client: {e}")
```

**Needed**:
```python
logger.info("web_search_started", extra={
    "request_id": request_id,
    "persona": persona_key,
    "query_length": len(query),
    "duration_ms": duration
})
```

---

### ⚠️ 6. Health Checks (MINOR)

**Current State**: Basic `/health` endpoint

```python
@app.get("/health")
def health():
    try:
        base = get_ollama_base()
        model = get_persona_model()
        get_session_repo().get_all_sessions()  # DB ping
        return {"status": "ok", "model": model, "db": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

**Issues**:
- ⚠️ **No Ollama Connectivity**: Just returns config, doesn't actually ping Ollama
- ⚠️ **Single Endpoint**: No distinction between liveness/readiness (K8s needs both)
- ⚠️ **MCP Client Health**: Doesn't check Brave/MongoDB connectivity
- ⚠️ **No Startup Probe**: Can't detect when app is still initializing

**Impact**: Kubernetes may route traffic to unhealthy pods

---

### ❌ 7. No Containerization (BLOCKER)

**Current State**: Zero Docker/Kubernetes artifacts

**Missing**:
- ❌ No `Dockerfile` for backend
- ❌ No `Dockerfile` for frontend (React build)
- ❌ No `docker-compose.yml` for local development
- ❌ No Kubernetes manifests (Deployments, Services, ConfigMaps)
- ❌ No Helm charts
- ❌ No container registry workflow
- ❌ No multi-stage builds for optimization

**Impact**: Cannot deploy to any container orchestration platform

---

## Recommended Approach

### Why NOT Kubernetes Now?

1. **SQLite Incompatibility**: Data loss on every pod restart/scale event
2. **Wasted Effort**: Complex K8s orchestration for single-instance architecture
3. **Debugging Nightmare**: Infrastructure issues masking architectural problems
4. **Ollama Coupling**: Cannot scale backend independently of LLM inference
5. **State Management**: In-memory state breaks load balancing
6. **MCP Architecture**: STDIO processes don't work in distributed systems

### Recommended: 3-Phase Migration

#### Timeline Overview
- **Phase 1**: Docker-First Migration (2-3 weeks)
- **Phase 2**: Cloud-Native Refactoring (3-4 weeks)
- **Phase 3**: Kubernetes Deployment (2-3 weeks)
- **Total**: 7-10 weeks for production-ready K8s deployment

---

## Phase 1: Docker-First Migration (2-3 weeks)

**Goal**: Containerize current architecture and fix database persistence

### Priority Tasks

#### 1.1 Database Migration (CRITICAL - Week 1-2)

**Option A: PostgreSQL** (Recommended)
```yaml
Pros:
  - Production-grade ACID compliance
  - Excellent JSON support (for persona data)
  - Connection pooling
  - Replication & backup tools
  - Horizontal scaling with extensions (Citus)

Cons:
  - Requires migration script
  - Slightly more complex setup

Recommendation: ✅ Use this for production
```

**Option B: SQLite + Persistent Volume** (Quick Fix)
```yaml
Pros:
  - Minimal code changes
  - Fast migration (1-2 days)

Cons:
  - Still single-instance only
  - Cannot scale horizontally
  - Requires K8s storage class configuration

Recommendation: ⚠️ Only for PoC/testing
```

**Migration Tasks**:
1. Install SQLAlchemy + asyncpg
2. Create SQLAlchemy models (map existing schema)
3. Write migration script (SQLite → PostgreSQL)
4. Update repositories to use SQLAlchemy
5. Test with production data copy
6. Update `config.py` to support `DATABASE_URL`

**Code Changes Required**:
```python
# New: src/coordinator/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

# Updated: src/coordinator/repositories/base_repository.py
# Replace sqlite3.connect() with SQLAlchemy sessions
```

---

#### 1.2 Create Dockerfiles (Week 2)

**Backend Dockerfile**:
```dockerfile
# Dockerfile (root directory)
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY personas/ ./personas/

# Create non-root user
RUN useradd -m -u 1000 coordinator && \
    chown -R coordinator:coordinator /app
USER coordinator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "src.coordinator.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile (Multi-Stage Build)**:
```dockerfile
# react-ui/Dockerfile
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/build /usr/share/nginx/html

# Custom nginx config (for React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Nginx Config for React Router**:
```nginx
# react-ui/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # React Router support
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional)
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Gzip compression
    gzip on;
    gzip_types text/css application/json application/javascript;
}
```

---

#### 1.3 Docker Compose Setup (Week 2)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  # PostgreSQL database
  postgres:
    image: postgres:16-alpine
    container_name: mcp_postgres
    environment:
      POSTGRES_DB: mcp_coordinator
      POSTGRES_USER: coordinator
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U coordinator"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcp-network

  # Redis cache (for Phase 2)
  redis:
    image: redis:7-alpine
    container_name: mcp_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcp-network

  # Ollama LLM server
  ollama:
    image: ollama/ollama:latest
    container_name: mcp_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    # GPU support (uncomment if you have NVIDIA GPU)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mcp-network

  # Backend FastAPI server
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mcp_backend
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      # Database
      DATABASE_URL: postgresql+asyncpg://coordinator:${DB_PASSWORD:-changeme}@postgres:5432/mcp_coordinator

      # Ollama
      OLLAMA_BASE: http://ollama:11434
      PERSONA_MODEL: ${PERSONA_MODEL:-llama3.1:latest}
      PERSONA_TEMPERATURE: ${PERSONA_TEMPERATURE:-0.1}

      # Server
      COORD_PORT: 8000
      COORD_URL: http://backend:8000
      PERSONA_DIR: personas

      # CORS (comma-separated origins)
      CORS_ORIGINS: http://localhost:3000,http://127.0.0.1:3000,http://frontend:80

      # Brave MCP
      BRAVE_API_KEY: ${BRAVE_API_KEY}
      BRAVE_ENABLED_RARITIES: rare,epic,legendary

      # MongoDB MCP
      MONGODB_URI: ${MONGODB_URI}
      MONGODB_ENABLED: ${MONGODB_ENABLED:-false}

      # Redis cache
      REDIS_URL: redis://redis:6379/0

      # Memory settings
      MEMORY_EMBEDDING_MODEL: ${MEMORY_EMBEDDING_MODEL:-nomic-embed-text:latest}
      MEMORY_SUMMARIZATION_INTERVAL: 30
      MEMORY_FACT_EXTRACTION_INTERVAL: 10
    volumes:
      - ./personas:/app/personas
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mcp-network

  # Frontend React app
  frontend:
    build:
      context: ./react-ui
      dockerfile: Dockerfile
    container_name: mcp_frontend
    depends_on:
      - backend
    environment:
      REACT_APP_API_URL: http://localhost:8000
    ports:
      - "3000:80"
    networks:
      - mcp-network

volumes:
  pgdata:
    driver: local
  redis_data:
    driver: local
  ollama_models:
    driver: local

networks:
  mcp-network:
    driver: bridge
```

**Environment File (.env.docker)**:
```bash
# Database
DB_PASSWORD=your_secure_password_here

# Ollama
PERSONA_MODEL=llama3.1:latest
PERSONA_TEMPERATURE=0.1

# Brave Search
BRAVE_API_KEY=your_brave_api_key_here

# MongoDB
MONGODB_URI=
MONGODB_ENABLED=false

# Memory
MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest
```

---

#### 1.4 Configuration Updates (Week 2)

**Add CORS_ORIGINS Support**:
```python
# src/coordinator/config.py (add to CoordinatorSettings)
cors_origins: str = Field(
    default="http://localhost:3000,http://127.0.0.1:3000",
    description="Comma-separated list of allowed CORS origins",
    alias="CORS_ORIGINS"
)

@property
def cors_origins_list(self) -> list[str]:
    """Get CORS origins as a list."""
    return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
```

**Update CORS Middleware**:
```python
# src/coordinator/server.py (line 40)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # ← Dynamic from env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Add DATABASE_URL Support**:
```python
# src/coordinator/config.py (add to CoordinatorSettings)
database_url: str = Field(
    default="sqlite:///./chats.db",
    description="Database connection URL (SQLAlchemy format)",
    alias="DATABASE_URL"
)

@property
def is_postgres(self) -> bool:
    """Check if using PostgreSQL."""
    return self.database_url.startswith("postgresql")
```

---

#### 1.5 Health Check Improvements (Week 2)

**Enhanced Health Endpoints**:
```python
# src/coordinator/routes/health.py (new file)
from fastapi import APIRouter, status
from ..startup import get_session_repo, get_brave_client, get_mongodb_client
from ..config import get_ollama_base, get_persona_model
import httpx

router = APIRouter()

@router.get("/health")
def health_check():
    """Basic health check (liveness probe)."""
    return {"status": "ok", "service": "mcp-coordinator"}

@router.get("/health/ready")
async def readiness_check():
    """Readiness probe - checks all dependencies."""
    checks = {
        "status": "healthy",
        "checks": {}
    }

    # Database check
    try:
        get_session_repo().get_all_sessions()
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["database"] = f"error: {str(e)}"

    # Ollama check
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{get_ollama_base()}/api/tags", timeout=5.0)
            if response.status_code == 200:
                checks["checks"]["ollama"] = "ok"
            else:
                checks["status"] = "unhealthy"
                checks["checks"]["ollama"] = f"status_code: {response.status_code}"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["ollama"] = f"error: {str(e)}"

    # Brave MCP check (if enabled)
    brave_client = get_brave_client()
    if brave_client:
        checks["checks"]["brave_mcp"] = "enabled"
    else:
        checks["checks"]["brave_mcp"] = "disabled"

    # MongoDB MCP check (if enabled)
    mongodb_client = get_mongodb_client()
    if mongodb_client:
        checks["checks"]["mongodb_mcp"] = "enabled"
    else:
        checks["checks"]["mongodb_mcp"] = "disabled"

    status_code = status.HTTP_200_OK if checks["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return checks, status_code

@router.get("/health/startup")
def startup_check():
    """Startup probe - checks if app is initialized."""
    from ..startup import _session_repo, _memory_manager

    if _session_repo is None or _memory_manager is None:
        return {"status": "initializing"}, status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ready"}, status.HTTP_200_OK
```

**Register Health Router**:
```python
# src/coordinator/server.py
from .routes.health import router as health_router
app.include_router(health_router, tags=["health"])
```

---

### Phase 1 Deliverables

By end of Phase 1, you will have:

- ✅ **PostgreSQL Database**: Production-grade database with migration scripts
- ✅ **Docker Compose Stack**: Full local development environment
- ✅ **Dockerfiles**: Backend + Frontend containerized
- ✅ **Persistent Volumes**: All stateful data preserved across restarts
- ✅ **Environment Config**: CORS, DATABASE_URL, all settings externalized
- ✅ **Health Checks**: Liveness, readiness, and startup probes
- ✅ **Documentation**: Updated README with Docker instructions
- ✅ **Testing**: All existing tests pass in Docker environment

**Ready to Deploy To**:
- ✅ Single VM with Docker Compose
- ✅ DigitalOcean App Platform
- ✅ AWS ECS (single-instance)
- ✅ Google Cloud Run (with Cloud SQL)

**NOT Ready For**:
- ❌ Kubernetes (horizontal scaling)
- ❌ Multi-region deployment
- ❌ High availability (still has single points of failure)

---

## Phase 2: Cloud-Native Refactoring (3-4 weeks)

**Goal**: Make application horizontally scalable

### Priority Tasks

#### 2.1 Distributed Caching (Week 1)

**Replace In-Memory Caches with Redis**:
```python
# New: src/coordinator/cache_redis.py
import redis.asyncio as aioredis
from typing import Optional
import json

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[dict]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict, ttl: int = 60):
        await self.redis.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str):
        await self.redis.delete(key)

# Update: src/coordinator/startup.py
_redis_cache: Optional[RedisCache] = None

def init_redis_cache():
    global _redis_cache
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis_cache = RedisCache(redis_url)
```

**Migrate MongoDB Cache**:
```python
# Update: src/coordinator/services/mongodb_handlers.py
# Replace MongoDBCache with RedisCache
```

---

#### 2.2 Externalize RAG Vector Store (Week 1-2)

**Option A: Qdrant** (Recommended)
```python
# New: src/coordinator/memory_rag_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

class EpisodicMemoryRAGQdrant:
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = "episodic_memory"
        self._ensure_collection()

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        if self.collection_name not in [c.name for c in collections]:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )
```

**Add to Docker Compose**:
```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
  volumes:
    - qdrant_storage:/qdrant/storage
```

**Option B: Weaviate** (Enterprise Alternative)
```yaml
weaviate:
  image: semitechnologies/weaviate:latest
  ports:
    - "8080:8080"
  environment:
    QUERY_DEFAULTS_LIMIT: 20
    AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
    PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
```

---

#### 2.3 MCP Architecture Redesign (Week 2-3)

**Current Problem**: STDIO-based MCP clients (subprocess spawning)

**Solution**: Deploy MCP servers as HTTP APIs

**Brave MCP Server (Standalone)**:
```dockerfile
# brave-mcp/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "brave_mcp_server:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Update Backend to Use HTTP MCP**:
```python
# src/coordinator/mcp_client_http.py
import httpx

class BraveMCPClientHTTP:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def search(self, query: str, max_results: int = 5):
        response = await self.client.post(
            f"{self.base_url}/search",
            json={"query": query, "max_results": max_results}
        )
        return response.json()
```

---

#### 2.4 Observability Stack (Week 3-4)

**Structured Logging**:
```python
# New: src/coordinator/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
```

**Prometheus Metrics**:
```python
# New: src/coordinator/metrics.py
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['persona', 'model']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['persona', 'model']
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active chat sessions'
)

# Add to FastAPI
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**Middleware for Request Tracking**:
```python
# src/coordinator/middleware.py
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration * 1000
            }
        )

        # Update metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response
```

---

#### 2.5 Database Connection Pooling (Week 4)

**Add SQLAlchemy Async Engine**:
```python
# src/coordinator/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from .config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,          # Max connections in pool
    max_overflow=10,       # Extra connections beyond pool_size
    pool_pre_ping=True,    # Verify connections before using
    pool_recycle=3600,     # Recycle connections after 1 hour
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Update Repositories**:
```python
# src/coordinator/repositories/session_repository.py
from sqlalchemy import select
from ..database import AsyncSessionLocal

class SessionRepository:
    async def get_all_sessions(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChatSession).order_by(ChatSession.created_at.desc())
            )
            return result.scalars().all()
```

---

### Phase 2 Deliverables

By end of Phase 2, you will have:

- ✅ **Stateless Backend**: Can run 10+ replicas simultaneously
- ✅ **Redis Cache**: Shared cache across all backend pods
- ✅ **External Vector DB**: Qdrant/Weaviate for persistent RAG
- ✅ **HTTP-based MCP**: Microservices architecture
- ✅ **Prometheus Metrics**: `/metrics` endpoint with 20+ metrics
- ✅ **Structured Logging**: JSON logs to stdout
- ✅ **Request Tracing**: Request IDs for correlation
- ✅ **Connection Pooling**: PostgreSQL pool with auto-scaling

**Ready to Deploy To**:
- ✅ Kubernetes (horizontal scaling works)
- ✅ Multi-region deployment
- ✅ High availability setups
- ✅ Auto-scaling groups

---

## Phase 3: Kubernetes Deployment (2-3 weeks)

**Goal**: Production orchestration with K8s

### Priority Tasks

#### 3.1 Kubernetes Manifests (Week 1)

**Namespace**:
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-coordinator
  labels:
    app: mcp-coordinator
```

**ConfigMap**:
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
  namespace: mcp-coordinator
data:
  PERSONA_MODEL: "llama3.1:latest"
  PERSONA_TEMPERATURE: "0.1"
  BRAVE_ENABLED_RARITIES: "rare,epic,legendary"
  MONGODB_ENABLED: "false"
  MEMORY_SUMMARIZATION_INTERVAL: "30"
  MEMORY_FACT_EXTRACTION_INTERVAL: "10"
  CORS_ORIGINS: "https://chat.example.com,https://www.example.com"
```

**Secrets**:
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-secrets
  namespace: mcp-coordinator
type: Opaque
stringData:
  DB_PASSWORD: "your_secure_password"
  BRAVE_API_KEY: "your_brave_api_key"
  MONGODB_URI: "your_mongodb_uri"
```

**PostgreSQL StatefulSet**:
```yaml
# k8s/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: mcp-coordinator
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          value: "mcp_coordinator"
        - name: POSTGRES_USER
          value: "coordinator"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: DB_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - coordinator
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - coordinator
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 20Gi
```

**Backend Deployment**:
```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: mcp-coordinator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/mcp-backend:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql+asyncpg://coordinator:$(DB_PASSWORD)@postgres:5432/mcp_coordinator"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: DB_PASSWORD
        - name: OLLAMA_BASE
          value: "http://ollama:11434"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: BRAVE_API_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: BRAVE_API_KEY
        envFrom:
        - configMapRef:
            name: mcp-config
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 5
          failureThreshold: 30
```

**HorizontalPodAutoscaler**:
```yaml
# k8s/backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: mcp-coordinator
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Ollama Deployment (GPU)**:
```yaml
# k8s/ollama-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: mcp-coordinator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        env:
        - name: OLLAMA_HOST
          value: "0.0.0.0:11434"
        volumeMounts:
        - name: ollama-models
          mountPath: /root/.ollama
        resources:
          requests:
            cpu: 2000m
            memory: 8Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 4000m
            memory: 16Gi
            nvidia.com/gpu: 1
      volumes:
      - name: ollama-models
        persistentVolumeClaim:
          claimName: ollama-models-pvc
```

**Ingress (NGINX)**:
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-ingress
  namespace: mcp-coordinator
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - chat.example.com
    secretName: mcp-tls
  rules:
  - host: chat.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

---

#### 3.2 Helm Chart (Week 1-2)

**Chart.yaml**:
```yaml
# helm/mcp-coordinator/Chart.yaml
apiVersion: v2
name: mcp-coordinator
description: AI Companion Coordinator with GraphRAG & MCP
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - ai
  - chat
  - llm
  - ollama
  - fastapi
maintainers:
  - name: Your Name
    email: your@email.com
```

**values.yaml**:
```yaml
# helm/mcp-coordinator/values.yaml
global:
  environment: production

backend:
  replicaCount: 3
  image:
    repository: your-registry/mcp-backend
    tag: v1.0.0
    pullPolicy: IfNotPresent

  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

  config:
    personaModel: "llama3.1:latest"
    personaTemperature: "0.1"
    corsOrigins: "https://chat.example.com"

frontend:
  replicaCount: 2
  image:
    repository: your-registry/mcp-frontend
    tag: v1.0.0

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

postgres:
  enabled: true
  persistence:
    size: 20Gi
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

redis:
  enabled: true
  persistence:
    size: 5Gi

ollama:
  replicaCount: 2
  gpu:
    enabled: true
    type: nvidia.com/gpu
    count: 1
  persistence:
    size: 50Gi
  resources:
    requests:
      cpu: 2000m
      memory: 8Gi
    limits:
      cpu: 4000m
      memory: 16Gi

qdrant:
  enabled: true
  persistence:
    size: 10Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: chat.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: mcp-tls
      hosts:
        - chat.example.com

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

---

#### 3.3 Monitoring Stack (Week 3)

**Prometheus + Grafana**:
```yaml
# k8s/monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: mcp-coordinator
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s

    scrape_configs:
    - job_name: 'backend'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - mcp-coordinator
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: backend
      - source_labels: [__meta_kubernetes_pod_ip]
        target_label: __address__
        replacement: ${1}:8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: mcp-coordinator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: storage
          mountPath: /prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: storage
        persistentVolumeClaim:
          claimName: prometheus-storage
```

**Grafana Dashboards**:
```json
{
  "dashboard": {
    "title": "MCP Coordinator - Production Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Request Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "LLM Request Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "active_sessions"
          }
        ]
      }
    ]
  }
}
```

---

### Phase 3 Deliverables

By end of Phase 3, you will have:

- ✅ **Production K8s Cluster**: EKS/GKE/AKS with all services
- ✅ **Auto-Scaling**: HPA for backend (3-10 replicas)
- ✅ **GPU Support**: Ollama pods with NVIDIA GPU scheduling
- ✅ **Load Balancing**: Ingress with SSL/TLS termination
- ✅ **Monitoring**: Prometheus + Grafana dashboards
- ✅ **Log Aggregation**: ELK or Loki for centralized logs
- ✅ **Disaster Recovery**: Backup strategy for PostgreSQL + Ollama models
- ✅ **High Availability**: Multi-AZ deployment
- ✅ **Network Policies**: Pod-to-pod security

**Production-Ready For**:
- ✅ 1,000+ concurrent users
- ✅ Multi-region deployment
- ✅ 99.9% uptime SLA
- ✅ Auto-scaling based on load
- ✅ Zero-downtime deployments

---

## Decision Matrix

| Approach | Timeline | Prod-Ready | Risk | Effort | Recommendation |
|----------|----------|------------|------|--------|----------------|
| **Skip to K8s now** | 1 week | ❌ No | 🔴 High | Medium | ❌ **Don't do this** |
| **Docker PoC (SQLite)** | 3-5 days | ⚠️ Partial | 🟡 Medium | Low | ⚠️ Only for learning |
| **Phase 1 (PostgreSQL)** | 2-3 weeks | ✅ Yes (single) | 🟢 Low | High | ✅ **Recommended** |
| **Phase 1-2 (Scalable)** | 5-7 weeks | ✅ Yes (scaled) | 🟢 Low | High | ✅ Ideal for growth |
| **Phase 1-3 (Full K8s)** | 7-10 weeks | ✅ Yes (enterprise) | 🟢 Low | Very High | ✅ Enterprise-ready |

---

## Next Steps

### Immediate Actions (This Week)

**Recommended**: Start with Phase 1 foundations

1. **Day 1-2**: PostgreSQL migration planning
   - Create SQLAlchemy models
   - Write migration script
   - Test with copy of production data

2. **Day 3-4**: Docker Compose setup
   - Create Dockerfiles (backend + frontend)
   - Write docker-compose.yml
   - Test full stack locally

3. **Day 5**: Configuration externalization
   - Add CORS_ORIGINS env var
   - Add DATABASE_URL support
   - Update health checks

4. **Week 2-3**: Complete Phase 1 deliverables

---

### Alternative: Quick Docker PoC (If You Want Fast Feedback)

**Goal**: See your app in Docker within 1 week

1. **Days 1-3**: Create minimal Dockerfiles (keep SQLite for now)
2. **Day 4**: Basic docker-compose.yml
3. **Day 5**: Test and document limitations

**Pros**: Learn Docker basics quickly
**Cons**: Still has SQLite issues, not production-ready

---

## Appendix: Useful Commands

### Docker Compose Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build backend
```

### Kubernetes Commands
```bash
# Deploy with Helm
helm install mcp-coordinator ./helm/mcp-coordinator -f values-prod.yaml

# Upgrade deployment
helm upgrade mcp-coordinator ./helm/mcp-coordinator

# Check pod status
kubectl get pods -n mcp-coordinator

# View logs
kubectl logs -f deployment/backend -n mcp-coordinator

# Scale deployment
kubectl scale deployment backend --replicas=5 -n mcp-coordinator

# Port forward for testing
kubectl port-forward svc/backend 8000:8000 -n mcp-coordinator
```

### Database Migration Commands
```bash
# Backup SQLite
sqlite3 chats.db .dump > backup.sql

# Test PostgreSQL connection
psql postgresql://coordinator:password@localhost:5432/mcp_coordinator

# Run migration
python scripts/migrate_sqlite_to_postgres.py

# Verify data
python scripts/verify_migration.py
```

---

## References

- [Phase 1 Implementation Plan](PHASE1_IMPLEMENTATION_PLAN.md) ← Detailed task breakdown
- [CLAUDE.md](CLAUDE.md) ← Project documentation
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI with Kubernetes](https://fastapi.tiangolo.com/deployment/docker/)
