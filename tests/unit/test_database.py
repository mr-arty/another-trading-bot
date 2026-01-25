"""
Unit tests for database module
"""
import pytest
import aiosqlite
from pathlib import Path
import tempfile
import os

from src.database.db import Database


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        await db.initialize()
        yield db
        await db.close()


@pytest.mark.asyncio
async def test_database_initialization():
    """Test that database initializes and creates schema"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        
        # Initialize database
        await db.initialize()
        
        # Verify database file was created
        assert Path(db_path).exists()
        
        # Verify connection is active
        assert db.connection is not None
        
        # Verify tables were created
        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = await cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        assert "positions" in table_names
        assert "order_history" in table_names
        assert "atr_metrics" in table_names
        assert "trade_log" in table_names
        
        await db.close()


@pytest.mark.asyncio
async def test_positions_table_schema(temp_db):
    """Test positions table has correct schema"""
    conn = await temp_db.get_connection()
    cursor = await conn.execute("PRAGMA table_info(positions)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    expected_columns = [
        "id", "symbol", "quantity", "entry_price", "current_price",
        "unrealized_pnl", "realized_pnl", "status", "opened_at",
        "closed_at", "strategy_name"
    ]
    
    for col in expected_columns:
        assert col in column_names


@pytest.mark.asyncio
async def test_order_history_table_schema(temp_db):
    """Test order_history table has correct schema"""
    conn = await temp_db.get_connection()
    cursor = await conn.execute("PRAGMA table_info(order_history)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    expected_columns = [
        "id", "order_id", "strategy_name", "symbol", "side",
        "order_type", "quantity", "price", "filled_quantity",
        "status", "created_at", "updated_at"
    ]
    
    for col in expected_columns:
        assert col in column_names


@pytest.mark.asyncio
async def test_atr_metrics_table_schema(temp_db):
    """Test atr_metrics table has correct schema"""
    conn = await temp_db.get_connection()
    cursor = await conn.execute("PRAGMA table_info(atr_metrics)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    expected_columns = [
        "id", "symbol", "timeframe", "atr_value", "calculated_at"
    ]
    
    for col in expected_columns:
        assert col in column_names


@pytest.mark.asyncio
async def test_trade_log_table_schema(temp_db):
    """Test trade_log table has correct schema"""
    conn = await temp_db.get_connection()
    cursor = await conn.execute("PRAGMA table_info(trade_log)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    expected_columns = [
        "id", "strategy_name", "symbol", "side", "quantity",
        "entry_price", "exit_price", "pnl", "pnl_percent",
        "opened_at", "closed_at", "exit_reason"
    ]
    
    for col in expected_columns:
        assert col in column_names


@pytest.mark.asyncio
async def test_atr_index_exists(temp_db):
    """Test that index on atr_metrics exists"""
    conn = await temp_db.get_connection()
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_symbol_time'"
    )
    result = await cursor.fetchone()
    
    assert result is not None
    assert result[0] == "idx_symbol_time"


@pytest.mark.asyncio
async def test_get_connection_before_initialize():
    """Test that get_connection raises error if not initialized"""
    db = Database("test.db")
    
    with pytest.raises(RuntimeError, match="Database not initialized"):
        await db.get_connection()


@pytest.mark.asyncio
async def test_close_connection(temp_db):
    """Test that close properly closes the connection"""
    assert temp_db.connection is not None
    
    await temp_db.close()
    
    assert temp_db.connection is None
