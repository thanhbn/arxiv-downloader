#!/bin/bash
# Install Google Drive API dependencies with virtual environment support

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

echo -e "${BLUE}🚀 ArXiv Downloader - Google Drive Dependencies Installer${NC}"
echo "=================================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to activate virtual environment
activate_venv() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo -e "${GREEN}✅ Virtual environment already active: $VIRTUAL_ENV${NC}"
        return 0
    fi
    
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${BLUE}🔄 Activating virtual environment...${NC}"
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
        return 0
    fi
    
    return 1
}

# Function to create virtual environment
create_venv() {
    echo -e "${BLUE}📦 Creating virtual environment in $VENV_DIR...${NC}"
    
    if ! command_exists $PYTHON_CMD; then
        echo -e "${RED}❌ Error: $PYTHON_CMD not found. Please install Python 3.7+${NC}"
        exit 1
    fi
    
    # Check Python version
    python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo -e "${BLUE}🐍 Using Python $python_version${NC}"
    
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Virtual environment created successfully${NC}"
    else
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
}

# Function to setup direnv if available
setup_direnv() {
    if command_exists direnv; then
        echo -e "${BLUE}🔧 Setting up direnv integration...${NC}"
        
        # Create or update .envrc file
        if [ ! -f ".envrc" ]; then
            cat > .envrc << 'EOF'
#!/bin/bash
# Auto-activate virtual environment for ArXiv Downloader

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🔄 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Add project root to Python path
export PYTHONPATH="$PWD:$PYTHONPATH"

# Custom prompt to show we're in ArXiv environment
export PS1="(arxiv-env) $PS1"

echo "✅ ArXiv Downloader environment activated"
echo "📁 Working directory: $PWD"
echo "🐍 Python: $(which python)"
echo "📦 Virtual env: $VIRTUAL_ENV"
EOF
            chmod +x .envrc
            echo -e "${GREEN}✅ Created .envrc file${NC}"
        else
            echo -e "${YELLOW}⚠️  .envrc already exists, skipping creation${NC}"
        fi
        
        # Allow direnv for this directory
        echo -e "${BLUE}🔓 Allowing direnv for this directory...${NC}"
        direnv allow .
        
        echo -e "${GREEN}✅ Direnv setup complete${NC}"
        echo -e "${BLUE}💡 Tip: Run 'direnv reload' to refresh environment${NC}"
    else
        echo -e "${YELLOW}⚠️  direnv not found. Install direnv for automatic environment activation:${NC}"
        echo -e "${YELLOW}   Ubuntu/Debian: sudo apt install direnv${NC}"
        echo -e "${YELLOW}   macOS: brew install direnv${NC}"
        echo -e "${YELLOW}   Then add 'eval \"\$(direnv hook bash)\"' to your ~/.bashrc${NC}"
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${BLUE}📥 Installing Google Drive API dependencies...${NC}"
    
    # Upgrade pip first
    pip install --upgrade pip
    
    # Install required packages
    local packages=(
        "google-api-python-client"
        "google-auth"
        "google-auth-oauthlib"
        "google-auth-httplib2"
    )
    
    for package in "${packages[@]}"; do
        echo -e "${BLUE}📦 Installing $package...${NC}"
        pip install "$package"
    done
    
    # Also install some useful optional packages
    echo -e "${BLUE}📦 Installing optional packages for better experience...${NC}"
    pip install tqdm  # For better progress bars
    
    echo -e "${GREEN}✅ All dependencies installed successfully!${NC}"
}

# Function to verify installation
verify_installation() {
    echo -e "${BLUE}🔍 Verifying installation...${NC}"
    
    python3 -c "
import sys
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    print('✅ Google Drive API libraries imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
    
try:
    import tqdm
    print('✅ tqdm (progress bars) available')
except ImportError:
    print('⚠️  tqdm not available (optional)')
"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Installation verification passed${NC}"
    else
        echo -e "${RED}❌ Installation verification failed${NC}"
        exit 1
    fi
}

# Main installation process
main() {
    echo -e "${BLUE}🔍 Checking current environment...${NC}"
    
    # Try to activate existing virtual environment
    if ! activate_venv; then
        echo -e "${YELLOW}📦 Virtual environment not found or not active${NC}"
        
        # Ask user if they want to create a virtual environment
        read -p "🤔 Create virtual environment? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}⚠️  Continuing without virtual environment...${NC}"
        else
            create_venv
            activate_venv
        fi
    fi
    
    # Setup direnv integration
    setup_direnv
    
    # Install dependencies
    install_dependencies
    
    # Verify installation
    verify_installation
    
    # Final instructions
    echo ""
    echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
    echo "=================================================================="
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo "1. 📖 Follow the setup guide: ${YELLOW}cat GOOGLE_DRIVE_SETUP.md${NC}"
    echo "2. 🔑 Download service account key as: ${YELLOW}service-account-key.json${NC}"
    echo "3. 🚀 Run upload script: ${YELLOW}python3 scripts/upload_to_drive.py --folder-id YOUR_ID${NC}"
    echo ""
    
    if command_exists direnv; then
        echo -e "${BLUE}💡 Environment Tips:${NC}"
        echo "• 🔄 Reload environment: ${YELLOW}direnv reload${NC}"
        echo "• 🚪 Environment auto-activates when entering directory"
        echo "• 🐍 Python path includes project root automatically"
    else
        echo -e "${BLUE}💡 Manual Activation:${NC}"
        echo "• 🔄 Activate manually: ${YELLOW}source .venv/bin/activate${NC}"
        echo "• 🚪 Deactivate: ${YELLOW}deactivate${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✨ Happy uploading!${NC}"
}

# Run main function
main "$@"