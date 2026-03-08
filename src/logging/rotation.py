"""Log rotation monitoring and management."""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class LogRotationMonitor:
    """Monitor and manage log file rotation."""
    
    def __init__(
        self,
        log_file: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5
    ):
        """
        Initialize log rotation monitor.
        
        Args:
            log_file: Path to the log file
            max_bytes: Maximum size before rotation
            backup_count: Number of backup files to keep
        """
        self.log_file = Path(log_file)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handler: Optional[logging.handlers.RotatingFileHandler] = None
    
    def get_current_size(self) -> int:
        """
        Get current log file size in bytes.
        
        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        if self.log_file.exists():
            return self.log_file.stat().st_size
        return 0
    
    def should_rotate(self) -> bool:
        """
        Check if log file should be rotated.
        
        Returns:
            True if file size exceeds max_bytes
        """
        return self.get_current_size() >= self.max_bytes
    
    def rotate_logs(self) -> None:
        """
        Manually trigger log rotation.
        
        This method rotates the log file by renaming it with a numeric suffix
        and creating a new empty log file.
        """
        if not self.log_file.exists():
            return
        
        # Rotate existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            old_file = Path(f"{self.log_file}.{i}")
            new_file = Path(f"{self.log_file}.{i + 1}")
            
            if old_file.exists():
                if new_file.exists():
                    new_file.unlink()
                old_file.rename(new_file)
        
        # Rotate current log file to .1
        backup_file = Path(f"{self.log_file}.1")
        if backup_file.exists():
            backup_file.unlink()
        self.log_file.rename(backup_file)
        
        # Create new empty log file
        self.log_file.touch()
    
    def get_rotation_info(self) -> dict:
        """
        Get information about log rotation status.
        
        Returns:
            Dictionary with rotation status information
        """
        current_size = self.get_current_size()
        return {
            'log_file': str(self.log_file),
            'current_size': current_size,
            'max_bytes': self.max_bytes,
            'backup_count': self.backup_count,
            'should_rotate': self.should_rotate(),
            'usage_percent': (current_size / self.max_bytes * 100) if self.max_bytes > 0 else 0
        }
    
    def cleanup_old_logs(self) -> int:
        """
        Remove log files beyond the backup count.
        
        Returns:
            Number of files removed
        """
        removed = 0
        for i in range(self.backup_count + 1, 100):  # Check up to 100 backups
            backup_file = Path(f"{self.log_file}.{i}")
            if backup_file.exists():
                backup_file.unlink()
                removed += 1
            else:
                break
        return removed
