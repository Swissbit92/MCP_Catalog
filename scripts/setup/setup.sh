#!/bin/bash
# setup.sh - Automated setup script for MCP Catalog

echo "🚀 Setting up MCP Catalog..."

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install React dependencies
echo "⚛️ Installing React dependencies..."
cd react-ui && npm install && cd ..

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "1. Create a .env file (see README.md for example)"
echo "2. Run: python run.py"
echo "3. In another terminal: cd react-ui && npm start"
echo ""
echo "Make sure Ollama is running with the required model."