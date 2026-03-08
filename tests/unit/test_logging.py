"""Unit tests for logging system."""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from src.logging import (
    setup_logging,
    get_logger,
    log_order,
    log_fill,
    log_error,
    log_system_event,
    LogRotationMonitor
)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_setup_logging(temp_log_dir):
    """Test logging system setup."""
    logger = setup_logging(
        log_dir=temp_log_dir,
        log_level="INFO",
        max_bytes=1024,
        backup_count=3,
        json_format=True
    )
    
    assert logger is not None
    log_file = Path(temp_log_dir) / "trading_bot.log"
    assert log_file.exists()


def test_get_logger_auto_initialize():
    """Test get_logger auto-initializes if not set up."""
    # Reset global logger
    import src.logging.logger as logger_module
    logger_module._logger = None
    
    logger = get_logger()
    assert logger is not None


def test_log_order(temp_log_dir):
    """Test order logging."""
    import logging
    setup_logging(log_dir=temp_log_dir, json_format=True)
    
    log_order(
        order_id="TEST-001",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        price=50000.0,
        strategy_id="test-strategy",
        order_type="LIMIT"
    )
    
    # Flush all handlers
    for handler in logging.root.handlers:
        handler.flush()
    
    log_file = Path(temp_log_dir) / "trading_bot.log"
    assert log_file.exists()
    
    content = log_file.read_text()
    assert "order_placed" in content
    assert "TEST-001" in content
    assert "BTCUSDT" in content


def test_log_fill(temp_log_dir):
    """Test fill logging."""
    import logging
    setup_logging(log_dir=temp_log_dir, json_format=True)
    
    log_fill(
        order_id="TEST-002",
        symbol="ETHUSDT",
        side="SELL",
        quantity=1.5,
        price=3200.0,
        strategy_id="test-strategy",
        fill_type="FULL"
    )
    
    # Flush all handlers
    for handler in logging.root.handlers:
        handler.flush()
    
    log_file = Path(temp_log_dir) / "trading_bot.log"
    content = log_file.read_text()
    assert "order_filled" in content
    assert "TEST-002" in content


def test_log_error(temp_log_dir):
    """Test error logging."""
    import logging
    setup_logging(log_dir=temp_log_dir, json_format=True)
    
    log_error(
        "test_error",
        "Test error message",
        component="test"
    )
    
    # Flush all handlers
    for handler in logging.root.handlers:
        handler.flush()
    
    log_file = Path(temp_log_dir) / "trading_bot.log"
    content = log_file.read_text()
    assert "test_error" in content
    assert "Test error message" in content


def test_log_error_with_exception(temp_log_dir):
    """Test error logging with exception."""
    import logging
    setup_logging(log_dir=temp_log_dir, json_format=True)
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_error("exception_test", "Exception occurred", exc_info=e)
    
    # Flush all handlers
    for handler in logging.root.handlers:
        handler.flush()
    
    log_file = Path(temp_log_dir) / "trading_bot.log"
    content = log_file.read_text()
    assert "exception_test" in content
    assert "ValueError" in content


def test_log_system_event(temp_log_dir):
    """Test system event logging."""
    import logging
    setup_logging(log_dir=temp_log_dir, json_format=True)
    
    log_system_event(
        "system_start",
        "System starting",
        version="1.0.0"
    )
    
    # Flush all handlers
    for handler in logging.root.handlers:
        handler.flush()
    
    log_file = Path(temp_log_dir) / "trading_bot.log"
    content = log_file.read_text()
    assert "system_start" in content
    assert "System starting" in content


def test_log_rotation_monitor():
    """Test log rotation monitor."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('x' * 2000)
        temp_file = f.name
    
    try:
        monitor = LogRotationMonitor(temp_file, max_bytes=1000, backup_count=3)
        
        # Check size
        assert monitor.get_current_size() == 2000
        assert monitor.should_rotate() is True
        
        # Get rotation info
        info = monitor.get_rotation_info()
        assert info['current_size'] == 2000
        assert info['max_bytes'] == 1000
        assert info['should_rotate'] is True
        assert info['usage_percent'] == 200.0
        
    finally:
        os.unlink(temp_file)


def test_log_rotation_trigger():
    """Test manual log rotation."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test content')
        temp_file = f.name
    
    try:
        monitor = LogRotationMonitor(temp_file, max_bytes=1000, backup_count=3)
        
        # Rotate logs
        monitor.rotate_logs()
        
        # Check backup exists
        backup_file = f"{temp_file}.1"
        assert os.path.exists(backup_file)
        
        # Check original file is empty
        assert monitor.get_current_size() == 0
        
        # Cleanup
        os.unlink(backup_file)
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_log_rotation_cleanup():
    """Test cleanup of old log files."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name
    
    try:
        # Create extra backup files
        for i in range(1, 10):
            backup = f"{temp_file}.{i}"
            Path(backup).touch()
        
        monitor = LogRotationMonitor(temp_file, max_bytes=1000, backup_count=3)
        removed = monitor.cleanup_old_logs()
        
        # Should remove files beyond backup_count
        assert removed == 6  # Files 4-9
        
        # Check that only backups 1-3 remain
        for i in range(1, 4):
            assert os.path.exists(f"{temp_file}.{i}")
        for i in range(4, 10):
            assert not os.path.exists(f"{temp_file}.{i}")
        
        # Cleanup
        for i in range(1, 4):
            os.unlink(f"{temp_file}.{i}")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
