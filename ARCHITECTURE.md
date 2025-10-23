# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Entry Point)                             │
│                                                              │
│  Command Line Arguments:                                     │
│  • --mode [cli|server]                                       │
│  • --host [127.0.0.1|0.0.0.0]                               │
│  • --port [8000|custom]                                      │
│  • --no-auto-port                                            │
└─────────────┬───────────────────────┬────────────────────────┘
              │                       │
              ▼                       ▼
    ┌─────────────────┐    ┌──────────────────────┐
    │   CLI Mode      │    │   Server Mode        │
    │   (Direct)      │    │   (FastAPI)          │
    └─────────┬───────┘    └──────────┬───────────┘
              │                       │
              │                       ▼
              │            ┌──────────────────────┐
              │            │     server.py        │
              │            │   (FastAPI App)      │
              │            │                      │
              │            │  ┌────────────────┐  │
              │            │  │   Lifespan     │  │
              │            │  │   Context Mgr  │  │
              │            │  │                │  │
              │            │  │  • Startup     │  │
              │            │  │  • Initialize  │  │
              │            │  │  • Shutdown    │  │
              │            │  └────────────────┘  │
              │            │                      │
              │            │  ┌────────────────┐  │
              │            │  │ Port Discovery │  │
              │            │  │                │  │
              │            │  │  • Check 8000  │  │
              │            │  │  • Try 8001    │  │
              │            │  │  • Find Free   │  │
              │            │  └────────────────┘  │
              │            │                      │
              │            │  API Endpoints:      │
              │            │  • GET /health       │
              │            │  • POST /api/query   │
              │            │  • GET /docs         │
              │            └──────────┬───────────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   hr_agent.py         │
              │   (Core Logic)        │
              │                       │
              │  • Load LLM Model     │
              │  • Extract Info       │
              │  • Generate Docs      │
              │  • Vector Search      │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
    ┌─────────────────┐    ┌──────────────────────┐
    │ EechatDeepSeek  │    │ warning_document     │
    │ LLM.py          │    │ _generator.py        │
    │                 │    │                      │
    │ • Model Load    │    │ • Generate DOCX      │
    │ • Inference     │    │ • Template B1/B2     │
    │ • Text Gen      │    │ • Save to Output/    │
    └─────────────────┘    └──────────────────────┘
```

## Request Flow (Server Mode)

```
Client Request
      │
      ▼
┌──────────────┐
│   FastAPI    │
│   Routing    │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  POST /api/query │
│   Validation     │
└──────┬───────────┘
       │
       ▼
┌────────────────────┐
│  HRKnowledgeBase   │
│      Agent         │
│                    │
│  1. Extract Info   │
│  2. Validate Data  │
│  3. Generate Doc   │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│  Document          │
│  Generator         │
│                    │
│  • Create DOCX     │
│  • Save to Output/ │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│  JSON Response     │
│                    │
│  {                 │
│    "status": "ok", │
│    "message": "…"  │
│  }                 │
└────────────────────┘
```

## Port Discovery Algorithm

```
Start with port 8000
      │
      ▼
┌─────────────────┐
│ Try bind to     │
│ host:port       │
└────┬────────────┘
     │
     ├─── Success? ──► Use this port ──► Start server
     │
     └─── Failed? ──► port += 1 ──► Try again (max 10 attempts)
                          │
                          └─── No free port? ──► Raise error
```

## Security Architecture

```
┌────────────────────────────────────────┐
│          Network Binding               │
│                                        │
│  Default: 127.0.0.1 (localhost only)   │
│  ┌──────────────────────────────────┐  │
│  │  ✓ Safe: Local access only       │  │
│  │  ✓ No external exposure          │  │
│  │  ✓ Development & testing         │  │
│  └──────────────────────────────────┘  │
│                                        │
│  Optional: 0.0.0.0 (all interfaces)    │
│  ┌──────────────────────────────────┐  │
│  │  ⚠ Warning: External access      │  │
│  │  ⚠ Requires firewall config      │  │
│  │  ⚠ Requires authentication       │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## Component Dependencies

```
main.py
  ├── hr_agent.py
  │     ├── EechatDeepSeekLLM.py
  │     │     ├── transformers
  │     │     ├── torch
  │     │     └── sentence-transformers
  │     ├── warning_document_generator.py
  │     │     └── python-docx
  │     ├── langchain (vector store)
  │     │     ├── FAISS
  │     │     └── HuggingFace embeddings
  │     └── polars (data processing)
  │
  └── server.py (server mode only)
        ├── fastapi
        ├── uvicorn
        └── pydantic
```

## Deployment Options

### Option 1: Development (localhost)
```bash
python -m main --mode server
# Accessible: http://127.0.0.1:8000
# Security: High (localhost only)
```

### Option 2: Production (behind proxy)
```bash
# Run server on localhost
python -m main --mode server --port 8000

# Nginx reverse proxy configuration
upstream hr_agent {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://hr_agent;
    }
}
```

### Option 3: Direct external access (not recommended)
```bash
python -m main --mode server --host 0.0.0.0
# Accessible: http://<server-ip>:8000
# Security: Configure firewall + authentication
```

## File Organization

```
Cai-Niao-Post-Station/
├── main.py                      # Entry point
├── server.py                    # FastAPI application
├── hr_agent.py                  # Core HR agent logic
├── EechatDeepSeekLLM.py        # LLM wrapper
├── warning_document_generator.py # Document generation
├── file_recognizer.py          # File categorization
├── requirements.txt            # Dependencies
├── .gitignore                  # Git exclusions
├── USAGE.md                    # Usage guide
├── CHANGES.md                  # Change log
├── SECURITY.md                 # Security documentation
├── ARCHITECTURE.md             # This file
├── PR_SUMMARY.md              # PR summary
├── example_usage.py           # API client example
└── verify_implementation.py   # Verification script
```

## Technology Stack

- **Web Framework**: FastAPI 0.104+
- **ASGI Server**: Uvicorn
- **LLM**: DeepSeek-R1-Distill-Qwen-1.5B
- **Document Generation**: python-docx
- **Vector Store**: FAISS
- **Embeddings**: HuggingFace (distilbert)
- **Data Processing**: Polars
- **Language**: Python 3.8+
