# Branch Protection Configuration

## Overview

This document provides specific recommendations for configuring GitHub branch protection rules to enforce the git workflow and quality standards for the Faculty Research Opportunity Notifier project.

## Branch Protection Rules

### Main Branch (`main`)

**Required Settings:**
- ✅ Restrict pushes that create files larger than 100MB
- ✅ Require a pull request before merging
- ✅ Require approvals: **2**
- ✅ Dismiss stale PR approvals when new commits are pushed
- ✅ Require review from code owners
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Restrict pushes that create files larger than 100MB
- ✅ Do not allow bypassing the above settings
- ✅ Restrict pushes to matching branches (administrators only)

**Required Status Checks:**
- `CI/CD Pipeline / code-quality`
- `CI/CD Pipeline / test (3.10)`  
- `CI/CD Pipeline / test (3.11)`
- `CI/CD Pipeline / security`
- `CI/CD Pipeline / docker`
- `CI/CD Pipeline / integration`

**Additional Restrictions:**
- Only administrators can push to main
- Force pushes disabled
- Deletions disabled

### Develop Branch (`develop`)

**Required Settings:**
- ✅ Require a pull request before merging
- ✅ Require approvals: **1**
- ✅ Dismiss stale PR approvals when new commits are pushed
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Allow force pushes (administrators only)

**Required Status Checks:**
- `CI/CD Pipeline / code-quality`
- `CI/CD Pipeline / test (3.10)`
- `CI/CD Pipeline / security`
- `CI/CD Pipeline / docker`

**Additional Settings:**
- Allow administrators to bypass pull request requirements
- Auto-delete head branches after merge

## Implementation Steps

### 1. Navigate to Repository Settings
1. Go to your GitHub repository
2. Click on **Settings** tab
3. Select **Branches** from the left sidebar

### 2. Configure Main Branch Protection

Click **Add rule** and configure:

```yaml
Branch name pattern: main
Settings:
  - Restrict pushes that create files larger than 100MB: ✓
  - Require a pull request before merging: ✓
    - Required approvals: 2
    - Dismiss stale PR approvals: ✓
    - Require review from code owners: ✓
    - Restrict push access: ✓
  - Require status checks to pass: ✓
    - Require branches up to date: ✓
    - Status checks:
      - CI/CD Pipeline / code-quality
      - CI/CD Pipeline / test (3.10)
      - CI/CD Pipeline / test (3.11)
      - CI/CD Pipeline / security
      - CI/CD Pipeline / docker
      - CI/CD Pipeline / integration
  - Require conversation resolution: ✓
  - Restrict pushes that create files larger than 100MB: ✓
  - Do not allow bypassing settings: ✓
  - Restrict pushes to matching branches: ✓
```

### 3. Configure Develop Branch Protection

Click **Add rule** and configure:

```yaml
Branch name pattern: develop
Settings:
  - Require a pull request before merging: ✓
    - Required approvals: 1
    - Dismiss stale PR approvals: ✓
    - Allow bypass by administrators: ✓
  - Require status checks to pass: ✓
    - Require branches up to date: ✓
    - Status checks:
      - CI/CD Pipeline / code-quality
      - CI/CD Pipeline / test (3.10)
      - CI/CD Pipeline / security
      - CI/CD Pipeline / docker
  - Require conversation resolution: ✓
  - Allow force pushes: ✓ (administrators only)
  - Allow deletions: ✗
```

### 4. Configure Feature Branch Pattern (Optional)

For enhanced control over feature branches:

```yaml
Branch name pattern: feature/*
Settings:
  - Require a pull request before merging: ✓
    - Required approvals: 1
  - Require status checks to pass: ✓
    - Status checks:
      - CI/CD Pipeline / code-quality
      - CI/CD Pipeline / test (3.10)
  - Delete branch on merge: ✓
```

## Code Owners Configuration

Create `.github/CODEOWNERS` file:

```gitignore
# Global code owners
* @devops-team @lead-developer

# Multi-agent architecture files
/src/agents/ @agent-team @lead-developer
/src/core/a2a_protocols.py @agent-team @architecture-team

# Infrastructure and deployment
/docker* @devops-team
/.github/workflows/ @devops-team
/scripts/ @devops-team
/nginx/ @devops-team

# Core models and API
/src/core/models.py @backend-team @lead-developer
/src/main.py @backend-team @lead-developer

# Configuration and documentation
/config/ @devops-team @lead-developer
/docs/ @documentation-team
/CLAUDE.md @lead-developer @documentation-team
/development_checklist.yaml @project-manager @lead-developer

# Testing
/tests/ @qa-team @backend-team

# Security sensitive files
/secrets/ @security-team @devops-team
/.env* @security-team @devops-team
```

## Deployment Keys and Access

### Required Secrets

Configure the following secrets in GitHub repository settings:

