#!/bin/bash

# Setup script for arxiv-downloader project
# This script creates and configures the Python virtual environment

set -e  # Exit on any error

PROJECT_NAME="arxiv-downloader"
PYTHON_VERSION="3.9"
VENV_DIR=".venv"

echo "🚀 Setting up $PROJECT_NAME development environment..."

# Check if Python is installed
if ! command -v python$PYTHON_VERSION &> /dev/null; then
    echo "❌ Python $PYTHON_VERSION is not installed. Please install it first."
    exit 1
fi

# Check if direnv is installed
if ! command -v direnv &> /dev/null; then
    echo "⚠️  direnv is not installed. Installing direnv is recommended."
    echo "   Install with: sudo apt install direnv (Ubuntu/Debian)"
    echo "   Or: brew install direnv (macOS)"
    echo "   Then add 'eval \"\$(direnv hook bash)\"' to your ~/.bashrc"
    echo ""
    read -p "Continue without direnv? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create virtual environment
echo "📦 Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "   Virtual environment already exists at $VENV_DIR"
else
    python$PYTHON_VERSION -m venv $VENV_DIR
    echo "   ✓ Virtual environment created at $VENV_DIR"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source $VENV_DIR/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install main requirements
if [ -f "requirements.txt" ]; then
    echo "📋 Installing main requirements..."
    pip install -r requirements.txt
    echo "   ✓ Main requirements installed"
else
    echo "⚠️  requirements.txt not found, creating basic one..."
    cat > requirements.txt << EOF
requests>=2.28.0
beautifulsoup4>=4.11.0
tqdm>=4.64.0
aiohttp>=3.8.0
aiofiles>=22.1.0
EOF
    pip install -r requirements.txt
fi

# Install vocabulary requirements
if [ -f "vocabulary/requirements.txt" ]; then
    echo "📚 Installing vocabulary requirements..."
    pip install -r vocabulary/requirements.txt
    echo "   ✓ Vocabulary requirements installed"
fi

# Create .python-version file
echo "$PYTHON_VERSION" > .python-version

# Setup direnv if available
if command -v direnv &> /dev/null; then
    echo "🔧 Setting up direnv..."
    if [ -f ".envrc" ]; then
        echo "   .envrc already exists"
    fi
    
    # Allow direnv for this directory
    direnv allow
    echo "   ✓ direnv configured"
else
    echo "⚠️  direnv not available, manual activation required"
    echo "   Run: source $VENV_DIR/bin/activate"
fi

# Create useful scripts
echo "📝 Creating utility scripts..."

# Create activate script
cat > activate_env.sh << 'EOF'
#!/bin/bash
# Quick activation script for the virtual environment
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo "  Python: $(python --version)"
echo "  Location: $(which python)"
EOF
chmod +x activate_env.sh

# Create test script
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test script to verify the environment setup"""

import sys
import subprocess

def test_imports():
    """Test importing required packages"""
    required_packages = [
        'requests',
        'bs4',
        'tqdm',
        'aiohttp',
        'aiofiles'
    ]
    
    vocabulary_packages = [
        'nltk',
        'sklearn',
        'numpy',
        'PyPDF2',
        'yake'
    ]
    
    print("Testing main packages...")
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package} - not installed")
    
    print("\nTesting vocabulary packages...")
    for package in vocabulary_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package} - not installed")

def test_environment():
    """Test environment configuration"""
    print(f"\nPython version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Virtual environment: {sys.prefix}")

if __name__ == "__main__":
    print("🧪 Testing environment setup...")
    test_imports()
    test_environment()
    print("\n✅ Environment test completed!")
EOF
chmod +x test_setup.py

echo ""
echo "✅ Environment setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. If using direnv: cd out and back in to auto-activate"
echo "2. If not using direnv: run 'source .venv/bin/activate'"
echo "3. Test setup with: python test_setup.py"
echo "4. Start using the keyword extractor in vocabulary/"
echo ""
echo "🔗 Useful commands:"
echo "  - Activate manually: source .venv/bin/activate"
echo "  - Quick activate: ./activate_env.sh"
echo "  - Test environment: python test_setup.py"
echo "  - Run keyword extractor: python vocabulary/example_usage.py"