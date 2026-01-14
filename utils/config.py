"""Configuration management for EntraFlow."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from .exceptions import ConfigurationError

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration manager with support for YAML files and environment variables."""
    
    _instance = None
    _config_data: Dict[str, Any] = {}
    
    def __new__(cls, config_path: Optional[str] = None):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        if self._initialized:
            return
        
        if config_path is None:
            # Default to config.yaml in project root
            config_path = Path(__file__).parent.parent / 'config.yaml'
        
        self._load_config(config_path)
        self._override_with_env()
        self._initialized = True
    
    def _load_config(self, config_path: str):
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}"
            )
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration: {str(e)}"
            )
    
    def _override_with_env(self):
        """Override configuration with environment variables."""
        # API keys from environment
        env_mappings = {
            'OPENWEATHER_API_KEY': ['api', 'weather', 'api_key'],
            'NEWS_API_KEY': ['api', 'news', 'api_key'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(config_path, value)
    
    def _set_nested_value(self, path: list, value: Any):
        """Set a value in nested dictionary using path list."""
        current = self._config_data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, *keys, default=None) -> Any:
        """
        Get configuration value using dot notation or key path.
        
        Args:
            *keys: Key path (e.g., 'api', 'weather', 'base_url')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        
        Examples:
            config.get('api', 'weather', 'base_url')
            config.get('logging', 'level', default='INFO')
        """
        current = self._config_data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent (lowercase with underscores)
        
        Returns:
            Agent configuration dictionary
        """
        return self.get('agents', agent_name, default={})
    
    def get_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        Get workflow definition.
        
        Args:
            workflow_name: Name of the workflow
        
        Returns:
            Workflow configuration dictionary
        """
        workflow = self.get('workflows', workflow_name)
        if workflow is None:
            raise ConfigurationError(
                f"Workflow '{workflow_name}' not found in configuration",
                config_key=f"workflows.{workflow_name}"
            )
        return workflow
    
    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all defined workflows."""
        return self.get('workflows', default={})
    
    def reload(self, config_path: Optional[str] = None):
        """Reload configuration from file."""
        self._initialized = False
        self.__init__(config_path)
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        return self._config_data.copy()
