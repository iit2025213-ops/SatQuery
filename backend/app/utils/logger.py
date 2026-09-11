# app/utils/logger.py

import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logging"""
    
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level.upper())
    
    # JSON formatter
    formatter = jsonlogger.JsonFormatter()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


class StructuredLogger:
    """Helper class for structured logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(self, method: str, path: str, user_id: str = None, **extra):
        """Log incoming request"""
        self.logger.info(
            f"Request: {method} {path}",
            extra={
                "event": "request",
                "method": method,
                "path": path,
                "user_id": user_id,
                **extra
            }
        )
    
    def log_job_created(self, job_id: str, user_id: str, query: str):
        """Log job creation"""
        self.logger.info(
            f"Job created: {job_id}",
            extra={
                "event": "job_created",
                "job_id": job_id,
                "user_id": user_id,
                "query": query[:100]  # First 100 chars
            }
        )
    
    def log_capability_executed(self, job_id: str, step: int, capability: str, latency_ms: float):
        """Log capability execution"""
        self.logger.info(
            f"Capability executed: {capability}",
            extra={
                "event": "capability_executed",
                "job_id": job_id,
                "step": step,
                "capability": capability,
                "latency_ms": latency_ms
            }
        )
    
    def log_error(self, error: str, job_id: str = None, **extra):
        """Log error with context"""
        self.logger.error(
            f"Error: {error}",
            extra={
                "event": "error",
                "job_id": job_id,
                **extra
            },
            exc_info=True
        )
