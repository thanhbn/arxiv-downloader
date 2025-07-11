#!/usr/bin/env python3
"""
ArXiv Downloader Project Initialization Script
===============================================

This script helps newcomers set up the ArXiv Downloader project by:
- Checking system requirements
- Installing dependencies
- Setting up the virtual environment
- Configuring direnv
- Installing shell autocompletion
- Creating initial configuration files
- Running setup verification

Perfect for first-time users who want to get started quickly.

Usage:
    python3 init_project.py              # Interactive setup
    python3 init_project.py --quick       # Quick setup with defaults
    python3 init_project.py --full        # Full setup with all features
    python3 init_project.py --help        # Show help
"""

import os
import sys
import subprocess
import argparse
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time

class Colors:
    """Terminal color codes for better UX."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ProjectInitializer:
    """Initialize the ArXiv Downloader project for new users."""
    
    def __init__(self, quick: bool = False, full: bool = False):
        self.quick = quick
        self.full = full
        self.interactive = not (quick or full)
        
        self.project_dir = Path.cwd()
        self.venv_dir = self.project_dir / ".venv"
        self.system_info = self.detect_system()
        
        # Track what we've done for final summary
        self.completed_steps = []
        self.failed_steps = []
        self.skipped_steps = []
        
        # Configuration
        self.config = {
            'python_version': '3.9',
            'create_venv': True,
            'install_deps': True,
            'setup_direnv': True,
            'install_completion': True,
            'run_tests': True,
            'create_config': True
        }
    
    def detect_system(self) -> Dict[str, str]:
        """Detect system information."""
        return {
            'os': platform.system().lower(),
            'arch': platform.machine(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
            'shell': os.environ.get('SHELL', '').split('/')[-1],
            'user': os.environ.get('USER', 'unknown')
        }
    
    def print_header(self, text: str):
        """Print a colorful header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    
    def print_step(self, step: str, status: str = "running"):
        """Print a step with status."""
        if status == "running":
            print(f"{Colors.OKCYAN}🔄 {step}...{Colors.ENDC}")
        elif status == "success":
            print(f"{Colors.OKGREEN}✅ {step}{Colors.ENDC}")
            self.completed_steps.append(step)
        elif status == "warning":
            print(f"{Colors.WARNING}⚠️  {step}{Colors.ENDC}")
            self.skipped_steps.append(step)
        elif status == "error":
            print(f"{Colors.FAIL}❌ {step}{Colors.ENDC}")
            self.failed_steps.append(step)
    
    def ask_user(self, question: str, default: bool = True) -> bool:
        """Ask user a yes/no question."""
        if not self.interactive:
            return default
        
        default_str = "Y/n" if default else "y/N"
        while True:
            try:
                response = input(f"{Colors.OKCYAN}❓ {question} ({default_str}): {Colors.ENDC}").strip().lower()
                if not response:
                    return default
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                else:
                    print("Please answer 'y' or 'n'")
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
                sys.exit(1)
    
    def run_command(self, cmd: List[str], description: str = "", check: bool = True) -> bool:
        """Run a command and return success status."""
        try:
            if description:
                self.print_step(description, "running")
            
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )
            
            if result.returncode == 0:
                if description:
                    self.print_step(description, "success")
                return True
            else:
                if description:
                    self.print_step(f"{description} - {result.stderr.strip()}", "error")
                return False
                
        except subprocess.CalledProcessError as e:
            if description:
                self.print_step(f"{description} - {e.stderr.strip()}", "error")
            return False
        except Exception as e:
            if description:
                self.print_step(f"{description} - {str(e)}", "error")
            return False
    
    def check_requirements(self) -> bool:
        """Check system requirements."""
        self.print_step("Checking system requirements", "running")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.print_step("Python 3.8+ required", "error")
            return False
        
        # Check git
        if not shutil.which('git'):
            self.print_step("Git not found - some features may not work", "warning")
        
        # Check pip
        if not shutil.which('pip') and not shutil.which('pip3'):
            self.print_step("pip not found", "error")
            return False
        
        self.print_step("System requirements check passed", "success")
        return True
    
    def setup_virtual_environment(self) -> bool:
        """Setup Python virtual environment."""
        if not self.config['create_venv']:
            return True
            
        self.print_step("Setting up virtual environment", "running")
        
        # Create virtual environment
        if self.venv_dir.exists():
            if self.interactive:
                overwrite = self.ask_user("Virtual environment exists. Recreate?", False)
                if overwrite:
                    shutil.rmtree(self.venv_dir)
                else:
                    self.print_step("Using existing virtual environment", "success")
                    return True
            else:
                self.print_step("Using existing virtual environment", "success")
                return True
        
        # Create new venv
        success = self.run_command(
            [sys.executable, "-m", "venv", str(self.venv_dir)],
            "Creating virtual environment"
        )
        
        if not success:
            return False
        
        # Test activation
        venv_python = self.venv_dir / "bin" / "python"
        if not venv_python.exists():
            venv_python = self.venv_dir / "Scripts" / "python.exe"  # Windows
        
        if venv_python.exists():
            self.print_step("Virtual environment created successfully", "success")
            return True
        else:
            self.print_step("Virtual environment creation failed", "error")
            return False
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        if not self.config['install_deps']:
            return True
            
        self.print_step("Installing dependencies", "running")
        
        # Get pip path
        pip_path = self.venv_dir / "bin" / "pip"
        if not pip_path.exists():
            pip_path = self.venv_dir / "Scripts" / "pip.exe"  # Windows
        
        if not pip_path.exists():
            pip_path = "pip3"  # Fallback to system pip
        
        # Upgrade pip first
        success = self.run_command(
            [str(pip_path), "install", "--upgrade", "pip"],
            "Upgrading pip"
        )
        
        if not success:
            return False
        
        # Install main requirements
        req_file = self.project_dir / "requirements.txt"
        if req_file.exists():
            success = self.run_command(
                [str(pip_path), "install", "-r", str(req_file)],
                "Installing main requirements"
            )
            if not success:
                return False
        else:
            # Install essential packages
            essential_packages = [
                "requests>=2.28.0",
                "beautifulsoup4>=4.11.0", 
                "tqdm>=4.64.0",
                "aiohttp>=3.8.0",
                "aiofiles>=22.1.0",
                "PyPDF2>=3.0.0",
                "pdfplumber>=0.7.0"
            ]
            
            success = self.run_command(
                [str(pip_path), "install"] + essential_packages,
                "Installing essential packages"
            )
            
            if success:
                # Create requirements.txt
                with open(req_file, 'w') as f:
                    f.write('\n'.join(essential_packages) + '\n')
                self.print_step("Created requirements.txt", "success")
        
        return success
    
    def setup_direnv(self) -> bool:
        """Setup direnv configuration."""
        if not self.config['setup_direnv']:
            return True
            
        self.print_step("Setting up direnv", "running")
        
        # Check if direnv is installed
        if not shutil.which('direnv'):
            self.print_step("direnv not found - skipping direnv setup", "warning")
            print(f"{Colors.WARNING}   Install direnv with:{Colors.ENDC}")
            if self.system_info['os'] == 'linux':
                print(f"{Colors.WARNING}   sudo apt install direnv{Colors.ENDC}")
            elif self.system_info['os'] == 'darwin':
                print(f"{Colors.WARNING}   brew install direnv{Colors.ENDC}")
            print(f"{Colors.WARNING}   Then add to shell config: eval \"$(direnv hook bash)\"{Colors.ENDC}")
            return True
        
        # Create .envrc file
        envrc_file = self.project_dir / ".envrc"
        envrc_content = f"""#!/bin/bash
# ArXiv Downloader Environment Configuration
# Auto-generated by init_project.py

# Activate Python virtual environment
source .venv/bin/activate

# Set project-specific environment variables
export PYTHONPATH="$PWD:$PYTHONPATH"
export ARXIV_DOWNLOAD_DIR="$PWD"
export ARXIV_RATE_LIMIT=3

# Optional: Set OpenAI API key for translation features
# export OPENAI_API_KEY="your-api-key-here"

# Optional: Set Claude API key for translation features  
# export ANTHROPIC_API_KEY="your-api-key-here"

echo "🚀 ArXiv Downloader environment activated"
echo "   Python: $(python --version)"
echo "   Virtual env: {self.venv_dir.name}"
"""
        
        with open(envrc_file, 'w') as f:
            f.write(envrc_content)
        
        # Make it executable
        envrc_file.chmod(0o755)
        
        # Allow direnv
        success = self.run_command(
            ["direnv", "allow"],
            "Allowing direnv configuration"
        )
        
        if success:
            self.print_step("direnv configuration completed", "success")
            return True
        else:
            self.print_step("direnv setup failed", "error")
            return False
    
    def setup_autocompletion(self) -> bool:
        """Setup shell autocompletion."""
        if not self.config['install_completion']:
            return True
            
        completion_script = self.project_dir / "setup_autocompletion.py"
        if not completion_script.exists():
            self.print_step("Autocompletion script not found - skipping", "warning")
            return True
        
        self.print_step("Setting up shell autocompletion", "running")
        
        # Run autocompletion setup
        success = self.run_command(
            [sys.executable, str(completion_script), "--install"],
            "Installing shell autocompletion"
        )
        
        if success:
            self.print_step("Autocompletion setup completed", "success")
            return True
        else:
            self.print_step("Autocompletion setup failed", "warning")
            return True  # Not critical
    
    def create_config_files(self) -> bool:
        """Create initial configuration files."""
        if not self.config['create_config']:
            return True
            
        self.print_step("Creating configuration files", "running")
        
        # Create basic config
        config_data = {
            "project_name": "arxiv-downloader",
            "version": "1.0.0",
            "python_version": self.system_info['python_version'],
            "setup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.system_info['user'],
            "system": self.system_info['os'],
            "default_settings": {
                "download_workers": 1,
                "rate_limit_seconds": 3,
                "output_format": "pdf",
                "auto_convert_to_txt": False,
                "translation_enabled": False
            }
        }
        
        config_file = self.project_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Create .gitignore if it doesn't exist
        gitignore_file = self.project_dir / ".gitignore"
        if not gitignore_file.exists():
            gitignore_content = """# ArXiv Downloader
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# API Keys
.env
.env.local
.env.production
.env.development

# Downloaded papers
*.pdf
*_vi.txt
translation_queue.txt
translation_manager.log
processing_results*.log

# Backup files
backup/
"""
            with open(gitignore_file, 'w') as f:
                f.write(gitignore_content)
        
        self.print_step("Configuration files created", "success")
        return True
    
    def run_tests(self) -> bool:
        """Run setup verification tests."""
        if not self.config['run_tests']:
            return True
            
        self.print_step("Running setup verification", "running")
        
        # Test basic imports
        test_script = self.project_dir / "test_setup.py"
        if test_script.exists():
            success = self.run_command(
                [sys.executable, str(test_script)],
                "Running setup tests"
            )
            return success
        else:
            # Basic import test
            python_path = self.venv_dir / "bin" / "python"
            if not python_path.exists():
                python_path = self.venv_dir / "Scripts" / "python.exe"
            
            if python_path.exists():
                test_cmd = [
                    str(python_path), "-c", 
                    "import requests, bs4, tqdm; print('✅ Basic imports successful')"
                ]
                success = self.run_command(test_cmd, "Testing basic imports")
                return success
            else:
                self.print_step("Could not find Python executable for testing", "warning")
                return True
    
    def print_summary(self):
        """Print setup summary."""
        self.print_header("SETUP SUMMARY")
        
        if self.completed_steps:
            print(f"{Colors.OKGREEN}✅ Completed Steps:{Colors.ENDC}")
            for step in self.completed_steps:
                print(f"   • {step}")
        
        if self.skipped_steps:
            print(f"\n{Colors.WARNING}⚠️  Skipped Steps:{Colors.ENDC}")
            for step in self.skipped_steps:
                print(f"   • {step}")
        
        if self.failed_steps:
            print(f"\n{Colors.FAIL}❌ Failed Steps:{Colors.ENDC}")
            for step in self.failed_steps:
                print(f"   • {step}")
        
        print(f"\n{Colors.HEADER}🎉 SETUP COMPLETE!{Colors.ENDC}")
        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print(f"1. {Colors.OKCYAN}Restart your shell{Colors.ENDC} (or run: source ~/.bashrc)")
        print(f"2. {Colors.OKCYAN}Test the CLI:{Colors.ENDC} python3 arxivdl_cli.py --help")
        print(f"3. {Colors.OKCYAN}Try downloading papers:{Colors.ENDC} python3 arxivdl_cli.py download --help")
        print(f"4. {Colors.OKCYAN}View samples:{Colors.ENDC} python3 arxivdl_cli.py --samples")
        
        if self.venv_dir.exists():
            print(f"\n{Colors.BOLD}Virtual Environment:{Colors.ENDC}")
            print(f"   Activate: {Colors.OKCYAN}source .venv/bin/activate{Colors.ENDC}")
            print(f"   Deactivate: {Colors.OKCYAN}deactivate{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Documentation:{Colors.ENDC}")
        print(f"   Read: {Colors.OKCYAN}CLAUDE.md{Colors.ENDC} for detailed usage")
        print(f"   Help: {Colors.OKCYAN}python3 arxivdl_cli.py --help{Colors.ENDC}")
        print(f"   Examples: {Colors.OKCYAN}python3 arxivdl_cli.py --samples{Colors.ENDC}")
    
    def get_user_preferences(self):
        """Get user preferences for setup."""
        if not self.interactive:
            return
            
        self.print_header("SETUP PREFERENCES")
        
        print(f"{Colors.BOLD}Let's configure your setup preferences:{Colors.ENDC}")
        
        self.config['create_venv'] = self.ask_user(
            "Create Python virtual environment?", True
        )
        
        self.config['install_deps'] = self.ask_user(
            "Install Python dependencies?", True
        )
        
        self.config['setup_direnv'] = self.ask_user(
            "Setup direnv for automatic environment activation?", True
        )
        
        self.config['install_completion'] = self.ask_user(
            "Install shell autocompletion?", True
        )
        
        self.config['run_tests'] = self.ask_user(
            "Run setup verification tests?", True
        )
        
        self.config['create_config'] = self.ask_user(
            "Create configuration files?", True
        )
    
    def welcome_message(self):
        """Display welcome message."""
        self.print_header("ARXIV DOWNLOADER PROJECT SETUP")
        
        print(f"{Colors.BOLD}Welcome to the ArXiv Downloader Project!{Colors.ENDC}")
        print(f"\nThis script will help you set up the project by:")
        print(f"  📦 Creating a Python virtual environment")
        print(f"  🔧 Installing dependencies")
        print(f"  🌍 Configuring direnv (if available)")
        print(f"  ⚡ Setting up shell autocompletion")
        print(f"  📋 Creating configuration files")
        print(f"  🧪 Running setup verification tests")
        
        print(f"\n{Colors.BOLD}System Information:{Colors.ENDC}")
        print(f"  OS: {self.system_info['os']} ({self.system_info['arch']})")
        print(f"  Python: {self.system_info['python_version']}")
        print(f"  Shell: {self.system_info['shell']}")
        print(f"  User: {self.system_info['user']}")
        
        if self.interactive:
            print(f"\n{Colors.OKCYAN}Press Enter to continue or Ctrl+C to cancel...{Colors.ENDC}")
            try:
                input()
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
                sys.exit(1)
    
    def run(self):
        """Run the complete setup process."""
        self.welcome_message()
        
        # Configure based on mode
        if self.quick:
            print(f"\n{Colors.BOLD}Running quick setup with defaults...{Colors.ENDC}")
        elif self.full:
            print(f"\n{Colors.BOLD}Running full setup with all features...{Colors.ENDC}")
        else:
            self.get_user_preferences()
        
        # Run setup steps
        steps = [
            ("Check system requirements", self.check_requirements),
            ("Setup virtual environment", self.setup_virtual_environment),
            ("Install dependencies", self.install_dependencies),
            ("Setup direnv", self.setup_direnv),
            ("Setup autocompletion", self.setup_autocompletion),
            ("Create configuration files", self.create_config_files),
            ("Run verification tests", self.run_tests)
        ]
        
        print(f"\n{Colors.BOLD}Starting setup process...{Colors.ENDC}")
        
        for step_name, step_func in steps:
            try:
                success = step_func()
                if not success and step_name in ["Check system requirements", "Setup virtual environment"]:
                    print(f"{Colors.FAIL}Critical step failed: {step_name}{Colors.ENDC}")
                    print(f"{Colors.FAIL}Setup cannot continue.{Colors.ENDC}")
                    sys.exit(1)
            except Exception as e:
                self.print_step(f"{step_name} - {str(e)}", "error")
                if step_name in ["Check system requirements", "Setup virtual environment"]:
                    sys.exit(1)
        
        # Print final summary
        self.print_summary()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Initialize ArXiv Downloader project for new users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 init_project.py              # Interactive setup
    python3 init_project.py --quick       # Quick setup with defaults
    python3 init_project.py --full        # Full setup with all features
    
This script is perfect for newcomers who want to get started quickly
with the ArXiv Downloader project. It handles all the setup steps
automatically and provides a great user experience.
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick setup with sensible defaults (no prompts)'
    )
    
    group.add_argument(
        '--full', '-f',
        action='store_true',
        help='Full setup with all features enabled'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='ArXiv Downloader Project Initializer 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Create and run initializer
    initializer = ProjectInitializer(
        quick=args.quick,
        full=args.full
    )
    
    try:
        initializer.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Setup failed with error: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()