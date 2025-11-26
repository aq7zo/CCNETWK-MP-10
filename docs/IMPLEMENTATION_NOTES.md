# PokeProtocol Implementation Notes

## Project Structure

### Core Modules

1. **pokemon_data.py** - Pokémon database and type effectiveness
   - `PokemonDataLoader`: Loads CSV data
   - `Pokemon`: Data class for Pokémon stats
   - Type effectiveness calculations

2. **moves.py** - Move database
   - `Move`: Move data class (power, category, type)
   - `MoveDatabase`: Predefined moves across all types

3. **messages.py** - Protocol message handling
   - All 11 message types
   - Serialization/deserialization
   - Message parsing and routing

4. **reliability.py** - UDP reliability layer
   - Sequence numbers
   - ACK handling
   - Retransmission (500ms timeout, 3 retries max)
   - Duplicate detection

5. **battle_state.py** - Battle state machine
   - `BattleState`: State enumeration
   - `BattleStateMachine`: Manages battle flow
   - `BattlePokemon`: In-battle Pokémon with HP

6. **damage_calculator.py** - Synchronized damage calculation
   - Deterministic formula
   - Type effectiveness
   - STAB (Same Type Attack Bonus)
   - Random variation (85%-100%)

7. **peer.py** - Peer implementations
   - `BasePeer`: Common functionality
   - `HostPeer`: Battle host
   - `JoinerPeer`: Battle participant
   - `SpectatorPeer`: Observer (stub)

### Supporting Files

- **pokemon.csv**: Pokémon stats database (801 Pokémon)
- **RFC PokeProtocol.txt**: Protocol specification
- **example_battle.py**: Usage examples
- **README.md**: User documentation

## Protocol Implementation

### Message Flow

**Connection:**
1. Host listens on port
2. Joiner sends HANDSHAKE_REQUEST
3. Host responds with HANDSHAKE_RESPONSE (includes seed)
4. Both send BATTLE_SETUP with Pokémon data

**Turn Execution:**
1. Attacker sends ATTACK_ANNOUNCE
2. Defender sends DEFENSE_ANNOUNCE
3. Both independently calculate damage
4. Both send CALCULATION_REPORT
5. If match: both send CALCULATION_CONFIRM
6. If mismatch: RESOLUTION_REQUEST exchange

**End Game:**
- When HP ≤ 0, send GAME_OVER
- Winner announced

### Reliability Features

- **Sequence Numbers**: Monotonically increasing
- **ACKs**: Auto-sent for all non-ACK messages
- **Retransmission**: 500ms timeout, 3 max retries
- **Duplicates**: Tracked via sequence deque (last 1000)

### Damage Calculation

Formula used:
```
damage = ((2 × Level / 5 + 2) × Power × A/D / 50 + 2) × Modifiers
```

Modifiers:
- **Type Effectiveness**: Multiplied for dual-types
- **STAB**: 1.5x for same-type moves
- **Random**: 0.85-1.0 uniform distribution

Minimum damage: 1 HP

## Design Decisions

### State Management

- Explicit state machine for clarity
- State transitions are atomic
- Turn order managed by `my_turn` flag

### Message Handling

- Single deserialization entry point
- Type-based routing via MessageType enum
- Field validation during parsing

### Synchronization

- Both peers calculate independently
- Shared RNG seed ensures identical results
- CALCULATION_REPORT acts as checksum
- Discrepancy resolution via RESOLUTION_REQUEST

### Error Handling

- Timeout-based connection attempts
- Max retry limits prevent infinite loops
- Graceful disconnection
- Validation of move/Pokémon existence

## Usage Patterns

### Basic Battle

```python
# Host side
host = HostPeer(port=8888)
host.start_listening()
# Wait for connection...
host.start_battle("Pikachu")
host.use_move("Thunderbolt")

# Joiner side
joiner = JoinerPeer(port=8889)
joiner.connect("127.0.0.1", 8888)
joiner.start_battle("Charmander")
# Wait for turn...
joiner.use_move("Flame Thrower")
```

### Chat

```python
peer.send_chat_message("Player1", "Hello!")
peer.on_chat_message = lambda name, msg: print(f"{name}: {msg}")
```

## Testing Recommendations

1. **Unit Tests**: Each module independently
2. **Integration Tests**: Full battle flow
3. **Network Tests**: Loss, latency, out-of-order
4. **Concurrency**: Multiple simultaneous battles
5. **Edge Cases**: Max HP damage, status effects

## Known Limitations

1. **Spectator Mode**: Not fully implemented
2. **Stat Boosts**: Defined but not applied in damage calc
3. **Status Effects**: Not implemented
4. **Multiple Moves**: Pokémon limited to all moves
5. **Level**: Fixed at 50
6. **Connection Recovery**: No reconnection logic

## Extension Points

### Easy to Add

- Additional move types
- More Pokémon
- Status effect messages
- Battle log export

### Medium Complexity

- Stat boost application
- Multiple Pokémon teams
- Spectator mode
- Broadcast mode

### Advanced

- Network discovery
- Multi-hop routing
- Encryption
- Tournament brackets

## Performance Considerations

- UDP packet size: Max 1472 bytes (MTU)
- Stickers: Base64 encoded, max 10MB recommended
- Sequence tracking: Circular deque (memory bounded)
- Socket: Non-blocking with select()

## Security Considerations

- No authentication
- No encryption
- Open to packet injection
- No replay protection beyond sequence deques

## Future Improvements

1. Full spectator implementation
2. Stat boosts in damage calculation
3. Status effects (paralysis, burn, etc.)
4. Multiple moves per Pokémon
5. Connection recovery logic
6. Network discovery protocol
7. Authentication and encryption

## Compliance with RFC

This implementation follows the RFC PokeProtocol.txt specification:

✅ UDP transport  
✅ Plain text messages  
✅ All 11 message types  
✅ Four-step turn handshake  
✅ Reliability layer  
✅ Synchronized damage calculation  
✅ Discrepancy resolution  
✅ Chat (text and stickers)  
✅ Spectator mode (partial)  
✅ Battle flow states  
✅ Type effectiveness  
✅ STAB calculation  

## Credits

Implementation for academic/educational purposes based on RFC PokeProtocol specification.

