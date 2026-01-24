@echo off
REM setup.bat - Automated setup script for MCP Catalog (Windows)

echo 🚀 Setting up MCP Catalog...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.11 or higher.
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js.
    pause
    exit /b 1
)

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt

REM Install React dependencies
echo ⚛️ Installing React dependencies...
cd react-ui && npm install && cd ..

echo ✅ Setup complete!
echo.
echo To start the application:
echo 1. Create a .env file (see README.md for example)
echo 2. Run: python run.py
echo 3. In another terminal: cd react-ui && npm start
echo.
echo Make sure Ollama is running with the required model.
echo.
pause