```yaml
Repository Secrets:
  - DOCKER_REGISTRY_TOKEN: GitHub Container Registry access
  - PRODUCTION_SSH_KEY: Production server access
  - POSTGRES_PASSWORD: Database password
  - SECRET_KEY: Application secret key
  - GOOGLE_API_KEY: Google AI API access
  - ORCID_CLIENT_SECRET: ORCID API credentials

Environment Secrets (if using GitHub Environments):
  development:
    - DEV_DATABASE_URL
  staging:
    - STAGING_DATABASE_URL
    - STAGING_SECRET_KEY
  production:
    - PRODUCTION_DATABASE_URL
    - PRODUCTION_SECRET_KEY
    - SSL_CERTIFICATE
    - SSL_PRIVATE_KEY
```

### Team Permissions

Configure team access levels:

```yaml
Teams:
  devops-team:
    - Repository: Admin
    - Can bypass branch protection: Yes
    - Can force push: Yes
    
  backend-team:
    - Repository: Write
    - Can approve PRs: Yes
    - Required for: /src/core/, /src/main.py
    
  agent-team:
    - Repository: Write
    - Can approve PRs: Yes
    - Required for: /src/agents/
    
  qa-team:
    - Repository: Write
    - Can approve PRs: Yes
    - Required for: /tests/
    
  documentation-team:
    - Repository: Write
    - Can approve PRs: Yes
    - Required for: /docs/, *.md files
```

## Status Check Configuration

### GitHub Actions Integration

The status checks reference jobs from `.github/workflows/ci.yml`:

```yaml
Status Check Names (exactly as they appear in GitHub):
  - "CI/CD Pipeline / code-quality"
  - "CI/CD Pipeline / test (3.10)"
  - "CI/CD Pipeline / test (3.11)"
  - "CI/CD Pipeline / security"  
  - "CI/CD Pipeline / docker"
  - "CI/CD Pipeline / integration"
```

### External Integrations

If using external services, add their status checks:

```yaml
External Status Checks:
  - "codecov/project"           # Code coverage
  - "sonarcloud"               # Code quality
  - "snyk"                     # Security scanning
  - "dependabot"               # Dependency updates
```

## Enforcement Recommendations

### 1. Gradual Rollout

**Phase 1: Warning Mode (Week 1-2)**
- Enable all rules but allow bypass
- Monitor compliance
- Train team on new workflow

**Phase 2: Soft Enforcement (Week 3-4)**
- Enable enforcement for develop branch
- Keep main branch flexible
- Address any workflow issues

**Phase 3: Full Enforcement (Week 5+)**
- Enable all protection rules
- Monitor and adjust as needed
- Document any exceptions

### 2. Exception Handling

**Emergency Hotfixes:**
- Create `hotfix/*` branches from main
- Require post-merge review and documentation
- Temporary bypass allowed for critical issues

**Automated Updates:**
- Dependabot PRs can bypass some checks
- Auto-merge for trusted updates
- Require manual review for major updates

### 3. Monitoring and Compliance

**Weekly Reviews:**
- Review branch protection violations
- Analyze failed status checks
- Team feedback on workflow efficiency

**Monthly Audits:**
- Access permission review
- Code owner effectiveness
- Status check reliability

## Troubleshooting

### Common Issues

**Status Checks Not Appearing:**
1. Ensure GitHub Actions workflow has run at least once
2. Check workflow job names match exactly
3. Verify branch protection rule spelling

**PRs Blocked Unexpectedly:**
1. Check if all required status checks passed
2. Verify branch is up to date with target
3. Ensure all conversations resolved

**Unable to Merge Despite Approvals:**
1. Check if dismiss stale reviews is enabled
2. Verify required number of approvals
3. Ensure code owner approval if required

### Solutions

**Reset Branch Protection:**
```bash
# If configuration gets corrupted, start fresh
# Delete existing rules in GitHub UI
# Re-apply configuration step by step
```

**Force Push Emergency:**
```bash
# Only for administrators in true emergencies
git push origin feature-branch --force-with-lease
# Document the reason and notify team
```

**Bypass for Urgent Fixes:**
1. Use administrator override temporarily
2. Create follow-up issue for proper process
3. Document exception in commit message

## Validation Checklist

After implementing branch protection rules:

- [ ] Test creating PR to main branch
- [ ] Verify status checks are required and working
- [ ] Test that failed status checks block merge
- [ ] Confirm review requirements work
- [ ] Test force push restrictions
- [ ] Verify code owner requirements
- [ ] Test conversation resolution requirement
- [ ] Confirm branch deletion restrictions
- [ ] Test administrator bypass capabilities
- [ ] Verify auto-delete of feature branches

## Maintenance

### Regular Tasks

**Weekly:**
- Review branch protection violations
- Update status check requirements if workflow changes
- Monitor team feedback on workflow friction

**Monthly:**
- Audit team permissions and access
- Review code owner assignments
- Update protection rules based on project evolution

**Quarterly:**
- Comprehensive security review
- Branch protection rule effectiveness analysis
- Team workflow satisfaction survey

---

**Implementation Date**: To be scheduled  
**Review Date**: Monthly  
**Owner**: DevOps Team  
**Approvers**: Lead Developer, Project Manager