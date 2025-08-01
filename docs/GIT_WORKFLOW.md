# Git Workflow and Branching Strategy

## Overview

This document outlines the git workflow and branching strategy for the Faculty Research Opportunity Notifier project. Our approach is designed to support the multi-agent architecture development while maintaining code quality and enabling continuous integration.

## Branching Strategy

### Main Branches

#### `main`
- **Purpose**: Production-ready code
- **Protection**: Protected branch with required reviews
- **Deployment**: Automatically deploys to production
- **Merge Policy**: Only from `develop` via pull request
- **Status Checks**: All CI/CD checks must pass

#### `develop`
- **Purpose**: Integration branch for development
- **Protection**: Protected branch with required reviews
- **Testing**: Automated testing on every push
- **Merge Policy**: From feature branches via pull request
- **Status Checks**: All CI/CD checks must pass

### Supporting Branches

#### Feature Branches
- **Naming**: `feature/task-id-description` (e.g., `feature/3.1.1-matcher-agent`)
- **Source**: Branch from `develop`
- **Merge Target**: `develop`
- **Lifetime**: Temporary (deleted after merge)
- **Purpose**: Individual feature development

#### Bugfix Branches
- **Naming**: `bugfix/issue-description` (e.g., `bugfix/api-timeout-error`)
- **Source**: Branch from `develop` (or `main` for hotfixes)
- **Merge Target**: `develop` (or `main` for hotfixes)
- **Lifetime**: Temporary (deleted after merge)

#### Release Branches
- **Naming**: `release/v1.0.0`
- **Source**: Branch from `develop`
- **Merge Target**: Both `main` and `develop`
- **Purpose**: Release preparation and bug fixes

#### Hotfix Branches
- **Naming**: `hotfix/critical-issue-description`
- **Source**: Branch from `main`
- **Merge Target**: Both `main` and `develop`
- **Purpose**: Critical production fixes

#### Agent-Specific Branches
- **Naming**: `agent/agent-name-feature` (e.g., `agent/ingestion-enhancement`)
- **Source**: Branch from `develop`
- **Merge Target**: `develop`
- **Purpose**: Multi-agent system specific development

## Development Workflow

### 1. Starting New Work

```bash
# Update your local develop branch
git checkout develop
git pull origin develop

# Create a new feature branch
git checkout -b feature/3.1.1-matcher-agent

# Push the new branch to remote
git push -u origin feature/3.1.1-matcher-agent
```

### 2. Development Process

```bash
# Make your changes
# Follow the development checklist tasks

# Stage and commit changes
git add .
git commit -m "feat: implement multi-dimensional scoring for matcher agent

- Add scoring models for research methodology alignment
- Implement deadline urgency weighting
- Add career stage considerations
- Update task 3.1.1 in development checklist

Refs: #3.1.1"

# Push changes regularly
git push origin feature/3.1.1-matcher-agent
```

### 3. Creating Pull Requests

```bash
# Ensure your branch is up to date
git checkout develop
git pull origin develop
git checkout feature/3.1.1-matcher-agent
git merge develop

# Resolve any conflicts
# Run all tests
pytest -v --cov=src --cov-report=term-missing

# Push final changes
git push origin feature/3.1.1-matcher-agent
```

Create a pull request using the GitHub UI with the provided PR template.

### 4. After PR Approval

```bash
# Switch to develop and pull the merged changes
git checkout develop
git pull origin develop

# Delete the feature branch
git branch -d feature/3.1.1-matcher-agent
git push origin --delete feature/3.1.1-matcher-agent
```

## Commit Message Guidelines

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Scope (Optional)
- `agent`: Agent-related changes
- `api`: API changes
- `docker`: Docker configuration
- `tests`: Test-related changes
- `docs`: Documentation
- `ci`: CI/CD pipeline

