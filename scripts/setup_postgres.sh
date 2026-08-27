#!/bin/bash
# Quick setup script for Postgres integration

set -e  # Exit on error

echo "========================================="
echo "AI Analyst - Postgres Setup"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Run this script from the ai-analyst root directory"
    exit 1
fi

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create reports directory structure
echo "Creating reports directory structure..."
mkdir -p reports/analyses
mkdir -p reports/charts
mkdir -p reports/decks
mkdir -p reports/data
echo "✓ Created:"
echo "  - reports/analyses/"
echo "  - reports/charts/"
echo "  - reports/decks/"
echo "  - reports/data/"
echo ""

# Check if config exists
if [ ! -f ".knowledge/config.yaml" ]; then
    echo "Warning: .knowledge/config.yaml not found"
    echo "The config file should already exist. Check your setup."
else
    echo "✓ Configuration file found"
fi
echo ""

# Check if Postgres dataset config exists
if [ ! -f ".knowledge/datasets/company_postgres/manifest.yaml" ]; then
    echo "Warning: Postgres dataset config not found"
    echo "Expected: .knowledge/datasets/company_postgres/manifest.yaml"
else
    echo "✓ Postgres dataset config found"
fi
echo ""

# Prompt for environment variable
echo "========================================="
echo "Environment Setup"
echo "========================================="
echo ""
echo "You need to set your Postgres password as an environment variable."
echo "Add this line to your ~/.bashrc or ~/.zshrc:"
echo ""
echo "  export POSTGRES_PASSWORD='your_password_here'"
echo ""
read -p "Have you set POSTGRES_PASSWORD? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please set the environment variable and re-run this script."
    exit 1
fi
echo ""

# Test if environment variable is set
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Warning: POSTGRES_PASSWORD environment variable is not set in this session"
    echo "You may need to restart your terminal or run: source ~/.bashrc"
else
    echo "✓ POSTGRES_PASSWORD is set"
fi
echo ""

# Instructions for next steps
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your Postgres connection details:"
echo "   nano .knowledge/datasets/company_postgres/manifest.yaml"
echo ""
echo "2. Update these fields:"
echo "   - host: your_postgres_host"
echo "   - database: your_database_name"
echo "   - user: your_username"
echo "   - tables: [list your table names]"
echo ""
echo "3. Test the connection:"
echo "   python3 -c 'from helpers.data.postgres_helpers import test_connection; print(test_connection())'"
echo ""
echo "4. Activate the dataset:"
echo "   In Claude Code, run: /switch-dataset company_postgres"
echo ""
echo "5. Start analyzing:"
echo "   In Claude Code, run: /explore"
echo ""
echo "For detailed instructions, see:"
echo "   docs/postgres-integration-guide.md"
echo ""
