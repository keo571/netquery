"""
Enhanced configuration management with versioning, validation, and hot-reloading.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import threading
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydantic import BaseModel, Field, validator
from .config import TextToSQLConfig

logger = logging.getLogger(__name__)

CONFIG_VERSION = "1.0.0"


class ConfigMetadata(BaseModel):
    """Configuration metadata."""
    version: str = Field(default=CONFIG_VERSION, description="Config schema version")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_modified: str = Field(default_factory=lambda: datetime.now().isoformat())
    environment: str = Field(default="development", description="Environment name")


class EnhancedTextToSQLConfig(TextToSQLConfig):
    """Enhanced configuration with metadata and validation."""
    metadata: ConfigMetadata = Field(default_factory=ConfigMetadata)
    
    @validator('database')
    def validate_database(cls, v):
        """Validate database configuration."""
        if not v.database_url:
            raise ValueError("Database URL is required")
        return v
    
    @validator('llm')
    def validate_llm(cls, v):
        """Validate LLM configuration."""
        if v.temperature < 0 or v.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        if v.max_tokens < 100:
            raise ValueError("Max tokens must be at least 100")
        return v
    
    @validator('safety')
    def validate_safety(cls, v):
        """Validate safety configuration."""
        if v.max_result_rows < 1:
            raise ValueError("Max result rows must be at least 1")
        if v.max_query_length < 100:
            raise ValueError("Max query length must be at least 100")
        return v


class ConfigManager:
    """
    Configuration manager with hot-reloading and versioning support.
    """
    
    def __init__(self, config_path: Optional[Path] = None, enable_hot_reload: bool = False):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
            enable_hot_reload: Enable automatic config reloading
        """
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[EnhancedTextToSQLConfig] = None
        self._lock = threading.RLock()
        self._observer: Optional[Observer] = None
        self._callbacks = []
        
        # Load initial configuration
        self.reload_config()
        
        # Setup hot-reloading if enabled
        if enable_hot_reload and self.config_path and self.config_path.exists():
            self._setup_hot_reload()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in standard locations."""
        # Search order: environment variable, current dir, parent dirs, home dir
        locations = [
            os.getenv('TEXT_TO_SQL_CONFIG'),
            Path.cwd() / 'config.yaml',
            Path.cwd() / 'config.json',
            Path.cwd() / '.text_to_sql.yaml',
            Path.home() / '.text_to_sql' / 'config.yaml',
        ]
        
        for location in locations:
            if location and Path(location).exists():
                return Path(location)
        
        return None
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        with self._lock:
            if self.config_path and self.config_path.exists():
                logger.info(f"Loading configuration from {self.config_path}")
                
                # Load config based on file extension
                if self.config_path.suffix == '.yaml' or self.config_path.suffix == '.yml':
                    with open(self.config_path, 'r') as f:
                        config_data = yaml.safe_load(f)
                elif self.config_path.suffix == '.json':
                    with open(self.config_path, 'r') as f:
                        config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")
                
                # Validate and migrate if necessary
                config_data = self._migrate_config(config_data)
                
                # Create config object
                self._config = EnhancedTextToSQLConfig(**config_data)
            else:
                logger.info("Using default configuration")
                self._config = EnhancedTextToSQLConfig()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(self._config)
                except Exception as e:
                    logger.error(f"Error in config reload callback: {e}")
    
    def _migrate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate configuration to current version if needed.
        
        Args:
            config_data: Raw configuration data
            
        Returns:
            Migrated configuration data
        """
        metadata = config_data.get('metadata', {})
        current_version = metadata.get('version', '0.0.0')
        
        if current_version != CONFIG_VERSION:
            logger.info(f"Migrating config from {current_version} to {CONFIG_VERSION}")
            
            # Add migration logic here for different versions
            if current_version < '1.0.0':
                # Example migration: add new fields with defaults
                if 'agent' in config_data and 'complexity_analysis' not in config_data['agent']:
                    config_data['agent']['complexity_analysis'] = True
            
            # Update version
            config_data['metadata'] = config_data.get('metadata', {})
            config_data['metadata']['version'] = CONFIG_VERSION
            config_data['metadata']['last_modified'] = datetime.now().isoformat()
        
        return config_data
    
    def _setup_hot_reload(self) -> None:
        """Setup file watcher for hot-reloading."""
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, manager):
                self.manager = manager
            
            def on_modified(self, event):
                if not event.is_directory and Path(event.src_path) == self.manager.config_path:
                    logger.info(f"Config file modified: {event.src_path}")
                    self.manager.reload_config()
        
        self._observer = Observer()
        handler = ConfigFileHandler(self)
        self._observer.schedule(handler, str(self.config_path.parent), recursive=False)
        self._observer.start()
        logger.info(f"Hot-reloading enabled for {self.config_path}")
    
    def register_reload_callback(self, callback) -> None:
        """
        Register a callback to be called when config is reloaded.
        
        Args:
            callback: Function to call with new config
        """
        self._callbacks.append(callback)
    
    def save_config(self, path: Optional[Path] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            path: Path to save configuration to
        """
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No path specified for saving configuration")
        
        with self._lock:
            config_dict = self._config.dict()
            config_dict['metadata']['last_modified'] = datetime.now().isoformat()
            
            if save_path.suffix in ['.yaml', '.yml']:
                with open(save_path, 'w') as f:
                    yaml.safe_dump(config_dict, f, default_flow_style=False)
            elif save_path.suffix == '.json':
                with open(save_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
            else:
                raise ValueError(f"Unsupported config file format: {save_path.suffix}")
            
            logger.info(f"Configuration saved to {save_path}")
    
    def get_config(self) -> EnhancedTextToSQLConfig:
        """Get current configuration."""
        with self._lock:
            return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
        """
        with self._lock:
            config_dict = self._config.dict()
            
            # Deep merge updates
            def deep_merge(base, updates):
                for key, value in updates.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
            
            deep_merge(config_dict, updates)
            config_dict['metadata']['last_modified'] = datetime.now().isoformat()
            
            # Recreate config with validation
            self._config = EnhancedTextToSQLConfig(**config_dict)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(self._config)
                except Exception as e:
                    logger.error(f"Error in config update callback: {e}")
    
    def get_environment_config(self, env: str) -> Dict[str, Any]:
        """
        Get environment-specific configuration.
        
        Args:
            env: Environment name (development, staging, production)
            
        Returns:
            Environment-specific configuration
        """
        env_config_path = self.config_path.parent / f"config.{env}.yaml"
        if env_config_path.exists():
            with open(env_config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def validate_config(self) -> bool:
        """
        Validate current configuration.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Pydantic validation happens automatically
            _ = self._config.dict()
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Path] = None, enable_hot_reload: bool = False) -> ConfigManager:
    """
    Get or create global config manager instance.
    
    Args:
        config_path: Path to configuration file
        enable_hot_reload: Enable automatic config reloading
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path, enable_hot_reload)
    return _config_manager


# Convenience function to get config
def get_config() -> EnhancedTextToSQLConfig:
    """Get current configuration."""
    return get_config_manager().get_config()