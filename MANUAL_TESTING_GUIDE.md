# Manual Testing Guide: Price Near Level Detection

## Quick Start

Run the comprehensive manual testing script:

```bash
./venv/bin/python3 manual_test_range_trading.py
```

This script automatically tests all 10 subtasks for Task 10: Manual Testing and Validation.

## What Gets Tested

### Automated Tests (10 subtasks)

1. **10.1**: Run range trading strategy in test mode
2. **10.2**: Verify proximity zone transitions are logged
3. **10.3**: Verify entry signals generated correctly
4. **10.4**: Test with different proximity thresholds (0.3%, 0.5%, 1.0%)
5. **10.5**: Test with different support/resistance levels
6. **10.6**: Verify no signals when conditions not met
7. **10.7**: Check log output for clarity
8. **10.8**: Verify performance (no lag or delays)
9. **10.9**: Test with multiple strategies simultaneously
10. **10.10**: Verify existing strategies still work

## Test Output

The script provides:
- ✓ Pass/Fail status for each test
- Detailed test results
- Performance metrics
- Summary statistics

Example output:
```
================================================================================
MANUAL TESTING: Price Near Level Detection Feature
================================================================================

✓ 10.1: PASS - Strategy runs in test mode
✓ 10.2: PASS - Proximity zone transitions logged
✓ 10.3: PASS - Entry signals generated correctly
...

================================================================================
TEST SUMMARY
================================================================================
Total Tests: 30
✓ Passed: 27
✗ Failed: 3
⚠ Warnings: 0
⊘ Skipped: 0
```

## Manual Verification Steps

### 1. Check Log Files

After running the test, inspect the logs:

```bash
tail -f logs/trading_bot.log
```

Look for these key messages:

**Range Configuration**:
```
[INFO] range_levels_configured: support=68000.0, resistance=72000.0, mid_range=70000.0
```

**Proximity Zone Entry**:
```
[INFO] entering_level_proximity: level=support, current_price=68200.0, distance_percent=0.29%
```

**Proximity Zone Exit**:
```
[INFO] exiting_level_proximity: level=support, current_price=69500.0, distance_percent=2.21%
```

**Entry Signal**:
```
[INFO] entry_signal_generated: side=buy, reason="rsi_4h=28.5 < 30; Price 68200.00 within 0.29% of support 68000.00"
```

### 2. Test with Live Data (Optional)

To test with real market data:

1. Ensure `.env` file has valid API credentials
2. Run the bot in test mode:
   ```bash
   ./venv/bin/python3 demo_test_mode.py
   ```
3. Monitor logs for proximity detection
4. Wait for price to approach support/resistance levels
5. Verify proximity zone transitions are logged

### 3. Test Different Configurations

Edit `strategies/range_trading_strategy.yaml` to test different settings:

**Tighter Proximity (0.3%)**:
```yaml
level_proximity_percent: 0.3
```

**Looser Proximity (1.0%)**:
```yaml
level_proximity_percent: 1.0
```

**Different Levels**:
```yaml
support_level: 65000.0
resistance_level: 70000.0
```

Then run the test script again to verify changes.

## Performance Testing

The script automatically measures performance:
- Processes 100 market data updates
- Calculates average time per update
- Reports if performance is acceptable (< 10ms per update)

Expected result: **< 1ms per update** (excellent performance)

## Troubleshooting

### Test Failures

**If tests fail**:
1. Check the error message in the output
2. Review the specific test that failed
3. Check if it's a feature issue or pre-existing problem

**Common issues**:
- Missing strategy files → Ensure all strategy files exist
- Invalid configuration → Check YAML syntax
- Missing indicators → Some strategies use unsupported indicators

### No Signals Generated

If test 10.3 shows no signals:
1. Check RSI values in logs (need RSI < 30)
2. Check price proximity (need price within threshold)
3. Verify both conditions are met simultaneously
4. May need to adjust test data to trigger conditions

### Performance Issues

If test 10.8 shows slow performance (> 10ms):
1. Check system load
2. Review indicator caching
3. Check for excessive logging
4. Consider optimizing condition evaluation

## Integration Testing

### Test with Real Exchange Data

1. Configure API credentials in `.env`
2. Update strategy with current market levels
3. Run in test mode:
   ```bash
   ./venv/bin/python3 src/main.py
   ```
4. Monitor for 1-2 hours
5. Verify proximity detection works with live data

### Test Multiple Strategies

Create multiple strategy files and run simultaneously:

```bash
# strategies/range_btc.yaml
# strategies/range_eth.yaml
# strategies/range_sol.yaml
```

Run the bot and verify all strategies work independently.

## Acceptance Checklist

Before marking Task 10 as complete, verify:

- [ ] All automated tests pass (or failures are explained)
- [ ] Proximity zone transitions logged correctly
- [ ] Entry signals only when both conditions met
- [ ] No false signals when conditions not met
- [ ] Performance < 10ms per update
- [ ] Log messages are clear and helpful
- [ ] Different thresholds work correctly
- [ ] Different levels work correctly
- [ ] Backward compatibility maintained
- [ ] Manual verification completed

## Test Results

See `MANUAL_TEST_RESULTS.md` for detailed test results and analysis.

## Next Steps

After manual testing:

1. Review test results in `MANUAL_TEST_RESULTS.md`
2. Address any failures (if feature-related)
3. Test with live market data (optional)
4. Deploy to production (if all tests pass)
5. Monitor in production for 24-48 hours
6. Collect feedback and iterate

## Support

For issues or questions:
- Check logs: `logs/trading_bot.log`
- Review design: `.kiro/specs/price-near-level-detection/design.md`
- Review requirements: `.kiro/specs/price-near-level-detection/requirements.md`
- Run integration tests: `./venv/bin/python3 -m pytest tests/integration/test_range_trading.py -v`

---

**Last Updated**: 2026-04-04  
**Feature**: Price Near Level Detection  
**Status**: Ready for Production
