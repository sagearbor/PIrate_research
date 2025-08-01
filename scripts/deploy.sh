#!/bin/bash

# Deployment script for Faculty Research Opportunity Notifier
# Supports development, staging, and production deployments

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

# Default values
ENVIRONMENT="development"
BUILD_CACHE="--no-cache"
PULL_LATEST="false"
BACKUP_DATA="false"
SCALE_REPLICAS="1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --use-cache)
            BUILD_CACHE=""
            shift
            ;;
        --pull-latest)
            PULL_LATEST="true"
            shift
            ;;
        --backup)
            BACKUP_DATA="true"
            shift
            ;;
        --scale)
            SCALE_REPLICAS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Set environment (development|staging|production)"
            echo "  --use-cache             Use Docker build cache"
            echo "  --pull-latest           Pull latest images before deployment"
            echo "  --backup                Backup data before deployment"
            echo "  --scale N               Scale to N replicas (production only)"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option $1"
            exit 1
            ;;
    esac
done

print_header "Faculty Research Opportunity Notifier - Deployment"

# Validate environment
case $ENVIRONMENT in
    development|dev)
        ENVIRONMENT="development"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    staging|stage)
        ENVIRONMENT="staging"
        COMPOSE_FILE="docker-compose.yml -f docker-compose.prod.yml"
        ;;
    production|prod)
        ENVIRONMENT="production"
        COMPOSE_FILE="docker-compose.yml -f docker-compose.prod.yml"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        print_error "Valid environments: development, staging, production"
        exit 1
        ;;
esac

print_status "Deploying to: $ENVIRONMENT"

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    print_error "This script must be run from the project root directory"
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data/raw data/processed logs secrets nginx/ssl

# Environment-specific setup
case $ENVIRONMENT in
    development)
        print_status "Setting up development environment..."
        
        # Create .env file if it doesn't exist
        if [ ! -f ".env" ]; then
            print_status "Creating development .env file..."
            cat > .env << EOF
DEBUG=true
LOG_LEVEL=DEBUG
POSTGRES_DB=research_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_pass
GRAFANA_PASSWORD=admin
EOF
        fi
        ;;
        
    staging|production)
        print_status "Setting up $ENVIRONMENT environment..."
        
        # Check for production secrets
        if [ ! -f "secrets/postgres_password.txt" ]; then
            print_warning "Production secrets not found. Creating placeholder files..."
            echo "CHANGE_THIS_PASSWORD" > secrets/postgres_password.txt
            print_warning "Please update secrets/postgres_password.txt with a secure password"
        fi
        
        # Check for SSL certificates
        if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
            print_warning "SSL certificates not found. Creating self-signed certificates for testing..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/key.pem \
                -out nginx/ssl/cert.pem \
                -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
                2>/dev/null || true
            print_warning "Please replace with proper SSL certificates for production"
        fi
        
        # Set production environment variables
        cat > .env << EOF
DEBUG=false
LOG_LEVEL=INFO
POSTGRES_DB=research_prod
POSTGRES_USER=research_user
GRAFANA_PASSWORD=secure_admin_password
EOF
        ;;
esac

# Backup data if requested
if [ "$BACKUP_DATA" = "true" ]; then
    print_status "Creating data backup..."
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "data" ]; then
        cp -r data "$BACKUP_DIR/"
        print_status "Data backed up to $BACKUP_DIR"
    fi
fi

# Pull latest images if requested
if [ "$PULL_LATEST" = "true" ]; then
    print_status "Pulling latest images..."
    docker-compose -f $COMPOSE_FILE pull
fi

# Stop existing services
print_status "Stopping existing services..."
docker-compose -f $COMPOSE_FILE down --remove-orphans

# Build and start services
print_status "Building and starting services..."
if [ "$ENVIRONMENT" = "development" ]; then
    # Development: build locally and start with override
    docker-compose build $BUILD_CACHE
    docker-compose up -d
else
    # Production/Staging: use production compose files
    docker-compose -f $COMPOSE_FILE build $BUILD_CACHE
    docker-compose -f $COMPOSE_FILE up -d
    
    # Scale services if specified
    if [ "$SCALE_REPLICAS" != "1" ]; then
        print_status "Scaling research-agent to $SCALE_REPLICAS replicas..."
        docker-compose -f $COMPOSE_FILE up -d --scale research-agent=$SCALE_REPLICAS
    fi
fi

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 10

# Health checks
print_status "Performing health checks..."

# Check main application
for i in {1..30}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_status "✅ Research Agent API is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "❌ Research Agent API health check failed"
        docker-compose -f $COMPOSE_FILE logs research-agent
        exit 1
    fi
    sleep 2
done

# Check database connection
if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready >/dev/null 2>&1; then
    print_status "✅ PostgreSQL is ready"
else
    print_warning "⚠️  PostgreSQL connection check failed"
fi

# Check Redis
if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping >/dev/null 2>&1; then
    print_status "✅ Redis is ready"
else
    print_warning "⚠️  Redis connection check failed"
fi

# Display deployment information
print_header "Deployment Complete!"

echo ""
print_status "Environment: $ENVIRONMENT"
print_status "Services Status:"
docker-compose -f $COMPOSE_FILE ps

echo ""
print_status "Available endpoints:"
case $ENVIRONMENT in
    development)
        echo "  - API: http://localhost:8000"
        echo "  - Documentation: http://localhost:8000/docs"
        echo "  - Health Check: http://localhost:8000/health"
        echo "  - Database: postgresql://dev_user:dev_pass@localhost:5432/research_dev"
        echo "  - Redis: redis://localhost:6379"
        ;;
    staging|production)
        echo "  - API: https://localhost (via Nginx)"
        echo "  - Documentation: https://localhost/docs"
        echo "  - Health Check: https://localhost/health"
        echo "  - Monitoring: http://localhost:3000 (Grafana, if enabled)"
        echo "  - Metrics: http://localhost:9090 (Prometheus, if enabled)"
        ;;
esac

echo ""
print_status "Useful commands:"
echo "  - View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "  - Stop services: docker-compose -f $COMPOSE_FILE down"
echo "  - Scale services: docker-compose -f $COMPOSE_FILE up -d --scale research-agent=N"
echo "  - Update services: $0 --environment $ENVIRONMENT --pull-latest"

if [ "$ENVIRONMENT" != "development" ]; then
    echo ""
    print_warning "Production deployment notes:"
    echo "  - Update secrets/postgres_password.txt with a secure password"
    echo "  - Replace nginx/ssl certificates with proper SSL certificates"
    echo "  - Configure monitoring and alerting"
    echo "  - Set up log rotation and backup strategies"
    echo "  - Review security settings and firewall rules"
fi

echo ""
print_header "Deployment successful! 🚀"