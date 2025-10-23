# HR Knowledge Base Agent - Usage Guide

## Overview

The HR Knowledge Base Agent provides both CLI and API server modes for generating HR warning documents.

## Fixed Issues

### 1. Deprecated `@app.on_event("startup")` Warning
- **Problem**: FastAPI's `@app.on_event("startup")` and `@app.on_event("shutdown")` are deprecated
- **Solution**: Implemented modern lifespan event handlers using `@asynccontextmanager`
- **Reference**: [FastAPI Lifespan Events Documentation](https://fastapi.tiangolo.com/advanced/events/)

### 2. Address Already in Use Error
- **Problem**: `ERROR: [Errno 98] Address already in use` when port 8000 is occupied
- **Solution**: 
  - Implemented automatic port detection that finds the next available port
  - Added `--port` flag to specify custom port
  - Added `--no-auto-port` flag to disable automatic port selection
  - Server will automatically use ports 8000, 8001, 8002, etc. until it finds an available one

## Installation

```bash
pip install -r requirements.txt
```

## Usage Modes

### 1. CLI Mode (Default)

Run the agent in command-line mode for quick testing:

```bash
python -m main
# or explicitly
python -m main --mode cli
```

### 2. Server Mode (API)

Start the FastAPI server:

```bash
# Default (localhost only on port 8000 with auto-port selection)
python -m main --mode server

# Specify custom port
python -m main --mode server --port 8080

# Disable auto-port selection (fail if port is in use)
python -m main --mode server --no-auto-port

# Bind to all interfaces (use with caution - ensure firewall is configured)
python -m main --mode server --host 0.0.0.0 --port 9000
```

**Security Note:** By default, the server binds to `127.0.0.1` (localhost only) for security. To make the server accessible from external networks, use `--host 0.0.0.0`, but ensure proper firewall rules and authentication are in place.

## API Endpoints

When running in server mode, the following endpoints are available:

### Health Check
```bash
GET http://localhost:8000/health
```

### Root Information
```bash
GET http://localhost:8000/
```

### Process Query
```bash
POST http://localhost:8000/api/query
Content-Type: application/json

{
  "query": "请帮我为员工张三生成一份B1模板的警告文档，违规原因是多次迟到，职位是工程师，员工ID是666，部门是研发部，经理是李四，违规详情是经常上班迟到早退。",
  "template_type": "B1"
}
```

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Example Client

Test the API server using the provided example script:

```bash
# Make sure server is running first
python example_usage.py

# Test with custom URL
python example_usage.py http://localhost:8001
```

## Environment Variables

- `PORT`: Default port for server mode (default: 8000)

```bash
PORT=9000 python -m main --mode server
```

## Architecture Changes

### New Files
- `server.py`: FastAPI application with lifespan event handlers
- `requirements.txt`: Python dependencies
- `USAGE.md`: This usage guide
- `example_usage.py`: Example API client
- `.gitignore`: Git ignore patterns

### Modified Files
- `main.py`: Updated to support both CLI and server modes with argument parsing

## Notes

- The server uses modern FastAPI lifespan event handlers (no deprecation warnings)
- Automatic port selection prevents "Address already in use" errors
- Both CLI and server modes share the same HRKnowledgeBaseAgent instance
- Generated documents are saved to the `Output/` directory
