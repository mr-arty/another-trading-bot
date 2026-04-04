"""Strategy configuration loading and validation."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


logger = logging.getLogger(__name__)


@dataclass
class IndicatorConfig:
    """Configuration for a technical indicator."""
    type: str  # 'rsi' or 'ema'
    timeframe: str
    period: int
    # RSI-specific fields
    oversold: Optional[float] = None
    overbought: Optional[float] = None


@dataclass
class EntryCondition:
    """Configuration for an entry condition."""
    type: str  # 'less_than', 'greater_than', 'cross_above', 'cross_below'
    indicator: Optional[str] = None  # For less_than, greater_than
    indicator1: Optional[str] = None  # For cross_above, cross_below
    indicator2: Optional[str] = None  # For cross_above, cross_below
    value: Optional[float] = None  # For less_than, greater_than
    description: Optional[str] = None


@dataclass
class ExitCondition:
    """Configuration for an exit condition."""
    type: str  # 'take_profit', 'stop_loss', 'time_exceeds', 'support_resistance', 'end_of_day'
    percent: Optional[float] = None  # For take_profit, stop_loss
    seconds: Optional[int] = None  # For time_exceeds
    price: Optional[float] = None  # For support_resistance
    direction: Optional[str] = None  # For support_resistance: 'above' or 'below'
    time_utc: Optional[str] = None  # For end_of_day: HH:MM format
    description: Optional[str] = None


@dataclass
class RiskParameters:
    """Risk management parameters for a strategy."""
    max_trades_per_day: Optional[int] = None
    cooldown_after_loss: Optional[int] = None  # seconds


@dataclass
class StrategyConfig:
    """Complete strategy configuration loaded from YAML."""
    name: str
    symbol: str
    timeframes: List[str]
    indicators: Dict[str, IndicatorConfig]
    entry_conditions: List[EntryCondition] = field(default_factory=list)
    exit_conditions: List[ExitCondition] = field(default_factory=list)
    position_size: float = 0.0
    max_position_size: float = 0.0
    risk_parameters: Optional[RiskParameters] = None
    position_direction: str = "long"  # 'long' or 'short'
    strategy_type: Optional[str] = None  # Optional: 'test' for testing mode
    
    # Support/Resistance levels for range trading
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    level_proximity_percent: float = 0.5
    
    def __post_init__(self):
        """Validate strategy configuration after initialization."""
        self._validate()
        self._validate_support_resistance_levels()
    
    def _validate(self):
        """Validate strategy configuration."""
        errors = []
        
        # Validate required fields
        if not self.name:
            errors.append("Strategy name is required")
        if not self.symbol:
            errors.append("Symbol is required")
        if not self.timeframes:
            errors.append("At least one timeframe is required")
        if not self.indicators:
            errors.append("At least one indicator is required")
        
        # Check if this is a test strategy FIRST
        is_test_strategy = self.strategy_type == "test"
        
        if is_test_strategy:
            # Test strategies: entry/exit conditions and position sizes are optional
            # Set defaults if not provided
            if not self.entry_conditions:
                self.entry_conditions = []
            if not self.exit_conditions:
                self.exit_conditions = []
            if self.position_size <= 0:
                self.position_size = 0.0
            if self.max_position_size <= 0:
                self.max_position_size = 0.0
        else:
            # Regular strategies require entry/exit conditions and position sizes
            if not self.entry_conditions:
                errors.append("At least one entry condition is required")
            if not self.exit_conditions:
                errors.append("At least one exit condition is required")
            
            # Validate position sizes
            if self.position_size <= 0:
                errors.append("position_size must be positive")
            if self.max_position_size <= 0:
                errors.append("max_position_size must be positive")
            if self.position_size > self.max_position_size:
                errors.append("position_size cannot exceed max_position_size")
            
            # Validate position direction
            if self.position_direction not in ["long", "short"]:
                errors.append(f"position_direction must be 'long' or 'short', got '{self.position_direction}'")
        
        # Validate timeframes
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for tf in self.timeframes:
            if tf not in valid_timeframes:
                errors.append(f"Invalid timeframe '{tf}'. Must be one of {valid_timeframes}")
        
        # Validate indicators
        for name, indicator in self.indicators.items():
            indicator_errors = self._validate_indicator(name, indicator)
            errors.extend(indicator_errors)
        
        # Only validate entry/exit conditions for non-test strategies
        if not is_test_strategy:
            # Validate entry conditions
            for i, condition in enumerate(self.entry_conditions):
                condition_errors = self._validate_entry_condition(i, condition)
                errors.extend(condition_errors)
            
            # Validate exit conditions
            for i, condition in enumerate(self.exit_conditions):
                condition_errors = self._validate_exit_condition(i, condition)
                errors.extend(condition_errors)
        
        if errors:
            error_message = f"Strategy '{self.name}' validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_message)
    
    def _validate_indicator(self, name: str, indicator: IndicatorConfig) -> List[str]:
        """Validate an indicator configuration."""
        errors = []
        
        # Validate indicator type
        valid_types = ["rsi", "ema"]
        if indicator.type not in valid_types:
            errors.append(f"Indicator '{name}': type must be one of {valid_types}")
        
        # Validate timeframe
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        if indicator.timeframe not in valid_timeframes:
            errors.append(f"Indicator '{name}': timeframe must be one of {valid_timeframes}")
        
        # Validate period
        if indicator.period <= 0:
            errors.append(f"Indicator '{name}': period must be positive")
        
        # Validate RSI-specific fields
        if indicator.type == "rsi":
            if indicator.oversold is not None and (indicator.oversold < 0 or indicator.oversold > 100):
                errors.append(f"Indicator '{name}': oversold must be between 0 and 100")
            if indicator.overbought is not None and (indicator.overbought < 0 or indicator.overbought > 100):
                errors.append(f"Indicator '{name}': overbought must be between 0 and 100")
        
        return errors
    
    def _validate_entry_condition(self, index: int, condition: EntryCondition) -> List[str]:
        """Validate an entry condition."""
        errors = []
        
        valid_types = ["less_than", "greater_than", "cross_above", "cross_below"]
        if condition.type not in valid_types:
            errors.append(f"Entry condition {index}: type must be one of {valid_types}")
            return errors
        
        # Validate comparison conditions
        if condition.type in ["less_than", "greater_than"]:
            if not condition.indicator:
                errors.append(f"Entry condition {index}: 'indicator' is required for {condition.type}")
            elif condition.indicator not in self.indicators:
                errors.append(f"Entry condition {index}: indicator '{condition.indicator}' not defined")
            if condition.value is None:
                errors.append(f"Entry condition {index}: 'value' is required for {condition.type}")
        
        # Validate cross conditions
        if condition.type in ["cross_above", "cross_below"]:
            if not condition.indicator1:
                errors.append(f"Entry condition {index}: 'indicator1' is required for {condition.type}")
            elif condition.indicator1 not in self.indicators:
                errors.append(f"Entry condition {index}: indicator1 '{condition.indicator1}' not defined")
            if not condition.indicator2:
                errors.append(f"Entry condition {index}: 'indicator2' is required for {condition.type}")
            elif condition.indicator2 not in self.indicators:
                errors.append(f"Entry condition {index}: indicator2 '{condition.indicator2}' not defined")
        
        return errors
    
    def _validate_exit_condition(self, index: int, condition: ExitCondition) -> List[str]:
        """Validate an exit condition."""
        errors = []
        
        valid_types = ["take_profit", "stop_loss", "time_exceeds", "support_resistance", "end_of_day"]
        if condition.type not in valid_types:
            errors.append(f"Exit condition {index}: type must be one of {valid_types}")
            return errors
        
        # Validate take_profit and stop_loss
        if condition.type in ["take_profit", "stop_loss"]:
            if condition.percent is None:
                errors.append(f"Exit condition {index}: 'percent' is required for {condition.type}")
            elif condition.percent <= 0:
                errors.append(f"Exit condition {index}: 'percent' must be positive")
        
        # Validate time_exceeds
        if condition.type == "time_exceeds":
            if condition.seconds is None:
                errors.append(f"Exit condition {index}: 'seconds' is required for time_exceeds")
            elif condition.seconds <= 0:
                errors.append(f"Exit condition {index}: 'seconds' must be positive")
        
        # Validate support_resistance
        if condition.type == "support_resistance":
            if condition.price is None:
                errors.append(f"Exit condition {index}: 'price' is required for support_resistance")
            elif condition.price <= 0:
                errors.append(f"Exit condition {index}: 'price' must be positive")
            if condition.direction not in ["above", "below"]:
                errors.append(f"Exit condition {index}: 'direction' must be 'above' or 'below'")
        
        # Validate end_of_day
        if condition.type == "end_of_day":
            if not condition.time_utc:
                errors.append(f"Exit condition {index}: 'time_utc' is required for end_of_day")
            else:
                # Validate time format HH:MM
                try:
                    parts = condition.time_utc.split(":")
                    if len(parts) != 2:
                        raise ValueError()
                    hour, minute = int(parts[0]), int(parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError()
                except (ValueError, AttributeError):
                    errors.append(f"Exit condition {index}: 'time_utc' must be in HH:MM format")
        
        return errors

    def _validate_support_resistance_levels(self):
        """Validate support/resistance levels if defined."""
        # Only validate if both levels are defined
        if self.support_level is not None and self.resistance_level is not None:
            # Both must be positive
            if self.support_level <= 0:
                raise ValueError(f"support_level must be positive, got {self.support_level}")
            if self.resistance_level <= 0:
                raise ValueError(f"resistance_level must be positive, got {self.resistance_level}")

            # Resistance must be greater than support
            if self.resistance_level <= self.support_level:
                raise ValueError(
                    f"resistance_level ({self.resistance_level}) must be greater than "
                    f"support_level ({self.support_level})"
                )

            # Calculate range width
            range_width_percent = ((self.resistance_level - self.support_level) /
                                   self.support_level * 100)

            # Warn if range is too narrow
            if range_width_percent < 1.0:
                logger.warning(
                    f"narrow_range_detected: support={self.support_level}, "
                    f"resistance={self.resistance_level}, "
                    f"range_width_percent={range_width_percent:.2f}. "
                    f"Range width < 1% may result in frequent false signals"
                )

            # Warn if range is too wide
            if range_width_percent > 20.0:
                logger.warning(
                    f"wide_range_detected: support={self.support_level}, "
                    f"resistance={self.resistance_level}, "
                    f"range_width_percent={range_width_percent:.2f}. "
                    f"Range width > 20% may not be suitable for range trading"
                )

            # Log mid-range calculation
            mid_range = (self.support_level + self.resistance_level) / 2
            logger.info(
                f"range_levels_configured: support={self.support_level}, "
                f"resistance={self.resistance_level}, "
                f"mid_range={mid_range}, "
                f"range_width_percent={range_width_percent:.2f}"
            )

        # Validate proximity percent
        if self.level_proximity_percent < 0.1 or self.level_proximity_percent > 5.0:
            raise ValueError(
                f"level_proximity_percent must be between 0.1 and 5.0, "
                f"got {self.level_proximity_percent}"
            )



def load_strategy_from_yaml(file_path: Path) -> StrategyConfig:
    """
    Load and parse a strategy configuration from a YAML file.
    
    Args:
        file_path: Path to the YAML strategy file
        
    Returns:
        StrategyConfig: Parsed and validated strategy configuration
        
    Raises:
        ValueError: If the YAML is invalid or validation fails
        FileNotFoundError: If the file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file {file_path}: {e}")
        raise ValueError(f"Invalid YAML syntax in {file_path}: {e}")
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise
    
    if not isinstance(data, dict):
        raise ValueError(f"Strategy file {file_path} must contain a YAML dictionary")
    
    try:
        # Parse indicators
        indicators = {}
        indicators_data = data.get("indicators", {})
        for name, indicator_data in indicators_data.items():
            indicators[name] = IndicatorConfig(
                type=indicator_data.get("type"),
                timeframe=indicator_data.get("timeframe"),
                period=indicator_data.get("period"),
                oversold=indicator_data.get("oversold"),
                overbought=indicator_data.get("overbought")
            )
        
        # Parse entry conditions
        entry_conditions = []
        for condition_data in data.get("entry_conditions", []):
            entry_conditions.append(EntryCondition(
                type=condition_data.get("type"),
                indicator=condition_data.get("indicator"),
                indicator1=condition_data.get("indicator1"),
                indicator2=condition_data.get("indicator2"),
                value=condition_data.get("value"),
                description=condition_data.get("description")
            ))
        
        # Parse exit conditions
        exit_conditions = []
        for condition_data in data.get("exit_conditions", []):
            exit_conditions.append(ExitCondition(
                type=condition_data.get("type"),
                percent=condition_data.get("percent"),
                seconds=condition_data.get("seconds"),
                price=condition_data.get("price"),
                direction=condition_data.get("direction"),
                time_utc=condition_data.get("time_utc"),
                description=condition_data.get("description")
            ))
        
        # Parse risk parameters if present
        risk_parameters = None
        if "risk_parameters" in data:
            risk_data = data["risk_parameters"]
            risk_parameters = RiskParameters(
                max_trades_per_day=risk_data.get("max_trades_per_day"),
                cooldown_after_loss=risk_data.get("cooldown_after_loss")
            )
        
        # Create strategy config
        strategy = StrategyConfig(
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            timeframes=data.get("timeframes", []),
            indicators=indicators,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            position_size=data.get("position_size", 0.0),
            max_position_size=data.get("max_position_size", 0.0),
            risk_parameters=risk_parameters,
            position_direction=data.get("position_direction", "long"),
            strategy_type=data.get("strategy_type")
        )
        
        logger.info(f"Successfully loaded strategy '{strategy.name}' from {file_path}")
        return strategy
        
    except (KeyError, TypeError, AttributeError) as e:
        logger.error(f"Failed to parse strategy from {file_path}: {e}")
        raise ValueError(f"Invalid strategy structure in {file_path}: {e}")
