#!/bin/bash
#
# MemoGarden Core - Installation Script for Linux
#
# This script installs and configures MemoGarden Core as a systemd service.
# It can be run for fresh installs or re-installs (will preserve existing .env)
#
# Usage:
#   sudo ./install.sh
#
# For installs from a tarball/clone without .env:
#   - Creates .env from .env.example
#   - Generates a secure JWT_SECRET_KEY automatically
#
# For re-installs:
#   - Backs up existing .env to .env.backup
#   - Preserves your configuration
#   - Restarts the service
#

set -euxo pipefail  # Exit on error, undefined vars, pipe failures; verbose

#=============================================================================
# Configuration
#=============================================================================

SERVICE_NAME="memogarden-core"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
INSTALL_DIR=$(pwd)
PYTHON_MIN_VERSION="3.13"

#=============================================================================
# Colors for output
#=============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#=============================================================================
# Pre-flight checks
#=============================================================================

log_info "Starting MemoGarden Core installation..."

# Check running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Check we're in the memogarden-core directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "memogarden_core" ]]; then
    log_error "Must be run from memogarden-core directory (containing pyproject.toml)"
    exit 1
fi

# Check Python version
log_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 13 ]]; then
    log_error "Python ${PYTHON_MIN_VERSION}+ required, found ${PYTHON_VERSION}"
    exit 1
fi
log_info "Python ${PYTHON_VERSION} OK"

# Check for git
if ! command -v git &> /dev/null; then
    log_error "git not found. Install with: apt install git"
    exit 1
fi

#=============================================================================
# Install Poetry if not present
#=============================================================================

if ! command -v poetry &> /dev/null; then
    log_info "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
else
    log_info "Poetry already installed: $(poetry --version)"
fi

#=============================================================================
# Install Python dependencies
#=============================================================================

log_info "Configuring Poetry to use in-project virtual environment..."
poetry config virtualenvs.in-project true

log_info "Installing Python dependencies with Poetry..."
poetry install

# Get the actual gunicorn path for the systemd service
GUNICORN_PATH=$(poetry run which gunicorn)
log_info "Gunicorn found at: ${GUNICORN_PATH}"

#=============================================================================
# Handle .env file
#=============================================================================

log_info "Configuring environment..."

if [[ -f ".env" ]]; then
    # Backup existing .env
    BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
    log_warn "Found existing .env, backing up to ${BACKUP_FILE}"
    cp .env "$BACKUP_FILE"
    log_info "Your existing .env will be preserved. Review backup if needed."
else
    # Create .env from .env.example
    log_info "Creating .env from .env.example..."
    cp .env.example .env

    # Generate secure JWT secret
    log_info "Generating secure JWT_SECRET_KEY..."
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/change-me-in-production-use-env-var/${JWT_SECRET}/" .env

    # Set production-friendly defaults
    sed -i 's|DATABASE_PATH=.*|DATABASE_PATH=./data/memogarden.db|' .env

    # Loose CORS for Tailscale testing
    sed -i 's|CORS_ORIGINS=\["http://localhost:3000"\]|CORS_ORIGINS=["*"]|' .env

    # Ensure production settings
    sed -i 's/BYPASS_LOCALHOST_CHECK=true/BYPASS_LOCALHOST_CHECK=false/' .env

    log_info ".env created with:"
    log_info "  - Generated JWT_SECRET_KEY"
    log_info "  - CORS_ORIGINS set to [*] (restrict for public deployment)"
    log_info "  - BYPASS_LOCALHOST_CHECK=false"
fi

#=============================================================================
# Create data directory
#=============================================================================

log_info "Ensuring data directory exists..."
mkdir -p ./data

#=============================================================================
# Initialize database
#=============================================================================

if [[ ! -f "./data/memogarden.db" ]]; then
    log_info "Initializing database..."
    poetry run python -m memogarden_core.db.seed
else
    log_info "Database already exists at ./data/memogarden.db (skipping init)"
fi

#=============================================================================
# Create systemd service file
#=============================================================================

log_info "Creating systemd service at ${SERVICE_FILE}..."

cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=MemoGarden Core API
After=network.target
Wants=network-online.target

[Service]
Type=notify
User=${SUDO_USER:-root}
Group=${SUDO_USER:-root}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=$(dirname ${GUNICORN_PATH})"
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${GUNICORN_PATH} --bind 0.0.0.0:5000 --workers 2 --timeout 120 --access-logfile - --error-logfile - --log-level info --capture-output memogarden_core.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=memogarden-core

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_DIR}/data

[Install]
WantedBy=multi-user.target
EOF

log_info "Service file created"

#=============================================================================
# Enable and start service
#=============================================================================

log_info "Reloading systemd daemon..."
systemctl daemon-reload

log_info "Enabling ${SERVICE_NAME} to start on boot..."
systemctl enable ${SERVICE_NAME}

# Check if service is already running
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "Service already running, restarting..."
    systemctl restart ${SERVICE_NAME}
else
    log_info "Starting ${SERVICE_NAME} service..."
    systemctl start ${SERVICE_NAME}
fi

#=============================================================================
# Verify installation
#=============================================================================

sleep 2  # Give service a moment to start

if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "✓ Service is running!"
    echo ""
    echo "=================================================="
    echo "MemoGarden Core installed successfully!"
    echo "=================================================="
    echo ""
    echo "Service Management:"
    echo "  Status:   sudo systemctl status ${SERVICE_NAME}"
    echo "  Restart:  sudo systemctl restart ${SERVICE_NAME}"
    echo "  Stop:     sudo systemctl stop ${SERVICE_NAME}"
    echo "  Logs:     sudo journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "API Endpoints:"
    echo "  Health:   http://$(hostname -I | awk '{print $1}'):5000/health"
    echo "  API:      http://$(hostname -I | awk '{print $1}'):5000/api/v1/..."
    echo ""
    echo "Next Steps:"
    echo "  1. Check service status: sudo systemctl status ${SERVICE_NAME}"
    echo "  2. Visit admin registration at: http://$(hostname -I | awk '{print $1}'):5000/admin/register"
    echo "     (only accessible from localhost - SSH into the pi and use curl or port-forward)"
    echo ""
else
    log_error "Service failed to start. Check logs:"
    echo "  sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
