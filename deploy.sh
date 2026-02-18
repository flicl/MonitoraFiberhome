#!/bin/bash
#
# Deploy script for Fiberhome OLT monitoring scripts.
#
# Usage:
#   sudo ./deploy.sh [--backup]
#
# Options:
#   --backup    Create backup of legacy scripts before deployment
#
# This script:
#   1. Verifies Python version (>= 3.10)
#   2. Creates directory structure
#   3. Copies scripts to Zabbix externalscripts directory
#   4. Sets proper permissions
#   5. (Optional) Backs up legacy scripts
#
# Dependencies:
#   - Python 3.10+ (uses asyncio, type hints with | syntax)
#   - No external pip packages required (uses stdlib only)
#

set -e

# Configuration
SCRIPTS_DIR="/usr/lib/zabbix/externalscripts"
FIBERHOME_DIR="${SCRIPTS_DIR}/fiberhome"
BACKUP_DIR="/opt/fiberhome_backup/$(date +%Y%m%d_%H%M%S)"
SOURCE_DIR="$(dirname "$(readlink -f "$0")")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

backup_legacy() {
    log_info "Creating backup of legacy scripts..."
    mkdir -p "${BACKUP_DIR}/legacy_scripts"

    # Backup old scripts if they exist
    for script in GetONUOnline.py GetONUSignal.py GetPONName.py; do
        if [[ -f "${SCRIPTS_DIR}/${script}" ]]; then
            cp "${SCRIPTS_DIR}/${script}" "${BACKUP_DIR}/legacy_scripts/"
            log_info "Backed up: ${script}"
        fi
    done

    # Backup cron file if exists
    if [[ -f "/etc/cron.d/TemplateOLT" ]]; then
        cp "/etc/cron.d/TemplateOLT" "${BACKUP_DIR}/"
        log_info "Backed up: /etc/cron.d/TemplateOLT"
    fi

    # Backup old template if exists
    if [[ -f "${SCRIPTS_DIR}/../Template Fiberhome.yaml" ]]; then
        cp "${SCRIPTS_DIR}/../Template Fiberhome.yaml" "${BACKUP_DIR}/"
    fi

    log_info "Backup created at: ${BACKUP_DIR}"
}

check_python() {
    log_info "Checking Python version..."
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python version: ${PYTHON_VERSION}"

    # Check Python version >= 3.10
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [[ "$MAJOR" -lt 3 ]] || ([[ "$MAJOR" -eq 3 ]] && [[ "$MINOR" -lt 10 ]]); then
        log_error "Python 3.10+ is required. Found: ${PYTHON_VERSION}"
        exit 1
    fi

    log_info "Python version OK (no external dependencies required)"
}

create_directories() {
    log_info "Creating directory structure..."
    mkdir -p "${FIBERHOME_DIR}"
    chown -R zabbix:zabbix "${FIBERHOME_DIR}"
    chmod 755 "${FIBERHOME_DIR}"
}

deploy_scripts() {
    log_info "Deploying scripts..."

    # Copy module files to fiberhome/ subdirectory
    cp "${SOURCE_DIR}/fiberhome/"*.py "${FIBERHOME_DIR}/"

    # Copy wrapper scripts to main externalscripts directory
    cp "${SOURCE_DIR}/GetPONStatus.py" "${SCRIPTS_DIR}/"
    cp "${SOURCE_DIR}/GetPONSignals.py" "${SCRIPTS_DIR}/"

    # Copy GetPONName.py to main scripts directory
    cp "${SOURCE_DIR}/GetPONName.py" "${SCRIPTS_DIR}/"

    # Set permissions
    chmod +x "${SCRIPTS_DIR}/GetPONStatus.py"
    chmod +x "${SCRIPTS_DIR}/GetPONSignals.py"
    chmod +x "${SCRIPTS_DIR}/GetPONName.py"

    chown -R zabbix:zabbix "${FIBERHOME_DIR}"
    chown zabbix:zabbix "${SCRIPTS_DIR}/GetPONStatus.py"
    chown zabbix:zabbix "${SCRIPTS_DIR}/GetPONSignals.py"
    chown zabbix:zabbix "${SCRIPTS_DIR}/GetPONName.py"

    log_info "Scripts deployed successfully"
    log_info "  - ${SCRIPTS_DIR}/GetPONStatus.py"
    log_info "  - ${SCRIPTS_DIR}/GetPONSignals.py"
    log_info "  - ${SCRIPTS_DIR}/GetPONName.py"
    log_info "  - ${FIBERHOME_DIR}/ (module files)"
}

test_scripts() {
    log_info "Testing script syntax..."
    # Module files
    python3 -m py_compile "${FIBERHOME_DIR}/constants.py"
    python3 -m py_compile "${FIBERHOME_DIR}/parsers.py"
    python3 -m py_compile "${FIBERHOME_DIR}/scrapli_client.py"
    python3 -m py_compile "${FIBERHOME_DIR}/fiberhome_olt_status.py"
    python3 -m py_compile "${FIBERHOME_DIR}/fiberhome_olt_signals.py"
    # Wrapper scripts
    python3 -m py_compile "${SCRIPTS_DIR}/GetPONStatus.py"
    python3 -m py_compile "${SCRIPTS_DIR}/GetPONSignals.py"
    python3 -m py_compile "${SCRIPTS_DIR}/GetPONName.py"
    log_info "Syntax check passed"
}

show_next_steps() {
    echo ""
    log_info "=========================================="
    log_info "Deployment complete!"
    log_info "=========================================="
    echo ""
    log_warn "Next steps:"
    echo ""
    echo "1. Import the updated template YAML into Zabbix:"
    echo "   ${SOURCE_DIR}/Template Fiberhome.yaml"
    echo ""
    echo "2. Test a script manually (replace with real credentials):"
    echo "   python3 ${FIBERHOME_DIR}/fiberhome_olt_status.py <IP> <USER> <PASS> <PORT> | jq ."
    echo ""
    echo "3. Remove cron entries for legacy scripts:"
    echo "   sudo rm -f /etc/cron.d/TemplateOLT"
    echo ""
    echo "4. After 7 days of stable operation, remove legacy scripts:"
    echo "   rm -f ${SCRIPTS_DIR}/GetONUOnline.py ${SCRIPTS_DIR}/GetONUSignal.py"
    echo ""
    echo "5. Verify data is arriving in Zabbix:"
    echo "   Monitoring → Latest Data → [Select OLT Host]"
    echo ""
}

main() {
    local do_backup=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup)
                do_backup=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    check_root

    if [[ "$do_backup" == true ]]; then
        backup_legacy
    fi

    check_python
    create_directories
    deploy_scripts
    test_scripts
    show_next_steps
}

main "$@"
