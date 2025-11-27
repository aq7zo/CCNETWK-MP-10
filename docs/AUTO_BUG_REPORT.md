# Automatic Bug Report Generation

## Overview

The PokeProtocol now automatically generates a comprehensive bug report when the host closes the program. This happens automatically - no manual steps required!

## How It Works

When you run the host:

```bash
python scripts/interactive_battle.py host
```

The system will:

1. **Enable Debug Logging**: Automatically starts tracking all events
2. **Monitor Everything**: Captures messages, connections, errors, state changes
3. **Generate Report on Exit**: When the host closes (normally or with errors), a bug report is automatically generated

## When Reports Are Generated

The bug report is automatically generated when:

- ✅ Host disconnects normally after battle ends
- ✅ Host exits after declining rematch
- ✅ Connection timeout occurs (no joiner connected)
- ✅ Battle setup timeout (opponent didn't select Pokémon)
- ✅ User exits early (chooses not to retry on errors)
- ✅ Program exits for any reason (via `atexit` handler)

## Report Location

Reports are saved in the current directory with the filename format:
```
bug_report_YYYYMMDD_HHMMSS.txt
```

Example: `bug_report_20241127_123553.txt`

## What You'll See

When the host closes, you'll see:

```
Disconnecting...

Generating bug report...

============================================================
  GENERATING BUG REPORT...
============================================================

✓ Bug report generated successfully!
  File: bug_report_20241127_123553.txt
============================================================
```

## Report Contents

The automatically generated report includes:

- **Executive Summary**: Quick overview of system health
- **Peer Overview**: Statistics for Host, Joiner, Spectator
- **Connection Analysis**: All connection/disconnection events
- **Message Flow**: Complete message tracking
- **Error Analysis**: All errors with stack traces
- **Warning Analysis**: All warnings with context
- **Battle State**: State transitions and events
- **Timing Analysis**: Timeouts and retransmissions
- **Network Analysis**: Connection stability
- **Chat Analysis**: All chat messages
- **Spectator Analysis**: Spectator joins and message reception
- **Recommendations**: Actionable suggestions
- **Detailed Event Log**: Chronological log of everything

## Notes

- **Rematch Handling**: If players choose a rematch, the report is generated after the final battle ends
- **Multiple Sessions**: Each host session generates its own report
- **No Data**: If no peers were running, the report will indicate this (but still be generated)
- **Automatic**: No need to manually run `generate_bug_report.py` - it happens automatically!

## Troubleshooting

### Report Not Generated

If the report isn't generated:

1. Check that `scripts/generate_bug_report.py` exists
2. Verify that `src/debug_logger.py` exists
3. Check console for error messages
4. Ensure the host actually ran (not just imported)

### Empty Report

If the report shows "No debug loggers found":

- This is normal if no peers were actually running
- Run a complete battle session to generate data
- The report will be populated when peers are active

### Import Errors

If you see import errors:

- Ensure all files are in the correct directories
- Check that Python can find the modules
- Verify the path setup in `interactive_battle.py`

## Example Session

```
$ python scripts/interactive_battle.py host

============================================================
  POKEPROTOCOL - HOST MODE
============================================================
  (Bug report will be generated automatically on exit)
============================================================

[... battle session ...]

Disconnecting...

Generating bug report...

============================================================
  GENERATING BUG REPORT...
============================================================

✓ Bug report generated successfully!
  File: bug_report_20241127_123553.txt
============================================================
```

The bug report is now ready for analysis!

