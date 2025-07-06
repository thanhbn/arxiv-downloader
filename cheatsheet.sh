#!/bin/bash
# ArXiv Downloader Cheatsheet
# Comprehensive command reference for all available scripts and tools

# Colors for better output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

# Function to print command with description
print_command() {
    local cmd="$1"
    local desc="$2"
    local help_option="$3"
    
    echo -e "${GREEN}$cmd${NC}"
    echo -e "  ${WHITE}Description:${NC} $desc"
    if [[ -n "$help_option" ]]; then
        echo -e "  ${YELLOW}Help:${NC} $cmd $help_option"
    fi
    echo
}

# Function to show script help if available
show_help() {
    local script="$1"
    local help_option="$2"
    
    if [[ -f "$script" ]]; then
        echo -e "${BLUE}Help for $(basename $script):${NC}"
        if python3 "$script" $help_option 2>/dev/null | head -20; then
            echo
        elif bash "$script" $help_option 2>/dev/null | head -20; then
            echo
        else
            echo -e "${RED}No help available or script error${NC}"
            echo
        fi
    fi
}

# Function to test if script supports help
supports_help() {
    local script="$1"
    local help_option="$2"
    
    if [[ -f "$script" ]]; then
        if python3 "$script" $help_option >/dev/null 2>&1; then
            return 0
        elif bash "$script" $help_option >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to get script description from file
get_description() {
    local script="$1"
    local desc=""
    
    if [[ -f "$script" ]]; then
        # Try to extract description from docstring or comments
        desc=$(grep -E "^(#|\"\"\"|\"\"\"|''')" "$script" | head -5 | tail -3 | sed 's/^[#"'"'"'[:space:]]*//' | tr '\n' ' ' | sed 's/[[:space:]]*$//')
        if [[ -z "$desc" ]]; then
            # Fallback to filename-based description
            case "$(basename $script)" in
                arxiv_downloader.py) desc="Download ArXiv papers with parallel processing and rate limiting" ;;
                arxiv_orchestrator.py) desc="Orchestrate downloads across multiple collections with progress tracking" ;;
                pdf_to_txt_converter.py) desc="Convert PDF papers to TXT format with smart renaming" ;;
                check_and_move_papers_enhanced.py) desc="Enhanced paper organization and collection management" ;;
                translate_papers.py) desc="Translate papers to different languages" ;;
                translate_manager.py) desc="Automated parallel translation manager with queue management" ;;
                download_arxiv.sh) desc="Shell script for downloading ArXiv papers with retry logic" ;;
                setup_direnv_fixed.sh) desc="Setup direnv environment with Python virtual environment" ;;
                *) desc="ArXiv downloader utility script" ;;
            esac
        fi
    fi
    echo "$desc"
}

