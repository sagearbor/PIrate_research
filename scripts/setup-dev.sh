#!/bin/bash

# Development Environment Setup Script
# Faculty Research Opportunity Notifier

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if running in project root
if [ ! -f "requirements.txt" ] || [ ! -f "src/main.py" ]; then
    print_error "This script must be run from the project root directory"
    print_error "Make sure you're in the Faculty Research Opportunity Notifier directory"
    exit 1
fi

print_header "Faculty Research Opportunity Notifier - Development Setup"

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    print_status "Python $python_version detected - OK"
else
    print_error "Python 3.10 or higher is required. Found: $python_version"
    print_error "Please install Python 3.10+ and try again"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created in ./venv"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install development dependencies
print_status "Installing development dependencies..."
pip install black isort flake8 mypy pytest-cov pytest-xdist pre-commit bandit safety

# Create data directories
print_status "Creating data directories..."
mkdir -p data/raw data/processed logs temp

# Set up pre-commit hooks
print_status "Setting up pre-commit hooks..."
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install
    print_status "Pre-commit hooks installed"
else
    print_warning "Pre-commit not available. Install manually if needed: pip install pre-commit"
fi

# Create .env template if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env template..."
    cat > .env << EOF
# Environment Configuration
# Copy this file and modify as needed

# Application Settings
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database Settings (if applicable)
# DATABASE_URL=sqlite:///./data/app.db

# External API Keys (add as needed)
# GOOGLE_API_KEY=your_key_here
# NIH_API_KEY=your_key_here

# Security Settings
SECRET_KEY=your-secret-key-here

# Development Settings
PYTHONPATH=./src
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
EOF
    print_status ".env template created - please configure with your settings"
else
    print_status ".env file already exists"
fi

# Run initial tests to verify setup
print_status "Running initial test suite to verify setup..."
if python -m pytest tests/test_main.py -v; then
    print_status "Basic tests passed - setup verification successful"
else
    print_warning "Some tests failed - please check the output above"
fi

# Check Docker installation
print_status "Checking Docker installation..."
if command -v docker >/dev/null 2>&1; then
    docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
    print_status "Docker $docker_version detected"
    
    # Test Docker build
    print_status "Testing Docker build..."
    if docker build -t research-agent-test . >/dev/null 2>&1; then
        print_status "Docker build successful"
        docker rmi research-agent-test >/dev/null 2>&1
    else
        print_warning "Docker build failed - check Dockerfile"
    fi
else
    print_warning "Docker not found - install Docker for containerization features"
fi

# Check Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    compose_version=$(docker-compose --version | cut -d' ' -f3 | sed 's/,//')
    print_status "Docker Compose $compose_version detected"
else
    print_warning "Docker Compose not found - install for multi-container development"
fi

# Create development scripts
print_status "Creating development helper scripts..."

# Test runner script
cat > scripts/run-tests.sh << 'EOF'
#!/bin/bash
set -e

echo "Running comprehensive test suite..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests with coverage
echo "Running pytest with coverage..."
python -m pytest -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80

echo "Test suite completed!"
EOF

# Code quality script
cat > scripts/check-quality.sh << 'EOF'
#!/bin/bash
set -e

echo "Running code quality checks..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Checking code formatting with black..."
black --check --diff src/ tests/

echo "Checking import sorting with isort..."
isort --check-only --diff src/ tests/

echo "Running flake8 linting..."
flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503

echo "Running type checking with mypy..."
mypy src/ --ignore-missing-imports --no-strict-optional || true

echo "Running security scan with bandit..."
bandit -r src/ -f json || true

echo "Checking dependencies with safety..."
safety check || true

echo "Code quality checks completed!"
EOF

# Development server script
cat > scripts/run-dev.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting development server..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the development server
echo "Starting FastAPI development server..."
echo "API will be available at: http://localhost:8000"
echo "API Documentation at: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"

python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
EOF

# Make scripts executable
chmod +x scripts/run-tests.sh
chmod +x scripts/check-quality.sh
chmod +x scripts/run-dev.sh

print_status "Development helper scripts created in ./scripts/"

# Create VS Code configuration if .vscode doesn't exist
if [ ! -d ".vscode" ]; then
    print_status "Creating VS Code configuration..."
    mkdir -p .vscode
    
    # VS Code settings
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/.mypy_cache": true,
        "**/htmlcov": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
EOF

    # VS Code launch configuration
    cat > .vscode/launch.json << EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Development Server",
            "type": "python",
            "request": "launch",
            "program": "-m",
            "args": [
                "uvicorn",
                "src.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "console": "integratedTerminal",
            "cwd": "\${workspaceFolder}",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}/src"
            }
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "program": "-m",
            "args": [
                "pytest",
                "-v",
                "--cov=src"
            ],
            "console": "integratedTerminal",
            "cwd": "\${workspaceFolder}"
        }
    ]
}
EOF

    print_status "VS Code configuration created"
else
    print_status "VS Code configuration already exists"
fi

print_header "Development Environment Setup Complete!"

echo ""
print_status "Next steps:"
echo "  1. Configure your .env file with necessary API keys and settings"
echo "  2. Run tests: ./scripts/run-tests.sh"
echo "  3. Start development server: ./scripts/run-dev.sh"
echo "  4. Check code quality: ./scripts/check-quality.sh"
echo ""
print_status "Available endpoints:"
echo "  - API: http://localhost:8000"
echo "  - Documentation: http://localhost:8000/docs"
echo "  - Health Check: http://localhost:8000/health"
echo ""
print_status "Development tools installed:"
echo "  - pytest (testing)"
echo "  - black (code formatting)"
echo "  - isort (import sorting)"
echo "  - flake8 (linting)"
echo "  - mypy (type checking)"
echo "  - bandit (security scanning)"
echo "  - safety (dependency scanning)"
echo ""
print_status "For git workflow information, see: docs/GIT_WORKFLOW.md"
print_status "For project documentation, see: CLAUDE.md"

echo ""
print_header "Happy coding! 🚀"