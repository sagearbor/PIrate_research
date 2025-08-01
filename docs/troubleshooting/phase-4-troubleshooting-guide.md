# Phase 4 Troubleshooting Guide
## Dashboard, Analytics, Export System, and Configuration Management

**Document Version:** 1.0  
**Last Updated:** January 31, 2025  
**Maintained by:** Infrastructure Agent  

---

## Quick Reference

### Emergency Commands
```bash
# System health check
curl -s http://localhost:8000/dashboard/system-status

# Clear all caches
curl -X POST http://localhost:8000/dashboard/controls -H "Content-Type: application/json" -d '{"action": "clear_cache"}'

# Check critical metrics
curl -s "http://localhost:9090/api/v1/query?query=up{job=\"research-api\"}"
```

### Performance Targets
- **Dashboard Load Time:** < 2 seconds (target), < 5 seconds (critical)
- **Analytics Cache Hit Rate:** > 70% (target), > 50% (warning)
- **Export Processing:** < 10 seconds for 50+ items
- **Configuration Load:** < 50ms

---

## Dashboard Issues

### Issue: Dashboard Won't Load (HTTP 500/502)

**Symptoms:**
- Browser shows "Internal Server Error" or "Bad Gateway"
- Dashboard URL returns HTTP 500/502
- Dashboard metrics not updating

**Diagnosis:**
```bash
# Check application status
sudo systemctl status research-system

# Check application logs
tail -f /var/log/research-system/application.log

# Check if dashboard endpoints are accessible
curl -v http://localhost:8000/dashboard/metrics
```

**Resolution:**
1. **Check for Python/FastAPI errors:**
   ```bash
   tail -n 50 /var/log/research-system/application.log | grep -i error
   ```

2. **Restart the application:**
   ```bash
   sudo systemctl restart research-system
   sleep 10
   curl -f http://localhost:8000/dashboard/
   ```

3. **Check for dependency issues:**
   ```bash
   python3 -c "from src.dashboard.admin_dashboard import dashboard_router; print('Dashboard module OK')"
   ```

### Issue: Dashboard Loads Slowly (> 5 seconds)

**Symptoms:**
- Dashboard takes more than 5 seconds to load
- Browser shows loading state for extended time
- Users report poor performance

**Diagnosis:**
```bash
# Check dashboard load time metrics
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(dashboard_load_time_seconds_bucket[5m]))"

# Check system resources
htop
df -h

# Test dashboard response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/dashboard/
```

**Resolution:**
1. **Clear analytics cache:**
   ```bash
   curl -X POST http://localhost:8000/dashboard/controls \
     -H "Content-Type: application/json" \
     -d '{"action": "clear_cache"}'
   ```

2. **Check for resource constraints:**
   ```bash
   # Check CPU usage
   top -bn1 | head -10
   
   # Check memory usage
   free -h
   
   # Check disk I/O
   iostat -x 1 5
   ```

3. **Optimize analytics processing:**
   ```python
   # In analytics.py, temporarily reduce data processing
   # Consider implementing pagination for large datasets
   ```

### Issue: Dashboard Auto-Refresh Not Working

**Symptoms:**
- Dashboard data doesn't update automatically
- Timestamp shows old data
- Manual refresh works but auto-refresh doesn't

**Diagnosis:**
```bash
# Check auto-refresh metrics
curl -s "http://localhost:9090/api/v1/query?query=rate(dashboard_auto_refresh_total[5m])"

# Check browser console for JavaScript errors
# Check CORS headers
curl -I http://localhost:8000/dashboard/metrics
```

**Resolution:**
1. **Check JavaScript console in browser**
2. **Verify CORS configuration:**
   ```python
   # In main.py, ensure CORS is properly configured
   from fastapi.middleware.cors import CORSMiddleware
   ```
3. **Clear browser cache and cookies**
4. **Test with different browser**

### Issue: Dashboard Shows "No Data" or Empty Metrics

**Symptoms:**
- Dashboard loads but shows no data
- Metrics show zero values
- System appears healthy but no analytics data

