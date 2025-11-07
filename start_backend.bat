@echo off
REM Simple startup script for the backend
cd /d "%~dp0"

REM Set environment variables from .env file
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%b"=="" set %%a=%%b
)

REM Start the server
cd src
python -c "
import sys
import os
sys.path.insert(0, '.')

# Import and run the server
from coordinator.server import app
import uvicorn

print('Starting GraphRAG Coordinator...')
print(f'Ollama Base: {os.getenv(\"OLLAMA_BASE\", \"not set\")}')
print(f'Persona Model: {os.getenv(\"PERSONA_MODEL\", \"not set\")}')

uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
"