# Debug System Documentation

## Overview

The PokeProtocol debug system provides comprehensive logging, message tracking, state monitoring, and bug report generation to help diagnose battle hanging issues and other problems.

## Quick Start

### Running with Debug Mode

Use the debug-enabled battle script instead of the regular interactive script:

**Terminal 1 (Host):**
```bash
python scripts/debug_battle.py host
```

**Terminal 2 (Joiner):**
```bash
python scripts/debug_battle.py joiner
```

### What Gets Logged

The debug system automatically logs:
- **All messages** sent and received (with sequence numbers)
- **State transitions** (SETUP → WAITING_FOR_MOVE → PROCESSING_TURN → etc.)
- **Errors** and exceptions
- **Warnings** (duplicate messages, unexpected states)
- **Timing information** for all events

### Bug Report Generation

At the end of each battle (or when interrupted), a bug report is automatically generated and saved as a JSON file:

```
bug_report_host_1234567890.json
bug_report_joiner_1234567890.json
```

## Debug Levels

The system supports multiple debug levels:

- **NONE** (0): No logging
- **ERROR** (1): Only errors
- **WARNING** (2): Errors and warnings
- **INFO** (3): Errors, warnings, and info messages
- **DEBUG** (4): All of the above plus debug messages
- **VERBOSE** (5): Everything including verbose state checks

Default level is **DEBUG**.

## Bug Report Structure

Bug reports are JSON files containing:

```json
{
  "title": "Battle Hanging Bug Report",
  "description": "Additional description",
  "generated_at": "2024-01-01T12:00:00",
  "duration": 45.2,
  "summary": {
    "total_logs": 150,
    "total_messages": 25,
    "total_state_transitions": 8,
    "total_errors": 0
  },
  "message_flow": {
    "total_messages": 25,
    "by_type": {
      "ATTACK_ANNOUNCE": {"SEND": 2, "RECEIVE": 2},
      "DEFENSE_ANNOUNCE": {"SEND": 2, "RECEIVE": 2},
      ...
    },
    "by_direction": {
      "SEND": 12,
      "RECEIVE": 13
    },
    "messages": [...]
  },
  "state_transitions": {
    "total_transitions": 8,
    "transitions": [...],
    "current_state": "WAITING_FOR_MOVE"
  },
  "errors": [...],
  "recent_logs": [...],
  "full_logs": [...]
}
```

## Analyzing Bug Reports

### Common Issues to Look For

1. **Missing Messages**
   - Check `message_flow.by_type` to see if expected messages are missing
   - Example: If ATTACK_ANNOUNCE has SEND but no corresponding DEFENSE_ANNOUNCE RECEIVE

2. **State Stuck**
   - Check `state_transitions.transitions` for the last transition
   - If stuck in PROCESSING_TURN, look for missing CALCULATION_REPORT or CALCULATION_CONFIRM

3. **Message Sequence Issues**
   - Check `message_flow.messages` for sequence numbers
   - Look for gaps or out-of-order messages

4. **Errors**
   - Check `errors` array for exceptions or error conditions
   - Each error includes timestamp, type, message, and context

### Example Analysis

```python
import json

# Load bug report
with open('bug_report_host_1234567890.json', 'r') as f:
    report = json.load(f)

# Check message flow
msg_flow = report['message_flow']
print(f"Total messages: {msg_flow['total_messages']}")
print(f"Sent: {msg_flow['by_direction']['SEND']}")
print(f"Received: {msg_flow['by_direction']['RECEIVE']}")

# Check for missing DEFENSE_ANNOUNCE
defense = msg_flow['by_type'].get('DEFENSE_ANNOUNCE', {})
if defense.get('RECEIVE', 0) == 0:
    print("WARNING: No DEFENSE_ANNOUNCE received!")

# Check state transitions
transitions = report['state_transitions']['transitions']
print(f"\nLast state: {transitions[-1]['new_state']}")
print(f"Total transitions: {len(transitions)}")

# Check errors
if report['errors']:
    print(f"\nErrors found: {len(report['errors'])}")
    for error in report['errors']:
        print(f"  [{error['timestamp']:.2f}s] {error['error_type']}: {error['message']}")
```

