@echo off
REM =============================================================================
REM AI Companion - Docker Setup Script (Windows Batch)
REM =============================================================================
REM One-command setup for AI Companion with Docker
REM
REM Usage:
REM   setup-docker.bat
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo            AI Companion - Docker Setup
echo ================================================================
echo.

REM Check if Docker is running
echo [INFO] Checking Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    exit /b 1
)
echo [OK] Docker is running
echo.

REM Check if docker-compose.yml exists
if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found. Are you in the project root?
    exit /b 1
)

REM Step 1: Start Docker containers
echo [INFO] Starting Docker containers...
echo        This will download images (~2GB) on first run
echo.
docker-compose --env-file .env.docker up -d
if errorlevel 1 (
    echo [ERROR] Failed to start containers. Check the error above.
    exit /b 1
)
echo [OK] Containers started
echo.

REM Step 2: Wait for Ollama to be ready
echo [INFO] Waiting for Ollama to be ready...
timeout /t 10 /nobreak >nul

REM Check if Ollama is responsive (try 6 times, 5 seconds apart)
set OLLAMA_READY=0
for /L %%i in (1,1,6) do (
    docker exec ai-companion-brain ollama list >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Ollama is ready
        set OLLAMA_READY=1
        goto :ollama_ready
    )
    if %%i LSS 6 (
        echo        Waiting... (attempt %%i/6)
        timeout /t 5 /nobreak >nul
    )
)

if %OLLAMA_READY%==0 (
    echo [WARN] Ollama is taking longer than expected. Continuing anyway...
)

:ollama_ready
echo.

REM Step 3: Pull main LLM model
echo [INFO] Pulling AI model (9GB download, this will take 5-10 minutes)
echo        Model: nchapman/gemma-2-9b-it-abliterated:9b
echo.
docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
if errorlevel 1 (
    echo.
    echo [WARN] Model download failed or was interrupted.
    echo        You can retry manually:
    echo        docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b
    exit /b 1
)
echo.
echo [OK] Main model downloaded
echo.

REM Step 4: Pull embedding model (for Phase 3 memory features)
echo [INFO] Pulling embedding model (for memory features, ~274MB)
echo        Model: nomic-embed-text:latest
echo.
docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest
if errorlevel 1 (
    echo.
    echo [WARN] Embedding model download failed. This is optional for basic usage.
    echo        You can retry manually later:
    echo        docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest
)
echo.

REM Step 5: Verify all services are running
echo [INFO] Verifying services...
timeout /t 3 /nobreak >nul

set SERVICES_OK=1

REM Check Ollama
docker exec ai-companion-brain ollama list >nul 2>&1
if not errorlevel 1 (
    echo [OK] ai-companion-brain (Ollama LLM)
) else (
    echo [WARN] ai-companion-brain (not responding)
    set SERVICES_OK=0
)

REM Check Backend
curl -f http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    echo [OK] ai-companion-api (Backend)
) else (
    echo [WARN] ai-companion-api (not ready yet)
    set SERVICES_OK=0
)

REM Check Frontend
curl -f http://localhost:3000 >nul 2>&1
if not errorlevel 1 (
    echo [OK] ai-companion-web (Frontend)
) else (
    echo [WARN] ai-companion-web (not ready yet)
    set SERVICES_OK=0
)

echo.

REM Final message
if %SERVICES_OK%==1 (
    echo ================================================================
    echo                    Setup complete!
    echo ================================================================
    echo.
    echo Your AI Companion is ready at:
    echo.
    echo    Frontend:  http://localhost:3000
    echo    Backend:   http://localhost:8000
    echo    API Docs:  http://localhost:8000/docs
    echo.
    echo Next steps:
    echo    1. Open http://localhost:3000 in your browser
    echo    2. Pull a character from the gacha
    echo    3. Start chatting with your AI personas!
    echo.
    echo Useful commands:
    echo    View logs:     docker-compose logs -f
    echo    Stop services: docker-compose down
    echo    Restart:       docker-compose restart
    echo.

    REM Open browser automatically
    start http://localhost:3000
) else (
    echo ================================================================
    echo              Setup completed with warnings
    echo ================================================================
    echo.
    echo Some services may still be starting up. Wait 30 seconds and try:
    echo    curl http://localhost:8000/health
    echo    curl http://localhost:3000
    echo.
    echo View logs to troubleshoot:
    echo    docker-compose logs -f
    echo.
)

endlocal
