"""
Structured logging configuration for the multi-agent research system.

This module provides comprehensive logging setup with:
- JSON formatting for structured logs
- Multi-agent communication tracking
- Security event logging
- Performance monitoring
- Correlation ID tracking
"""

import logging
import logging.config
import json
import sys
import uuid
import contextvars
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from pythonjsonlogger import jsonlogger

# ============================================================================
# Structured Logging Configuration
# ============================================================================

def setup_structured_logging(
    log_level: str = "INFO",
    enable_json: bool = True,
    enable_console: bool = True,
    log_file: Optional[str] = None
):
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Enable JSON formatting for structured logs
        enable_console: Enable console output
        log_file: Optional log file path
    """
    
    # Configure structlog processors
    structlog_processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            parameters=[structlog.processors.CallsiteParameter.FUNC_NAME,
                       structlog.processors.CallsiteParameter.LINENO]
        ),
        add_correlation_id,
        add_agent_context,
    ]
    
    if enable_json:
        structlog_processors.append(structlog.processors.JSONRenderer())
    else:
        structlog_processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    handlers = []
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_json:
            console_formatter = CustomJsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = CustomJsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        force=True
    )

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields for multi-agent system."""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service information
        log_record['service'] = 'research-opportunity-notifier'
        log_record['version'] = '1.0.0'
        
        # Add environment (could be set via env var)
        log_record['environment'] = 'development'  # TODO: Make configurable

# ============================================================================
# Structured Logging Processors
# ============================================================================

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID for request tracking."""
    import contextvars
    
    # Try to get correlation ID from context
    try:
        correlation_id = correlation_context.get()
    except LookupError:
        # Generate new correlation ID if not present
        correlation_id = str(uuid.uuid4())
        correlation_context.set(correlation_id)
    
    event_dict['correlation_id'] = correlation_id
    return event_dict

def add_agent_context(logger, method_name, event_dict):
    """Add agent context information for multi-agent logging."""
    import contextvars
    
    try:
        agent_name = agent_context.get()
        event_dict['agent'] = agent_name
    except LookupError:
        # No agent context available
        pass
    
    return event_dict

# Context variables for tracking across async operations
correlation_context = contextvars.ContextVar('correlation_id')
agent_context = contextvars.ContextVar('agent_name')

# ============================================================================
# Agent-Specific Loggers
# ============================================================================

class AgentLogger:
    """Structured logger for agent operations."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = structlog.get_logger(agent_name)
    
    async def __aenter__(self):
        """Set agent context on entry."""
        agent_context.set(self.agent_name)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clear agent context on exit."""
        try:
            agent_context.get()
            # Don't actually clear - let it propagate
        except LookupError:
            pass
    
    def info(self, message: str, **kwargs):
        """Log info message with agent context."""
        self.logger.info(message, agent=self.agent_name, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with agent context."""
        self.logger.warning(message, agent=self.agent_name, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with agent context."""
        self.logger.error(message, agent=self.agent_name, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with agent context."""
        self.logger.debug(message, agent=self.agent_name, **kwargs)
    
    def log_execution_start(self, operation: str, **kwargs):
        """Log the start of an agent operation."""
        self.info(
            f"Starting {operation}",
            operation=operation,
            event_type="execution_start",
            **kwargs
        )
    
    def log_execution_end(self, operation: str, duration: float, success: bool = True, **kwargs):
        """Log the end of an agent operation."""
        level = "info" if success else "error"
        getattr(self.logger, level)(
            f"Completed {operation}",
            operation=operation,
            event_type="execution_end",
            duration_seconds=duration,
            success=success,
            agent=self.agent_name,
            **kwargs
        )
    
    def log_a2a_message(self, message_type: str, target_agent: str, payload_size: int = None, **kwargs):
        """Log agent-to-agent communication for Phase 5."""
        self.info(
            f"Sending {message_type} message to {target_agent}",
            event_type="a2a_message",
            message_type=message_type,
            target_agent=target_agent,
            source_agent=self.agent_name,
            payload_size_bytes=payload_size,
            **kwargs
        )

# ============================================================================
# Security and Audit Logging
# ============================================================================

class SecurityLogger:
    """Specialized logger for security events and audit trails."""
    
    def __init__(self):
        self.logger = structlog.get_logger("security")
    
    def log_api_access(self, endpoint: str, method: str, user_agent: str = None, ip_address: str = None, **kwargs):
        """Log API access for security monitoring."""
        self.logger.info(
            f"API access: {method} {endpoint}",
            event_type="api_access",
            endpoint=endpoint,
            method=method,
            user_agent=user_agent,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_rate_limit_hit(self, endpoint: str, ip_address: str = None, **kwargs):
        """Log rate limit violations."""
        self.logger.warning(
            f"Rate limit exceeded for {endpoint}",
            event_type="rate_limit_exceeded",
            endpoint=endpoint,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_authentication_failure(self, reason: str, ip_address: str = None, **kwargs):
        """Log authentication failures."""
        self.logger.warning(
            f"Authentication failed: {reason}",
            event_type="auth_failure",
            reason=reason,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_external_api_call(self, service: str, endpoint: str, status_code: int, duration: float, **kwargs):
        """Log external API calls for monitoring."""
        level = "info" if 200 <= status_code < 400 else "warning"
        getattr(self.logger, level)(
            f"External API call to {service}/{endpoint}",
            event_type="external_api_call",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            duration_seconds=duration,
            **kwargs
        )

# ============================================================================
# Performance Monitoring Logger
# ============================================================================

class PerformanceLogger:
    """Logger for performance monitoring and metrics."""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    def log_slow_query(self, query_type: str, duration: float, threshold: float = 1.0, **kwargs):
        """Log slow database queries or operations."""
        if duration > threshold:
            self.logger.warning(
                f"Slow {query_type} detected",
                event_type="slow_query",
                query_type=query_type,
                duration_seconds=duration,
                threshold_seconds=threshold,
                **kwargs
            )
    
    def log_memory_usage(self, memory_usage_mb: float, threshold: float = 500.0, **kwargs):
        """Log high memory usage."""
        if memory_usage_mb > threshold:
            self.logger.warning(
                f"High memory usage detected",
                event_type="high_memory_usage",
                memory_usage_mb=memory_usage_mb,
                threshold_mb=threshold,
                **kwargs
            )
    
    def log_processing_metrics(self, operation: str, items_processed: int, duration: float, **kwargs):
        """Log bulk processing metrics."""
        throughput = items_processed / duration if duration > 0 else 0
        self.logger.info(
            f"Processed {items_processed} items in {duration:.2f}s",
            event_type="bulk_processing",
            operation=operation,
            items_processed=items_processed,
            duration_seconds=duration,
            throughput_per_second=throughput,
            **kwargs
        )

# ============================================================================
# Global Logger Instances
# ============================================================================

# Initialize default structured logging
setup_structured_logging()

# Create global logger instances
security_logger = SecurityLogger()
performance_logger = PerformanceLogger()

def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get a structured logger for a specific agent."""
    return AgentLogger(agent_name)

def set_correlation_id(correlation_id: str):
    """Set correlation ID for request tracking."""
    correlation_context.set(correlation_id)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    try:
        return correlation_context.get()
    except LookupError:
        return None