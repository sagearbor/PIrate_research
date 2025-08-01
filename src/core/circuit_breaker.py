"""
Circuit breaker pattern implementation for external service monitoring.

This module provides robust circuit breaker functionality for external API calls
and service dependencies, with comprehensive monitoring and failure handling.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
import logging
from contextlib import asynccontextmanager

from src.core.metrics import (
    external_api_calls_total,
    external_api_duration_seconds,
    external_api_rate_limit_hits_total,
    record_rate_limit_hit
)
from src.core.logging_config import get_agent_logger

logger = logging.getLogger(__name__)

# ============================================================================
# Circuit Breaker States and Configuration
# ============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, rejecting calls
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 60.0              # Seconds to wait before half-open
    call_timeout: float = 30.0         # Individual call timeout
    expected_exception: Exception = Exception
    fallback_function: Optional[Callable] = None

class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitBreakerTimeoutException(Exception):
    """Raised when call times out"""
    pass

# ============================================================================
# Circuit Breaker Implementation
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker for external service calls with monitoring integration.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        
        # Monitoring
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.circuit_open_count = 0
        
        # Logging
        self.logger = get_agent_logger(f"circuit-breaker-{name}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if exc_type is not None:
            await self._record_failure(exc_val)
        else:
            await self._record_success()
    
    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: When circuit is open
            CircuitBreakerTimeoutException: When call times out
            Exception: Original function exceptions
        """
        self.total_calls += 1
        
        # Check if circuit breaker should allow the call
        if not await self._should_allow_call():
            self.circuit_open_count += 1
            external_api_calls_total.labels(
                service=self.name,
                endpoint="circuit_breaker",
                status="circuit_open"
            ).inc()
            
            # Try fallback if available
            if self.config.fallback_function:
                self.logger.info(
                    f"Circuit breaker open, using fallback",
                    circuit_breaker=self.name,
                    state=self.state.value
                )
                return await self.config.fallback_function(*args, **kwargs)
            
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is open"
            )
        
        # Execute the call with timeout
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )
            
            # Record success
            duration = time.time() - start_time
            await self._record_success()
            
            external_api_calls_total.labels(
                service=self.name,
                endpoint="function_call",
                status="success"
            ).inc()
            
            external_api_duration_seconds.labels(
                service=self.name,
                endpoint="function_call"
            ).observe(duration)
            
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            timeout_error = CircuitBreakerTimeoutException(
                f"Call to '{self.name}' timed out after {self.config.call_timeout}s"
            )
            
            await self._record_failure(timeout_error)
            
            external_api_calls_total.labels(
                service=self.name,
                endpoint="function_call",
                status="timeout"
            ).inc()
            
            external_api_duration_seconds.labels(
                service=self.name,
                endpoint="function_call"
            ).observe(duration)
            
            raise timeout_error
            
        except Exception as e:
            duration = time.time() - start_time
            await self._record_failure(e)
            
            external_api_calls_total.labels(
                service=self.name,
                endpoint="function_call",
                status="error"
            ).inc()
            
            external_api_duration_seconds.labels(
                service=self.name,
                endpoint="function_call"
            ).observe(duration)
            
            raise
    
    async def _should_allow_call(self) -> bool:
        """Determine if a call should be allowed based on circuit breaker state"""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if timeout has elapsed
            if (self.last_failure_time and 
                current_time - self.last_failure_time >= self.config.timeout):
                
                self.logger.info(
                    f"Circuit breaker transitioning to half-open",
                    circuit_breaker=self.name,
                    timeout_elapsed=current_time - self.last_failure_time
                )
                
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    async def _record_success(self):
        """Record a successful call"""
        self.successful_calls += 1
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.config.success_threshold:
                self.logger.info(
                    f"Circuit breaker closing after {self.success_count} successes",
                    circuit_breaker=self.name,
                    previous_state=self.state.value
                )
                
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
    
    async def _record_failure(self, exception: Exception):
        """Record a failed call"""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        self.logger.warning(
            f"Circuit breaker recorded failure",
            circuit_breaker=self.name,
            exception=str(exception),
            failure_count=self.failure_count,
            state=self.state.value
        )
        
        # Check if we should open the circuit
        if (self.state == CircuitBreakerState.CLOSED and 
            self.failure_count >= self.config.failure_threshold):
            
            self.logger.error(
                f"Circuit breaker opening after {self.failure_count} failures",
                circuit_breaker=self.name,
                threshold=self.config.failure_threshold
            )
            
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.logger.warning(
                f"Circuit breaker re-opening from half-open state",
                circuit_breaker=self.name
            )
            
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "circuit_open_count": self.circuit_open_count,
            "success_rate": (
                self.successful_calls / self.total_calls 
                if self.total_calls > 0 else 0
            ),
            "last_failure_time": self.last_failure_time
        }

# ============================================================================
# External Service Monitor
# ============================================================================

