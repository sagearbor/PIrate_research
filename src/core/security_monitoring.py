"""
Security monitoring and audit logging for the multi-agent research system.

This module provides comprehensive security monitoring including:
- Authentication and authorization logging
- Suspicious activity detection
- Rate limiting enforcement
- Security event correlation
- Audit trail maintenance
"""

import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import ipaddress
import re

from src.core.logging_config import security_logger, get_correlation_id
from src.core.metrics import external_api_rate_limit_hits_total

# ============================================================================
# Security Event Types and Models
# ============================================================================

class SecurityEventType(Enum):
    """Types of security events"""
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_FAILURE = "authz_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_ABUSE = "api_abuse"
    DATA_ACCESS = "data_access"
    ADMIN_ACTION = "admin_action"
    EXTERNAL_API_ERROR = "external_api_error"
    UNUSUAL_TRAFFIC_PATTERN = "unusual_traffic"
    POTENTIAL_ATTACK = "potential_attack"

class SecurityLevel(Enum):
    """Security alert levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: SecurityEventType
    level: SecurityLevel
    timestamp: datetime
    source_ip: str
    user_agent: str
    endpoint: str
    method: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0

@dataclass
class TrafficPattern:
    """Traffic pattern analysis"""
    ip_address: str
    request_count: int = 0
    unique_endpoints: Set[str] = field(default_factory=set)
    unique_user_agents: Set[str] = field(default_factory=set)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    average_response_time: float = 0.0
    suspicious_score: float = 0.0

# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter with security monitoring"""
    
    def __init__(self, max_requests: int, window_seconds: int, burst_limit: int = None):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests * 2
        
        # Track requests per IP
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
        self.warning_ips: Set[str] = set()
    
    async def is_allowed(self, ip_address: str, endpoint: str = None) -> bool:
        """
        Check if request is allowed under rate limiting rules.
        
        Args:
            ip_address: Client IP address
            endpoint: Optional endpoint for endpoint-specific limiting
            
        Returns:
            bool: True if request is allowed
        """
        current_time = time.time()
        
        # Check if IP is currently blocked
        if ip_address in self.blocked_ips:
            block_time = self.blocked_ips[ip_address]
            if datetime.now() - block_time < timedelta(minutes=15):
                return False
            else:
                # Unblock IP after timeout
                del self.blocked_ips[ip_address]
                self.warning_ips.discard(ip_address)
        
        # Clean old requests
        request_times = self.request_counts[ip_address]
        while request_times and current_time - request_times[0] > self.window_seconds:
            request_times.popleft()
        
        # Check rate limit
        if len(request_times) >= self.max_requests:
            # Log rate limit violation
            security_logger.log_rate_limit_hit(
                endpoint=endpoint or "unknown",
                ip_address=ip_address,
                request_count=len(request_times),
                window_seconds=self.window_seconds
            )
            
            # Block IP if exceeding burst limit
            if len(request_times) >= self.burst_limit:
                self.blocked_ips[ip_address] = datetime.now()
                
                security_logger.logger.warning(
                    f"IP blocked for exceeding burst limit",
                    event_type="ip_blocked",
                    ip_address=ip_address,
                    request_count=len(request_times),
                    burst_limit=self.burst_limit
                )
            
            return False
        
        # Add current request
        request_times.append(current_time)
        
        # Warn if approaching limit
        if len(request_times) > self.max_requests * 0.8 and ip_address not in self.warning_ips:
            self.warning_ips.add(ip_address)
            security_logger.logger.info(
                f"IP approaching rate limit",
                event_type="rate_limit_warning",
                ip_address=ip_address,
                request_count=len(request_times),
                limit=self.max_requests
            )
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "active_ips": len(self.request_counts),
            "blocked_ips": len(self.blocked_ips),
            "warning_ips": len(self.warning_ips),
            "total_requests": sum(len(requests) for requests in self.request_counts.values())
        }

# ============================================================================
# Security Monitor
# ============================================================================

