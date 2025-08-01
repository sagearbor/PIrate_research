# Faculty Research Opportunity Notifier - Operational Runbook

## Table of Contents

1. [System Overview](#system-overview)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
4. [Emergency Procedures](#emergency-procedures)
5. [Maintenance Tasks](#maintenance-tasks)
6. [Escalation Procedures](#escalation-procedures)
7. [System Recovery](#system-recovery)
8. [Performance Tuning](#performance-tuning)

## System Overview

### Architecture Summary
- **FastAPI Application**: Main API service
- **Multi-Agent Pipeline**: Specialized processing agents
- **Monitoring Stack**: Prometheus + Grafana + AlertManager
- **External Services**: NIH, PCORI, Google Scholar, arXiv, PubMed, ORCID

### Key URLs
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### Health Endpoints
- **Basic Health**: `/health`
- **Detailed Health**: `/health/detailed`
- **Readiness**: `/health/ready`
- **External Services**: `/health/external-services`

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Health
```
# API Response Time (95th percentile should be < 1s)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error Rate (should be < 1%)
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Request Rate
rate(http_requests_total[5m])
```

#### Agent Performance
```
# Agent Execution Time
histogram_quantile(0.95, rate(agent_execution_duration_seconds_bucket[5m]))

# Agent Success Rate
rate(agent_executions_total{status="success"}[5m]) / rate(agent_executions_total[5m])

# Agent Queue Size
agent_queue_size
```

#### System Resources
```
# CPU Usage (should be < 80%)
system_cpu_usage_percent

# Memory Usage (should be < 2GB)
system_memory_usage_bytes / (1024*1024*1024)

# Disk Usage
node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}
```

#### External Services
```
# External API Success Rate
rate(external_api_calls_total{status="success"}[5m]) / rate(external_api_calls_total[5m])

# Circuit Breaker Status (0=closed, 1=open, 2=half-open)
circuit_breaker_state
```

### Alert Response Matrix

| Alert Level | Response Time | Actions Required |
|-------------|---------------|------------------|
| Critical | 15 minutes | Immediate investigation, consider service restart |
| Warning | 1 hour | Investigation during business hours |
| Info | 4 hours | Log review, trend analysis |

## Common Issues and Troubleshooting

### Issue: API is Down (HTTP 503 or connection refused)

**Symptoms:**
- Health check returns 503 or times out
- API requests fail with connection errors
- Grafana shows no recent metrics

**Diagnosis:**
```bash
# Check if the process is running
ps aux | grep python
ps aux | grep uvicorn

# Check port availability
netstat -tlnp | grep 8000
lsof -i :8000

# Check system resources
top
free -h
df -h

# Check logs
tail -f logs/application.log
journalctl -u research-api -f
```

**Resolution:**
1. **Service Restart**:
   ```bash
   # For systemd service
   sudo systemctl restart research-api
   
   # For Docker
   docker-compose restart research-api
   
   # For development
   pkill -f uvicorn
   uvicorn src.main:app --reload
   ```

2. **Check Dependencies**:
   ```bash
   # Verify Python environment
   python --version
   pip list | grep fastapi
   
   # Check file permissions
   ls -la src/main.py
   ```

3. **Resource Issues**:
   ```bash
   # Free up disk space
   docker system prune -f
   rm -rf logs/*.log.old
   
   # Check memory leaks
   ps aux --sort=-%mem | head -10
   ```

### Issue: High API Latency (> 1 second response time)

**Symptoms:**
- Slow API responses
- Grafana shows high response times
- Users report timeouts

**Diagnosis:**
```bash
# Check system load
uptime
vmstat 1 5

# Check I/O wait
iostat -x 1 5

# Check database/file I/O
lsof | grep python | wc -l

# Check for slow queries
tail -f logs/performance.log | grep slow_query
```

**Resolution:**
1. **Scale Resources**:
   ```bash
   # Increase worker processes
   export WORKERS=4
   uvicorn src.main:app --workers $WORKERS
   
   # For Docker
   docker-compose up --scale research-api=2
   ```

2. **Optimize Queries**:
   - Review agent execution times in Grafana
   - Check external API response times
   - Implement caching for frequent requests

3. **Circuit Breaker Tuning**:
   - Check `/health/external-services`
   - Adjust timeout settings if needed
   - Verify external service health

### Issue: Agent Execution Failures

**Symptoms:**
- High error rate in agent metrics
- Failed matches or notifications
- Circuit breakers opening frequently

**Diagnosis:**
```bash
# Check agent logs
grep -i error logs/application.log | tail -20
grep "agent_name" logs/application.log | grep error

# Check external service status
curl http://localhost:8000/health/external-services

# Review Grafana agent dashboard
# Check agent execution duration and success rates
```

**Resolution:**
1. **External Service Issues**:
   ```bash
   # Test external APIs manually
   curl -I https://api.reporter.nih.gov/
   curl -I https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi
   
   # Check rate limiting
   curl -H "User-Agent: ResearchBot/1.0" https://api.service.com/endpoint
   ```

2. **Configuration Issues**:
   ```bash
   # Validate configuration files
   python -c "import yaml; yaml.safe_load(open('config/scraping_urls.yaml'))"
   python -c "import yaml; yaml.safe_load(open('config/faculty_search_sources.yaml'))"
   ```

3. **Agent Recovery**:
   ```bash
   # Clear agent queues (if implemented)
   # Restart specific agent processes
   # Review and adjust circuit breaker thresholds
   ```

### Issue: External Service Circuit Breakers Open

**Symptoms:**
- Circuit breaker state shows "open"
- External API calls being rejected
- Fallback mechanisms activated

**Diagnosis:**
```bash
# Check circuit breaker status
curl http://localhost:8000/health/external-services | jq '.[] | select(.circuit_breaker.state == "open")'

# Test external service directly
curl -v https://api.service.com/health

# Check rate limit headers
curl -I https://api.service.com/endpoint
```

**Resolution:**
1. **Wait for Circuit Breaker Recovery**:
   - Circuit breakers automatically attempt recovery
   - Monitor for transition to "half-open" state
   - Verify service health before manual intervention

2. **Manual Circuit Breaker Reset** (if available):
   ```bash
   # Reset circuit breaker (implementation dependent)
   curl -X POST http://localhost:8000/admin/circuit-breakers/reset/{service_name}
   ```

3. **Service-Specific Actions**:
   - **NIH Reporter**: Check for maintenance windows
   - **Google Scholar**: Verify rate limiting compliance
   - **PubMed**: Check NCBI service status
   - **arXiv**: Verify API endpoint availability

### Issue: High Memory Usage

**Symptoms:**
- Memory usage approaching system limits
- Slow performance
- Potential OOM kills

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check for memory leaks
top -p $(pgrep -f uvicorn)

# Review memory metrics in Grafana
```

**Resolution:**
1. **Immediate Actions**:
   ```bash
   # Clear caches
   sync && echo 3 > /proc/sys/vm/drop_caches
   
   # Restart service to clear memory
   sudo systemctl restart research-api
   ```

2. **Long-term Solutions**:
   - Review data processing batch sizes
   - Implement pagination for large datasets
   - Optimize agent memory usage
   - Consider horizontal scaling

### Issue: Data Ingestion Stalled

**Symptoms:**
- No new funding opportunities or faculty profiles
- Ingestion agent metrics showing zero activity
- Stale data in dashboard

**Diagnosis:**
```bash
# Check ingestion agent logs
grep "ingestion_agent" logs/application.log | tail -20

# Verify external service availability
curl -I https://api.reporter.nih.gov/
curl -I https://eutils.ncbi.nlm.nih.gov/

# Check data files
ls -la data/raw/
ls -la data/processed/
```

**Resolution:**
1. **Service Connectivity**:
   ```bash
   # Test network connectivity
   ping api.reporter.nih.gov
   telnet api.reporter.nih.gov 443
   
   # Check DNS resolution
   nslookup api.reporter.nih.gov
   ```

2. **Configuration Validation**:
   ```bash
   # Validate scraping configuration
   python -c "
   import yaml
   with open('config/scraping_urls.yaml') as f:
       config = yaml.safe_load(f)
       print(config)
   "
   ```

3. **Manual Trigger**:
   ```bash
   # Manually trigger ingestion (if endpoint available)
   curl -X POST http://localhost:8000/admin/trigger-ingestion
   ```

## Emergency Procedures

### Complete Service Outage

1. **Immediate Response (0-5 minutes)**:
   ```bash
   # Check system status
   systemctl status research-api
   docker-compose ps
   
   # Check system resources
   uptime
   free -h
   df -h
   ```

2. **Service Recovery (5-15 minutes)**:
   ```bash
   # Attempt service restart
   systemctl restart research-api
   # OR
   docker-compose restart
   
   # Check health after restart
   curl http://localhost:8000/health
   ```

3. **Escalation (15+ minutes)**:
   - Contact on-call engineer
   - Create incident ticket
   - Document findings and actions taken

### Database/Storage Issues

1. **Check Storage Space**:
   ```bash
   df -h
   du -sh data/
   du -sh logs/
   ```

2. **Clean Up Space**:
   ```bash
   # Rotate logs
   logrotate -f /etc/logrotate.d/research-api
   
   # Clean old data files
   find data/raw/ -name "*.json" -mtime +7 -delete
   
   # Clean Docker images
   docker system prune -f
   ```

### Security Incident Response

1. **Suspected Attack**:
   ```bash
   # Check for unusual patterns
   grep -i "401\|403" logs/access.log | tail -50
   grep -i "unusual_traffic" logs/security.log
   
   # Block suspicious IPs (if identified)
   iptables -A INPUT -s SUSPICIOUS_IP -j DROP
   ```

2. **Data Breach Investigation**:
   - Preserve logs and system state
   - Contact security team immediately
   - Document all findings
   - Follow incident response procedures

## Maintenance Tasks

### Daily Tasks

1. **Health Check Review**:
   ```bash
   # Check all health endpoints
   curl http://localhost:8000/health
   curl http://localhost:8000/health/detailed
   curl http://localhost:8000/health/external-services
   ```

2. **Log Review**:
   ```bash
   # Check for errors
   grep -i error logs/application.log | tail -10
   
   # Check performance issues
   grep -i "slow_query\|high_memory" logs/performance.log
   ```

3. **Metrics Review**:
   - Review Grafana dashboards
   - Check for alert notifications
   - Verify metric collection is working

### Weekly Tasks

1. **System Updates**:
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Update Python packages
   pip list --outdated
   ```

2. **Data Cleanup**:
   ```bash
   # Archive old data
   tar -czf data/archive/data-$(date +%Y%m%d).tar.gz data/raw/*.json
   
   # Clean up old archives
   find data/archive/ -name "*.tar.gz" -mtime +30 -delete
   ```

3. **Performance Review**:
   - Analyze weekly performance trends
   - Review resource utilization
   - Plan capacity adjustments

### Monthly Tasks

1. **Security Updates**:
   ```bash
   # Update all dependencies
   pip install -r requirements.txt --upgrade
   
   # Security scan
   pip-audit
   ```

2. **Backup Verification**:
   ```bash
   # Test backup restoration
   # Verify backup integrity
   # Update backup procedures if needed
   ```

3. **Documentation Updates**:
   - Update runbook with new issues/solutions
   - Review and update configuration documentation
   - Update emergency contact information

## Escalation Procedures

### Level 1: Self-Service Resolution
- Use this runbook for common issues
- Check monitoring dashboards
- Review logs and metrics
- Attempt standard resolution procedures

### Level 2: Engineering Team
**Contact:** engineering-team@company.com
**When to escalate:**
- Issues not covered in runbook
- Multiple system failures
- Performance degradation > 1 hour
- External service issues affecting operations

### Level 3: On-Call Engineer
**Contact:** oncall@company.com
**When to escalate:**
- Complete system outage > 15 minutes
- Security incidents
- Data loss or corruption
- Critical business impact

### Level 4: Management
**Contact:** management@company.com
**When to escalate:**
- Extended outages (> 4 hours)
- Security breaches
- Regulatory compliance issues
- Major incident requiring external communication

## System Recovery

### Recovery Verification Checklist

After any incident or maintenance:

1. **Service Health**:
   - [ ] All health endpoints return 200 OK
   - [ ] API documentation accessible
   - [ ] Metrics collection working

2. **Functionality Testing**:
   - [ ] Basic API calls work
   - [ ] Agent execution functioning
   - [ ] External service integration working

3. **Monitoring**:
   - [ ] Grafana dashboards showing data
   - [ ] Alerts configured and working
   - [ ] Log collection functioning

4. **Performance**:
   - [ ] Response times within acceptable ranges
   - [ ] Resource usage normal
   - [ ] No memory leaks detected

### Rollback Procedures

If issues persist after attempted fixes:

1. **Application Rollback**:
   ```bash
   # Docker deployment
   docker-compose down
   docker-compose -f docker-compose.prev.yml up -d
   
   # Git-based deployment
   git checkout previous-stable-commit
   systemctl restart research-api
   ```

2. **Configuration Rollback**:
   ```bash
   # Restore previous configuration
   cp config/backup/config-$(date -d yesterday +%Y%m%d)/* config/
   systemctl restart research-api
   ```

3. **Data Rollback** (if necessary):
   ```bash
   # Restore from backup
   tar -xzf data/backup/data-$(date -d yesterday +%Y%m%d).tar.gz -C data/
   ```

## Performance Tuning

### Application-Level Optimizations

1. **Worker Process Tuning**:
   ```bash
   # Calculate optimal workers: (2 x CPU cores) + 1
   WORKERS=$(python -c "import multiprocessing; print(2 * multiprocessing.cpu_count() + 1)")
   uvicorn src.main:app --workers $WORKERS
   ```

2. **Memory Optimization**:
   - Implement pagination for large datasets
   - Use streaming for file processing
   - Optimize agent memory usage patterns

3. **External API Optimization**:
   - Implement request caching
   - Batch API calls where possible
   - Optimize circuit breaker thresholds

### System-Level Optimizations

1. **File System**:
   ```bash
   # Enable faster file system for logs
   mount -o noatime /dev/disk /logs
   
   # Use tmpfs for temporary data
   mount -t tmpfs tmpfs /tmp/processing
   ```

2. **Network Optimization**:
   ```bash
   # Increase connection limits
   echo 'net.core.somaxconn = 1024' >> /etc/sysctl.conf
   sysctl -p
   ```

3. **Resource Monitoring**:
   - Set up automated scaling triggers
   - Monitor resource trends
   - Plan capacity upgrades proactively

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Next Review**: February 2025

For questions or updates to this runbook, contact the engineering team.