### Examples
```bash
# Good commit messages
git commit -m "feat(agent): add matcher agent with multi-dimensional scoring

- Implement research methodology alignment scoring
- Add deadline urgency weighting
- Include career stage considerations
- Update development checklist task 3.1.1

Closes #123"

git commit -m "fix(api): resolve health check timeout issue

- Increase health check timeout from 5s to 10s
- Add retry logic for database connections
- Update Docker health check configuration

Fixes #456"

git commit -m "test: add comprehensive tests for ingestion agent

- Mock external API calls for scrapers
- Test data validation and error handling
- Achieve 95% code coverage for ingestion module

Refs: task-2.3.1"
```

## Branch Protection Rules

### For `main` branch:
- Require pull request reviews (2 reviewers)
- Dismiss stale reviews when new commits are pushed
- Require status checks to pass:
  - CI/CD Pipeline (all jobs)
  - Code Quality Checks
  - Security Scan
  - Docker Build
- Restrict pushes to administrators only
- Require branches to be up to date before merging

### For `develop` branch:
- Require pull request reviews (1 reviewer)
- Require status checks to pass:
  - CI/CD Pipeline
  - Code Quality Checks
  - All Tests Pass
- Allow force pushes for administrators
- Require branches to be up to date before merging

## Release Process

### 1. Prepare Release Branch
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.1.0
```

### 2. Update Version Information
- Update version in `src/main.py`
- Update CHANGELOG.md
- Update any version references in documentation

### 3. Testing and Bug Fixes
- Perform thorough testing
- Fix any release-specific bugs
- Update development checklist status

### 4. Merge to Main
```bash
# Create PR from release/v1.1.0 to main
# After approval and CI passes:
git checkout main
git pull origin main
git merge --no-ff release/v1.1.0
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin main --tags
```

### 5. Merge Back to Develop
```bash
git checkout develop
git merge --no-ff release/v1.1.0
git push origin develop
git branch -d release/v1.1.0
```

## Multi-Agent Development Considerations

### Agent Integration
- Each agent should be developed in isolation when possible
- Use feature branches for agent-specific work
- Test agent communication interfaces thoroughly
- Update A2A protocol documentation

### Development Checklist Integration
- Reference specific task IDs in commit messages
- Update task status in development_checklist.yaml
- Ensure all prerequisites are met before starting tasks
- Include testing requirements in PR descriptions

### Data Flow Testing
- Test complete pipeline from ingestion to notification
- Validate agent-to-agent communication
- Ensure data consistency across agent boundaries
- Performance test multi-agent workflows

## Troubleshooting

### Common Issues

#### Merge Conflicts
```bash
# When merging develop into feature branch
git checkout feature/your-branch
git fetch origin
git merge origin/develop

# Resolve conflicts in your editor
# After resolving:
git add .
git commit -m "resolve merge conflicts with develop"
```

#### Failed CI Checks
1. Check GitHub Actions logs for specific failures
2. Run tests locally: `pytest -v`
3. Check code formatting: `black --check src/ tests/`
4. Verify Docker build: `docker build -t test .`
5. Fix issues and push again

#### Stale Branches
```bash
# Clean up local branches
git remote prune origin
git branch -vv | grep ': gone]' | awk '{print $1}' | xargs git branch -d
```

## Best Practices

### Code Quality
- Run tests before every commit
- Use pre-commit hooks for formatting
- Follow PEP 8 style guidelines
- Write descriptive commit messages
- Keep commits focused and atomic

### Collaboration
- Communicate early about major changes
- Use draft PRs for work-in-progress
- Request reviews from relevant team members
- Respond to review feedback promptly
- Keep PRs focused and reasonably sized

### Documentation
- Update documentation with code changes
- Include examples in commit messages
- Reference development checklist tasks
- Update API documentation for endpoint changes

## Tools and Automation

### Pre-commit Hooks
Consider setting up pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

### GitHub CLI
For efficient PR management:
```bash
# Create PR from command line
gh pr create --title "feat: implement matching agent" --body "Implements task 3.1.1"

# Check PR status
gh pr status

# Review PR
gh pr review --approve
```

This workflow ensures code quality, maintains project integrity, and supports the multi-agent architecture development process effectively.