class SecurityMonitor:
    """Main security monitoring and analysis engine"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self.events: deque = deque(maxlen=10000)  # Store recent security events
        self.traffic_patterns: Dict[str, TrafficPattern] = {}
        self.suspicious_ips: Set[str] = set()
        self.threat_intelligence: Dict[str, Any] = {}
        
        # Pattern detection settings
        self.max_pattern_age = timedelta(hours=1)
        self.suspicious_thresholds = {
            "unique_endpoints_per_minute": 20,
            "requests_per_minute": 300,
            "error_rate_threshold": 0.5,
            "unique_user_agents": 10
        }
    
    async def log_request(
        self,
        ip_address: str,
        method: str,
        endpoint: str,
        status_code: int,
        user_agent: str,
        response_time: float,
        correlation_id: str = None
    ):
        """
        Log and analyze an incoming request for security purposes.
        
        Args:
            ip_address: Client IP address
            method: HTTP method
            endpoint: Request endpoint
            status_code: Response status code
            user_agent: User agent string
            response_time: Request processing time
            correlation_id: Request correlation ID
        """
        current_time = datetime.now()
        
        # Update traffic pattern
        pattern = await self._update_traffic_pattern(
            ip_address, endpoint, user_agent, status_code, response_time, current_time
        )
        
        # Analyze for suspicious activity
        risk_score = await self._calculate_risk_score(pattern, method, endpoint, status_code)
        
        # Check for security violations
        await self._check_security_violations(
            ip_address, method, endpoint, status_code, user_agent, risk_score, correlation_id
        )
        
        # Rate limiting check
        if not await self.rate_limiter.is_allowed(ip_address, endpoint):
            await self._log_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityLevel.MEDIUM,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"status_code": status_code, "risk_score": risk_score}
            )
    
    async def _update_traffic_pattern(
        self,
        ip_address: str,
        endpoint: str,
        user_agent: str,
        status_code: int,
        response_time: float,
        timestamp: datetime
    ) -> TrafficPattern:
        """Update traffic pattern for an IP address"""
        
        if ip_address not in self.traffic_patterns:
            self.traffic_patterns[ip_address] = TrafficPattern(ip_address=ip_address)
        
        pattern = self.traffic_patterns[ip_address]
        pattern.request_count += 1
        pattern.unique_endpoints.add(endpoint)
        pattern.unique_user_agents.add(user_agent)
        pattern.last_seen = timestamp
        pattern.status_codes[status_code] += 1
        
        # Update average response time
        pattern.average_response_time = (
            (pattern.average_response_time * (pattern.request_count - 1) + response_time) 
            / pattern.request_count
        )
        
        return pattern
    
    async def _calculate_risk_score(
        self,
        pattern: TrafficPattern,
        method: str,
        endpoint: str,
        status_code: int
    ) -> float:
        """Calculate risk score for a request pattern"""
        
        risk_score = 0.0
        
        # High request volume
        time_window = (datetime.now() - pattern.first_seen).total_seconds() / 60  # minutes
        if time_window > 0:
            requests_per_minute = pattern.request_count / time_window
            if requests_per_minute > self.suspicious_thresholds["requests_per_minute"]:
                risk_score += 30.0
            elif requests_per_minute > 50:
                risk_score += 10.0
        
        # Many unique endpoints (potential scanning)
        if len(pattern.unique_endpoints) > self.suspicious_thresholds["unique_endpoints_per_minute"]:
            risk_score += 25.0
        
        # Multiple user agents (potential bot)
        if len(pattern.unique_user_agents) > self.suspicious_thresholds["unique_user_agents"]:
            risk_score += 15.0
        
        # High error rate
        total_requests = sum(pattern.status_codes.values())
        error_requests = sum(count for status, count in pattern.status_codes.items() if status >= 400)
        if total_requests > 0:
            error_rate = error_requests / total_requests
            if error_rate > self.suspicious_thresholds["error_rate_threshold"]:
                risk_score += 20.0
        
        # Suspicious endpoints
        suspicious_patterns = [
            r'/admin', r'/wp-admin', r'\.php$', r'\.asp$', r'/api/v\d+/.*',
            r'/health.*', r'/metrics.*', r'/docs.*'
        ]
        for suspicious_pattern in suspicious_patterns:
            if re.search(suspicious_pattern, endpoint, re.IGNORECASE):
                risk_score += 10.0
                break
        
        # SQL injection patterns
        sql_patterns = [
            r"'.*or.*'", r"union.*select", r"drop.*table", r"insert.*into",
            r"delete.*from", r"update.*set"
        ]
        for sql_pattern in sql_patterns:
            if re.search(sql_pattern, endpoint, re.IGNORECASE):
                risk_score += 40.0
                break
        
        # XSS patterns
        xss_patterns = [r"<script", r"javascript:", r"onerror=", r"onload="]
        for xss_pattern in xss_patterns:
            if re.search(xss_pattern, endpoint, re.IGNORECASE):
                risk_score += 35.0
                break
        
        # Update pattern suspicious score
        pattern.suspicious_score = max(pattern.suspicious_score, risk_score)
        
        return risk_score
    
    async def _check_security_violations(
        self,
        ip_address: str,
        method: str,
        endpoint: str,
        status_code: int,
        user_agent: str,
        risk_score: float,
        correlation_id: str = None
    ):
        """Check for various security violations"""
        
        # High risk score
        if risk_score >= 50.0:
            await self._log_security_event(
                SecurityEventType.POTENTIAL_ATTACK,
                SecurityLevel.HIGH,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"risk_score": risk_score, "status_code": status_code}
            )
            self.suspicious_ips.add(ip_address)
        
        elif risk_score >= 25.0:
            await self._log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecurityLevel.MEDIUM,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"risk_score": risk_score, "status_code": status_code}
            )
        
        # Authentication failures
        if status_code == 401:
            await self._log_security_event(
                SecurityEventType.AUTHENTICATION_FAILURE,
                SecurityLevel.LOW,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"status_code": status_code}
            )
        
        # Authorization failures
        if status_code == 403:
            await self._log_security_event(
                SecurityEventType.AUTHORIZATION_FAILURE,
                SecurityLevel.MEDIUM,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"status_code": status_code}
            )
        
        # Check for known bad IPs
        if await self._is_known_malicious_ip(ip_address):
            await self._log_security_event(
                SecurityEventType.POTENTIAL_ATTACK,
                SecurityLevel.CRITICAL,
                ip_address,
                user_agent,
                endpoint,
                method,
                correlation_id,
                details={"threat_intelligence": "known_malicious_ip"}
            )
    
    async def _log_security_event(
        self,
        event_type: SecurityEventType,
        level: SecurityLevel,
        source_ip: str,
        user_agent: str,
        endpoint: str,
        method: str,
        correlation_id: str = None,
        user_id: str = None,
        details: Dict[str, Any] = None
    ):
        """Log a security event"""
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            timestamp=datetime.now(),
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            correlation_id=correlation_id,
            user_id=user_id,
            details=details or {},
            risk_score=details.get("risk_score", 0.0) if details else 0.0
        )
        
        self.events.append(event)
        
        # Log to structured logging system
        security_logger.logger.warning(
            f"Security event: {event_type.value}",
            event_type=event_type.value,
            security_level=level.value,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            correlation_id=correlation_id,
            user_id=user_id,
            risk_score=event.risk_score,
            **event.details
        )
    
    async def _is_known_malicious_ip(self, ip_address: str) -> bool:
        """Check if IP is in threat intelligence database"""
        # This would integrate with threat intelligence feeds in production
        # For now, check against basic patterns
        
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            
            # Check for private/internal IPs (generally safe)
            if ip_obj.is_private or ip_obj.is_loopback:
                return False
            
            # Check known malicious ranges (example)
            malicious_ranges = [
                "10.0.0.0/8",    # This would be real threat intelligence
                "192.168.0.0/16" # in production
            ]
            
            for malicious_range in malicious_ranges:
                if ip_obj in ipaddress.ip_network(malicious_range):
                    return True
                    
        except ValueError:
            # Invalid IP address
            return True
        
        return False
    
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary"""
        current_time = datetime.now()
        recent_events = [e for e in self.events if current_time - e.timestamp < timedelta(hours=24)]
        
        # Count events by type and level
        event_counts = defaultdict(int)
        level_counts = defaultdict(int)
        
        for event in recent_events:
            event_counts[event.event_type.value] += 1
            level_counts[event.level.value] += 1
        
        # Top suspicious IPs
        ip_risk_scores = {}
        for ip, pattern in self.traffic_patterns.items():
            if current_time - pattern.last_seen < timedelta(hours=1):
                ip_risk_scores[ip] = pattern.suspicious_score
        
        top_suspicious_ips = sorted(
            ip_risk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "summary": {
                "total_events_24h": len(recent_events),
                "high_risk_events": len([e for e in recent_events if e.level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]]),
                "suspicious_ips": len(self.suspicious_ips),
                "blocked_ips": len(self.rate_limiter.blocked_ips),
                "active_patterns": len([p for p in self.traffic_patterns.values() if current_time - p.last_seen < timedelta(hours=1)])
            },
            "event_types": dict(event_counts),
            "security_levels": dict(level_counts),
            "top_suspicious_ips": [{"ip": ip, "risk_score": score} for ip, score in top_suspicious_ips],
            "rate_limiter": self.rate_limiter.get_stats()
        }
    
    async def get_ip_details(self, ip_address: str) -> Dict[str, Any]:
        """Get detailed information about a specific IP"""
        if ip_address not in self.traffic_patterns:
            return {"error": "IP address not found"}
        
        pattern = self.traffic_patterns[ip_address]
        
        # Get recent events for this IP
        recent_events = [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "level": e.level.value,
                "endpoint": e.endpoint,
                "method": e.method,
                "risk_score": e.risk_score
            }
            for e in self.events
            if e.source_ip == ip_address and datetime.now() - e.timestamp < timedelta(hours=24)
        ]
        
        return {
            "ip_address": ip_address,
            "pattern": {
                "request_count": pattern.request_count,
                "unique_endpoints": len(pattern.unique_endpoints),
                "unique_user_agents": len(pattern.unique_user_agents),
                "first_seen": pattern.first_seen.isoformat(),
                "last_seen": pattern.last_seen.isoformat(),
                "suspicious_score": pattern.suspicious_score,
                "average_response_time": pattern.average_response_time,
                "status_code_distribution": dict(pattern.status_codes)
            },
            "recent_events": recent_events,
            "is_blocked": ip_address in self.rate_limiter.blocked_ips,
            "is_suspicious": ip_address in self.suspicious_ips
        }
    
    async def cleanup_old_data(self):
        """Clean up old security monitoring data"""
        current_time = datetime.now()
        
        # Remove old traffic patterns
        expired_ips = [
            ip for ip, pattern in self.traffic_patterns.items()
            if current_time - pattern.last_seen > self.max_pattern_age
        ]
        
        for ip in expired_ips:
            del self.traffic_patterns[ip]
            self.suspicious_ips.discard(ip)
        
        # Clean up old blocked IPs
        expired_blocks = [
            ip for ip, block_time in self.rate_limiter.blocked_ips.items()
            if current_time - block_time > timedelta(hours=24)
        ]
        
        for ip in expired_blocks:
            del self.rate_limiter.blocked_ips[ip]
            self.rate_limiter.warning_ips.discard(ip)

# ============================================================================
# Global Security Monitor Instance
# ============================================================================

# Global security monitor instance
security_monitor = SecurityMonitor()

# Background cleanup task
async def security_cleanup_task():
    """Background task to clean up old security data"""
    while True:
        try:
            await security_monitor.cleanup_old_data()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            security_logger.logger.error(f"Security cleanup task failed: {e}")
            await asyncio.sleep(3600)

# Convenience functions
async def log_request_security(
    ip_address: str,
    method: str,
    endpoint: str,
    status_code: int,
    user_agent: str,
    response_time: float,
    correlation_id: str = None
):
    """Log a request for security analysis"""
    await security_monitor.log_request(
        ip_address, method, endpoint, status_code, user_agent, response_time, correlation_id
    )

async def check_rate_limit(ip_address: str, endpoint: str = None) -> bool:
    """Check if request is allowed by rate limiter"""
    return await security_monitor.rate_limiter.is_allowed(ip_address, endpoint)

async def get_security_status() -> Dict[str, Any]:
    """Get current security monitoring status"""
    return await security_monitor.get_security_summary()

async def get_ip_security_details(ip_address: str) -> Dict[str, Any]:
    """Get security details for a specific IP"""
    return await security_monitor.get_ip_details(ip_address)