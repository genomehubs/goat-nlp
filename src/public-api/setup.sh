#!/bin/bash

echo "🧬 GoaT Public API Setup"
echo "======================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate secret key
    secret_key=$(openssl rand -hex 32)
    sed -i.bak "s/your-secret-key-generate-with-openssl-rand-hex-32/$secret_key/" .env
    
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - OPENAI_API_KEY"
    echo "   - ADMIN_API_KEY"
    echo ""
    read -p "Press Enter to open .env in editor..."
    ${EDITOR:-nano} .env
fi

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
print('✓ Database initialized')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "Or with Docker:"
echo "  docker-compose up -d"
echo ""
echo "Access at: http://localhost:8000"
