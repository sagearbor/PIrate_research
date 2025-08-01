# Phase 4 Operations Runbook
## Dashboard, Analytics, Export System, and Configuration Management

**Document Version:** 1.0  
**Last Updated:** January 31, 2025  
**Maintained by:** Infrastructure Agent  

---

## Table of Contents

1. [Overview](#overview)
2. [Dashboard Operations](#dashboard-operations)
3. [Analytics System Operations](#analytics-system-operations)
4. [Export System Operations](#export-system-operations)
5. [Configuration Management Operations](#configuration-management-operations)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Emergency Procedures](#emergency-procedures)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Performance Tuning](#performance-tuning)

---

## Overview

This runbook covers operational procedures for Phase 4 components of the Faculty Research Opportunity Notifier system, including:

- **Admin Dashboard:** Real-time system monitoring and management interface
- **Analytics Engine:** Data processing and effectiveness tracking with 15-minute caching
- **Export System:** Multi-format proposal and collaboration export capabilities
- **Configuration Management:** Institutional template and settings management

### Key Performance Targets
- Dashboard load time: < 2 seconds (95th percentile)
- Analytics cache hit rate: > 70%
- Export processing: < 10 seconds for 50+ items
- Configuration loading: < 50ms

---

## Dashboard Operations

### Normal Operations

#### Starting the Dashboard
```bash
# Dashboard is integrated with main FastAPI application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Verify dashboard is accessible
curl -f http://localhost:8000/dashboard/
```

#### Dashboard Health Check
```bash
# Check dashboard system status
curl -s http://localhost:8000/dashboard/system-status

# Expected response:
# {"status": "healthy", "health": {...}, "timestamp": "..."}
```

#### Dashboard Metrics Verification
```bash
# Verify metrics endpoint
curl -s http://localhost:8000/dashboard/metrics

# Check Prometheus metrics
curl -s http://localhost:9090/api/v1/query?query=dashboard_page_views_total
```

### Common Operations

#### Clear Dashboard Cache
```bash
# Via API
curl -X POST http://localhost:8000/dashboard/controls \
  -H "Content-Type: application/json" \
  -d '{"action": "clear_cache"}'

# Via dashboard UI: Click "Clear Cache" button
```

#### Trigger Data Refresh
```bash
# Via API
curl -X POST http://localhost:8000/dashboard/controls \
  -H "Content-Type: application/json" \
  -d '{"action": "refresh_metrics"}'
```

#### Export Dashboard Data
```bash
# Get exportable dashboard data
curl -s http://localhost:8000/dashboard/export > dashboard_export_$(date +%Y%m%d_%H%M%S).json
```

---

## Analytics System Operations

### Normal Operations

#### Analytics Cache Management
```bash
# Check cache status
python3 -c "
from src.core.analytics import analytics_engine
print(f'Cache valid: {analytics_engine._is_cache_valid()}')
print(f'Cache age: {analytics_engine._cache_timestamp}')
"

# Clear analytics cache
python3 -c "
from src.core.analytics import clear_analytics_cache
clear_analytics_cache()
print('Analytics cache cleared')
"
```

#### Data Freshness Check
```bash
# Check data freshness via metrics
curl -s http://localhost:9090/api/v1/query?query=analytics_data_freshness_hours

# Manual data freshness check
python3 -c "
from src.core.analytics import get_system_health
import asyncio
health = asyncio.run(get_system_health())
print(f'Data freshness: {health.get(\"data_freshness_hours\", \"unknown\")} hours')
"
```

### Performance Monitoring

#### Cache Performance Metrics
```bash
# Check cache hit rate
curl -s "http://localhost:9090/api/v1/query?query=rate(analytics_cache_hits_total[10m])/(rate(analytics_cache_hits_total[10m])+rate(analytics_cache_misses_total[10m]))*100"

# Monitor cache age
curl -s "http://localhost:9090/api/v1/query?query=analytics_cache_age_seconds"
```

#### Processing Performance
```bash
# Check processing duration
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(analytics_processing_duration_seconds_bucket[10m]))"
```

---

## Export System Operations

### Normal Operations

#### Export System Health Check
```bash
# Check export system metrics
curl -s "http://localhost:9090/api/v1/query?query=rate(export_requests_total[5m])"

# Test export functionality
python3 -c "
from src.tools.exporters.proposal_exporter import ProposalExporter
from src.tools.exporters.collaboration_exporter import CollaborationExporter
print('Export system modules loaded successfully')
"
```

#### Manual Export Operations
```bash
# Example: Export proposals in JSON format
python3 -c "
from src.tools.exporters.proposal_exporter import ProposalExporter
exporter = ProposalExporter()
# Add export logic here based on your data
print('Manual export completed')
"
```

### Performance Monitoring

#### Export Performance Metrics
```bash
# Check export success rate
curl -s "http://localhost:9090/api/v1/query?query=rate(export_requests_total{status=\"success\"}[10m])/rate(export_requests_total[10m])*100"

# Monitor processing time
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(export_processing_duration_seconds_bucket[10m]))"

# Check file sizes
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(export_file_size_bytes_bucket[10m]))"
```

#### Disk Space Management
```bash
# Check export directory disk usage
df -h /data/exports/

# Clean old export files (if needed)
find /data/exports/ -name "*.json" -mtime +7 -delete
find /data/exports/ -name "*.csv" -mtime +7 -delete
```

---

## Configuration Management Operations

### Normal Operations

#### Configuration Health Check
```bash
# Check configuration load operations
curl -s "http://localhost:9090/api/v1/query?query=rate(config_load_operations_total[5m])"

# Test configuration loading
python3 -c "
from src.core.config_manager import ConfigManager
manager = ConfigManager()
config = manager.get_institution_config('default')
print(f'Configuration loaded: {len(config)} keys')
"
```

#### Configuration Validation
```bash
# Validate all institution configs
python3 -c "
from src.core.config_manager import ConfigManager
import glob

manager = ConfigManager()
config_files = glob.glob('config/institution_templates/*.yaml')
for config_file in config_files:
    try:
        config = manager.load_config(config_file)
        print(f'✓ {config_file}: Valid')
    except Exception as e:
        print(f'✗ {config_file}: {e}')
"
```

### Configuration Updates

#### Safe Configuration Updates
```bash
# 1. Backup current configuration
cp config/institution_templates/default.yaml config/institution_templates/default.yaml.backup.$(date +%Y%m%d_%H%M%S)

# 2. Validate new configuration
python3 -c "
from src.core.config_manager import ConfigManager
manager = ConfigManager()
try:
    config = manager.load_config('config/institution_templates/default.yaml')
    print('Configuration validation: PASSED')
except Exception as e:
    print(f'Configuration validation: FAILED - {e}')
    exit(1)
"

# 3. Clear configuration cache after update
python3 -c "
from src.core.config_manager import ConfigManager
manager = ConfigManager()
manager.clear_cache()
print('Configuration cache cleared')
"
```

---

## Monitoring and Alerting

### Key Metrics to Monitor

#### Dashboard Metrics
- `dashboard_load_time_seconds`: Dashboard page load performance
- `dashboard_page_views_total`: Dashboard usage tracking
- `dashboard_auto_refresh_total`: Auto-refresh functionality

#### Analytics Metrics
- `analytics_cache_hits_total` / `analytics_cache_misses_total`: Cache performance
- `analytics_data_freshness_hours`: Data staleness
- `analytics_processing_duration_seconds`: Processing performance

#### Export Metrics
- `export_requests_total`: Export system usage and success rate
- `export_processing_duration_seconds`: Export performance
- `export_file_size_bytes`: Generated file sizes

#### Configuration Metrics
- `config_load_operations_total`: Configuration loading
- `config_validation_errors_total`: Configuration errors
- `config_load_duration_seconds`: Configuration performance

### Alert Response Procedures

#### Dashboard Load Time Alert
```bash
# 1. Check dashboard response
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/dashboard/

# 2. Check system resources
top -bn1 | head -20

# 3. Check for blocking operations
ps aux | grep python | grep -v grep

# 4. Restart if necessary
sudo systemctl restart research-system
```

#### Analytics Cache Performance Alert
```bash
# 1. Check cache statistics
curl -s "http://localhost:9090/api/v1/query?query=analytics_cache_age_seconds"

# 2. Clear cache if stale
python3 -c "
from src.core.analytics import clear_analytics_cache
clear_analytics_cache()
print('Cache cleared')
"

# 3. Verify data freshness
curl -s "http://localhost:9090/api/v1/query?query=analytics_data_freshness_hours"
```

#### Export System Failure Alert
```bash
# 1. Check export system logs
tail -n 100 /var/log/research-system/export.log

# 2. Check disk space
df -h /data/exports/

# 3. Test export functionality
python3 -c "
from src.tools.exporters.proposal_exporter import ProposalExporter
exporter = ProposalExporter()
print('Export system test completed')
"

# 4. Clear old files if disk space is low
find /data/exports/ -mtime +3 -delete
```

---

## Troubleshooting Guide

### Dashboard Issues

#### Dashboard Not Loading (Load Time > 5 seconds)
1. **Check system resources:**
   ```bash
   htop
   df -h
   ```

2. **Check for database locks:**
   ```bash
   python3 -c "
   from src.core.analytics import analytics_engine
   print('Analytics engine status check')
   "
   ```

3. **Restart dashboard service:**
   ```bash
   sudo systemctl restart research-system
   ```

#### Dashboard Auto-Refresh Not Working
1. **Check browser console for JavaScript errors**
2. **Verify metrics endpoint:**
   ```bash
   curl -f http://localhost:8000/dashboard/metrics
   ```
3. **Check for CORS issues in logs**

### Analytics System Issues

#### Low Cache Hit Rate (< 70%)
1. **Check cache TTL configuration:**
   ```bash
   grep -n "_cache_ttl_minutes" src/core/analytics.py
   ```
2. **Monitor cache age patterns:**
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=analytics_cache_age_seconds[1h]"
   ```
3. **Consider increasing cache TTL if appropriate**

#### Stale Analytics Data (> 24 hours)
1. **Check data ingestion status:**
   ```bash
   ls -la data/processed/
   ```
2. **Trigger manual data ingestion:**
   ```bash
   python3 -c "
   # Add manual ingestion trigger here
   print('Manual ingestion triggered')
   "
   ```
3. **Check ingestion agent logs for errors**

### Export System Issues

#### Export Processing Timeout (> 30 seconds)
1. **Check available disk space:**
   ```bash
   df -h /data/exports/
   ```
2. **Monitor memory usage during export:**
   ```bash
   watch -n 1 'ps aux | grep export'
   ```
3. **Check for large data sets:**
   ```bash
   find data/processed/ -name "*.json" -size +10M
   ```

#### Export File Size Too Large (> 100MB)
1. **Identify problematic export types:**
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=export_file_size_bytes"
   ```
2. **Implement pagination or filtering**
3. **Consider data archiving strategies**

### Configuration Management Issues

#### Configuration Load Failures
1. **Validate YAML syntax:**
   ```bash
   python3 -c "
   import yaml
   with open('config/institution_templates/default.yaml', 'r') as f:
       yaml.safe_load(f)
   print('YAML syntax: Valid')
   "
   ```
2. **Check file permissions:**
   ```bash
   ls -la config/institution_templates/
   ```
3. **Verify schema compliance:**
   ```bash
   python3 -c "
   from src.core.config_manager import ConfigManager
   manager = ConfigManager()
   config = manager.load_config('config/institution_templates/default.yaml')
   print('Schema validation: Passed')
   "
   ```

---

## Emergency Procedures

### Dashboard Completely Unavailable
1. **Check main application status:**
   ```bash
   sudo systemctl status research-system
   ```
2. **Check for port conflicts:**
   ```bash
   netstat -tulpn | grep :8000
   ```
3. **Emergency restart:**
   ```bash
   sudo systemctl stop research-system
   sleep 5
   sudo systemctl start research-system
   ```
4. **Verify dashboard recovery:**
   ```bash
   curl -f http://localhost:8000/dashboard/
   ```

### Complete Analytics System Failure
1. **Clear all caches:**
   ```bash
   python3 -c "
   from src.core.analytics import clear_analytics_cache
   clear_analytics_cache()
   "
   ```
2. **Restart analytics processes:**
   ```bash
   sudo systemctl restart research-system
   ```
3. **Verify data integrity:**
   ```bash
   find data/processed/ -name "*.json" -exec python3 -m json.tool {} \; > /dev/null
   ```

### Export System Complete Failure
1. **Check and clear export directory:**
   ```bash
   ls -la /data/exports/
   find /data/exports/ -mtime +1 -delete
   ```
2. **Verify export modules:**
   ```bash
   python3 -c "
   from src.tools.exporters import proposal_exporter, collaboration_exporter
   print('Export modules loaded successfully')
   "
   ```
3. **Restart with clean state:**
   ```bash
   sudo systemctl restart research-system
   ```

---

## Maintenance Procedures

### Daily Maintenance
1. **Check system health:**
   ```bash
   curl -s http://localhost:8000/dashboard/system-status
   ```
2. **Verify alert status:**
   ```bash
   curl -s http://localhost:9093/api/v1/alerts
   ```
3. **Monitor disk usage:**
   ```bash
   df -h | grep -E "(data|logs|exports)"
   ```

### Weekly Maintenance
1. **Clear old export files:**
   ```bash
   find /data/exports/ -mtime +7 -delete
   ```
2. **Validate all configurations:**
   ```bash
   python3 scripts/validate_all_configs.py  # Create this script
   ```
3. **Review performance metrics:**
   ```bash
   # Generate weekly performance report
   python3 scripts/generate_performance_report.py  # Create this script
   ```

### Monthly Maintenance
1. **Performance optimization review**
2. **Configuration template updates**
3. **Security audit of dashboard access logs**
4. **Capacity planning review**

---

## Performance Tuning

### Dashboard Performance Optimization
1. **Adjust auto-refresh interval based on usage:**
   - High usage: 60 seconds
   - Normal usage: 30 seconds
   - Low usage: 15 seconds

2. **Optimize analytics cache TTL:**
   - Development: 5 minutes
   - Production: 15 minutes
   - High-load: 30 minutes

### Analytics System Tuning
1. **Cache size optimization:**
   ```python
   # In analytics.py, adjust cache size based on memory
   self._max_cache_entries = 1000  # Adjust based on available RAM
   ```

2. **Processing timeout optimization:**
   ```python
   # Adjust processing timeouts based on data volume
   self._processing_timeout = 60  # seconds
   ```

### Export System Tuning
1. **Batch size optimization:**
   ```python
   # In export modules, adjust batch sizes
   BATCH_SIZE = 50  # Adjust based on memory and performance
   ```

2. **File format priorities:**
   ```python
   # Prioritize formats based on usage
   PRIORITY_FORMATS = ['json', 'csv', 'html']  # Most to least used
   ```

---

## Contact Information

**Primary Contact:** Infrastructure Team  
**Escalation:** DevOps Team  
**Emergency Contact:** On-call Engineer  

**Documentation maintained by:** Infrastructure Agent  
**Last reviewed:** January 31, 2025  
**Next review:** February 28, 2025  

---

*This runbook should be updated whenever Phase 4 components are modified or new operational procedures are established.*