**Diagnosis:**
```bash
# Check if processed data files exist
ls -la data/processed/

# Check analytics data freshness
curl -s "http://localhost:9090/api/v1/query?query=analytics_data_freshness_hours"

# Test analytics engine directly
python3 -c "
from src.core.analytics import get_system_metrics
import asyncio
data = asyncio.run(get_system_metrics())
print(f'Data available: {len(data)} keys')
"
```

**Resolution:**
1. **Trigger data ingestion:**
   ```bash
   curl -X POST http://localhost:8000/dashboard/controls \
     -H "Content-Type: application/json" \
     -d '{"action": "run_ingestion"}'
   ```

2. **Check data file permissions:**
   ```bash
   ls -la data/processed/
   chmod -R 644 data/processed/*.json
   ```

3. **Verify data format:**
   ```bash
   # Check if JSON files are valid
   python3 -m json.tool data/processed/faculty_funding_matches_*.json > /dev/null
   ```

---

## Analytics System Issues

### Issue: Low Analytics Cache Hit Rate (< 70%)

**Symptoms:**
- Prometheus shows cache hit rate below 70%
- Dashboard response times are slower
- High analytics processing load

**Diagnosis:**
```bash
# Check current cache hit rate
curl -s "http://localhost:9090/api/v1/query?query=rate(analytics_cache_hits_total[10m])/(rate(analytics_cache_hits_total[10m])+rate(analytics_cache_misses_total[10m]))*100"

# Check cache age patterns
curl -s "http://localhost:9090/api/v1/query?query=analytics_cache_age_seconds"

# Check cache configuration
grep -n "_cache_ttl_minutes" src/core/analytics.py
```

**Resolution:**
1. **Increase cache TTL if appropriate:**
   ```python
   # In analytics.py
   self._cache_ttl_minutes = 20  # Increase from 15 to 20 minutes
   ```

2. **Check for frequent cache invalidation:**
   ```bash
   # Monitor cache clearing frequency
   grep "cache cleared" /var/log/research-system/application.log
   ```

3. **Optimize cache usage patterns:**
   ```python
   # Implement intelligent cache warming
   # Reduce unnecessary cache clears
   ```

### Issue: Analytics Data is Stale (> 24 hours)

**Symptoms:**
- Grafana shows data freshness > 24 hours
- Dashboard shows old data
- Analytics metrics haven't updated recently

**Diagnosis:**
```bash
# Check data file timestamps
ls -lt data/processed/ | head -10

# Check ingestion agent status
curl -s "http://localhost:9090/api/v1/query?query=increase(funding_opportunities_scraped_total[24h])"

# Check for ingestion errors
tail -n 100 /var/log/research-system/ingestion.log | grep -i error
```

**Resolution:**
1. **Manually trigger data ingestion:**
   ```bash
   # Trigger ingestion via dashboard
   curl -X POST http://localhost:8000/dashboard/controls \
     -H "Content-Type: application/json" \
     -d '{"action": "run_ingestion"}'
   ```

2. **Check ingestion agent health:**
   ```bash
   python3 -c "
   from src.agents.ingestion_agent import IngestionAgent
   agent = IngestionAgent()
   print('Ingestion agent loaded successfully')
   "
   ```

3. **Verify external data sources:**
   ```bash
   # Test external API connectivity
   curl -f https://www.nih.nih.gov/ > /dev/null && echo "NIH accessible"
   curl -f https://www.pcori.org/ > /dev/null && echo "PCORI accessible"
   ```

### Issue: Analytics Processing Timeout (> 30 seconds)

**Symptoms:**
- Analytics processing takes more than 30 seconds
- Dashboard shows loading state for extended time
- Timeout errors in logs

**Diagnosis:**
```bash
# Check processing duration metrics
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(analytics_processing_duration_seconds_bucket[10m]))"

# Check data volume
find data/processed/ -name "*.json" -exec wc -l {} + | tail -1

# Check memory usage during processing
watch -n 1 'ps aux | grep analytics'
```

**Resolution:**
1. **Implement data pagination:**
   ```python
   # In analytics.py, process data in batches
   BATCH_SIZE = 1000  # Process 1000 items at a time
   ```

2. **Optimize data processing:**
   ```python
   # Use more efficient data structures
   # Implement parallel processing where possible
   ```

3. **Increase processing timeout:**
   ```python
   # Temporarily increase timeout
   PROCESSING_TIMEOUT = 60  # seconds
   ```

