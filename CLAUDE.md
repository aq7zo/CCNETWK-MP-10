# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **PokeProtocol** implementation - a peer-to-peer Pokémon battle system over UDP as specified in RFC PokeProtocol.txt. The protocol implements a custom reliability layer on top of UDP for turn-based battles with synchronized damage calculation.

## Testing and Development Commands

### Run Automated Tests
```bash
python test_suite.py
```
Runs 21 comprehensive unit and integration tests covering all components. All tests should pass.

### Run Example Battle (Two Terminals Required)

**Terminal 1 (Host):**
```bash
python example_battle.py host
```

**Terminal 2 (Joiner):**
```bash
python example_battle.py joiner
```

The host must be running before the joiner connects. Default connection is to 127.0.0.1:8888.

### Data Cleaning
```bash
python data_cleaning.py
```
Validates and cleans the Pokemon CSV file, producing `pokemon_cleaned.csv`.

## Architecture

### Core Protocol Flow

**Connection Sequence:**
1. Host listens on port (UDP socket, non-blocking)
2. Joiner sends HANDSHAKE_REQUEST
3. Host responds with HANDSHAKE_RESPONSE containing RNG seed
4. Both exchange BATTLE_SETUP messages with Pokémon data

**Turn Execution (Four-Step Handshake):**
1. Attacker sends ATTACK_ANNOUNCE
2. Defender responds with DEFENSE_ANNOUNCE
3. Both peers independently calculate damage using shared seed
4. Both send CALCULATION_REPORT with their results
5. If calculations match: both send CALCULATION_CONFIRM
6. If calculations mismatch: RESOLUTION_REQUEST exchange occurs

**Game End:**
- When HP ≤ 0, GAME_OVER message is sent
- Winner is announced, battle terminates

### Module Architecture

**peer.py** (870 lines): Main peer implementations
- `BasePeer`: Common UDP socket management, message sending/receiving, reliability integration
- `HostPeer`: Battle host that listens for connections
- `JoinerPeer`: Battle participant that connects to host
- `SpectatorPeer`: Observer implementation (stub)

**battle_state.py**: State machine managing battle flow
- States: SETUP → WAITING_FOR_MOVE → PROCESSING_TURN → GAME_OVER
- `BattlePokemon`: Tracks current HP, stat boosts (special_attack_uses, special_defense_uses)
- `BattleStateMachine`: Manages turns, tracks whose turn it is, validates state transitions

**reliability.py**: Custom reliability layer over UDP
- Sequence numbers (monotonically increasing)
- ACK handling (auto-sent for non-ACK messages)
- Retransmission: 500ms timeout, 3 max retries
- Duplicate detection via sequence deque (last 1000 messages tracked)

**messages.py**: Protocol message types and serialization
- 11 message types defined in RFC (HANDSHAKE_REQUEST, ATTACK_ANNOUNCE, etc.)
- Plain text format: newline-separated `key: value` pairs
- Deserialization entry point with type-based routing

**damage_calculator.py**: Synchronized damage calculation
- Formula: `damage = ((2 × Level / 5 + 2) × Power × A/D / 50 + 2) × Modifiers`
- Modifiers: Type effectiveness (dual-type multiplicative), STAB (1.5x), Random (85%-100%)
- Both peers must calculate identical damage using shared RNG seed
- Minimum damage: 1 HP

**pokemon_data.py**: CSV loader for Pokémon stats
- Loads from `pokemon_cleaned.csv` (801 Pokémon)
- Type effectiveness calculations via `against_*` columns
- Pokemon data class with hp, attack, defense, sp_attack, sp_defense, speed

**moves.py**: Move database
- Predefined moves with power, category (physical/special), type
- Move lookup by name

## Key Implementation Details

### Synchronization Mechanism
Both peers independently calculate damage using:
- Shared RNG seed (exchanged during handshake)
- Identical damage formula
- Same Pokémon stats from CSV

CALCULATION_REPORT acts as a checksum - if values differ, discrepancy resolution occurs via RESOLUTION_REQUEST.

### Reliability Layer
- Every message gets sequence number via `reliability.send_message()`
- Non-ACK messages automatically trigger ACK responses
- Unacked messages stored in `pending_acks` dict with timestamp
- `process_reliability()` must be called regularly to handle retransmissions
- Max 3 retries before considering message failed

### State Management
- Battle state is explicit via `BattleState` enum
- Turn order managed by `my_turn` boolean flag
- State transitions are atomic and validated
- Host always goes first in battle

### Message Handling Pattern
```python
# Receive message
result = peer.receive_message(timeout=0.5)
if result:
    msg, addr = result
    peer.handle_message(msg, addr)

# Process reliability (retransmissions)
peer.process_reliability()
```

This pattern must be called in a loop for the protocol to function correctly.

## Known Limitations

1. **Stat Boosts**: Defined in BATTLE_SETUP but not applied in damage calculation
2. **Spectator Mode**: Not fully implemented
3. **Status Effects**: Not implemented (paralysis, burn, etc.)
4. **Level**: Fixed at 50 for all battles
5. **Connection Recovery**: No reconnection logic after disconnect
6. **Broadcast Mode**: Not implemented (only P2P)

## Important Technical Notes

- **Socket Management**: Non-blocking UDP sockets using `select()` for polling
- **CSV Format**: Requires specific column names including `type1`, `type2`, `against_*` fields
- **Port Requirements**: Host uses port 8888, Joiner uses port 8889 by default
- **Network**: Both peers must be able to reach each other via UDP (firewall rules may be required)
- **Turn Management**: Only the peer whose turn it is should send ATTACK_ANNOUNCE
- **RNG Synchronization**: Critical that both peers use the same seed for damage calculation

## Testing Approach

The test suite (`test_suite.py`) uses Python's `unittest` framework and can run on a single machine without network setup. Tests cover:
- Pokemon data loading and type effectiveness
- Move database functionality
- Message serialization/deserialization
- Reliability layer (ACK, sequence numbers)
- Battle state machine transitions
- Damage calculation accuracy
- Full integration flow

For network testing, two separate processes (or machines) are required running the example_battle.py script.
