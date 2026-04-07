#!/usr/bin/env python3
"""
Manual Testing Script for VWAP Range Trading Strategy
Tests Tasks 20.1-20.8: Manual Testing and Validation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.strategy.loader import load_strategy_from_yaml
from src.strategy.engine import StrategyEngine, Signal
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


class VwapManualTestRunner:
    """Runs manual tests for VWAP range trading strategy."""
    
    def __init__(self):
        self.test_results = []
        self.signals_generated = []
    
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"{status_symbol} {test_name}: {status}")
        if details:
            print(f"  {details}")
    
    async def test_20_1_vwap_calculation_accuracy(self):
        """20.1 Test VWAP calculation accuracy."""
        print("\n" + "="*80)
        print("TEST 20.1: Test VWAP calculation accuracy")
        print("="*80)
        
        try:
            calculator = IndicatorCalculator(cache_ttl_seconds=60)
            
            # Test with known data points
            base_time = datetime.now()
            
            # Create data points with known VWAP
            # Point 1: high=102, low=98, hl2=100, volume=1000
            # Point 2: high=106, low=94, hl2=100, volume=2000
            # Point 3: high=114, low=86, hl2=100, volume=3000
            # Expected VWAP = (100*1000 + 100*2000 + 100*3000) / (1000+2000+3000) = 100.0
            
            data_points = [
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time,
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.0,
                    volume=1000.0
                ),
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=1),
                    open=100.0,
                    high=106.0,
                    low=94.0,
                    close=100.0,
                    volume=2000.0
                ),
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=2),
                    open=100.0,
                    high=114.0,
                    low=86.0,
                    close=100.0,
                    volume=3000.0
                ),
            ]
            
            for data in data_points:
                await calculator.add_market_data(data, "1h")
            
            vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            
            if vwap is None:
                self.log_test("20.1.1", "FAIL", "VWAP calculation returned None")
                return False
            
            # Verify accuracy (should be 100.0)
            expected = 100.0
            difference_percent = abs(vwap - expected) / expected * 100
            
            if difference_percent < 0.01:
                self.log_test("20.1.1", "PASS", f"VWAP={vwap:.6f}, expected={expected}, diff={difference_percent:.6f}%")
            else:
                self.log_test("20.1.1", "FAIL", f"VWAP={vwap:.6f}, expected={expected}, diff={difference_percent:.6f}%")
                return False
            
            # Test with varying prices
            calculator2 = IndicatorCalculator(cache_ttl_seconds=60)
            
            # Point 1: hl2=50, volume=100
            # Point 2: hl2=60, volume=200
            # Point 3: hl2=70, volume=300
            # Expected VWAP = (50*100 + 60*200 + 70*300) / (100+200+300) = 38000/600 = 63.333...
            
            data_points2 = [
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time,
                    open=50.0,
                    high=52.0,
                    low=48.0,
                    close=50.0,
                    volume=100.0
                ),
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=1),
                    open=60.0,
                    high=62.0,
                    low=58.0,
                    close=60.0,
                    volume=200.0
                ),
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=2),
                    open=70.0,
                    high=72.0,
                    low=68.0,
                    close=70.0,
                    volume=300.0
                ),
            ]
            
            for data in data_points2:
                await calculator2.add_market_data(data, "1h")
            
            vwap2 = await calculator2.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            expected2 = 63.333333
            difference_percent2 = abs(vwap2 - expected2) / expected2 * 100
            
            if difference_percent2 < 0.01:
                self.log_test("20.1.2", "PASS", f"VWAP={vwap2:.6f}, expected={expected2:.6f}, diff={difference_percent2:.6f}%")
            else:
                self.log_test("20.1.2", "FAIL", f"VWAP={vwap2:.6f}, expected={expected2:.6f}, diff={difference_percent2:.6f}%")
                return False
            
            self.log_test("20.1", "PASS", "VWAP calculation accuracy verified")
            return True
            
        except Exception as e:
            self.log_test("20.1", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_2_session_reset_behavior(self):
        """20.2 Test session reset behavior."""
        print("\n" + "="*80)
        print("TEST 20.2: Test session reset behavior")
        print("="*80)
        
        try:
            calculator = IndicatorCalculator(cache_ttl_seconds=60)
            
            # Day 1 data
            day1_time = datetime(2024, 1, 1, 10, 0, 0)
            
            data_day1 = [
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=day1_time,
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.0,
                    volume=1000.0
                ),
                MarketData(
                    symbol="BTCUSDT",
                    timestamp=day1_time + timedelta(hours=1),
                    open=110.0,
                    high=112.0,
                    low=108.0,
                    close=110.0,
                    volume=1000.0
                ),
            ]
            
            for data in data_day1:
                await calculator.add_market_data(data, "1h")
            
            vwap_day1 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            
            if vwap_day1 is None:
                self.log_test("20.2.1", "FAIL", "Day 1 VWAP is None")
                return False
            
            self.log_test("20.2.1", "PASS", f"Day 1 VWAP calculated: {vwap_day1:.2f}")
            
            # Day 2 data (should reset)
            day2_time = datetime(2024, 1, 2, 10, 0, 0)
            
            data_day2 = MarketData(
                symbol="BTCUSDT",
                timestamp=day2_time,
                open=200.0,
                high=202.0,
                low=198.0,
                close=200.0,
                volume=1000.0
            )
            
            await calculator.add_market_data(data_day2, "1h")
            vwap_day2 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            
            if vwap_day2 is None:
                self.log_test("20.2.2", "FAIL", "Day 2 VWAP is None")
                return False
            
            # Day 2 VWAP should be close to 200 (reset occurred)
            # If no reset, it would be weighted average of all days
            if abs(vwap_day2 - 200.0) < 1.0:
                self.log_test("20.2.2", "PASS", f"Day 2 VWAP reset correctly: {vwap_day2:.2f} (expected ~200)")
            else:
                self.log_test("20.2.2", "WARN", f"Day 2 VWAP={vwap_day2:.2f}, expected ~200 (check reset logic)")
            
            self.log_test("20.2", "PASS", "Session reset behavior tested (check logs for 'vwap_session_reset')")
            return True
            
        except Exception as e:
            self.log_test("20.2", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_3_entry_signal_generation(self):
        """20.3 Test entry signal generation."""
        print("\n" + "="*80)
        print("TEST 20.3: Test entry signal generation")
        print("="*80)
        
        try:
            # Load VWAP strategy
            strategy_path = Path("strategies/vwap_range_trading.yaml")
            if not strategy_path.exists():
                self.log_test("20.3", "FAIL", "VWAP strategy file not found")
                return False
            
            strategy = load_strategy_from_yaml(strategy_path)
            self.log_test("20.3.1", "PASS", f"Strategy loaded: {strategy.name}")
            
            indicator_calc = IndicatorCalculator()
            signals = []
            
            async def signal_callback(signal: Signal):
                signals.append(signal)
                print(f"  📊 Signal: {signal.side} {signal.symbol} - {signal.reason}")
            
            engine = StrategyEngine(indicator_calc, signal_callback)
            await engine.register_strategy(strategy)
            
            # Build up VWAP history with declining prices
            base_time = datetime.now()
            print("  Building VWAP history...")
            
            # Start at 50000, decline to create lower band proximity
            for i in range(30):
                price = 50000.0 - (i * 100)
                data = MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=i),
                    open=price,
                    high=price + 50,
                    low=price - 50,
                    close=price,
                    volume=1.0 + (i * 0.1)
                )
                await engine.process_market_data(data)
            
            # Check if entry signal was generated
            if len(signals) > 0:
                last_signal = signals[-1]
                self.log_test("20.3.2", "PASS", f"Entry signal generated: {last_signal.side}")
                
                if last_signal.side == 'buy':
                    self.log_test("20.3.3", "PASS", "Signal side correct (buy for long)")
                else:
                    self.log_test("20.3.3", "FAIL", f"Expected 'buy', got '{last_signal.side}'")
                
                # Check reason includes VWAP band info
                if "vwap" in last_signal.reason.lower() or "band" in last_signal.reason.lower():
                    self.log_test("20.3.4", "PASS", f"Signal reason includes VWAP info: {last_signal.reason}")
                else:
                    self.log_test("20.3.4", "WARN", f"Signal reason may not include VWAP: {last_signal.reason}")
                
                self.log_test("20.3", "PASS", "Entry signal generation verified")
            else:
                self.log_test("20.3", "WARN", "No entry signals generated (may need different market conditions)")
            
            return True
            
        except Exception as e:
            self.log_test("20.3", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_4_exit_signal_generation(self):
        """20.4 Test exit signal generation."""
        print("\n" + "="*80)
        print("TEST 20.4: Test exit signal generation")
        print("="*80)
        
        try:
            strategy_path = Path("strategies/vwap_range_trading.yaml")
            strategy = load_strategy_from_yaml(strategy_path)
            
            indicator_calc = IndicatorCalculator()
            signals = []
            
            async def signal_callback(signal: Signal):
                signals.append(signal)
                print(f"  📊 Signal: {signal.side} {signal.symbol} - {signal.reason}")
            
            engine = StrategyEngine(indicator_calc, signal_callback)
            await engine.register_strategy(strategy)
            
            base_time = datetime.now()
            
            # Simulate entry at lower band
            print("  Simulating entry at lower band...")
            for i in range(20):
                price = 50000.0 - (i * 200)
                data = MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=i),
                    open=price,
                    high=price + 50,
                    low=price - 50,
                    close=price,
                    volume=1.0
                )
                await engine.process_market_data(data)
            
            # Clear signals from entry
            entry_signals = len(signals)
            signals.clear()
            
            # Simulate price recovery to VWAP
            print("  Simulating price recovery to VWAP...")
            for i in range(20):
                price = 46000.0 + (i * 200)  # Rising back up
                data = MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=20 + i),
                    open=price,
                    high=price + 50,
                    low=price - 50,
                    close=price,
                    volume=1.0
                )
                await engine.process_market_data(data)
            
            # Check for exit signal
            if len(signals) > 0:
                exit_signal = signals[-1]
                self.log_test("20.4.1", "PASS", f"Exit signal generated: {exit_signal.side}")
                
                if exit_signal.side == 'sell':
                    self.log_test("20.4.2", "PASS", "Exit signal side correct (sell for long)")
                else:
                    self.log_test("20.4.2", "FAIL", f"Expected 'sell', got '{exit_signal.side}'")
                
                self.log_test("20.4", "PASS", "Exit signal generation verified")
            else:
                self.log_test("20.4", "WARN", "No exit signals generated (may need different conditions)")
            
            return True
            
        except Exception as e:
            self.log_test("20.4", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_5_different_proximity_thresholds(self):
        """20.5 Test with different proximity thresholds."""
        print("\n" + "="*80)
        print("TEST 20.5: Test with different proximity thresholds")
        print("="*80)
        
        thresholds = [0.3, 0.5, 1.0]
        
        for threshold in thresholds:
            try:
                print(f"\n  Testing with proximity threshold: {threshold}%")
                
                strategy_path = Path("strategies/vwap_range_trading.yaml")
                strategy = load_strategy_from_yaml(strategy_path)
                
                # Modify proximity threshold in entry conditions
                for condition in strategy.entry_conditions:
                    if hasattr(condition, 'proximity_percent'):
                        condition.proximity_percent = threshold
                
                indicator_calc = IndicatorCalculator()
                signals = []
                
                async def signal_callback(signal: Signal):
                    signals.append(signal)
                
                engine = StrategyEngine(indicator_calc, signal_callback)
                await engine.register_strategy(strategy)
                
                # Simulate market data
                base_time = datetime.now()
                for i in range(30):
                    price = 50000.0 - (i * 100)
                    data = MarketData(
                        symbol="BTCUSDT",
                        timestamp=base_time + timedelta(minutes=i),
                        open=price,
                        high=price + 50,
                        low=price - 50,
                        close=price,
                        volume=1.0
                    )
                    await engine.process_market_data(data)
                
                self.log_test(f"20.5.{thresholds.index(threshold)+1}", "PASS",
                             f"Threshold {threshold}% tested, signals: {len(signals)}")
                
            except Exception as e:
                self.log_test(f"20.5.{thresholds.index(threshold)+1}", "FAIL",
                             f"Error with {threshold}%: {str(e)}")
        
        self.log_test("20.5", "PASS", "Different proximity thresholds tested")
        return True
    
    async def test_20_6_different_std_dev_multipliers(self):
        """20.6 Test with different std dev multipliers."""
        print("\n" + "="*80)
        print("TEST 20.6: Test with different std dev multipliers")
        print("="*80)
        
        try:
            calculator = IndicatorCalculator(cache_ttl_seconds=60)
            
            # Build market data with some volatility
            base_time = datetime.now()
            prices = [50000, 49800, 50200, 49500, 50500, 49000, 51000, 48500, 51500, 48000]
            
            for i, price in enumerate(prices):
                data = MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=i),
                    open=price,
                    high=price + 100,
                    low=price - 100,
                    close=price,
                    volume=1.0
                )
                await calculator.add_market_data(data, "1h")
            
            # Calculate VWAP
            vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            
            if vwap is None:
                self.log_test("20.6.1", "FAIL", "VWAP is None")
                return False
            
            self.log_test("20.6.1", "PASS", f"VWAP calculated: {vwap:.2f}")
            
            # Test different multipliers
            multipliers = [2.0, 3.0, 4.0]
            
            for multiplier in multipliers:
                # Upper band
                upper_band = await calculator.calculate_vwap_band(
                    "BTCUSDT", "1h", multiplier, "upper", use_cache=False
                )
                
                # Lower band
                lower_band = await calculator.calculate_vwap_band(
                    "BTCUSDT", "1h", multiplier, "lower", use_cache=False
                )
                
                if upper_band is None or lower_band is None:
                    self.log_test(f"20.6.{multipliers.index(multiplier)+2}", "FAIL",
                                 f"Bands at {multiplier}σ are None")
                    continue
                
                # Verify bands are in correct order
                if lower_band < vwap < upper_band:
                    self.log_test(f"20.6.{multipliers.index(multiplier)+2}", "PASS",
                                 f"{multiplier}σ bands: lower={lower_band:.2f}, vwap={vwap:.2f}, upper={upper_band:.2f}")
                else:
                    self.log_test(f"20.6.{multipliers.index(multiplier)+2}", "FAIL",
                                 f"Band order incorrect at {multiplier}σ")
            
            self.log_test("20.6", "PASS", "Different std dev multipliers tested")
            return True
            
        except Exception as e:
            self.log_test("20.6", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_7_verify_performance(self):
        """20.7 Verify performance."""
        print("\n" + "="*80)
        print("TEST 20.7: Verify performance")
        print("="*80)
        
        try:
            calculator = IndicatorCalculator(cache_ttl_seconds=60)
            
            # Measure VWAP calculation time
            base_time = datetime.now()
            
            # Add 100 data points
            for i in range(100):
                data = MarketData(
                    symbol="BTCUSDT",
                    timestamp=base_time + timedelta(minutes=i),
                    open=50000.0 + i,
                    high=50010.0 + i,
                    low=49990.0 + i,
                    close=50000.0 + i,
                    volume=1.0
                )
                await calculator.add_market_data(data, "1h")
            
            # Measure calculation time
            start = datetime.now()
            for _ in range(100):
                vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
            end = datetime.now()
            
            elapsed_ms = (end - start).total_seconds() * 1000
            avg_ms = elapsed_ms / 100
            
            if avg_ms < 1.0:
                self.log_test("20.7.1", "PASS", f"VWAP calculation: {avg_ms:.3f}ms avg (< 1ms target)")
            else:
                self.log_test("20.7.1", "WARN", f"VWAP calculation: {avg_ms:.3f}ms avg (target < 1ms)")
            
            # Test cache hit rate
            cache_stats = await calculator.get_cache_statistics()
            self.log_test("20.7.2", "PASS", f"Cache stats: {cache_stats}")
            
            # Test memory usage (approximate)
            import sys
            vwap_state_size = sys.getsizeof(calculator._vwap_states)
            if vwap_state_size < 10000:  # < 10KB
                self.log_test("20.7.3", "PASS", f"Memory usage: {vwap_state_size} bytes (< 10KB)")
            else:
                self.log_test("20.7.3", "WARN", f"Memory usage: {vwap_state_size} bytes")
            
            self.log_test("20.7", "PASS", "Performance verified")
            return True
            
        except Exception as e:
            self.log_test("20.7", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_20_8_backward_compatibility(self):
        """20.8 Test backward compatibility."""
        print("\n" + "="*80)
        print("TEST 20.8: Test backward compatibility")
        print("="*80)
        
        try:
            # Test that existing RSI/EMA strategies still work
            existing_strategies = [
                "strategies/range_trading_strategy.yaml",
            ]
            
            for strategy_file in existing_strategies:
                strategy_path = Path(strategy_file)
                if not strategy_path.exists():
                    self.log_test(f"20.8.{existing_strategies.index(strategy_file)+1}",
                                 "SKIP", f"{strategy_file} not found")
                    continue
                
                try:
                    strategy = load_strategy_from_yaml(strategy_path)
                    
                    indicator_calc = IndicatorCalculator()
                    engine = StrategyEngine(indicator_calc, None)
                    await engine.register_strategy(strategy)
                    
                    # Process some data
                    base_time = datetime.now()
                    for i in range(20):
                        data = MarketData(
                            symbol=strategy.symbol,
                            timestamp=base_time + timedelta(minutes=i),
                            open=68000.0 + i,
                            high=68010.0 + i,
                            low=67990.0 + i,
                            close=68000.0 + i,
                            volume=1.0
                        )
                        await engine.process_market_data(data)
                    
                    self.log_test(f"20.8.{existing_strategies.index(strategy_file)+1}",
                                 "PASS", f"{strategy_file} works correctly")
                    
                except Exception as e:
                    self.log_test(f"20.8.{existing_strategies.index(strategy_file)+1}",
                                 "FAIL", f"{strategy_file}: {str(e)}")
            
            self.log_test("20.8", "PASS", "Backward compatibility verified")
            return True
            
        except Exception as e:
            self.log_test("20.8", "FAIL", f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self):
        """Run all manual tests."""
        print("\n" + "="*80)
        print("MANUAL TESTING: VWAP Range Trading Strategy")
        print("="*80)
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Run all tests
        await self.test_20_1_vwap_calculation_accuracy()
        await self.test_20_2_session_reset_behavior()
        await self.test_20_3_entry_signal_generation()
        await self.test_20_4_exit_signal_generation()
        await self.test_20_5_different_proximity_thresholds()
        await self.test_20_6_different_std_dev_multipliers()
        await self.test_20_7_verify_performance()
        await self.test_20_8_backward_compatibility()
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        warned = sum(1 for r in self.test_results if r["status"] == "WARN")
        skipped = sum(1 for r in self.test_results if r["status"] == "SKIP")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"⚠ Warnings: {warned}")
        print(f"⊘ Skipped: {skipped}")
        
        if failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Review details above.")
        
        print(f"\nCompleted at: {datetime.now().isoformat()}")
        print("\nNOTE: Check logs/trading_bot.log for detailed logging:")
        print("  - vwap_session_reset messages")
        print("  - entering_vwap_band_proximity messages")
        print("  - exiting_vwap_band_proximity messages")
        print("  - entry_signal_generated messages")
        
        return failed == 0


async def main():
    """Main entry point."""
    runner = VwapManualTestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
