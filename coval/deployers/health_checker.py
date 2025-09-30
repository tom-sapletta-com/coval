#!/usr/bin/env python3
"""
COVAL Health Checker

Handles application health monitoring and verification for deployed containers.
Extracted from the monolithic deployment manager for better separation of concerns.
"""

import logging
import time
import socket
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import concurrent.futures
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    endpoint: str
    method: str = "GET"
    expected_status: int = 200
    timeout: int = 30
    interval: int = 10
    retries: int = 3
    retry_delay: int = 5
    headers: Dict[str, str] = None
    expected_response: Optional[str] = None
    port_check: bool = True


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: HealthStatus
    timestamp: datetime
    response_time: Optional[float]
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    port_accessible: bool = False


@dataclass
class ApplicationHealth:
    """Overall health status of an application."""
    application_name: str
    overall_status: HealthStatus
    last_check: datetime
    checks_performed: int
    successful_checks: int
    failed_checks: int
    average_response_time: Optional[float]
    recent_results: List[HealthCheckResult]
    uptime_start: Optional[datetime]
    last_failure: Optional[datetime]


class HealthChecker:
    """
    Monitors application health with comprehensive checks and reporting.
    
    Features:
    - HTTP endpoint health checks
    - Port connectivity checks
    - Retry logic with exponential backoff
    - Health status tracking and history
    - Concurrent health monitoring
    - Detailed health reporting
    """
    
    def __init__(self):
        """Initialize the HealthChecker."""
        self.monitored_apps: Dict[str, ApplicationHealth] = {}
        self.active_monitors: Dict[str, bool] = {}
        
        # Default health check configurations for common frameworks
        self.default_configs = {
            'fastapi': HealthCheckConfig(
                endpoint='/health',
                method='GET',
                expected_status=200,
                timeout=15,
                interval=10,
                retries=3
            ),
            'flask': HealthCheckConfig(
                endpoint='/health',
                method='GET', 
                expected_status=200,
                timeout=15,
                interval=10,
                retries=3
            ),
            'express': HealthCheckConfig(
                endpoint='/health',
                method='GET',
                expected_status=200,
                timeout=15,
                interval=10,
                retries=3
            ),
            'django': HealthCheckConfig(
                endpoint='/health/',
                method='GET',
                expected_status=200,
                timeout=15,
                interval=10,
                retries=3
            )
        }
    
    def perform_health_check(self, 
                           host: str, 
                           port: int, 
                           config: HealthCheckConfig) -> HealthCheckResult:
        """
        Perform a single health check against an application.
        
        Args:
            host: Host address
            port: Port number
            config: Health check configuration
            
        Returns:
            HealthCheckResult: Result of the health check
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        logger.debug(f"Performing health check: {host}:{port}{config.endpoint}")
        
        # First check port connectivity
        port_accessible = self._check_port_connectivity(host, port, timeout=5)
        
        if not port_accessible and config.port_check:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                timestamp=timestamp,
                response_time=None,
                status_code=None,
                response_body=None,
                error_message=f"Port {port} not accessible on {host}",
                port_accessible=False
            )
        
        # Perform HTTP health check
        try:
            url = f"http://{host}:{port}{config.endpoint}"
            headers = config.headers or {}
            
            response = requests.request(
                method=config.method,
                url=url,
                headers=headers,
                timeout=config.timeout,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            
            # Check status code
            if response.status_code == config.expected_status:
                status = HealthStatus.HEALTHY
                error_message = None
            else:
                status = HealthStatus.UNHEALTHY
                error_message = f"Expected status {config.expected_status}, got {response.status_code}"
            
            # Check response content if specified
            if config.expected_response and status == HealthStatus.HEALTHY:
                if config.expected_response not in response.text:
                    status = HealthStatus.UNHEALTHY
                    error_message = f"Expected response content '{config.expected_response}' not found"
            
            return HealthCheckResult(
                status=status,
                timestamp=timestamp,
                response_time=response_time,
                status_code=response.status_code,
                response_body=response.text[:500],  # Limit response body size
                error_message=error_message,
                port_accessible=port_accessible
            )
            
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                status=HealthStatus.TIMEOUT,
                timestamp=timestamp,
                response_time=None,
                status_code=None,
                response_body=None,
                error_message=f"Health check timed out after {config.timeout}s",
                port_accessible=port_accessible
            )
        except requests.exceptions.ConnectionError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                timestamp=timestamp,
                response_time=None,
                status_code=None,
                response_body=None,
                error_message=f"Connection error: {str(e)[:200]}",
                port_accessible=port_accessible
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                timestamp=timestamp,
                response_time=None,
                status_code=None,
                response_body=None,
                error_message=f"Unexpected error: {str(e)[:200]}",
                port_accessible=port_accessible
            )
    
    def perform_health_check_with_retries(self,
                                        host: str,
                                        port: int,
                                        config: HealthCheckConfig) -> HealthCheckResult:
        """
        Perform health check with retry logic.
        
        Args:
            host: Host address
            port: Port number
            config: Health check configuration
            
        Returns:
            HealthCheckResult: Final result after retries
        """
        last_result = None
        
        for attempt in range(config.retries + 1):
            result = self.perform_health_check(host, port, config)
            
            if result.status == HealthStatus.HEALTHY:
                logger.debug(f"Health check successful on attempt {attempt + 1}")
                return result
            
            last_result = result
            
            if attempt < config.retries:
                logger.debug(f"Health check failed, retrying in {config.retry_delay}s (attempt {attempt + 1}/{config.retries + 1})")
                time.sleep(config.retry_delay)
        
        logger.warning(f"Health check failed after {config.retries + 1} attempts")
        return last_result
    
    def wait_for_healthy(self,
                        host: str,
                        port: int,
                        config: HealthCheckConfig,
                        max_wait_time: int = 300) -> bool:
        """
        Wait for an application to become healthy.
        
        Args:
            host: Host address
            port: Port number
            config: Health check configuration
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            bool: True if application became healthy, False if timed out
        """
        logger.info(f"Waiting for application to become healthy: {host}:{port}")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait_time:
            attempt += 1
            result = self.perform_health_check(host, port, config)
            
            if result.status == HealthStatus.HEALTHY:
                elapsed = time.time() - start_time
                logger.info(f"✓ Application healthy after {elapsed:.1f}s ({attempt} attempts)")
                return True
            
            logger.debug(f"Health check attempt {attempt}: {result.status} - {result.error_message}")
            time.sleep(config.interval)
        
        logger.error(f"Application failed to become healthy within {max_wait_time}s")
        return False
    
    def start_monitoring(self,
                        app_name: str,
                        host: str,
                        port: int,
                        config: HealthCheckConfig):
        """
        Start continuous health monitoring for an application.
        
        Args:
            app_name: Name of the application
            host: Host address
            port: Port number
            config: Health check configuration
        """
        logger.info(f"Starting health monitoring for: {app_name}")
        
        # Initialize application health tracking
        self.monitored_apps[app_name] = ApplicationHealth(
            application_name=app_name,
            overall_status=HealthStatus.STARTING,
            last_check=datetime.now(),
            checks_performed=0,
            successful_checks=0,
            failed_checks=0,
            average_response_time=None,
            recent_results=[],
            uptime_start=None,
            last_failure=None
        )
        
        self.active_monitors[app_name] = True
        
        # Start monitoring in background thread
        def monitor_loop():
            app_health = self.monitored_apps[app_name]
            response_times = []
            
            while self.active_monitors.get(app_name, False):
                try:
                    result = self.perform_health_check_with_retries(host, port, config)
                    
                    # Update application health
                    app_health.last_check = result.timestamp
                    app_health.checks_performed += 1
                    
                    if result.status == HealthStatus.HEALTHY:
                        app_health.successful_checks += 1
                        if app_health.uptime_start is None:
                            app_health.uptime_start = result.timestamp
                        if result.response_time:
                            response_times.append(result.response_time)
                            app_health.average_response_time = sum(response_times) / len(response_times)
                    else:
                        app_health.failed_checks += 1
                        app_health.last_failure = result.timestamp
                        app_health.uptime_start = None  # Reset uptime
                    
                    app_health.overall_status = result.status
                    
                    # Keep recent results (last 10)
                    app_health.recent_results.append(result)
                    if len(app_health.recent_results) > 10:
                        app_health.recent_results.pop(0)
                    
                    # Log health status changes
                    if result.status != HealthStatus.HEALTHY:
                        logger.warning(f"Health check failed for {app_name}: {result.error_message}")
                    
                    time.sleep(config.interval)
                    
                except Exception as e:
                    logger.error(f"Health monitoring error for {app_name}: {e}")
                    time.sleep(config.interval)
        
        # Start monitoring in thread
        import threading
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def stop_monitoring(self, app_name: str):
        """
        Stop health monitoring for an application.
        
        Args:
            app_name: Name of the application
        """
        logger.info(f"Stopping health monitoring for: {app_name}")
        self.active_monitors[app_name] = False
    
    def get_application_health(self, app_name: str) -> Optional[ApplicationHealth]:
        """
        Get health status for an application.
        
        Args:
            app_name: Name of the application
            
        Returns:
            ApplicationHealth or None if not monitored
        """
        return self.monitored_apps.get(app_name)
    
    def get_all_application_health(self) -> Dict[str, ApplicationHealth]:
        """Get health status for all monitored applications."""
        return self.monitored_apps.copy()
    
    def get_health_config_for_framework(self, framework: str) -> HealthCheckConfig:
        """
        Get default health check configuration for a framework.
        
        Args:
            framework: Framework name (fastapi, flask, express, etc.)
            
        Returns:
            HealthCheckConfig: Default configuration for the framework
        """
        return self.default_configs.get(framework.lower(), self.default_configs['fastapi'])
    
    def _check_port_connectivity(self, host: str, port: int, timeout: int = 5) -> bool:
        """
        Check if a port is accessible on a host.
        
        Args:
            host: Host address
            port: Port number
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if port is accessible, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception as e:
            logger.debug(f"Port connectivity check failed for {host}:{port}: {e}")
            return False
    
    def generate_health_report(self, app_name: str) -> Optional[Dict[str, Any]]:
        """
        Generate a comprehensive health report for an application.
        
        Args:
            app_name: Name of the application
            
        Returns:
            Dict containing health report or None if not monitored
        """
        app_health = self.monitored_apps.get(app_name)
        if not app_health:
            return None
        
        # Calculate uptime
        uptime_seconds = None
        if app_health.uptime_start:
            uptime_seconds = (datetime.now() - app_health.uptime_start).total_seconds()
        
        # Calculate success rate
        success_rate = 0
        if app_health.checks_performed > 0:
            success_rate = (app_health.successful_checks / app_health.checks_performed) * 100
        
        return {
            'application_name': app_health.application_name,
            'overall_status': app_health.overall_status.value,
            'last_check': app_health.last_check.isoformat(),
            'checks_performed': app_health.checks_performed,
            'successful_checks': app_health.successful_checks,
            'failed_checks': app_health.failed_checks,
            'success_rate_percentage': round(success_rate, 2),
            'average_response_time_ms': round(app_health.average_response_time * 1000, 2) if app_health.average_response_time else None,
            'uptime_seconds': round(uptime_seconds, 0) if uptime_seconds else None,
            'uptime_human': self._format_uptime(uptime_seconds) if uptime_seconds else None,
            'last_failure': app_health.last_failure.isoformat() if app_health.last_failure else None,
            'recent_status_history': [
                {
                    'timestamp': result.timestamp.isoformat(),
                    'status': result.status.value,
                    'response_time_ms': round(result.response_time * 1000, 2) if result.response_time else None,
                    'error': result.error_message
                }
                for result in app_health.recent_results[-5:]  # Last 5 results
            ]
        }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            return f"{int(uptime_seconds // 60)}m {int(uptime_seconds % 60)}s"
        else:
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