## Programmatic Usage

### Enabling Debug in Your Code

```python
from peer import HostPeer, JoinerPeer
from debug import get_debug_logger, DebugLevel, set_debug_enabled

# Enable debug logging
set_debug_enabled(True)

# Create peer with debug enabled
host = HostPeer(port=8888, debug=True)

# Get logger and log custom events
logger = get_debug_logger()
logger.log(DebugLevel.INFO, 'CUSTOM', 'Custom event', {'data': 'value'}, 'host')

# Generate bug report
report = logger.generate_bug_report("My Bug Report", "Description")
logger.save_bug_report("my_report.json")
```

### Manual State Transition Logging

```python
# Log state transitions manually
logger.log_state_transition(
    old_state='WAITING_FOR_MOVE',
    new_state='PROCESSING_TURN',
    peer_type='host',
    reason='AttackAnnounce sent',
    context={'move': 'Thunderbolt'}
)
```

### Manual Message Logging

```python
# Log messages manually
logger.log_message(
    direction='SEND',
    message_type='ATTACK_ANNOUNCE',
    sequence_number=5,
    peer_type='host',
    details={'move': 'Thunderbolt'}
)
```

## Debug Output

During execution, debug output appears in the console:

```
[0.123s] [DEBUG] [MESSAGE] [HOST] SEND ATTACK_ANNOUNCE
  Data: {
    "direction": "SEND",
    "message_type": "ATTACK_ANNOUNCE",
    "sequence_number": 5,
    "address": "('192.168.1.100', 8889)",
    "message_size": 45
  }
[0.456s] [INFO] [STATE] [HOST] State transition: WAITING_FOR_MOVE -> PROCESSING_TURN
  Data: {
    "old_state": "WAITING_FOR_MOVE",
    "new_state": "PROCESSING_TURN",
    "reason": "Used Thunderbolt"
  }
```

## Troubleshooting

### Debug Not Working

1. Check that `src/debug.py` exists
2. Verify imports work: `python -c "from src.debug import get_debug_logger"`
3. Ensure `debug=True` is passed to peer constructors

### Too Much Output

Reduce debug level:
```python
from debug import set_debug_level, DebugLevel
set_debug_level(DebugLevel.WARNING)  # Only warnings and errors
```

### Bug Report Not Generated

- Check file permissions in current directory
- Look for error messages in console
- Bug reports are saved in the current working directory

## Integration with Regular Scripts

To add debug support to existing scripts:

```python
# At the top of your script
from debug import set_debug_enabled, set_debug_level, DebugLevel
set_debug_enabled(True)
set_debug_level(DebugLevel.DEBUG)

# When creating peers
host = HostPeer(port=8888, debug=True)
joiner = JoinerPeer(port=8889, debug=True)

# At the end, generate report
from debug import get_debug_logger
logger = get_debug_logger()
logger.save_bug_report("my_report.json")
```

## Best Practices

1. **Run with debug enabled** when experiencing issues
2. **Save bug reports** before closing terminals
3. **Compare reports** from both host and joiner
4. **Check timing** - look for long gaps between messages
5. **Verify state transitions** - ensure states change as expected
6. **Monitor message flow** - ensure all expected messages are sent/received

## Example Workflow

1. Start debug battle:
   ```bash
   python scripts/debug_battle.py host
   python scripts/debug_battle.py joiner
   ```

2. Reproduce the issue (battle hanging, etc.)

3. Let the script generate bug report automatically, or press Ctrl+C to interrupt and generate report

4. Analyze the bug report:
   ```python
   import json
   with open('bug_report_host_*.json') as f:
       report = json.load(f)
   # Analyze report...
   ```

5. Share bug report with developers or use for debugging

## Files

- `src/debug.py` - Debug logging system
- `scripts/debug_battle.py` - Debug-enabled battle script
- `bug_report_*.json` - Generated bug reports

## Support

For issues with the debug system itself, check:
- Console output for error messages
- That all dependencies are installed
- File permissions for bug report generation

