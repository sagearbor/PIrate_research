# DevOps Guide - Faculty Research Opportunity Notifier

## Overview

This document provides comprehensive guidance for DevOps operations including CI/CD pipelines, deployment procedures, monitoring, and quality assurance for the Faculty Research Opportunity Notifier project.

## Table of Contents

1. [CI/CD Pipeline](#cicd-pipeline)
2. [Quality Gates](#quality-gates)
3. [Deployment Guide](#deployment-guide)
4. [Environment Management](#environment-management)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security](#security)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## CI/CD Pipeline

### GitHub Actions Workflows

The project uses GitHub Actions for automated CI/CD with the following workflows:

#### 1. Main CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main`, `develop`, `multiAgent_claudCode_setup` branches
- Pull requests to `main`, `develop`
- Manual dispatch

**Jobs:**
1. **Code Quality Checks**
   - Black formatting
   - isort import sorting
   - flake8 linting
   - mypy type checking

2. **Testing**
   - Python 3.10 and 3.11 matrix
   - Comprehensive test suite (71 tests)
   - Coverage reporting (80% minimum)
   - Artifact upload

3. **Security Scanning**
   - Safety dependency scanning
   - Bandit security linting

4. **Docker Build & Test**
   - Multi-stage Docker build
   - Container health checks
   - Trivy vulnerability scanning
   - Registry push (on main branch)

5. **Integration Testing**
   - End-to-end API testing
   - Service health validation

#### 2. Release Pipeline (`.github/workflows/release.yml`)

**Triggers:**
- Git tags matching `v*`
- Published releases

**Features:**
- Production Docker image builds
- Release artifact generation
- Kubernetes manifests
- Security scanning
- Automated release notes

### Quality Gates

All code must pass the following quality gates before merging:

#### Automated Checks
- ✅ All tests pass (71/71)
- ✅ Code coverage ≥ 80%
- ✅ Black formatting compliance
- ✅ isort import ordering
- ✅ flake8 linting (max-line-length=88)
- ✅ Docker build success
- ✅ Security scans pass
- ✅ Type checking with mypy

#### Manual Reviews
- Code review by at least 1 team member
- Architecture review for agent changes
- Security review for external integrations

## Deployment Guide

### Quick Start

```bash
# Development environment
./scripts/setup-dev.sh
./scripts/run-dev.sh

# Production deployment
./scripts/deploy.sh --environment production --backup
```

### Environment Setup

#### Development
```bash
# Linux/macOS
./scripts/setup-dev.sh

# Windows
.\scripts\setup-dev.ps1

# Manual Docker setup
docker-compose up -d
```

#### Production
```bash
# Deploy with backup
./scripts/deploy.sh --environment production --backup --scale 2

# Quick production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Deployment Environments

#### 1. Development
- **Purpose**: Local development and testing
- **Configuration**: `docker-compose.yml` + `docker-compose.override.yml`
- **Features**: Hot reload, debug logging, exposed ports
- **Access**: http://localhost:8000

#### 2. Staging
- **Purpose**: Pre-production testing
- **Configuration**: `docker-compose.yml` + `docker-compose.prod.yml`
- **Features**: Production-like setup, limited resources
- **Access**: Configured domain with SSL

#### 3. Production
- **Purpose**: Live production environment
- **Configuration**: `docker-compose.yml` + `docker-compose.prod.yml`
- **Features**: Full security, monitoring, backups, load balancing
- **Access**: Production domain with SSL

### Container Registry

Images are automatically built and pushed to GitHub Container Registry:

```bash
# Pull latest image
docker pull ghcr.io/university/faculty-research-notifier:latest

# Pull specific version
docker pull ghcr.io/university/faculty-research-notifier:v1.0.0

# Pull development image
docker pull ghcr.io/university/faculty-research-notifier:develop
```

## Environment Management

### Environment Variables

#### Core Application
```env
# Application Settings
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=your-secret-key-here

# Database
POSTGRES_DB=research_prod
POSTGRES_USER=research_user
POSTGRES_PASSWORD=secure_password
```

#### External Services
```env
# AI/LLM APIs
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key

# Research APIs
NIH_API_KEY=your_nih_api_key
ORCID_CLIENT_ID=your_orcid_client_id
```

### Configuration Management

#### Development
- Local `.env` file
- Docker environment variables
- Default configurations in `config/`

#### Production
- Docker secrets for sensitive data
- External configuration management
- Environment-specific config files

### Data Persistence

#### Volumes
```yaml
volumes:
  postgres_data:      # Database data
  redis_data:         # Cache data
  prometheus_data:    # Metrics data
  grafana_data:       # Dashboard data
```

#### Backup Strategy
```bash
# Automated backup before deployment
./scripts/deploy.sh --backup

# Manual backup
docker-compose exec postgres pg_dump -U research_user research_db > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U research_user research_db < backup.sql
```

## Monitoring and Observability

### Application Monitoring

#### Health Checks
- **Endpoint**: `/health`
- **Docker**: Built-in health checks
- **Kubernetes**: Liveness and readiness probes

#### Logging
- **Format**: Structured JSON logging
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Storage**: Docker logs, external log aggregation

#### Metrics
- **Application**: Custom metrics via `/metrics`
- **System**: Prometheus monitoring
- **Visualization**: Grafana dashboards

### Infrastructure Monitoring

#### Services Monitored
- FastAPI application
- PostgreSQL database
- Redis cache
- Nginx reverse proxy

#### Key Metrics
- Request rate and latency
- Error rates
- Database connections
- Memory and CPU usage
- Agent processing times

### Alerting

#### Critical Alerts
- Application down
- Database connection failures
- High error rates (>5%)
- Memory usage >90%

#### Warning Alerts
- Response time >2s
- Disk usage >80%
- Failed agent tasks

## Security

### Container Security

#### Image Scanning
- Trivy vulnerability scanner
- Base image updates
- Minimal attack surface

#### Runtime Security
- Non-root user execution
- Read-only root filesystem
- Resource limits

### Network Security

#### Production Setup
- HTTPS only with SSL certificates
- Nginx reverse proxy
- Rate limiting
- Security headers

#### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw deny incoming
ufw enable
```

### Secrets Management

#### Development
- Local `.env` files
- Docker environment variables

#### Production
- Docker secrets
- External secret management
- Encrypted storage

### Security Scanning

#### Automated Scans
- Dependency scanning with Safety
- Code security with Bandit
- Container vulnerability scanning
- Secret detection

#### Manual Reviews
- Security architecture review
- Penetration testing
- Access control audit

## Troubleshooting

### Common Issues

#### CI/CD Pipeline Failures

**Test Failures**
```bash
# Run tests locally
pytest -v --cov=src --cov-report=term-missing

# Check specific test
pytest tests/test_main.py::TestMainApp::test_health_endpoint -v
```

**Docker Build Failures**
```bash
# Build locally with verbose output
docker build -t research-agent-test . --no-cache --progress=plain

# Check build context
docker build -t research-agent-test . --dry-run
```

**Quality Gate Failures**
```bash
# Fix formatting
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

#### Deployment Issues

**Container Won't Start**
```bash
# Check logs
docker-compose logs research-agent

# Debug container
docker-compose exec research-agent /bin/bash

# Check health
curl http://localhost:8000/health
```

**Database Connection Issues**
```bash
# Check database
docker-compose exec postgres pg_isready

# Check network
docker network ls
docker network inspect project_research-network
```

**Performance Issues**
```bash
# Check resource usage
docker stats

# Check application metrics
curl http://localhost:8000/metrics

# Database performance
docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### Debugging Tools

#### Development
```bash
# Live development server
./scripts/run-dev.sh

# Test runner with coverage
./scripts/run-tests.sh

# Code quality check
./scripts/check-quality.sh
```

#### Production
```bash
# View service status
docker-compose ps

# Follow logs
docker-compose logs -f research-agent

# Execute commands in container
docker-compose exec research-agent python -c "import sys; print(sys.path)"
```

## Best Practices

### Development Workflow

1. **Branch Strategy**
   - Follow git workflow in `docs/GIT_WORKFLOW.md`
   - Use feature branches for all changes
   - Require PR reviews before merging

2. **Code Quality**
   - Write tests for all new code
   - Maintain >80% test coverage
   - Follow PEP 8 style guidelines
   - Use type hints where appropriate

3. **Documentation**
   - Update documentation with code changes
   - Include docstrings for all functions
   - Keep README and CLAUDE.md current

### Deployment Best Practices

1. **Environment Parity**
   - Keep development and production similar
   - Use same base images and dependencies
   - Test in staging before production

2. **Zero-Downtime Deployments**
   - Use rolling updates for production
   - Health checks for service readiness
   - Rollback procedures documented

3. **Monitoring**
   - Monitor all critical metrics
   - Set up alerting for failures
   - Regular health check automation

### Security Best Practices

1. **Secrets Management**
   - Never commit secrets to version control
   - Use environment variables or secret management
   - Rotate secrets regularly

2. **Dependencies**
   - Keep dependencies updated
   - Regular security scanning
   - Pin dependency versions

3. **Access Control**
   - Principle of least privilege
   - Regular access reviews
   - Multi-factor authentication

### Multi-Agent Architecture Considerations

1. **Agent Communication**
   - Test agent interfaces thoroughly
   - Monitor agent-to-agent communication
   - Plan for A2A protocol integration

2. **Data Flow**
   - Validate data at agent boundaries
   - Monitor processing pipelines
   - Implement error recovery

3. **Scalability**
   - Design for horizontal scaling
   - Stateless agent implementation
   - Efficient resource utilization

## Quick Reference

### Useful Commands
```bash
# Development
./scripts/setup-dev.sh              # Setup development environment
./scripts/run-dev.sh                # Start development server
./scripts/run-tests.sh              # Run test suite
./scripts/check-quality.sh          # Code quality checks

# Deployment
./scripts/deploy.sh --environment dev    # Deploy to development
./scripts/deploy.sh --environment prod   # Deploy to production
docker-compose up -d                     # Start services
docker-compose down                      # Stop services
docker-compose logs -f research-agent    # View logs

# Docker Registry
docker pull ghcr.io/university/faculty-research-notifier:latest
docker push ghcr.io/university/faculty-research-notifier:v1.0.0

# Health Checks
curl http://localhost:8000/health        # Application health
curl http://localhost:8000/docs          # API documentation
```

### Port Reference
- **8000**: FastAPI application
- **5432**: PostgreSQL database
- **6379**: Redis cache
- **80/443**: Nginx reverse proxy
- **3000**: Grafana dashboards
- **9090**: Prometheus metrics

### File Structure
```
├── .github/
│   ├── workflows/           # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/      # Issue templates
│   └── pull_request_template.md
├── docs/
│   ├── DEVOPS.md           # This file
│   └── GIT_WORKFLOW.md     # Git workflow guide
├── scripts/
│   ├── setup-dev.sh        # Development setup
│   ├── deploy.sh           # Deployment script
│   └── init-db.sql         # Database initialization
├── nginx/
│   └── nginx.conf          # Nginx configuration
├── docker-compose.yml      # Docker Compose configuration
├── docker-compose.prod.yml # Production overrides
├── Dockerfile              # Container definition
├── pyproject.toml          # Python project configuration
└── .pre-commit-config.yaml # Pre-commit hooks
```

For additional support, refer to:
- [Git Workflow Guide](GIT_WORKFLOW.md)
- [Project Overview](../CLAUDE.md)
- [Development Checklist](../development_checklist.yaml)

---

**Last Updated**: July 31, 2025  
**Version**: 1.0.0  
**Maintainer**: DevOps Team