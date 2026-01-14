"""Centralized logging configuration for the AI Agent Orchestration System."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import colorama

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console."""
    
    COLORS = {
        'DEBUG': colorama.Fore.CYAN,
        'INFO': colorama.Fore.GREEN,
        'WARNING': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{colorama.Style.RESET_ALL}"
        
        # Add color to agent name if present
        if hasattr(record, 'agent_name'):
            record.agent_name = f"{colorama.Fore.MAGENTA}{record.agent_name}{colorama.Style.RESET_ALL}"
        
        return super().format(record)


class AgentLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds agent name to log records."""
    
    def process(self, msg, kwargs):
        # Add agent_name to extra fields
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['agent_name'] = self.extra.get('agent_name', 'Unknown')
        return msg, kwargs


def setup_logger(
    name: str = 'agent_orchestrator',
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up and configure a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(agent_name)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(agent_name)-15s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Add a default filter to add agent_name field if missing
    class AgentNameFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'agent_name'):
                record.agent_name = 'System'
            return True
    
    logger.addFilter(AgentNameFilter())
    
    return logger


def get_logger(agent_name: str) -> AgentLoggerAdapter:
    """
    Get a logger adapter for a specific agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Logger adapter with agent name
    """
    base_logger = logging.getLogger('agent_orchestrator')
    return AgentLoggerAdapter(base_logger, {'agent_name': agent_name})
