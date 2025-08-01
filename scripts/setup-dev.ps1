# Development Environment Setup Script for Windows
# Faculty Research Opportunity Notifier

param(
    [switch]$SkipTests,
    [switch]$Force
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $InfoColor
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $SuccessColor
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $WarningColor
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ErrorColor
}

function Write-Header {
    param([string]$Message)
    Write-Host "========================================" -ForegroundColor $InfoColor
    Write-Host $Message -ForegroundColor $InfoColor
    Write-Host "========================================" -ForegroundColor $InfoColor
}

# Check if running in project root
if (-not (Test-Path "requirements.txt") -or -not (Test-Path "src\main.py")) {
    Write-Error "This script must be run from the project root directory"
    Write-Error "Make sure you're in the Faculty Research Opportunity Notifier directory"
    exit 1
}

Write-Header "Faculty Research Opportunity Notifier - Development Setup (Windows)"

# Check Python version
Write-Status "Checking Python version..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -eq 3 -and $minor -ge 10) {
            Write-Success "Python $($matches[0]) detected - OK"
        } else {
            Write-Error "Python 3.10 or higher is required. Found: $($matches[0])"
            exit 1
        }
    }
} catch {
    Write-Error "Python not found or not accessible. Please install Python 3.10+ and add it to your PATH"
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path "venv") -or $Force) {
    Write-Status "Creating virtual environment..."
    python -m venv venv
    Write-Success "Virtual environment created in .\venv"
} else {
    Write-Status "Virtual environment already exists"
}

# Activate virtual environment
Write-Status "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Status "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
Write-Status "Installing Python dependencies..."
pip install -r requirements.txt

# Install development dependencies
Write-Status "Installing development dependencies..."
pip install black isort flake8 mypy pytest-cov pytest-xdist pre-commit bandit safety

# Create data directories
Write-Status "Creating data directories..."
New-Item -ItemType Directory -Path "data\raw", "data\processed", "logs", "temp" -Force | Out-Null

# Set up pre-commit hooks
Write-Status "Setting up pre-commit hooks..."
try {
    pre-commit install
    Write-Success "Pre-commit hooks installed"
} catch {
    Write-Warning "Pre-commit not available. Install manually if needed: pip install pre-commit"
}

# Create .env template if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Status "Creating .env template..."
    @"
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
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success ".env template created - please configure with your settings"
} else {
    Write-Status ".env file already exists"
}

# Run initial tests to verify setup
if (-not $SkipTests) {
    Write-Status "Running initial test suite to verify setup..."
    try {
        python -m pytest tests\test_main.py -v
        Write-Success "Basic tests passed - setup verification successful"
    } catch {
        Write-Warning "Some tests failed - please check the output above"
    }
}

# Check Docker installation
Write-Status "Checking Docker installation..."
try {
    $dockerVersion = docker --version
    Write-Success "Docker detected: $dockerVersion"
    
    # Test Docker build
    Write-Status "Testing Docker build..."
    docker build -t research-agent-test . 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker build successful"
        docker rmi research-agent-test 2>$null
    } else {
        Write-Warning "Docker build failed - check Dockerfile"
    }
} catch {
    Write-Warning "Docker not found - install Docker Desktop for containerization features"
}

# Check Docker Compose
try {
    $composeVersion = docker-compose --version
    Write-Success "Docker Compose detected: $composeVersion"
} catch {
    Write-Warning "Docker Compose not found - install for multi-container development"
}

# Create development scripts
Write-Status "Creating development helper scripts..."

# Test runner script
@"
@echo off
echo Running comprehensive test suite...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run tests with coverage
echo Running pytest with coverage...
python -m pytest -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80

echo Test suite completed!
pause
"@ | Out-File -FilePath "scripts\run-tests.bat" -Encoding ASCII

# Code quality script
@"
@echo off
echo Running code quality checks...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Checking code formatting with black...
black --check --diff src\ tests\

echo Checking import sorting with isort...
isort --check-only --diff src\ tests\

echo Running flake8 linting...
flake8 src\ tests\ --max-line-length=88 --extend-ignore=E203,W503

echo Running type checking with mypy...
mypy src\ --ignore-missing-imports --no-strict-optional

echo Running security scan with bandit...
bandit -r src\ -f json

echo Checking dependencies with safety...
safety check

echo Code quality checks completed!
pause
"@ | Out-File -FilePath "scripts\check-quality.bat" -Encoding ASCII

# Development server script
@"
@echo off
echo Starting development server...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Starting FastAPI development server...
echo API will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo Press Ctrl+C to stop the server

python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
"@ | Out-File -FilePath "scripts\run-dev.bat" -Encoding ASCII

Write-Success "Development helper scripts created in .\scripts\"

# Create VS Code configuration if .vscode doesn't exist
if (-not (Test-Path ".vscode")) {
    Write-Status "Creating VS Code configuration..."
    New-Item -ItemType Directory -Path ".vscode" -Force | Out-Null
    
    # VS Code settings
    @"
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
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
"@ | Out-File -FilePath ".vscode\settings.json" -Encoding UTF8

    # VS Code launch configuration
    @"
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
            "cwd": "`${workspaceFolder}",
            "env": {
                "PYTHONPATH": "`${workspaceFolder}/src"
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
            "cwd": "`${workspaceFolder}"
        }
    ]
}
"@ | Out-File -FilePath ".vscode\launch.json" -Encoding UTF8

    Write-Success "VS Code configuration created"
} else {
    Write-Status "VS Code configuration already exists"
}

Write-Header "Development Environment Setup Complete!"

Write-Host ""
Write-Status "Next steps:"
Write-Host "  1. Configure your .env file with necessary API keys and settings"
Write-Host "  2. Run tests: .\scripts\run-tests.bat"
Write-Host "  3. Start development server: .\scripts\run-dev.bat"
Write-Host "  4. Check code quality: .\scripts\check-quality.bat"
Write-Host ""
Write-Status "Available endpoints:"
Write-Host "  - API: http://localhost:8000"
Write-Host "  - Documentation: http://localhost:8000/docs"
Write-Host "  - Health Check: http://localhost:8000/health"
Write-Host ""
Write-Status "Development tools installed:"
Write-Host "  - pytest (testing)"
Write-Host "  - black (code formatting)"
Write-Host "  - isort (import sorting)"
Write-Host "  - flake8 (linting)"
Write-Host "  - mypy (type checking)"
Write-Host "  - bandit (security scanning)"
Write-Host "  - safety (dependency scanning)"
Write-Host ""
Write-Status "For git workflow information, see: docs\GIT_WORKFLOW.md"
Write-Status "For project documentation, see: CLAUDE.md"

Write-Host ""
Write-Header "Happy coding! 🚀"