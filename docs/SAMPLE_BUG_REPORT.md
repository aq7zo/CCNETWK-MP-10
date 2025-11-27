# Sample Bug Report

This is what a complete bug report looks like when peers are actually running:

```
================================================================================
POKEPROTOCOL COMPREHENSIVE BUG REPORT
================================================================================
Generated: 2024-11-27T12:35:53.218567

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

JoinerPeer (Port 8889):
  Total Events: 78
  Messages Sent: 22
  Messages Received: 23
  Errors: 0
  Warnings: 1
  Connections: 1
  Disconnections: 1
  Runtime: 45.23 seconds

SpectatorPeer (Port 8890):
  Total Events: 80
  Messages Sent: 5
  Messages Received: 75
  Errors: 0
  Warnings: 0
  Connections: 1
  Disconnections: 0
  Runtime: 40.12 seconds

CONNECTION ANALYSIS
--------------------------------------------------------------------------------
Total Connections: 4
Total Disconnections: 2

Connections:
  - Joiner at 127.0.0.1:8889
  - Spectator at 127.0.0.1:8890
  - Spectator at 127.0.0.1:8891

Disconnections:
  - 127.0.0.1:8889
  - 127.0.0.1:8890

MESSAGE FLOW ANALYSIS
--------------------------------------------------------------------------------
Unique Message Types: 12
Total Messages: 150

Message Breakdown:
  RECEIVED_ACK: 45
  RECEIVED_ATTACK_ANNOUNCE: 8
  RECEIVED_BATTLE_SETUP: 2
  RECEIVED_CALCULATION_REPORT: 8
  RECEIVED_CHAT_MESSAGE: 12
  RECEIVED_DEFENSE_ANNOUNCE: 8
  RECEIVED_GAME_OVER: 1
  RECEIVED_HANDSHAKE_RESPONSE: 2
  SENT_ACK: 45
  SENT_ATTACK_ANNOUNCE: 8
  SENT_BATTLE_SETUP: 2
  SENT_CALCULATION_REPORT: 8
  SENT_CHAT_MESSAGE: 12
  SENT_DEFENSE_ANNOUNCE: 8
  SENT_GAME_OVER: 1
  SENT_HANDSHAKE_RESPONSE: 2
  SENT_SPECTATOR_REQUEST: 2

ERROR ANALYSIS
--------------------------------------------------------------------------------
✓ No errors detected

WARNING ANALYSIS
--------------------------------------------------------------------------------
Total Warnings: 2

Warning Summary:
  Invalid sticker received from Player1: 1 occurrence(s)
  High retransmission rate detected: 1 occurrence(s)

Detailed Warnings:

  Warning #1:
    Time: 2024-11-27T12:30:15.123456
    Peer: HostPeer (Port 8888)
    Message: Invalid sticker received from Player1
    Context: {
      "sender": "Player1",
      "sticker_data_length": 15000000
    }

  Warning #2:
    Time: 2024-11-27T12:32:20.456789
    Peer: JoinerPeer (Port 8889)
    Message: High retransmission rate detected
    Context: {
      "retransmission_count": 15,
      "time_window": 5.0
    }

BATTLE STATE ANALYSIS
--------------------------------------------------------------------------------
Total Battle Events: 25

Battle Event Timeline:
  [2024-11-27T12:30:00.000000] HostPeer: Battle seed generated
    Data: {
      "seed": 12345
    }
  [2024-11-27T12:30:01.123456] HostPeer: State changed: SETUP -> WAITING_FOR_MOVE
    Data: {
      "old_state": "SETUP",
      "new_state": "WAITING_FOR_MOVE",
      "context": "Both Pokemon selected"
    }
  [2024-11-27T12:30:05.234567] HostPeer: State changed: WAITING_FOR_MOVE -> PROCESSING_TURN
    Data: {
      "old_state": "WAITING_FOR_MOVE",
      "new_state": "PROCESSING_TURN",
      "context": "Attack announced"
    }
  [2024-11-27T12:30:06.345678] HostPeer: State changed: PROCESSING_TURN -> TURN_COMPLETE
    Data: {
      "old_state": "PROCESSING_TURN",
      "new_state": "TURN_COMPLETE",
      "context": "Calculations confirmed"
    }
  [2024-11-27T12:30:10.456789] HostPeer: State changed: TURN_COMPLETE -> WAITING_FOR_MOVE
    Data: {
      "old_state": "TURN_COMPLETE",
      "new_state": "WAITING_FOR_MOVE",
      "context": "Next turn"
    }
  [2024-11-27T12:35:00.567890] HostPeer: State changed: WAITING_FOR_MOVE -> GAME_OVER
    Data: {
      "old_state": "WAITING_FOR_MOVE",
      "new_state": "GAME_OVER",
      "context": "Pokemon fainted"
    }

TIMING ANALYSIS
--------------------------------------------------------------------------------
Total Timeouts: 0
Total Retransmissions: 3

Retransmission Events:
  Retry attempt 1: 2 messages
  Retry attempt 2: 1 messages

NETWORK ANALYSIS
--------------------------------------------------------------------------------
HostPeer (Port 8888):
  Connections: 2
  Disconnections: 1

JoinerPeer (Port 8889):
  Connections: 1
  Disconnections: 1

SpectatorPeer (Port 8890):
  Connections: 1
  Disconnections: 0

✓ Network stability appears good

CHAT ANALYSIS
--------------------------------------------------------------------------------
Total Chat Messages: 12

Chat Message Timeline:
  [2024-11-27T12:30:02.123456] SENT - Host: Good luck!
  [2024-11-27T12:30:02.234567] RECEIVED - Host: Good luck!
  [2024-11-27T12:30:02.345678] RECEIVED - Host: Good luck!
  [2024-11-27T12:30:03.456789] SENT - Joiner: Thanks, you too!
  [2024-11-27T12:30:03.567890] RECEIVED - Joiner: Thanks, you too!
  [2024-11-27T12:30:03.678901] RECEIVED - Joiner: Thanks, you too!
  [2024-11-27T12:32:15.789012] SENT - Spectator: This is exciting!
  [2024-11-27T12:32:15.890123] RECEIVED - Spectator: This is exciting!
  [2024-11-27T12:32:15.901234] RECEIVED - Spectator: This is exciting!
  [2024-11-27T12:32:15.012345] RECEIVED - Spectator: This is exciting!

SPECTATOR ANALYSIS
--------------------------------------------------------------------------------
Total Spectator Joins: 2

Spectator Join Timeline:
  [2024-11-27T12:30:00.500000] Spectator joined from 127.0.0.1:8890
    Address: 127.0.0.1:8890
  [2024-11-27T12:31:00.600000] Spectator joined from 127.0.0.1:8891
    Address: 127.0.0.1:8891

Spectator Message Reception:
  SpectatorPeer (Port 8890):
    Messages Received: 75
    Battle Events: 25
  SpectatorPeer (Port 8891):
    Messages Received: 70
    Battle Events: 25

RECOMMENDATIONS
--------------------------------------------------------------------------------
✓ No critical issues detected
System appears to be functioning normally

1. Review warnings about sticker validation
2. Monitor retransmission rates during network instability
3. Consider implementing chat message deduplication for spectators

DETAILED EVENT LOG
--------------------------------------------------------------------------------
(Chronological order across all peers)

Total Events: 247

[2024-11-27T12:30:00.000000] HostPeer (Port 8888) - CONNECTION: Connected to 127.0.0.1:8889
  Data: {
    "address": "127.0.0.1",
    "port": 8889,
    "peer_type": "Joiner"
  }
[2024-11-27T12:30:00.100000] HostPeer (Port 8888) - BATTLE_EVENT: Battle seed generated
  Data: {
    "seed": 12345
  }
[2024-11-27T12:30:00.200000] HostPeer (Port 8888) - MESSAGE_SENT: Sent HANDSHAKE_RESPONSE
  Data: {
    "message_type": "HANDSHAKE_RESPONSE",
    "target_address": "127.0.0.1",
    "target_port": 8889,
    "sequence_number": 1
  }
[2024-11-27T12:30:00.300000] JoinerPeer (Port 8889) - MESSAGE_RECEIVED: Received HANDSHAKE_RESPONSE
  Data: {
    "message_type": "HANDSHAKE_RESPONSE",
    "source_address": "127.0.0.1",
    "source_port": 8888,
    "sequence_number": 1
  }
[... continues with all events ...]

================================================================================
END OF REPORT
================================================================================
```

## Current Status

The bug report you just generated shows:

```
WARNING: No debug loggers found. Debug logging may not be enabled.
```

This means:
1. **No peers were running** when the report was generated, OR
2. **The session ended** and loggers were cleared

## To Generate a Report with Data

1. **Run a battle session** with host, joiner, and spectator
2. **While they're running**, the debug logger automatically tracks everything
3. **After the session**, run `python scripts/generate_bug_report.py`
4. The report will contain all the detailed information shown above

The debugging system is ready and will automatically capture all events when peers are actually running!

