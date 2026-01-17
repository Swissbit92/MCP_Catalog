@echo off
REM =============================================================================
REM MCP Coordinator - Docker Network Quick Fix (Batch Version)
REM =============================================================================
REM Simple batch script for fixing Docker networking issues
REM For advanced options, use fix-docker-network.ps1
REM =============================================================================

echo.
echo ========================================
echo  MCP Coordinator - Docker Quick Fix
echo ========================================
echo.

echo [1/4] Stopping containers...
docker-compose down 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Some containers may not have stopped cleanly
)

echo [2/4] Cleaning orphaned networks...
docker network prune -f >nul 2>&1

echo [3/4] Starting services...
docker-compose --env-file .env.docker up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start services
    echo Run 'docker-compose logs' for details
    pause
    exit /b 1
)

echo [4/4] Waiting for health checks (40 seconds)...
timeout /t 40 /nobreak >nul

echo.
echo ========================================
echo  Verifying Services
echo ========================================
echo.

docker-compose ps

echo.
echo Fix complete! Access the app at:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000/docs
echo.

pause