class ExternalServiceMonitor:
    """
    Monitors external services and manages circuit breakers.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_configs: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
    
    def register_service(
        self, 
        service_name: str, 
        config: CircuitBreakerConfig,
        health_check_url: Optional[str] = None,
        health_check_interval: int = 60
    ):
        """
        Register an external service for monitoring.
        
        Args:
            service_name: Name of the service
            config: Circuit breaker configuration
            health_check_url: Optional health check endpoint
            health_check_interval: Health check interval in seconds
        """
        self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        self.service_configs[service_name] = {
            "health_check_url": health_check_url,
            "health_check_interval": health_check_interval,
            "last_health_check": None,
            "health_status": "unknown"
        }
        
        logger.info(
            f"Registered external service '{service_name}' for monitoring with "
            f"failure_threshold={config.failure_threshold}, timeout={config.timeout}"
        )
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get circuit breaker for a service"""
        if service_name not in self.circuit_breakers:
            # Create default circuit breaker
            default_config = CircuitBreakerConfig()
            self.register_service(service_name, default_config)
        
        return self.circuit_breakers[service_name]
    
    async def call_service(
        self, 
        service_name: str, 
        func: Callable[..., Awaitable], 
        *args, 
        **kwargs
    ):
        """
        Make a call to an external service through its circuit breaker.
        
        Args:
            service_name: Name of the service
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        circuit_breaker = self.get_circuit_breaker(service_name)
        return await circuit_breaker.call(func, *args, **kwargs)
    
    async def health_check_service(self, service_name: str) -> Dict[str, Any]:
        """
        Perform health check for a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            Health check results
        """
        if service_name not in self.service_configs:
            return {"status": "unknown", "message": "Service not registered"}
        
        config = self.service_configs[service_name]
        circuit_breaker = self.circuit_breakers[service_name]
        
        health_data = {
            "service": service_name,
            "circuit_breaker": circuit_breaker.get_stats(),
            "last_check": time.time(),
            "status": "healthy"
        }
        
        # If health check URL is configured, perform HTTP check
        if config["health_check_url"]:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        config["health_check_url"],
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            health_data["http_status"] = "healthy"
                        else:
                            health_data["http_status"] = "unhealthy"
                            health_data["status"] = "degraded"
                            health_data["http_response_code"] = response.status
                            
            except Exception as e:
                health_data["http_status"] = "error"
                health_data["status"] = "unhealthy"
                health_data["error"] = str(e)
        
        # Update service health status
        config["last_health_check"] = time.time()
        config["health_status"] = health_data["status"]
        self.health_status[service_name] = health_data
        
        return health_data
    
    async def health_check_all_services(self) -> Dict[str, Any]:
        """Perform health checks for all registered services"""
        results = {}
        
        for service_name in self.service_configs.keys():
            try:
                results[service_name] = await self.health_check_service(service_name)
            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "error": str(e),
                    "service": service_name
                }
        
        return results
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current status for a service"""
        if service_name not in self.circuit_breakers:
            return {"status": "unknown", "message": "Service not registered"}
        
        circuit_breaker = self.circuit_breakers[service_name]
        config = self.service_configs.get(service_name, {})
        
        return {
            "service": service_name,
            "circuit_breaker": circuit_breaker.get_stats(),
            "health_check": {
                "url": config.get("health_check_url"),
                "last_check": config.get("last_health_check"),
                "status": config.get("health_status", "unknown")
            }
        }
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all registered services"""
        return {
            service_name: self.get_service_status(service_name)
            for service_name in self.circuit_breakers.keys()
        }

# ============================================================================
# Convenience Decorators and Context Managers
# ============================================================================

def circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0,
    call_timeout: float = 30.0,
    fallback: Optional[Callable] = None
):
    """
    Decorator for applying circuit breaker to async functions.
    
    Args:
        service_name: Name of the service
        failure_threshold: Number of failures before opening
        timeout: Seconds to wait before half-open
        call_timeout: Individual call timeout
        fallback: Fallback function to call when circuit is open
    """
    def decorator(func):
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout=timeout,
            call_timeout=call_timeout,
            fallback_function=fallback
        )
        
        # Register service if not already registered
        if service_name not in external_service_monitor.circuit_breakers:
            external_service_monitor.register_service(service_name, config)
        
        async def wrapper(*args, **kwargs):
            return await external_service_monitor.call_service(
                service_name, func, *args, **kwargs
            )
        
        return wrapper
    return decorator

@asynccontextmanager
async def service_call(service_name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Context manager for service calls with circuit breaker protection.
    
    Args:
        service_name: Name of the service
        config: Optional circuit breaker configuration
    """
    if config and service_name not in external_service_monitor.circuit_breakers:
        external_service_monitor.register_service(service_name, config)
    
    circuit_breaker = external_service_monitor.get_circuit_breaker(service_name)
    
    async with circuit_breaker:
        yield circuit_breaker

# ============================================================================
# Global Service Monitor Instance
# ============================================================================

# Global instance for use throughout the application
external_service_monitor = ExternalServiceMonitor()

# Pre-configure common external services
external_service_monitor.register_service(
    "nih_reporter",
    CircuitBreakerConfig(
        failure_threshold=3,
        timeout=120.0,
        call_timeout=30.0
    ),
    health_check_url="https://api.reporter.nih.gov/",
    health_check_interval=300
)

external_service_monitor.register_service(
    "google_scholar",
    CircuitBreakerConfig(
        failure_threshold=5,
        timeout=60.0,
        call_timeout=20.0
    ),
    health_check_interval=300
)

external_service_monitor.register_service(
    "pubmed",
    CircuitBreakerConfig(
        failure_threshold=3,
        timeout=90.0,
        call_timeout=25.0
    ),
    health_check_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi",
    health_check_interval=300
)

external_service_monitor.register_service(
    "arxiv",
    CircuitBreakerConfig(
        failure_threshold=3,
        timeout=90.0,
        call_timeout=25.0
    ),
    health_check_url="http://export.arxiv.org/api/query?search_query=test",
    health_check_interval=300
)

async def get_external_services_health() -> Dict[str, Any]:
    """Get health status for all external services"""
    return await external_service_monitor.health_check_all_services()

def get_external_services_status() -> Dict[str, Any]:
    """Get current status for all external services"""
    return external_service_monitor.get_all_service_status()