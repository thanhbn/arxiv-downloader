#!/bin/bash

# Fixed setup script for direnv environments in arxiv-downloader repository
# This script sets up virtual environment and installs requirements

set -e  # Exit on any error

echo "🚀 Setting up direnv environment for arxiv-downloader repository"
echo "================================================================="

# Check if direnv is installed
if ! command -v direnv &> /dev/null; then
    echo "❌ direnv is not installed. Please install direnv first:"
    echo "   - Ubuntu/Debian: sudo apt install direnv"
    echo "   - macOS: brew install direnv"
    echo "   - Then add 'eval \"\$(direnv hook bash)\"' to your ~/.bashrc or ~/.zshrc"
    exit 1
fi

echo "✅ direnv is installed"

# Function to detect Python version
detect_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        echo "python3.12"
    elif command -v python3.11 >/dev/null 2>&1; then
        echo "python3.11"
    elif command -v python3.10 >/dev/null 2>&1; then
        echo "python3.10"
    elif command -v python3.9 >/dev/null 2>&1; then
        echo "python3.9"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo ""
    fi
}

# Function to setup environment
setup_env() {
    local env_name=$1
    local env_path=$2
    local requirements_file=$3
    
    echo ""
    echo "📦 Setting up $env_name environment..."
    echo "   Path: $env_path"
    echo "   Requirements: $requirements_file"
    
    # Change to the environment directory
    cd "$env_path"
    
    # Detect Python version
    local python_cmd=$(detect_python)
    if [[ -z "$python_cmd" ]]; then
        echo "   ❌ No Python installation found"
        return 1
    fi
    echo "   Using Python: $python_cmd"
    
    # Remove existing broken virtual environment if it exists
    if [[ -d ".venv" && ! -f ".venv/bin/activate" ]]; then
        echo "   Removing broken virtual environment..."
        rm -rf ".venv"
    fi
    
    # Create virtual environment manually if needed
    if [[ ! -d ".venv" ]]; then
        echo "   Creating virtual environment..."
        $python_cmd -m venv .venv
        if [[ $? -ne 0 ]]; then
            echo "   ❌ Failed to create virtual environment"
            return 1
        fi
    fi
    
    # Allow direnv to load the environment
    echo "   Allowing direnv..."
    direnv allow
    
    # Give direnv time to load
    sleep 2
    
    # Check if virtual environment was created
    local venv_dir=".venv"
    if [[ -d "$venv_dir" && -f "$venv_dir/bin/activate" ]]; then
        echo "   ✅ Virtual environment created: $venv_dir"
        
        # Activate the virtual environment manually
        source "$venv_dir/bin/activate"
        
        # Upgrade pip
        python -m pip install --upgrade pip
        
        # Install requirements if file exists
        if [[ -f "$requirements_file" ]]; then
            echo "   Installing requirements..."
            python -m pip install -r "$requirements_file"
        else
            echo "   ⚠️  Requirements file not found: $requirements_file"
        fi
        
        # Install vocabulary requirements if they exist
        if [[ -f "vocabulary/requirements.txt" ]]; then
            echo "   Installing vocabulary requirements..."
            python -m pip install -r vocabulary/requirements.txt
        fi
    else
        echo "   ⚠️  Virtual environment not found or incomplete"
    fi
    
    echo "   ✅ $env_name environment setup complete"
    cd - > /dev/null
}

# Setup main environment
setup_env "ArXiv Downloader" "." "requirements.txt"

# Setup vocabulary environment (if it has its own requirements)
if [[ -d "vocabulary" && -f "vocabulary/requirements.txt" ]]; then
    echo ""
    echo "📚 Setting up vocabulary environment..."
    echo "   Vocabulary requirements will be installed in main environment"
fi

echo ""
echo "🎉 Environment setup completed successfully!"

# Create test script
echo ""
echo "📝 Creating test script..."
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
echo "📋 ArXiv Downloader Environment Summary:"
echo "   📁 Main directory (/) - ArXiv paper downloader with keyword extraction → 📄 ArXiv Downloader"
echo "   📚 Vocabulary (/vocabulary) - Keyword extraction tools → 🔍 Keyword Extractor"
echo ""
echo "💡 Usage:"
echo "   - Navigate to the directory to automatically activate the environment (with direnv)"
echo "   - Use 'source .venv/bin/activate' to manually activate"
echo "   - Use 'direnv allow' to permit the .envrc file if prompted"
echo "   - Run 'python test_setup.py' to verify the setup"
echo ""
echo "🚀 Getting Started:"
echo "   - Download papers: python arxiv_downloader.py <url_file>"
echo "   - Extract keywords: python vocabulary/example_usage.py"
echo "   - Organize papers: python check_and_move_papers_enhanced.py"
echo ""
echo "🔧 To customize the environment:"
echo "   - Edit .envrc file for direnv configuration"
echo "   - Modify requirements.txt or vocabulary/requirements.txt as needed"
echo "   - Run 'direnv reload' after making changes to .envrc"