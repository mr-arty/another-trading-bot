"""
Database module for SQLite connection management and schema initialization
"""
import aiosqlite
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class Database:
    """Manages SQLite database connection and schema"""
    
    def __init__(self, db_path: str = "data/trading_bot.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[aiosqlite.Connection] = None
        
    async def initialize(self) -> None:
        """
        Initialize database connection and create schema if needed
        """
        # Create data directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.connection = await aiosqlite.connect(str(self.db_path))
        
        # Enable foreign keys
        await self.connection.execute("PRAGMA foreign_keys = ON")
        
        # Create schema
        await self._create_schema()
        
        logger.info(f"Database initialized at {self.db_path}")
        
    async def _create_schema(self) -> None:
        """Create database tables if they don't exist"""
        
        # Positions table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                unrealized_pnl REAL,
                realized_pnl REAL DEFAULT 0,
                status TEXT NOT NULL,
                opened_at TIMESTAMP NOT NULL,
                closed_at TIMESTAMP,
                strategy_name TEXT NOT NULL,
                UNIQUE(symbol, strategy_name, status)
            )
        """)
        
        # Order history table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                filled_quantity REAL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # ATR metrics table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS atr_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                atr_value REAL NOT NULL,
                calculated_at TIMESTAMP NOT NULL
            )
        """)
        
        # Create index for ATR metrics
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_time 
            ON atr_metrics(symbol, calculated_at)
        """)
        
        # Trade log table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS trade_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl REAL,
                pnl_percent REAL,
                opened_at TIMESTAMP NOT NULL,
                closed_at TIMESTAMP,
                exit_reason TEXT
            )
        """)
        
        await self.connection.commit()
        logger.info("Database schema created successfully")
        
    async def get_connection(self) -> aiosqlite.Connection:
        """
        Get database connection
        
        Returns:
            Active database connection
            
        Raises:
            RuntimeError: If database is not initialized
        """
        if self.connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.connection
        
    async def close(self) -> None:
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
