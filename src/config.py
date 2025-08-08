"""
Configuration management for K-Means Trading Strategy.

Handles loading and validation of configuration parameters from YAML file
with support for environment variable overrides.
"""

import os
import yaml
from typing import Any, Dict, Optional
import logging

class ConfigManager:
    """
    Manages configuration loading and access for the trading strategy.
    
    Supports YAML configuration files with environment variable overrides
    following a structured hierarchy for different system components.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._apply_env_overrides()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            # Try to load from project root first, then from src directory
            if os.path.exists(self.config_path):
                config_file = self.config_path
            else:
                # Try relative to src directory
                parent_config = os.path.join("..", self.config_path)
                if os.path.exists(parent_config):
                    config_file = parent_config
                else:
                    raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                
        except FileNotFoundError:
            logging.warning(f"Config file {self.config_path} not found. Using defaults.")
            self.config = self._get_default_config()
        except yaml.YAMLError as e:
            logging.error(f"Error parsing config file: {e}")
            raise
            
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_prefix = self.config.get('environment_overrides', {}).get('prefix', 'KMEANS_')
        
        # Common environment variable mappings
        env_mappings = {
            f'{env_prefix}IB_HOST': ['interactive_brokers', 'connection', 'host'],
            f'{env_prefix}IB_PORT': ['interactive_brokers', 'connection', 'port'],
            f'{env_prefix}WS_HOST': ['websocket_server', 'host'],
            f'{env_prefix}WS_PORT': ['websocket_server', 'port'],
            f'{env_prefix}LOG_LEVEL': ['logging', 'level'],
            f'{env_prefix}DEBUG': ['development', 'debug_mode'],
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_config(config_path, os.environ[env_var])
                
    def _set_nested_config(self, path: list, value: str) -> None:
        """Set nested configuration value from list of keys."""
        current = self.config
        for key in path[:-1]:
            current = current.setdefault(key, {})
        
        # Convert string values to appropriate types
        if value.lower() in ['true', 'false']:
            current[path[-1]] = value.lower() == 'true'
        elif value.isdigit():
            current[path[-1]] = int(value)
        elif value.replace('.', '').isdigit():
            current[path[-1]] = float(value)
        else:
            current[path[-1]] = value
            
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get configuration value by key path.
        
        Args:
            *keys: Nested keys to traverse (e.g., 'strategy', 'clustering', 'max_clusters')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
        
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy-specific configuration."""
        return self.get('strategy', default={})
        
    def get_ib_config(self) -> Dict[str, Any]:
        """Get Interactive Brokers configuration."""
        return self.get('interactive_brokers', default={})
        
    def get_websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket server configuration."""
        return self.get('websocket_server', default={})
        
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', default={})
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file not found."""
        return {
            'strategy': {
                'min_data_points': 30,
                'clustering': {
                    'max_clusters': 10,
                    'init_method': 'k-means++',
                    'random_state': 42,
                    'n_init': 10
                },
                'sectors': {
                    'epsilon_factor': 0.01,
                    'threshold_factor': 0.3
                }
            },
            'interactive_brokers': {
                'connection': {
                    'host': '127.0.0.1',
                    'port': 7497,
                    'client_id': 1
                },
                'data_request': {
                    'default_duration': '1 M',
                    'default_bar_size': '1 day',
                    'default_rth': True,
                    'request_timeout': 50
                }
            },
            'websocket_server': {
                'host': 'localhost',
                'port': 8765
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            }
        }

# Global configuration instance
config = ConfigManager()

# Convenience functions for common configuration access
def get_strategy_min_data_points() -> int:
    """Get minimum data points required for strategy analysis."""
    return config.get('strategy', 'min_data_points', default=30)

def get_clustering_params() -> Dict[str, Any]:
    """Get K-means clustering parameters."""
    return config.get('strategy', 'clustering', default={})

def get_sector_params() -> Dict[str, Any]:
    """Get sector analysis parameters."""
    return config.get('strategy', 'sectors', default={})

def get_ib_connection_params() -> Dict[str, Any]:
    """Get Interactive Brokers connection parameters."""
    return config.get('interactive_brokers', 'connection', default={})

def get_websocket_params() -> Dict[str, Any]:
    """Get WebSocket server parameters."""
    return config.get('websocket_server', default={})