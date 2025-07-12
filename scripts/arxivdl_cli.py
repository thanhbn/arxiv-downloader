#!/usr/bin/env python3
"""
ArXiv Downloader CLI - Unified Command Interface
================================================

A comprehensive command-line interface that wraps all ArXiv downloader tools
and provides easy access to their functionality through a single entry point.

Usage:
    python3 arxivdl_cli.py [COMMAND] [OPTIONS]
    python3 arxivdl_cli.py --help
    python3 arxivdl_cli.py --samples
    python3 arxivdl_cli.py --list

Commands:
    download      Download papers from ArXiv
    convert       Convert PDFs to TXT format
    translate     Translate papers to Vietnamese
    organize      Organize papers across collections
    analyze       Analyze collections and translations
    inventory     Create paper inventories
    setup         Setup and configuration tools
    workflow      End-to-end workflow examples
    
Examples:
    python3 arxivdl_cli.py download CoT.txt
    python3 arxivdl_cli.py convert --all
    python3 arxivdl_cli.py translate --check
    python3 arxivdl_cli.py workflow
    python3 arxivdl_cli.py --samples
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ArXivCLI:
    """Unified CLI for ArXiv downloader tools."""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent / "scripts"
        self.commands = self._discover_commands()
        self.samples = self._load_samples()
    
    def _discover_commands(self) -> Dict[str, Dict]:
        """Discover available commands and their scripts."""
        return {
            'download': {
                'description': 'Download papers from ArXiv URLs',
                'scripts': {
                    'single': 'arxiv_downloader.py',
                    'batch': 'arxiv_orchestrator.py',
                    'crawler': 'huggingface_crawler.py'
                },
                'default': 'arxiv_downloader.py',
                'help': 'Download papers from ArXiv with rate limiting and parallel processing'
            },
            'convert': {
                'description': 'Convert PDFs to TXT format',
                'scripts': {
                    'main': 'pdf_to_txt_converter.py'
                },
                'default': 'pdf_to_txt_converter.py',
                'help': 'Convert PDF papers to searchable text with intelligent renaming'
            },
            'translate': {
                'description': 'Translate papers to Vietnamese',
                'scripts': {
                    'claude': 'translate_manager.py',
                    'openai': 'translate_papers.py',
                    'check': 'check_translation_completeness.py',
                    'queue': 'add_to_translation_queue.py',
                    'cleanup': 'cleanup_translations.py',
                    'stalled': 'process_stalled_translations.py',
                    'test': 'test_translation.py'
                },
                'default': 'translate_manager.py',
                'help': 'Translate papers using Claude API or OpenAI, with quality checking and queue management'
            },
            'organize': {
                'description': 'Organize papers across collections',
                'scripts': {
                    'enhanced': 'check_and_move_papers_enhanced.py',
                    'basic': 'check_and_move_papers.py',
                    'simple': 'organize_papers.py'
                },
                'default': 'check_and_move_papers_enhanced.py',
                'help': 'Organize papers into correct collections with comprehensive logging'
            },
            'analyze': {
                'description': 'Analyze collections and translations',
                'scripts': {
                    'duplicates': 'arxiv_duplicate_analyzer.py',
                    'translations': 'check_bad_translations.py',
                    'monitor': 'monitor_translation.py',
                    'status': 'simple_status_checker.py'
                },
                'default': 'arxiv_duplicate_analyzer.py',
                'help': 'Analyze paper collections for duplicates and translation quality'
            },
            'inventory': {
                'description': 'Create paper inventories',
                'scripts': {
                    'all': 'inventory_all_papers.py',
                    'expected': 'inventory_expected_papers.py',
                    'quick': 'quick_inventory.py'
                },
                'default': 'inventory_all_papers.py',
                'help': 'Create comprehensive inventories of paper collections'
            },
            'setup': {
                'description': 'Setup and configuration tools',
                'scripts': {
                    'init': 'init_project.py',
                    'env': 'setup_env.sh',
                    'simple': 'setup_simple.sh',
                    'test': 'test_setup.py',
                    'direnv': 'setup_direnv_fixed.sh',
                    'completion': 'setup_autocompletion.py'
                },
                'default': 'init_project.py',
                'help': 'Setup development environment, dependencies, and direnv configuration'
            },
            'workflow': {
                'description': 'End-to-end workflow examples',
                'scripts': {
                    'help': 'workflow_help.py'
                },
                'default': 'workflow_help.py',
                'help': 'Complete business use case workflows from paper discovery to translation'
            }
        }
    
    def _load_samples(self) -> Dict[str, List[str]]:
        """Load sample commands for each category."""
        return {
            'download': [
                # Basic single collection downloads
                'python3 arxiv_downloader.py CoT.txt',
                'python3 arxiv_downloader.py RAG.txt',
                'python3 arxiv_downloader.py Benchmark.txt',
                'python3 arxiv_downloader.py icl.txt',
                
                # Downloads with custom directories and worker counts
                'python3 arxiv_downloader.py multimodal/arxiv_links.txt 1 multimodal',
                'python3 arxiv_downloader.py peft/arxiv_links.txt 1 peft',
                'python3 arxiv_downloader.py quantization/arxiv_links.txt 1 quantization',
                
                # ArXiv compliant downloads (1 worker, proper delays)
                'python3 arxiv_downloader.py diffusion/arxiv_links.txt 1',
                'python3 arxiv_downloader.py attention/arxiv_links.txt 1',
                'python3 arxiv_downloader.py interpretability/arxiv_links.txt 1',
                
                # Batch orchestrator examples
                'python3 arxiv_orchestrator.py 1 1',
                'python3 arxiv_orchestrator.py',
                
                # Specialized crawlers
                'python3 huggingface_crawler.py',
                
                # Shell script fallback examples
                './download_arxiv.sh CoT.txt ./papers/CoT',
                './download_arxiv.sh RAG.txt ./papers/RAG',
                './download_arxiv.sh multimodal/arxiv_links.txt ./papers/multimodal'
            ],
            'convert': [
                # Convert all collections
                'python3 pdf_to_txt_converter.py --all',
                
                # Convert specific collections with both conversion and renaming
                'python3 pdf_to_txt_converter.py --both --collection multimodal',
                'python3 pdf_to_txt_converter.py --both --collection CoT',
                'python3 pdf_to_txt_converter.py --both --collection RAG',
                'python3 pdf_to_txt_converter.py --both --collection peft',
                'python3 pdf_to_txt_converter.py --both --collection quantization',
                
                # Convert only (no renaming)
                'python3 pdf_to_txt_converter.py --convert --collection diffusion',
                'python3 pdf_to_txt_converter.py --convert --collection attention',
                'python3 pdf_to_txt_converter.py --convert --collection interpretability',
                
                # Rename only (recheck existing files)
                'python3 pdf_to_txt_converter.py --rename --collection multilingual',
                'python3 pdf_to_txt_converter.py --rename --collection long-context',
                'python3 pdf_to_txt_converter.py --rename --collection knowledge-graph',
                
                # Interactive mode
                'python3 pdf_to_txt_converter.py',
                
                # Get help
                'python3 pdf_to_txt_converter.py --help'
            ],
            'translate': [
                # Basic translation with different worker counts
                'python3 translate_manager.py --workers 1',
                'python3 translate_manager.py --workers 2',
                'python3 translate_manager.py --workers 4',
                
                # OpenAI translator
                'python3 translate_papers.py',
                
                # Check translation completeness with different thresholds
                'python3 check_translation_completeness.py --threshold 0.3',
                'python3 check_translation_completeness.py --threshold 0.5',
                'python3 check_translation_completeness.py --threshold 0.7',
                'python3 check_translation_completeness.py --threshold 0.9',
                
                # Generate completeness reports
                'python3 check_translation_completeness.py --output completeness_report.md',
                'python3 check_translation_completeness.py --threshold 0.6 --output completeness_report.md',
                
                # Add incomplete translations to queue
                'python3 check_translation_completeness.py --add-to-queue --threshold 0.6',
                'python3 check_translation_completeness.py --add-to-queue --threshold 0.4',
                
                # Remove big papers from queue
                'python3 check_translation_completeness.py --remove-big-papers translation_queue_big_file.txt',
                'python3 check_translation_completeness.py --add-to-queue --remove-big-papers translation_queue_big_file.txt --threshold 0.7',
                
                # Manual queue management
                'python3 add_to_translation_queue.py',
                
                # Cleanup low-quality translations
                'python3 cleanup_translations.py --threshold 0.1',
                'python3 cleanup_translations.py --threshold 0.2 --backup',
                'python3 cleanup_translations.py --threshold 0.1 --requeue',
                
                # Process stalled translations (uses 0.4 threshold by default)
                'python3 process_stalled_translations.py',
                'python3 process_stalled_translations.py --execute',
                'python3 process_stalled_translations.py --max-age 24',
                'python3 process_stalled_translations.py --execute --max-age 48',
                'python3 process_stalled_translations.py --score 0.3',
                'python3 process_stalled_translations.py --execute --score 0.5',
                
                # Test translation setup
                'python3 test_translation.py'
            ],
            'organize': [
                # Enhanced organization with execution
                'python3 check_and_move_papers_enhanced.py --execute',
                'python3 check_and_move_papers_enhanced.py --execute --verbose',
                'python3 check_and_move_papers_enhanced.py --execute --log-level INFO',
                
                # Dry run (preview mode)
                'python3 check_and_move_papers_enhanced.py',
                'python3 check_and_move_papers_enhanced.py --verbose',
                'python3 check_and_move_papers_enhanced.py --verbose --log-level DEBUG',
                
                # Specific collections
                'python3 check_and_move_papers_enhanced.py --collections multimodal',
                'python3 check_and_move_papers_enhanced.py --collections multimodal rag peft',
                'python3 check_and_move_papers_enhanced.py --collections CoT RAG Benchmark',
                
                # Logging options
                'python3 check_and_move_papers_enhanced.py --log-file organization.log',
                'python3 check_and_move_papers_enhanced.py --execute --log-file full_organization.log',
                'python3 check_and_move_papers_enhanced.py --verbose --log-level INFO --log-file detailed.log',
                
                # Basic organizer
                'python3 organize_papers.py',
                
                # Legacy organizer
                'python3 check_and_move_papers.py'
            ],
            'analyze': [
                # Duplicate analysis
                'python3 arxiv_duplicate_analyzer.py',
                'python3 arxiv_duplicate_analyzer.py --verbose',
                'python3 arxiv_duplicate_analyzer.py --verbose --output-file duplicates.txt',
                'python3 arxiv_duplicate_analyzer.py --output-file duplicates_report.txt',
                
                # Translation quality analysis
                'python3 check_bad_translations.py',
                'python3 check_bad_translations.py --verbose',
                
                # Translation monitoring
                'python3 monitor_translation.py',
                'python3 monitor_translation.py --continuous',
                
                # Status checking
                'python3 check_status.py',
                'python3 check_status.py --detailed',
                
                # Paper analysis
                'python3 analyze_papers.py',
                'python3 analyze_papers.py --collection multimodal',
                'python3 analyze_papers.py --collection CoT --detailed'
            ],
            'inventory': [
                # Complete inventory
                'python3 inventory_all_papers.py',
                'python3 inventory_all_papers.py --verbose',
                'python3 inventory_all_papers.py --output-file complete_inventory.txt',
                
                # Expected papers inventory
                'python3 inventory_expected_papers.py',
                'python3 inventory_expected_papers.py --collection multimodal',
                'python3 inventory_expected_papers.py --collection CoT RAG',
                
                # Quick inventory
                'python3 quick_inventory.py',
                'python3 quick_inventory.py --summary',
                
                # Collection-specific inventories
                'python3 inventory_all_papers.py --collections multimodal peft',
                'python3 inventory_expected_papers.py --collections CoT RAG Benchmark',
                
                # Export formats
                'python3 inventory_all_papers.py --format json',
                'python3 inventory_all_papers.py --format csv',
                'python3 inventory_expected_papers.py --format markdown'
            ],
            'setup': [
                # First-time setup (recommended for newbies)
                'python3 init_project.py',
                'python3 init_project.py --quick',
                'python3 init_project.py --full',
                
                # Environment setup
                './setup_env.sh',
                './setup_simple.sh',
                
                # Direnv configuration
                './setup_direnv_fixed.sh',
                
                # Autocompletion setup
                'python3 setup_autocompletion.py',
                'python3 setup_autocompletion.py --install',
                
                # Test setup
                'python3 test_setup.py',
                'python3 test_setup.py --verbose',
                
                # Dependency installation
                'pip install -r requirements.txt',
                'pip install -r requirements-dev.txt',
                
                # Virtual environment setup
                'python3 -m venv .venv',
                'source .venv/bin/activate && pip install -r requirements.txt',
                
                # Git hooks setup
                'pre-commit install',
                'pre-commit run --all-files',
                
                # Configuration validation
                'python3 validate_config.py',
                'python3 validate_config.py --fix-issues'
            ],
            'workflow': [
                # Complete End-to-End Workflow: From Collection Discovery to Translation
                '# === COMPLETE WORKFLOW EXAMPLE ===',
                '# Business Use Case: Process a new research collection from HuggingFace to translated Vietnamese papers',
                '',
                '# Step 1: Discover and crawl papers from HuggingFace collection',
                'python3 huggingface_crawler.py --collection "reinforcement-learning" --output reinforcement-learning',
                '',
                '# Step 2: Create collection directory and arxiv_links.txt',
                'mkdir -p reinforcement-learning',
                'echo "# ArXiv PDF links for reinforcement learning papers" > reinforcement-learning/arxiv_links.txt',
                '# Manual: Add discovered PDF links to reinforcement-learning/arxiv_links.txt',
                '',
                '# Step 3: Download papers from ArXiv (ArXiv compliant - 1 worker)',
                'python3 arxiv_downloader.py reinforcement-learning/arxiv_links.txt 1 reinforcement-learning',
                '',
                '# Step 4: Convert PDFs to text format with proper naming',
                'python3 pdf_to_txt_converter.py --both --collection reinforcement-learning',
                '',
                '# Step 5: Create translation queue from English text files',
                'find reinforcement-learning -name "*.txt" -not -name "*_vi.txt" | head -10 > translation_queue.txt',
                '# Or use: python3 add_to_translation_queue.py --collection reinforcement-learning',
                '',
                '# Step 6: Run translation process with Claude',
                'python3 translate_manager.py --workers 2',
                '',
                '# Step 7: Check translation quality with threshold',
                'python3 check_translation_completeness.py --threshold 0.7',
                '',
                '# Step 8: Backup and remove low-quality Vietnamese translations',
                'mkdir -p backup/low_quality_translations',
                'python3 check_translation_completeness.py --threshold 0.7 --move-vi --backup-dir backup/low_quality_translations',
                '',
                '# Step 9: Add English versions of removed translations back to queue',
                'python3 check_translation_completeness.py --add-to-queue --threshold 0.7',
                '',
                '# Step 10: Re-run translation for failed items',
                'python3 translate_manager.py --workers 1',
                '',
                '# Step 11: Final quality check and organize results',
                'python3 check_translation_completeness.py --threshold 0.8 --move-vi --zip-txt',
                '',
                '# Step 12: Create final inventory and reports',
                'python3 inventory_all_papers.py --collection reinforcement-learning --format json',
                'python3 arxiv_duplicate_analyzer.py --collection reinforcement-learning --output-file rl_duplicates.txt',
                '',
                '# === ALTERNATIVE WORKFLOWS ===',
                '',
                '# Quick Workflow: Process existing collection',
                'python3 arxiv_downloader.py CoT.txt 1 && python3 pdf_to_txt_converter.py --both --collection CoT && python3 translate_manager.py --workers 2',
                '',
                '# Quality Control Workflow: Re-process low quality translations',
                'python3 check_translation_completeness.py --threshold 0.6 --add-to-queue && python3 translate_manager.py --workers 1',
                '',
                '# Batch Processing Workflow: Process multiple collections',
                'python3 arxiv_orchestrator.py 1 1 && python3 pdf_to_txt_converter.py --all && python3 translate_manager.py --workers 4',
                '',
                '# Maintenance Workflow: Organize and clean up',
                'python3 check_and_move_papers_enhanced.py --execute && python3 arxiv_duplicate_analyzer.py && python3 inventory_all_papers.py',
                '',
                '# === WORKFLOW COMMANDS BY PHASE ===',
                '',
                '# Phase 1: Discovery & Download',
                'python3 huggingface_crawler.py && python3 arxiv_downloader.py collection/arxiv_links.txt 1 collection',
                '',
                '# Phase 2: Text Processing',
                'python3 pdf_to_txt_converter.py --both --collection collection && python3 organize_papers.py',
                '',
                '# Phase 3: Translation Pipeline',
                'python3 add_to_translation_queue.py --collection collection && python3 translate_manager.py --workers 2',
                '',
                '# Phase 4: Quality Assurance',
                'python3 check_translation_completeness.py --threshold 0.7 --add-to-queue && python3 translate_manager.py --workers 1',
                '',
                '# Phase 5: Final Processing',
                'python3 check_translation_completeness.py --move-vi --zip-txt && python3 inventory_all_papers.py --format json'
            ]
        }
    
    def show_help(self, command: Optional[str] = None):
        """Show help information."""
        if command and command in self.commands:
            cmd_info = self.commands[command]
            print(f"\n📋 {command.upper()} - {cmd_info['description']}")
            print(f"📝 {cmd_info['help']}")
            print(f"\n🔧 Available Scripts:")
            for variant, script in cmd_info['scripts'].items():
                print(f"  {variant}: {script}")
            print(f"\n🎯 Default: {cmd_info['default']}")
            print(f"\n📚 Sample Commands:")
            for sample in self.samples.get(command, []):
                print(f"  {sample}")
        else:
            print(self.__doc__)
            print("\n🔧 Available Commands:")
            for cmd, info in self.commands.items():
                print(f"  {cmd:<12} {info['description']}")
            print(f"\n💡 Use 'python3 arxivdl_cli.py [COMMAND] --help' for command-specific help")
            print(f"💡 Use 'python3 arxivdl_cli.py --samples' to see all sample commands")
    
    def show_samples(self, command: Optional[str] = None):
        """Show sample commands."""
        if command and command in self.samples:
            print(f"\n📚 Sample Commands for {command.upper()}:")
            if command == 'workflow':
                # Special handling for workflow - show as formatted text
                for sample in self.samples[command]:
                    print(f"  {sample}")
            else:
                for i, sample in enumerate(self.samples[command], 1):
                    print(f"  {i}. {sample}")
        else:
            print("\n📚 All Sample Commands:")
            for cmd, samples in self.samples.items():
                print(f"\n{cmd.upper()}:")
                if cmd == 'workflow':
                    # Special handling for workflow - show as formatted text
                    for sample in samples:
                        print(f"  {sample}")
                else:
                    for i, sample in enumerate(samples, 1):
                        print(f"  {i}. {sample}")
    
    def list_scripts(self):
        """List all available scripts."""
        print("\n📂 Available Scripts:")
        all_scripts = set()
        for cmd_info in self.commands.values():
            all_scripts.update(cmd_info['scripts'].values())
        
        # Add shell scripts
        for script in sorted(self.script_dir.glob("*.sh")):
            all_scripts.add(script.name)
        
        # Add remaining Python scripts
        for script in sorted(self.script_dir.glob("*.py")):
            all_scripts.add(script.name)
        
        for script in sorted(all_scripts):
            if script != 'arxivdl_cli.py':  # Don't list ourselves
                script_path = self.script_dir / script
                if script_path.exists():
                    print(f"  📄 {script}")
    
    def run_command(self, command: str, subcommand: Optional[str] = None, args: List[str] = None):
        """Run a command with the appropriate script."""
        if command not in self.commands:
            print(f"❌ Unknown command: {command}")
            print("💡 Use --help to see available commands")
            return 1
        
        # Special handling for workflow command - just show samples
        if command == 'workflow':
            self.show_samples('workflow')
            return 0
        
        cmd_info = self.commands[command]
        
        # Determine which script to use
        if subcommand and subcommand in cmd_info['scripts']:
            script = cmd_info['scripts'][subcommand]
        else:
            script = cmd_info['default']
        
        script_path = self.script_dir / script
        
        if not script_path.exists():
            print(f"❌ Script not found: {script}")
            return 1
        
        # Prepare command
        if script.endswith('.py'):
            # Use virtual environment Python if available
            venv_python = self.script_dir.parent / '.venv' / 'bin' / 'python'
            if venv_python.exists():
                cmd = [str(venv_python), str(script_path)]
            else:
                cmd = ['python3', str(script_path)]
        else:
            cmd = [str(script_path)]
        
        if args:
            cmd.extend(args)
        
        print(f"🚀 Running: {' '.join(cmd)}")
        
        try:
            # Run scripts from the parent directory (project root)
            result = subprocess.run(cmd, cwd=self.script_dir.parent)
            return result.returncode
        except KeyboardInterrupt:
            print("\n⏹️  Command interrupted")
            return 130
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return 1
    
    def interactive_sample_picker(self):
        """Enhanced interactive sample command picker."""
        while True:
            print("\n🎯 Interactive ArXiv Downloader CLI")
            print("=" * 50)
            
            # Show main categories
            categories = list(self.commands.keys())
            print("\n📚 Choose a category:")
            for i, category in enumerate(categories, 1):
                info = self.commands[category]
                print(f"  {i}. {category.upper():<12} - {info['description']}")
                print(f"     Equivalent: ./arxivdl_cli.py {category}")
            
            print(f"\n💡 Options:")
            print(f"  {len(categories)+1}. Show all samples")
            print(f"  {len(categories)+2}. Quick command builder")
            print(f"  q. Quit")
            
            try:
                choice = input("\n👉 Enter choice: ").strip()
                if choice.lower() == 'q':
                    break
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(categories):
                    category = categories[choice_num - 1]
                    self._interactive_category_picker(category)
                elif choice_num == len(categories) + 1:
                    self._show_all_samples_interactive()
                elif choice_num == len(categories) + 2:
                    self._quick_command_builder()
                else:
                    print("❌ Invalid choice")
            except ValueError:
                print("❌ Invalid input")
            except KeyboardInterrupt:
                print("\n⏹️  Exiting...")
                break
    
    def _get_equivalent_cli_command(self, sample_cmd: str, category: str) -> str:
        """Convert a sample command to its CLI equivalent."""
        # Handle shell scripts and comments
        if sample_cmd.startswith('#') or sample_cmd.startswith('./') or not sample_cmd.startswith('python'):
            return f"# {sample_cmd} (run directly as shown)"
        
        # Parse the python command
        parts = sample_cmd.split()
        if len(parts) < 2 or not parts[0].startswith('python'):
            return f"# {sample_cmd} (run directly as shown)"
        
        script_name = parts[1]
        script_args = parts[2:] if len(parts) > 2 else []
        
        # Map script to CLI command structure
        script_to_command = {
            # Download scripts
            'arxiv_downloader.py': ('download', 'single'),
            'scripts/arxiv_downloader.py': ('download', 'single'),
            'arxiv_orchestrator.py': ('download', 'batch'),
            'scripts/arxiv_orchestrator.py': ('download', 'batch'),
            'huggingface_crawler.py': ('download', 'crawler'),
            'scripts/huggingface_crawler.py': ('download', 'crawler'),
            
            # Convert scripts
            'pdf_to_txt_converter.py': ('convert', 'main'),
            'scripts/pdf_to_txt_converter.py': ('convert', 'main'),
            
            # Translate scripts
            'translate_manager.py': ('translate', 'claude'),
            'scripts/translate_manager.py': ('translate', 'claude'),
            'translate_papers.py': ('translate', 'openai'),
            'scripts/translate_papers.py': ('translate', 'openai'),
            'check_translation_completeness.py': ('translate', 'check'),
            'scripts/check_translation_completeness.py': ('translate', 'check'),
            'add_to_translation_queue.py': ('translate', 'queue'),
            'scripts/add_to_translation_queue.py': ('translate', 'queue'),
            'cleanup_translations.py': ('translate', 'cleanup'),
            'scripts/cleanup_translations.py': ('translate', 'cleanup'),
            'process_stalled_translations.py': ('translate', 'stalled'),
            'scripts/process_stalled_translations.py': ('translate', 'stalled'),
            'test_translation.py': ('translate', 'test'),
            'scripts/test_translation.py': ('translate', 'test'),
            
            # Organize scripts
            'check_and_move_papers_enhanced.py': ('organize', 'enhanced'),
            'scripts/check_and_move_papers_enhanced.py': ('organize', 'enhanced'),
            'check_and_move_papers.py': ('organize', 'basic'),
            'scripts/check_and_move_papers.py': ('organize', 'basic'),
            'organize_papers.py': ('organize', 'simple'),
            'scripts/organize_papers.py': ('organize', 'simple'),
            
            # Analyze scripts
            'arxiv_duplicate_analyzer.py': ('analyze', 'duplicates'),
            'scripts/arxiv_duplicate_analyzer.py': ('analyze', 'duplicates'),
            'check_bad_translations.py': ('analyze', 'translations'),
            'scripts/check_bad_translations.py': ('analyze', 'translations'),
            'monitor_translation.py': ('analyze', 'monitor'),
            'scripts/monitor_translation.py': ('analyze', 'monitor'),
            'simple_status_checker.py': ('analyze', 'status'),
            'scripts/simple_status_checker.py': ('analyze', 'status'),
            
            # Inventory scripts
            'inventory_all_papers.py': ('inventory', 'all'),
            'scripts/inventory_all_papers.py': ('inventory', 'all'),
            'inventory_expected_papers.py': ('inventory', 'expected'),
            'scripts/inventory_expected_papers.py': ('inventory', 'expected'),
            'quick_inventory.py': ('inventory', 'quick'),
            'scripts/quick_inventory.py': ('inventory', 'quick'),
            
            # Setup scripts
            'init_project.py': ('setup', 'init'),
            'scripts/init_project.py': ('setup', 'init'),
            'test_setup.py': ('setup', 'test'),
            'scripts/test_setup.py': ('setup', 'test'),
            'setup_autocompletion.py': ('setup', 'completion'),
            'scripts/setup_autocompletion.py': ('setup', 'completion'),
        }
        
        if script_name in script_to_command:
            cmd, subcmd = script_to_command[script_name]
            args_str = ' '.join(script_args) if script_args else ''
            return f"./arxivdl_cli.py {cmd} {subcmd} {args_str}".strip()
        else:
            # Fallback for unmapped scripts
            return f"# {sample_cmd} (run directly as shown)"
    
    def _interactive_category_picker(self, category: str):
        """Interactive picker for a specific category."""
        cmd_info = self.commands[category]
        samples = self.samples.get(category, [])
        
        while True:
            print(f"\n📋 {category.upper()} - {cmd_info['description']}")
            print("=" * 50)
            print(f"🎯 Default script: {cmd_info['default']}")
            print(f"📝 Base command: ./arxivdl_cli.py {category}")
            
            if category == 'workflow':
                # Special handling for workflow
                print("\n📚 Complete Workflow Examples:")
                for i, sample in enumerate(samples[:10], 1):  # Show first 10 lines
                    print(f"  {sample}")
                print("\n💡 Commands:")
                print("  1. Show complete workflow")
                print("  2. Back to main menu")
            else:
                print(f"\n📚 Available Commands:")
                for i, sample in enumerate(samples, 1):
                    # Get proper CLI equivalent
                    cli_equivalent = self._get_equivalent_cli_command(sample, category)
                    print(f"  {i}. {sample}")
                    print(f"     Equivalent: {cli_equivalent}")
                    if i >= 8:  # Limit display
                        remaining = len(samples) - i
                        if remaining > 0:
                            print(f"     ... and {remaining} more commands")
                        break
                
                print(f"\n💡 Commands:")
                print(f"  s. Show all {len(samples)} commands")
            
            print("  b. Back to main menu")
            print("  q. Quit")
            
            try:
                choice = input("\n👉 Enter choice: ").strip()
                if choice.lower() in ['q', 'quit']:
                    return
                elif choice.lower() in ['b', 'back']:
                    break
                elif choice.lower() == 's' and category != 'workflow':
                    self._show_category_samples(category)
                elif choice == '1' and category == 'workflow':
                    self.show_samples('workflow')
                    input("\nPress Enter to continue...")
                elif choice == '2' and category == 'workflow':
                    break
                elif category != 'workflow':
                    choice_num = int(choice)
                    if 1 <= choice_num <= min(len(samples), 8):
                        sample_cmd = samples[choice_num - 1]
                        self._execute_sample_command(sample_cmd, category)
                    else:
                        print("❌ Invalid choice")
                else:
                    print("❌ Invalid choice")
            except ValueError:
                print("❌ Invalid input")
            except KeyboardInterrupt:
                print("\n⏹️  Returning to main menu...")
                break
    
    def _show_category_samples(self, category: str):
        """Show all samples for a category."""
        samples = self.samples.get(category, [])
        print(f"\n📚 All {category.upper()} Commands:")
        print("=" * 50)
        
        for i, sample in enumerate(samples, 1):
            cli_equivalent = self._get_equivalent_cli_command(sample, category)
            print(f"{i:2}. {sample}")
            print(f"    Equivalent: {cli_equivalent}")
        
        print(f"\n💡 Choose a command (1-{len(samples)}), 'b' for back, or 'q' to quit:")
        
        try:
            choice = input("👉 Enter choice: ").strip()
            if choice.lower() in ['b', 'back']:
                return
            elif choice.lower() in ['q', 'quit']:
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(samples):
                sample_cmd = samples[choice_num - 1]
                self._execute_sample_command(sample_cmd, category)
        except ValueError:
            print("❌ Invalid input")
        except KeyboardInterrupt:
            print("\n⏹️  Returning...")
    
    def _show_all_samples_interactive(self):
        """Show all samples with interactive selection."""
        print("\n📚 All Sample Commands")
        print("=" * 50)
        
        all_samples = []
        for cmd, samples in self.samples.items():
            print(f"\n{cmd.upper()}:")
            for sample in samples:
                all_samples.append((cmd, sample))
                cli_equivalent = self._get_equivalent_cli_command(sample, cmd)
                print(f"  {len(all_samples):2}. {sample}")
                print(f"      Equivalent: {cli_equivalent}")
        
        print(f"\n💡 Choose a command (1-{len(all_samples)}), 'b' for back, or 'q' to quit:")
        
        try:
            choice = input("👉 Enter choice: ").strip()
            if choice.lower() in ['b', 'back']:
                return
            elif choice.lower() in ['q', 'quit']:
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(all_samples):
                cmd_type, sample_cmd = all_samples[choice_num - 1]
                self._execute_sample_command(sample_cmd, cmd_type)
        except ValueError:
            print("❌ Invalid input")
        except KeyboardInterrupt:
            print("\n⏹️  Returning...")
    
    def _quick_command_builder(self):
        """Quick command builder for common operations."""
        print("\n🔧 Quick Command Builder")
        print("=" * 50)
        
        print("1. Download papers from URL file")
        print("2. Convert PDFs to TXT")
        print("3. Translate papers")
        print("4. Organize papers")
        print("5. Check collection status")
        print("6. Remove big papers from queue")
        print("b. Back to main menu")
        
        try:
            choice = input("\n👉 Enter choice: ").strip()
            if choice.lower() in ['b', 'back']:
                return
            
            if choice == '1':
                url_file = input("📄 Enter URL file (e.g., CoT.txt): ").strip()
                workers = input("⚙️  Workers (1 for ArXiv compliance): ").strip() or "1"
                print(f"\n✅ Command: python3 scripts/arxiv_downloader.py {url_file} {workers}")
                print(f"✅ Equivalent: ./arxivdl_cli.py download single {url_file} {workers}")
                
            elif choice == '2':
                collection = input("📁 Collection name (or 'all' for all): ").strip()
                if collection == 'all':
                    print(f"\n✅ Command: python3 scripts/pdf_to_txt_converter.py --all")
                    print(f"✅ Equivalent: ./arxivdl_cli.py convert --all")
                else:
                    print(f"\n✅ Command: python3 scripts/pdf_to_txt_converter.py --both --collection {collection}")
                    print(f"✅ Equivalent: ./arxivdl_cli.py convert --both --collection {collection}")
                    
            elif choice == '3':
                workers = input("⚙️  Workers (1-4): ").strip() or "2"
                print(f"\n✅ Command: python3 scripts/translate_manager.py --workers {workers}")
                print(f"✅ Equivalent: ./arxivdl_cli.py translate claude --workers {workers}")
                
            elif choice == '4':
                print(f"\n✅ Command: python3 scripts/check_and_move_papers_enhanced.py --execute")
                print(f"✅ Equivalent: ./arxivdl_cli.py organize enhanced --execute")
                
            elif choice == '5':
                print(f"\n✅ Command: python3 scripts/inventory_all_papers.py")
                print(f"✅ Equivalent: ./arxivdl_cli.py inventory all")
                
            elif choice == '6':
                big_file = input("📄 Big file list (default: translation_queue_big_file.txt): ").strip() or "translation_queue_big_file.txt"
                print(f"\n✅ Command: python3 scripts/check_translation_completeness.py --remove-big-papers {big_file}")
                print(f"✅ Equivalent: ./arxivdl_cli.py translate check --remove-big-papers {big_file}")
            
            run_choice = input("\n🔧 Run this command? (y/N): ").strip().lower()
            if run_choice == 'y':
                # Execute the equivalent command would be implemented here
                print("📋 Command ready to execute (feature in development)")
                
        except KeyboardInterrupt:
            print("\n⏹️  Returning...")
    
    def _execute_sample_command(self, sample_cmd: str, category: str):
        """Execute a sample command with confirmation."""
        print(f"\n✅ Selected: {sample_cmd}")
        cli_equivalent = self._get_equivalent_cli_command(sample_cmd, category)
        print(f"✅ Equivalent: {cli_equivalent}")
        
        # Ask if user wants to run it
        run_choice = input("\n🔧 Run this command? (y/N): ").strip().lower()
        if run_choice == 'y':
            # Parse and run the command
            # Check if it's a compound command with &&
            if '&&' in sample_cmd:
                # Run as shell command
                result = subprocess.run(sample_cmd, shell=True, cwd=self.script_dir.parent)
                return result.returncode
            
            parts = sample_cmd.split()
            if parts[0] in ['python', 'python3'] and len(parts) > 1:
                script_name = parts[1]
                script_args = parts[2:] if len(parts) > 2 else []
                
                # Find the command that contains this script
                for cmd, info in self.commands.items():
                    if script_name in info['scripts'].values():
                        return self.run_command(cmd, None, script_args)
                
                # If script not found in commands, try to run it directly
                script_path = self.script_dir / script_name
                if script_path.exists():
                    venv_python = self.script_dir.parent / '.venv' / 'bin' / 'python'
                    if venv_python.exists():
                        cmd = [str(venv_python), str(script_path)] + script_args
                    else:
                        cmd = ['python3', str(script_path)] + script_args
                    result = subprocess.run(cmd, cwd=self.script_dir.parent)
                    return result.returncode
            else:
                # Shell script
                cmd = parts
                result = subprocess.run(cmd, cwd=self.script_dir.parent)
                return result.returncode
        else:
            print("📋 Command noted (not executed)")

def main():
    """Main CLI entry point."""
    cli = ArXivCLI()
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="ArXiv Downloader CLI - Unified Command Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 arxivdl_cli.py download CoT.txt
  python3 arxivdl_cli.py convert --all
  python3 arxivdl_cli.py translate --check
  python3 arxivdl_cli.py --samples download
  python3 arxivdl_cli.py --interactive
        """
    )
    
    parser.add_argument('command', nargs='?', help='Command to run')
    parser.add_argument('subcommand', nargs='?', help='Subcommand variant')
    parser.add_argument('--help-cmd', metavar='CMD', help='Show help for specific command')
    parser.add_argument('--samples', nargs='?', const='all', help='Show sample commands')
    parser.add_argument('--list', action='store_true', help='List all available scripts')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive sample picker')
    
    # Parse known args to allow passing through to underlying scripts
    args, remaining = parser.parse_known_args()
    
    # Handle special flags
    if args.help_cmd:
        cli.show_help(args.help_cmd)
        return 0
    
    if args.samples:
        if args.samples == 'all':
            cli.show_samples()
        else:
            cli.show_samples(args.samples)
        return 0
    
    if args.list:
        cli.list_scripts()
        return 0
    
    if args.interactive:
        cli.interactive_sample_picker()
        return 0
    
    # Show help if no command provided
    if not args.command:
        cli.show_help()
        return 0
    
    # Run the command
    return cli.run_command(args.command, args.subcommand, remaining)

if __name__ == "__main__":
    sys.exit(main())