---

## Export System Issues

### Issue: Export Processing Fails (High Error Rate)

**Symptoms:**
- Export requests return HTTP 500 errors
- High error rate in export_requests_total metric
- Users can't download export files

**Diagnosis:**
```bash
# Check export error rate
curl -s "http://localhost:9090/api/v1/query?query=rate(export_requests_total{status=\"error\"}[10m])/rate(export_requests_total[10m])*100"

# Check export system logs
tail -n 100 /var/log/research-system/export.log | grep -i error

# Test export modules
python3 -c "
from src.tools.exporters.proposal_exporter import ProposalExporter
from src.tools.exporters.collaboration_exporter import CollaborationExporter
print('Export modules loaded successfully')
"
```

**Resolution:**
1. **Check disk space:**
   ```bash
   df -h /data/exports/
   # Clean old files if needed
   find /data/exports/ -mtime +3 -delete
   ```

2. **Verify export directory permissions:**
   ```bash
   ls -la /data/exports/
   chmod 755 /data/exports/
   ```

3. **Test individual export formats:**
   ```python
   # Test each export format separately
   from src.tools.exporters.proposal_exporter import ProposalExporter
   exporter = ProposalExporter()
   # Test with small dataset first
   ```

### Issue: Export Processing Timeout (> 30 seconds)

**Symptoms:**
- Export operations take more than 30 seconds
- Users report slow export downloads
- Export processing duration metrics are high

**Diagnosis:**
```bash
# Check export processing time
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(export_processing_duration_seconds_bucket[10m]))"

# Check data volume being exported
curl -s "http://localhost:9090/api/v1/query?query=rate(export_items_processed_total[10m])"

# Monitor resource usage during export
htop
```

**Resolution:**
1. **Implement batch processing:**
   ```python
   # In export modules, process in smaller batches
   EXPORT_BATCH_SIZE = 50  # Reduce from larger batch size
   ```

2. **Optimize export templates:**
   ```python
   # Simplify complex templates
   # Cache template compilation
   ```

3. **Implement asynchronous exports:**
   ```python
   # For large exports, implement async processing
   # Provide download links when ready
   ```

### Issue: Export Files Too Large (> 100MB)

**Symptoms:**
- Export file size metrics show files > 100MB
- Download timeouts for users
- Disk space issues

**Diagnosis:**
```bash
# Check export file sizes
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(export_file_size_bytes_bucket[10m]))"

# Check largest export files
find /data/exports/ -size +100M -ls

# Identify problematic export types
ls -lh /data/exports/ | head -20
```

**Resolution:**
1. **Implement export filtering:**
   ```python
   # Add data filtering options
   # Limit number of items per export
   MAX_EXPORT_ITEMS = 1000
   ```

2. **Implement compression:**
   ```python
   # Compress large exports
   import gzip
   # Implement gzip compression for large files
   ```

3. **Provide pagination:**
   ```python
   # Split large exports into multiple files
   # Implement pagination for downloads
   ```

---

## Configuration Management Issues

### Issue: Configuration Load Failures

**Symptoms:**
- Configuration load operations show high error rate
- Application can't load institution configs
- Validation errors in logs

**Diagnosis:**
```bash
# Check config load error rate
curl -s "http://localhost:9090/api/v1/query?query=rate(config_load_operations_total{status=\"error\"}[10m])"

# Check validation errors
curl -s "http://localhost:9090/api/v1/query?query=rate(config_validation_errors_total[10m])"

# Test configuration loading
python3 -c "
from src.core.config_manager import ConfigManager
manager = ConfigManager()
try:
    config = manager.get_institution_config('default')
    print(f'Config loaded: {len(config)} keys')
except Exception as e:
    print(f'Config load failed: {e}')
"
```

**Resolution:**
1. **Validate YAML syntax:**
   ```bash
   python3 -c "
   import yaml
   with open('config/institution_templates/default.yaml', 'r') as f:
       try:
           yaml.safe_load(f)
           print('YAML syntax: Valid')
       except yaml.YAMLError as e:
           print(f'YAML syntax error: {e}')
   "
   ```

2. **Check file permissions:**
   ```bash
   ls -la config/institution_templates/
   chmod 644 config/institution_templates/*.yaml
   ```

