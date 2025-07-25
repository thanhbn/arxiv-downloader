#!/bin/bash
# Universal environment setup script for ArXiv Downloader
# Can be sourced by other scripts to ensure proper environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR=".venv"
PYTHON_CMD="python3"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if we're in virtual environment
in_venv() {
    [[ "$VIRTUAL_ENV" != "" ]]
}

# Function to activate virtual environment
activate_venv() {
    if in_venv; then
        return 0
    fi
    
    if [ -f "$PROJECT_ROOT/$VENV_DIR/bin/activate" ]; then
        source "$PROJECT_ROOT/$VENV_DIR/bin/activate"
        return 0
    fi
    
    return 1
}

# Function to create virtual environment
create_venv() {
    if ! command_exists $PYTHON_CMD; then
        echo -e "${RED}❌ Error: $PYTHON_CMD not found. Please install Python 3.7+${NC}" >&2
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Virtual environment created${NC}" >&2
    else
        echo -e "${RED}❌ Failed to create virtual environment${NC}" >&2
        exit 1
    fi
}

# Function to ensure environment is ready
ensure_env() {
    local quiet=${1:-false}
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Try to activate existing virtual environment
    if ! activate_venv; then
        if [ "$quiet" = "false" ]; then
            echo -e "${YELLOW}📦 Virtual environment not found, creating...${NC}" >&2
        fi
        create_venv
        activate_venv
    fi
    
    # Set Python path
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Set ArXiv-specific variables
    export ARXIV_DOWNLOAD_DIR="$PROJECT_ROOT"
    export ARXIV_RATE_LIMIT=3
    
    if [ "$quiet" = "false" ]; then
        echo -e "${GREEN}✅ Environment ready${NC}" >&2
        echo -e "${BLUE}🐍 Python: $(which python)${NC}" >&2
        echo -e "${BLUE}📦 Virtual env: $VIRTUAL_ENV${NC}" >&2
    fi
}

# Function to install package if not present
ensure_package() {
    local package="$1"
    local import_name="${2:-$package}"
    
    if ! python -c "import $import_name" >/dev/null 2>&1; then
        echo -e "${BLUE}📦 Installing $package...${NC}" >&2
        pip install "$package"
    fi
}

# Main function - can be called by other scripts
setup_arxiv_env() {
    local quiet=${1:-false}
    ensure_env "$quiet"
}

# If script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo -e "${BLUE}🚀 ArXiv Downloader Environment Setup${NC}"
    echo "================================================"
    setup_arxiv_env false
    echo -e "${GREEN}🎉 Environment setup complete!${NC}"
    echo ""
    echo -e "${BLUE}💡 Usage in other scripts:${NC}"
    echo "  source scripts/setup_env_common.sh"
    echo "  setup_arxiv_env true  # quiet mode"
fi