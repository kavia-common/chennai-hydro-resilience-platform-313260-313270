"""
Structured logging utility with correlation IDs for CHRIS Backend API.

Provides request-scoped correlation IDs for distributed tracing and
structured log output in JSON format for better log aggregation.
"""
import logging
import json
import uuid
from typing import Optional
from datetime import datetime
from contextvars import ContextVar
from fastapi import Request

# Context variable for correlation ID (thread-safe for async)
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

logger = logging.getLogger(__name__)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logs.
    
    Includes correlation ID, timestamp, and structured fields.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        correlation_id = _correlation_id.get()
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_structured_logging(log_level: str = "INFO"):
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add structured handler
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)
    
    logger.info("Structured logging configured")


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context.
    
    Returns:
        Correlation ID or None if not set
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID in context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate new correlation ID.
    
    Returns:
        UUID-based correlation ID
    """
    return str(uuid.uuid4())


def extract_correlation_id(request: Request) -> str:
    """
    Extract or generate correlation ID from request.
    
    Checks for X-Correlation-ID header, falls back to generating new ID.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Correlation ID
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    
    if not correlation_id:
        correlation_id = generate_correlation_id()
    
    return correlation_id


# PUBLIC_INTERFACE
class StructuredLogger:
    """
    Structured logger with correlation ID support.
    
    Usage:
    ```python
    log = StructuredLogger(__name__)
    log.info("Processing request", user_id="123", action="forecast")
    ```
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, message: str, **extra_fields):
        """
        Log message with extra structured fields.
        
        Args:
            level: Log level
            message: Log message
            **extra_fields: Additional fields to include
        """
        correlation_id = _correlation_id.get()
        
        # Create log record with extra fields
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(structured)",
            0,
            message,
            (),
            None
        )
        
        # Add extra fields
        record.extra_fields = {
            **extra_fields,
            "correlation_id": correlation_id
        }
        
        self.logger.handle(record)
    
    def debug(self, message: str, **extra_fields):
        """Log debug message with extra fields."""
        self._log(logging.DEBUG, message, **extra_fields)
    
    def info(self, message: str, **extra_fields):
        """Log info message with extra fields."""
        self._log(logging.INFO, message, **extra_fields)
    
    def warning(self, message: str, **extra_fields):
        """Log warning message with extra fields."""
        self._log(logging.WARNING, message, **extra_fields)
    
    def error(self, message: str, **extra_fields):
        """Log error message with extra fields."""
        self._log(logging.ERROR, message, **extra_fields)
    
    def critical(self, message: str, **extra_fields):
        """Log critical message with extra fields."""
        self._log(logging.CRITICAL, message, **extra_fields)


# PUBLIC_INTERFACE
async def correlation_id_middleware(request: Request, call_next):
    """
    Middleware to extract/generate correlation ID for each request.
    
    Add this to FastAPI app:
    ```python
    app.middleware("http")(correlation_id_middleware)
    ```
    
    Args:
        request: FastAPI request
        call_next: Next middleware/route handler
        
    Returns:
        Response with X-Correlation-ID header
    """
    # Extract or generate correlation ID
    correlation_id = extract_correlation_id(request)
    
    # Set in context
    set_correlation_id(correlation_id)
    
    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "extra_fields": {
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown"
            }
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    # Log request completion
    logger.info(
        f"Request completed: {request.method} {request.url.path} - {response.status_code}",
        extra={
            "extra_fields": {
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code
            }
        }
    )
    
    return response
