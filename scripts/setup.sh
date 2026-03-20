#!/usr/bin/env bash
# setup.sh — Set up the AI Analyst development environment
#
# Usage:
#   bash scripts/setup.sh           # Create venv and install dependencies
#   bash scripts/setup.sh --help    # Show this help
#
# Creates a Python virtual environment and installs all required packages.
# Run this once after cloning the repo.

set -euo pipefail

VENV_DIR=".venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: bash scripts/setup.sh [--help]"
    echo ""
    echo "Creates a Python virtual environment and installs dependencies."
    echo ""
    echo "Requirements:"
    echo "  - Python 3.9 or later"
    echo "  - pip (usually included with Python)"
}

# --- Main ---

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

# Ensure we're in the repo root
if [ ! -f "CLAUDE.md" ]; then
    echo -e "${RED}Error: Run this script from the AI Analyst repo root.${NC}"
    echo "  cd ~/Desktop/ai-analyst && bash scripts/setup.sh"
    exit 1
fi

# Check Python version
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found.${NC}"
    echo "Install Python 3.9+ from https://python.org or via your package manager."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9+ required. Found Python ${PYTHON_VERSION}.${NC}"
    exit 1
fi

echo -e "${GREEN}  Python ${PYTHON_VERSION} found${NC}"

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at ${VENV_DIR}/${NC}"
    echo "  To recreate: rm -rf ${VENV_DIR} && bash scripts/setup.sh"
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}  Created ${VENV_DIR}/${NC}"
fi

# Activate and install
echo "Installing dependencies..."

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

pip install --upgrade pip --quiet

if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet
    echo -e "${GREEN}  Installed from pyproject.toml${NC}"
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}  Installed from requirements.txt${NC}"
else
    # Install core dependencies directly
    pip install --quiet \
        pandas \
        matplotlib \
        clickhouse-connect \
        pyyaml \
        pytest \
        faker
    echo -e "${GREEN}  Installed core dependencies${NC}"
fi

# Verify key imports
echo "Verifying installation..."
python3 -c "
import pandas, matplotlib, yaml
print('  pandas', pandas.__version__)
print('  matplotlib', matplotlib.__version__)
print('  pyyaml', yaml.__version__)
" 2>/dev/null && echo -e "${GREEN}  All key packages verified${NC}" || {
    echo -e "${RED}  Some packages failed to import. Check the output above.${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}=== Setup complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Start Claude Code:  claude"
echo "  2. Connect your data:  /connect-data"
echo ""
echo "To activate the virtual environment manually:"
echo "  source ${VENV_DIR}/bin/activate"