# Main function
main() {
    local show_help_for=""
    local list_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                cat << EOF
ArXiv Downloader Cheatsheet

Usage: $0 [OPTIONS] [SCRIPT_NAME]

OPTIONS:
    -h, --help              Show this help message
    -l, --list              List all available scripts without descriptions
    --help-for SCRIPT       Show detailed help for specific script
    
EXAMPLES:
    $0                      Show all commands with descriptions
    $0 -l                   List all scripts
    $0 --help-for arxiv_downloader.py    Show help for specific script
    
SCRIPT_NAME: If provided, show help only for that specific script

EOF
                exit 0
                ;;
            -l|--list)
                list_only=true
                shift
                ;;
            --help-for)
                show_help_for="$2"
                shift 2
                ;;
            *)
                show_help_for="$1"
                shift
                ;;
        esac
    done
    
    # Print main header
    clear
    print_header "🚀 ArXiv Downloader Toolkit - Command Cheatsheet"
    echo -e "${WHITE}Working Directory:${NC} $(pwd)"
    echo -e "${WHITE}Total Scripts:${NC} $(find . -maxdepth 1 -type f \( -name "*.py" -o -name "*.sh" \) | wc -l)"
    echo

    # If specific script help requested
    if [[ -n "$show_help_for" ]]; then
        if [[ ! -f "$show_help_for" ]]; then
            # Try to find the script
            found_script=$(find . -maxdepth 1 -name "*$show_help_for*" -type f \( -name "*.py" -o -name "*.sh" \) | head -1)
            if [[ -n "$found_script" ]]; then
                show_help_for="$found_script"
            else
                echo -e "${RED}Script '$show_help_for' not found!${NC}"
                exit 1
            fi
        fi
        
        print_header "Help for $(basename $show_help_for)"
        desc=$(get_description "$show_help_for")
        echo -e "${WHITE}Description:${NC} $desc"
        echo
        
        for help_opt in "--help" "-h" "help"; do
            if supports_help "$show_help_for" "$help_opt"; then
                show_help "$show_help_for" "$help_opt"
                break
            fi
        done
        exit 0
    fi

    # Core Download Scripts
    print_header "📥 Core Download Scripts"
    
    # Python scripts
    for script in arxiv_downloader.py arxiv_orchestrator.py; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                # Determine help option
                help_opt=""
                for opt in "--help" "-h"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "python3 $script" "$desc" "$help_opt"
            fi
        fi
    done
    
    # Shell scripts
    for script in download_arxiv.sh; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h" "help"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "bash $script" "$desc" "$help_opt"
            fi
        fi
    done

    # PDF Processing Scripts
    print_header "📄 PDF Processing & Conversion"
    
    for script in pdf_to_txt_converter.py translate_papers.py translate_manager.py; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "python3 $script" "$desc" "$help_opt"
            fi
        fi
    done

    # Organization & Management Scripts
    print_header "📁 Paper Organization & Management"
    
    for script in check_and_move_papers_enhanced.py check_and_move_papers.py organize_papers.py; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "python3 $script" "$desc" "$help_opt"
            fi
        fi
    done

    # Development & Testing Scripts
    print_header "🔧 Development & Testing"
    
    for script in test_setup.py test_orchestrator.py check_status.py show_rate_limits.py; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "python3 $script" "$desc" "$help_opt"
            fi
        fi
    done

    # Setup & Configuration Scripts
    print_header "⚙️  Setup & Configuration"
    
    for script in setup_direnv_fixed.sh setup_env.sh setup_simple.sh download_config.sh; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h" "help"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "bash $script" "$desc" "$help_opt"
            fi
        fi
    done

    # Utility & Data Processing Scripts
    print_header "🛠️  Utility & Data Processing"
    
    for script in huggingface_crawler.py fix_multimodal.py check_multimodal.py; do
        if [[ -f "$script" ]]; then
            desc=$(get_description "$script")
            if [[ "$list_only" == "true" ]]; then
                echo "$script"
            else
                help_opt=""
                for opt in "--help" "-h"; do
                    if supports_help "$script" "$opt"; then
                        help_opt="$opt"
                        break
                    fi
                done
                print_command "python3 $script" "$desc" "$help_opt"
            fi
        fi
    done

    # Backup Scripts
    if [[ "$list_only" != "true" ]]; then
        print_header "💾 Backup Scripts"
        for script in *_backup.py; do
            if [[ -f "$script" ]]; then
                desc="Backup version of $(basename $script _backup.py).py"
                echo -e "${PURPLE}python3 $script${NC}"
                echo -e "  ${WHITE}Description:${NC} $desc"
                echo
            fi
        done
    fi

    # Footer with usage examples
    if [[ "$list_only" != "true" ]]; then
        print_header "💡 Quick Start Examples"
        
        echo -e "${YELLOW}1. Download papers:${NC}"
        echo -e "   python3 arxiv_downloader.py CoT.txt"
        echo
        
        echo -e "${YELLOW}2. Convert PDFs to TXT:${NC}"
        echo -e "   python3 pdf_to_txt_converter.py --all"
        echo
        
        echo -e "${YELLOW}3. Organize papers:${NC}"
        echo -e "   python3 check_and_move_papers_enhanced.py --execute"
        echo
        
        echo -e "${YELLOW}4. Translate papers:${NC}"
        echo -e "   python3 translate_manager.py --workers 4"
        echo -e "   python3 translate_manager.py --queue-file custom_queue.txt"
        echo
        
        echo -e "${YELLOW}5. Setup environment:${NC}"
        echo -e "   bash setup_direnv_fixed.sh"
        echo
        
        echo -e "${YELLOW}6. Get specific help:${NC}"
        echo -e "   $0 --help-for arxiv_downloader.py"
        echo
        
        print_header "📚 More Information"
        echo -e "• Check ${GREEN}CLAUDE.md${NC} for detailed documentation"
        echo -e "• Use ${GREEN}$0 -h${NC} for cheatsheet options"
        echo -e "• Use ${GREEN}$0 --help-for SCRIPT${NC} for script-specific help"
        echo
    fi
}

# Run main function with all arguments
main "$@"