# PokeProtocol Debugging System

## Overview

The PokeProtocol debugging system provides comprehensive logging and automatic bug report generation. It tracks all messages, state changes, errors, and network events across all peer types (Host, Joiner, Spectator).

## Features

- **Automatic Event Logging**: All messages, connections, errors, and state changes are automatically logged
- **Comprehensive Bug Reports**: Detailed analysis of system behavior, errors, warnings, and recommendations
- **Non-Intrusive**: Debugging is optional and doesn't affect normal operation if disabled
- **Real-Time Monitoring**: Track events as they happen across all peers

## Usage

### Step 1: Run Your Battle Session

Run the host, joiner, and spectator as normal:

**Terminal 1 - Host:**
```bash
python scripts/interactive_battle.py host
```

**Terminal 2 - Joiner:**
```bash
python scripts/interactive_battle.py joiner
```

**Terminal 3 - Spectator:**
```bash
python scripts/interactive_battle.py spectator
```

### Step 2: Generate Bug Report

After your battle session completes, generate the bug report:

```bash
python scripts/generate_bug_report.py
```

The report will be saved as `bug_report_YYYYMMDD_HHMMSS.txt` in the current directory.

### Alternative: Use Helper Script

```bash
python scripts/run_with_debugging.py
```

This script provides instructions and can generate the report after your session.

## Bug Report Contents

The generated bug report includes:

### 1. Executive Summary
- Total peers monitored
- Total events logged
- Error and warning counts
- Overall system health status

### 2. Peer Overview
- Statistics for each peer (Host, Joiner, Spectator)
- Message counts (sent/received)
- Connection/disconnection counts
- Runtime information

### 3. Connection Analysis
- All connection events
- Connection stability
- Connection/disconnection mismatches

### 4. Message Flow Analysis
- Message type breakdown
- Sent vs received message counts
- Unacknowledged message detection
- Message flow issues

### 5. Error Analysis
- All errors with timestamps
- Error categorization
- Stack traces
- Context information

### 6. Warning Analysis
- All warnings with timestamps
- Warning categorization
- Context information

### 7. Battle State Analysis
- Battle event timeline
- State transitions
- Battle progression tracking

### 8. Timing Analysis
- Timeout events
- Retransmission analysis
- Performance metrics

### 9. Network Analysis
- Connection stability
- Retransmission rates
- Network issue detection

### 10. Chat Analysis
- All chat messages
- Chat message timeline
- Chat flow verification

### 11. Spectator Analysis
- Spectator join events
- Spectator message reception
- Spectator connectivity

### 12. Recommendations
- Actionable recommendations based on detected issues
- Performance optimization suggestions
- Network troubleshooting tips

### 13. Detailed Event Log
- Chronological log of all events
- Complete event data
- Full system trace

## Debug Logger API

The debug logger is automatically integrated into peer classes. You can also use it programmatically:

```python
from debug_logger import get_logger, EventType

# Get logger for a peer
logger = get_logger("HostPeer", 8888)

# Log events
logger.log_message_sent("BATTLE_SETUP", ("127.0.0.1", 8889), 1)
logger.log_error("Connection failed", ConnectionError("Timeout"))
logger.log_state_change("SETUP", "WAITING_FOR_MOVE")

# Export data
data = logger.export_to_dict()
json_str = logger.export_to_json("debug_log.json")
```

## Event Types

The debug logger tracks these event types:

- `MESSAGE_SENT`: Message was sent
- `MESSAGE_RECEIVED`: Message was received
- `MESSAGE_ACK`: Message acknowledgment
- `STATE_CHANGE`: Battle state changed
- `CONNECTION`: Peer connected
- `DISCONNECTION`: Peer disconnected
- `ERROR`: Error occurred
- `WARNING`: Warning condition
- `BATTLE_EVENT`: Battle-specific event
- `CHAT_MESSAGE`: Chat message sent/received
- `SPECTATOR_JOIN`: Spectator joined
- `TIMEOUT`: Timeout occurred
- `RETRANSMISSION`: Message retransmitted

## Configuration

Debug logging is automatically enabled when `debug_logger.py` is available. To disable:

1. Remove or rename `src/debug_logger.py`
2. Or modify `src/peer.py` to set `DEBUG_LOGGING_ENABLED = False`

## Troubleshooting

### No Loggers Found

If you see "No debug loggers found" in the report:

1. Ensure `src/debug_logger.py` exists
2. Check that peers were actually created (not just imported)
3. Verify that `DEBUG_LOGGING_ENABLED` is `True` in `peer.py`

### Missing Events

If events are missing from the report:

1. Check that peers were running when events occurred
2. Verify that debug logger is properly initialized in peer `__init__`
3. Check for import errors in the console

### Report Generation Fails

If report generation fails:

1. Check that `scripts/generate_bug_report.py` exists
2. Verify Python can import `debug_logger`
3. Check file permissions for writing the report

## Example Bug Report

```
================================================================================
POKEPROTOCOL COMPREHENSIVE BUG REPORT
================================================================================
Generated: 2024-01-15T14:30:45.123456

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Total Peers Monitored: 3
Total Events Logged: 247
Total Errors: 0
Total Warnings: 2

✓ No errors detected
⚠️  2 warnings detected - Review Warning Analysis section
Total Runtime: 45.67 seconds

PEER OVERVIEW
--------------------------------------------------------------------------------
HostPeer (Port 8888):
  Total Events: 89
  Messages Sent: 23
  Messages Received: 22
  Errors: 0
  Warnings: 1
  Connections: 2
  Disconnections: 1
  Runtime: 45.67 seconds

[... detailed sections ...]
```

## Best Practices

1. **Run Complete Sessions**: Let battles complete fully before generating reports
2. **Multiple Runs**: Generate reports for multiple sessions to identify patterns
3. **Review Warnings**: Even if no errors, warnings can indicate potential issues
4. **Save Reports**: Keep reports for comparison and trend analysis
5. **Check Timing**: Review timing analysis for performance issues

## Integration with Testing

The debugging system integrates seamlessly with the test suite:

```python
from debug_logger import get_all_loggers, clear_loggers

# Clear loggers before test
clear_loggers()

# Run tests
# ... test code ...

# Generate report
loggers = get_all_loggers()
# Analyze results
```

## Future Enhancements

Potential future improvements:

- Real-time monitoring dashboard
- Automated issue detection and alerts
- Performance profiling integration
- Network packet capture analysis
- State machine visualization
- Message sequence diagram generation

