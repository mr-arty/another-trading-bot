"""File system watcher for strategy file changes."""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent


logger = logging.getLogger(__name__)


class StrategyFileHandler(FileSystemEventHandler):
    """Handler for strategy file system events."""
    
    def __init__(self, callback: Callable[[Path, str], None]):
        """
        Initialize the file handler.
        
        Args:
            callback: Async callback function to call when files change.
                     Receives (file_path, event_type) as arguments.
        """
        super().__init__()
        self.callback = callback
        self._loop = asyncio.get_event_loop()
    
    def _is_yaml_file(self, path: str) -> bool:
        """Check if the file is a YAML file."""
        return path.endswith('.yaml') or path.endswith('.yml')
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._is_yaml_file(event.src_path):
            logger.debug(f"Strategy file modified: {event.src_path}")
            asyncio.run_coroutine_threadsafe(
                self.callback(Path(event.src_path), "modified"),
                self._loop
            )
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._is_yaml_file(event.src_path):
            logger.debug(f"Strategy file created: {event.src_path}")
            asyncio.run_coroutine_threadsafe(
                self.callback(Path(event.src_path), "created"),
                self._loop
            )
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._is_yaml_file(event.src_path):
            logger.debug(f"Strategy file deleted: {event.src_path}")
            asyncio.run_coroutine_threadsafe(
                self.callback(Path(event.src_path), "deleted"),
                self._loop
            )


class StrategyWatcher:
    """Watches a directory for strategy file changes and triggers reloads."""
    
    def __init__(self, directory: str, reload_callback: Callable[[Path, str], None]):
        """
        Initialize the strategy watcher.
        
        Args:
            directory: Directory to watch for strategy files
            reload_callback: Async callback to call when files change.
                           Receives (file_path, event_type) as arguments.
        """
        self.directory = Path(directory)
        self.reload_callback = reload_callback
        self.observer: Optional[Observer] = None
        self._running = False
    
    def start(self):
        """Start watching the strategy directory."""
        if self._running:
            logger.warning("Strategy watcher is already running")
            return
        
        if not self.directory.exists():
            logger.error(f"Cannot watch non-existent directory: {self.directory}")
            return
        
        if not self.directory.is_dir():
            logger.error(f"Cannot watch non-directory path: {self.directory}")
            return
        
        # Create and start the observer
        event_handler = StrategyFileHandler(self.reload_callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.directory), recursive=False)
        self.observer.start()
        self._running = True
        
        logger.info(f"Started watching strategy directory: {self.directory}")
    
    def stop(self):
        """Stop watching the strategy directory."""
        if not self._running or not self.observer:
            return
        
        self.observer.stop()
        self.observer.join(timeout=5)
        self._running = False
        self.observer = None
        
        logger.info(f"Stopped watching strategy directory: {self.directory}")
    
    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running


async def watch_strategies(
    directory: str,
    reload_callback: Callable[[Path, str], None]
) -> StrategyWatcher:
    """
    Start watching a directory for strategy file changes.
    
    Args:
        directory: Directory to watch for strategy files
        reload_callback: Async callback to call when files change.
                        Receives (file_path, event_type) as arguments.
    
    Returns:
        StrategyWatcher instance that can be used to stop watching
    """
    watcher = StrategyWatcher(directory, reload_callback)
    watcher.start()
    return watcher
