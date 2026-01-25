"""Strategy directory loading and management."""

import logging
from pathlib import Path
from typing import Dict, List

from .config import StrategyConfig, load_strategy_from_yaml


logger = logging.getLogger(__name__)


class StrategyLoader:
    """Loads and manages strategy configurations from a directory."""
    
    def __init__(self):
        """Initialize the strategy loader."""
        self.strategies: Dict[str, StrategyConfig] = {}
    
    async def load_strategies_from_directory(self, directory: str) -> Dict[str, StrategyConfig]:
        """
        Load all YAML strategy files from a directory.
        
        Args:
            directory: Path to directory containing strategy YAML files
            
        Returns:
            Dict mapping strategy names to StrategyConfig objects
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.error(f"Strategy directory does not exist: {directory}")
            return {}
        
        if not directory_path.is_dir():
            logger.error(f"Strategy path is not a directory: {directory}")
            return {}
        
        # Find all YAML files in the directory
        yaml_files = list(directory_path.glob("*.yaml")) + list(directory_path.glob("*.yml"))
        
        if not yaml_files:
            logger.warning(f"No YAML files found in strategy directory: {directory}")
            return {}
        
        logger.info(f"Found {len(yaml_files)} strategy file(s) in {directory}")
        
        loaded_strategies = {}
        
        for yaml_file in yaml_files:
            try:
                strategy = load_strategy_from_yaml(yaml_file)
                
                # Check for duplicate strategy names
                if strategy.name in loaded_strategies:
                    logger.error(
                        f"Duplicate strategy name '{strategy.name}' in file {yaml_file}. "
                        f"Skipping this strategy."
                    )
                    continue
                
                loaded_strategies[strategy.name] = strategy
                logger.info(f"Successfully loaded strategy '{strategy.name}' from {yaml_file.name}")
                
            except FileNotFoundError as e:
                logger.error(f"Strategy file not found: {yaml_file} - {e}")
            except ValueError as e:
                logger.error(f"Invalid strategy in {yaml_file.name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading strategy from {yaml_file.name}: {e}")
        
        self.strategies = loaded_strategies
        logger.info(f"Loaded {len(loaded_strategies)} valid strategy/strategies")
        
        return loaded_strategies
    
    def get_strategy(self, name: str) -> StrategyConfig:
        """
        Get a strategy by name.
        
        Args:
            name: Strategy name
            
        Returns:
            StrategyConfig for the requested strategy
            
        Raises:
            KeyError: If strategy not found
        """
        if name not in self.strategies:
            raise KeyError(f"Strategy '{name}' not found")
        return self.strategies[name]
    
    def get_all_strategies(self) -> Dict[str, StrategyConfig]:
        """
        Get all loaded strategies.
        
        Returns:
            Dict mapping strategy names to StrategyConfig objects
        """
        return self.strategies.copy()
    
    def has_strategy(self, name: str) -> bool:
        """
        Check if a strategy is loaded.
        
        Args:
            name: Strategy name
            
        Returns:
            True if strategy is loaded, False otherwise
        """
        return name in self.strategies
    
    async def reload_strategy(self, file_path: Path) -> bool:
        """
        Reload a single strategy from a file.
        
        Args:
            file_path: Path to the strategy YAML file
            
        Returns:
            True if reload was successful, False otherwise
        """
        try:
            strategy = load_strategy_from_yaml(file_path)
            
            # Update or add the strategy
            old_name = None
            for name, existing_strategy in self.strategies.items():
                # Try to find if this file was previously loaded
                # (This is a simple implementation; in production you might track file paths)
                if name == strategy.name:
                    old_name = name
                    break
            
            self.strategies[strategy.name] = strategy
            
            if old_name and old_name != strategy.name:
                # Strategy was renamed, remove old entry
                del self.strategies[old_name]
                logger.info(f"Strategy renamed from '{old_name}' to '{strategy.name}'")
            elif old_name:
                logger.info(f"Reloaded strategy '{strategy.name}' from {file_path.name}")
            else:
                logger.info(f"Added new strategy '{strategy.name}' from {file_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload strategy from {file_path.name}: {e}")
            return False
    
    async def remove_strategy(self, name: str) -> bool:
        """
        Remove a strategy from the loaded strategies.
        
        Args:
            name: Strategy name to remove
            
        Returns:
            True if strategy was removed, False if not found
        """
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"Removed strategy '{name}'")
            return True
        return False
