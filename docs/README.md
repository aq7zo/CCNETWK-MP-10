# PokeProtocol Implementation

A complete implementation of the Peer-to-Peer Pokémon Battle Protocol (PokeProtocol) over UDP as specified in RFC PokeProtocol.txt.

## Overview

This implementation provides a turn-based Pokémon battle system over UDP with the following features:

- **Peer-to-Peer Architecture**: Direct one-to-one communication between peers
- **Reliability Layer**: Custom ACK/retransmission mechanism on top of UDP
- **Synchronized Damage Calculation**: Both peers independently calculate damage using the same formula
- **Four-Step Turn Handshake**: ATTACK_ANNOUNCE → DEFENSE_ANNOUNCE → CALCULATION_REPORT → CALCULATION_CONFIRM
- **Discrepancy Resolution**: Automatic handling of calculation mismatches
- **Chat Functionality**: Text messaging and sticker support
- **Spectator Mode**: Support for peers observing battles

## Architecture

### Modules

- **pokemon_data.py**: CSV loader for Pokémon stats and type effectiveness
- **moves.py**: Move database with physical/special damage categories
- **messages.py**: Protocol message types and serialization
- **reliability.py**: ACK, sequence numbers, and retransmission
- **battle_state.py**: State machine for battle flow
- **damage_calculator.py**: Synchronized damage calculation
- **peer.py**: Host, Joiner, and Spectator peer implementations

### Protocol Flow

1. **Connection Setup**:
   - Host starts listening on a port
   - Joiner sends HANDSHAKE_REQUEST
   - Host responds with HANDSHAKE_RESPONSE (including seed for RNG sync)
   - Both peers exchange BATTLE_SETUP messages

2. **Battle Turn**:
   - Attacker sends ATTACK_ANNOUNCE
   - Defender responds with DEFENSE_ANNOUNCE
   - Both peers independently calculate damage
   - Both send CALCULATION_REPORT
   - If calculations match, both send CALCULATION_CONFIRM
   - If mismatch, peers exchange RESOLUTION_REQUEST

3. **End Conditions**:
   - When HP reaches 0, GAME_OVER is sent
   - Battle terminates

### Reliability Features

- **Sequence Numbers**: Every message gets a unique sequence number
- **Acknowledgments**: Automatic ACK responses for non-ACK messages
- **Retransmission**: 500ms timeout with up to 3 retries
- **Duplicate Detection**: Sequence number tracking prevents duplicate processing

## Usage

### Basic Host Setup

```python
from peer import HostPeer

# Create host peer
host = HostPeer(port=8888)
host.start_listening()

# Wait for joiner to connect
while not host.connected:
    result = host.receive_message(timeout=1.0)
    if result:
        msg, addr = result
        host.handle_message(msg, addr)
    host.process_reliability()

# Choose Pokémon and start battle
host.start_battle("Pikachu", special_attack_uses=5, special_defense_uses=5)
```

### Basic Joiner Setup

```python
from peer import JoinerPeer

# Create joiner peer
joiner = JoinerPeer(port=8889)

# Connect to host
joiner.connect("127.0.0.1", 8888)

# Choose Pokémon and start battle
joiner.start_battle("Charmander", special_attack_uses=5, special_defense_uses=5)
```

### Turn Management

```python
# For attacker (on your turn)
from messages import AttackAnnounce
from moves import MoveDatabase

move_db = MoveDatabase()
move = move_db.get_move("Thunderbolt")

announce = AttackAnnounce(move.name, host.reliability.get_next_sequence_number())
host.send_message(announce)
```

### Chat

```python
# Send chat message
host.send_chat_message("Player1", "Good luck!")

# Set up chat callback
def on_chat(name, message):
    print(f"{name}: {message}")

host.on_chat_message = on_chat
```

## Requirements

- Python 3.7+
- Standard library only (socket, select, csv, etc.)

## Data Cleaning

The project includes a data cleaning utility (`data_cleaning.py`) that validates and cleans the Pokemon CSV file. The cleaned data is automatically used by default.

To run data cleaning manually:
```bash
python data_cleaning.py
```

This will:
- Validate all data types
- Normalize text fields
- Check value ranges
- Handle missing values
- Produce `pokemon_cleaned.csv`

## CSV Data Format

The implementation expects a `pokemon.csv` file with columns:
- `name`: Pokémon name
- `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`, `speed`: Base stats
- `type1`, `type2`: Types (type2 can be empty)
- `against_*`: Type effectiveness multipliers (bug, dark, dragon, etc.)

## Testing

Run example battles using the provided example files.

## Implementation Notes

- Damage calculation includes STAB (Same Type Attack Bonus)
- Type effectiveness is multiplied for dual-type Pokémon
- Random damage variation: 85%-100%
- Minimum damage: 1 HP
- Default level: 50

## License

Implementation for academic/educational purposes.

