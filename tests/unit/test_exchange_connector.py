"""Unit tests for Exchange Connector."""

import pytest
import asyncio
from datetime import datetime
from src.exchange.connector import (
    ExchangeConnector,
    TokenBucket,
    OrderSide,
    OrderType,
    MarketData,
)


class TestTokenBucket:
    """Test token bucket rate limiting."""
    
    @pytest.mark.asyncio
    async def test_token_bucket_allows_requests_within_limit(self):
        """Test that token bucket allows requests within rate limit."""
        bucket = TokenBucket(rate=10, capacity=10)
        
        # Should be able to acquire 10 tokens immediately
        start = asyncio.get_event_loop().time()
        for _ in range(10):
            await bucket.acquire(1)
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should complete almost instantly
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_token_bucket_delays_when_limit_exceeded(self):
        """Test that token bucket delays requests when limit exceeded."""
        bucket = TokenBucket(rate=10, capacity=10)
        
        # Exhaust all tokens
        for _ in range(10):
            await bucket.acquire(1)
        
        # Next request should wait
        start = asyncio.get_event_loop().time()
        await bucket.acquire(1)
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should wait approximately 0.1 seconds (1/10 rate)
        assert elapsed >= 0.09  # Allow small margin


class TestExchangeConnector:
    """Test Exchange Connector initialization and basic functionality."""
    
    def test_connector_initialization(self):
        """Test that connector initializes with correct parameters."""
        connector = ExchangeConnector(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
            rate_limit_per_second=10,
            max_reconnect_delay=60
        )
        
        assert connector.api_key == "test_key"
        assert connector.api_secret == "test_secret"
        assert connector.testnet is True
        assert connector.max_reconnect_delay == 60
        assert connector.rate_limiter is not None
    
    def test_connector_starts_disconnected(self):
        """Test that connector starts in disconnected state."""
        connector = ExchangeConnector(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert connector._connected is False
        assert connector._reconnecting is False
    
    @pytest.mark.asyncio
    async def test_error_callback_registration(self):
        """Test that error callbacks can be registered."""
        connector = ExchangeConnector(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        errors_received = []
        
        async def error_handler(operation: str, error: Exception):
            errors_received.append((operation, error))
        
        connector.register_error_callback(error_handler)
        
        # Trigger an error notification
        test_error = Exception("Test error")
        await connector._notify_error("test_operation", test_error)
        
        assert len(errors_received) == 1
        assert errors_received[0][0] == "test_operation"
        assert errors_received[0][1] == test_error


class TestMarketData:
    """Test MarketData dataclass."""
    
    def test_market_data_creation(self):
        """Test that MarketData can be created with valid data."""
        now = datetime.now()
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=now,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        assert data.symbol == "BTCUSDT"
        assert data.timestamp == now
        assert data.open == 50000.0
        assert data.high == 51000.0
        assert data.low == 49000.0
        assert data.close == 50500.0
        assert data.volume == 1000.0