3. **Restore from backup:**
   ```bash
   # Restore from latest backup
   cp config/institution_templates/default.yaml.backup.* config/institution_templates/default.yaml
   ```

### Issue: Configuration Load Slow (> 50ms)

**Symptoms:**
- Configuration load duration > 50ms
- Application startup is slow
- Configuration-dependent operations are slow

**Diagnosis:**
```bash
# Check config load time
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(config_load_duration_seconds_bucket[10m]))"

# Check config file sizes
ls -lh config/institution_templates/

# Check config cache age
curl -s "http://localhost:9090/api/v1/query?query=config_cache_age_seconds"
```

**Resolution:**
1. **Optimize configuration files:**
   ```bash
   # Remove unnecessary comments and whitespace
   # Split large configurations into smaller files
   ```

2. **Implement better caching:**
   ```python
   # In config_manager.py, implement persistent caching
   # Increase cache duration for stable configs
   ```

3. **Preload frequently used configs:**
   ```python
   # Implement config preloading during startup
   # Cache most commonly used configurations
   ```

---

## Performance Optimization

### System-Wide Performance Issues

**Symptoms:**
- All Phase 4 components are slow
- High system resource usage
- Multiple performance alerts firing

**Diagnosis:**
```bash
# Check overall system performance
htop
iostat -x 1 5
df -h

# Check application resource usage
ps aux | grep python | head -20

# Check for memory leaks
cat /proc/meminfo | grep -E "(MemTotal|MemFree|MemAvailable)"
```

**Resolution:**
1. **Scale resources:**
   ```bash
   # Increase system resources if possible
   # Consider horizontal scaling
   ```

2. **Optimize application:**
   ```python
   # Implement connection pooling
   # Optimize database queries
   # Add more caching layers
   ```

3. **Load balancing:**
   ```bash
   # Implement load balancing for high traffic
   # Use CDN for static assets
   ```

---

## Emergency Recovery Procedures

### Complete Phase 4 System Failure

**Symptoms:**
- All Phase 4 components are down
- Dashboard completely inaccessible
- All metrics show system failure

**Emergency Recovery:**
1. **Stop all services:**
   ```bash
   sudo systemctl stop research-system
   ```

2. **Clear all caches and temporary files:**
   ```bash
   rm -rf /tmp/research-system-*
   find /data/cache/ -type f -delete
   ```

3. **Restore from backup:**
   ```bash
   # Restore configurations
   cp -r /backup/config/ ./config/
   
   # Restore critical data
   cp -r /backup/data/processed/ ./data/processed/
   ```

4. **Start services:**
   ```bash
   sudo systemctl start research-system
   sleep 30
   curl -f http://localhost:8000/dashboard/
   ```

5. **Verify recovery:**
   ```bash
   # Check all endpoints
   curl -f http://localhost:8000/dashboard/system-status
   curl -f http://localhost:8000/metrics
   ```

---

## Prevention and Monitoring

### Proactive Monitoring Setup

1. **Set up comprehensive alerting:**
   ```yaml
   # In alertmanager.yml
   route:
     group_by: ['alertname', 'service']
     group_wait: 10s
     group_interval: 10s
     repeat_interval: 1h
     receiver: 'phase-4-alerts'
   ```

2. **Implement health checks:**
   ```bash
   # Add to crontab for regular health checks
   */5 * * * * curl -f http://localhost:8000/dashboard/system-status || echo "Dashboard health check failed" | mail -s "Alert" admin@example.com
   ```

3. **Regular maintenance:**
   ```bash
   # Weekly maintenance script
   #!/bin/bash
   # Clean old export files
   find /data/exports/ -mtime +7 -delete
   # Validate configurations
   python3 scripts/validate_configs.py
   # Generate performance report
   python3 scripts/performance_report.py
   ```

---

## Contact Information

**Primary Support:** Infrastructure Team  
**Escalation:** DevOps Team  
**Emergency:** On-call Engineer (24/7)  

**Documentation maintained by:** Infrastructure Agent  
**Last updated:** January 31, 2025  
**Next review:** February 28, 2025  

---

*This troubleshooting guide should be kept current with system changes and updated based on actual operational experience.*