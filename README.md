# PokeProtocol - Pokémon Battle System

A peer-to-peer Pokémon battle system using UDP networking, implementing the RFC PokeProtocol specification.

## Quick Start

### Option 1: Interactive Battle (Recommended)

The easiest way to run a battle with user-friendly prompts:

**Terminal 1 - Host:**
```bash
python scripts/interactive_battle.py host
```

**Terminal 2 - Joiner:**
```bash
python scripts/interactive_battle.py joiner
```

The interactive script will prompt you for:
- IP addresses (defaults to `127.0.0.1` for local testing)
- Ports (defaults: Host=8888, Joiner=8889)
- Pokémon selection
- Move selection during battle

### Option 2: Example Battle Script

For a simpler example with hardcoded settings:

**Terminal 1 - Host:**
```bash
python scripts/example_battle.py host
```

**Terminal 2 - Joiner:**
```bash
python scripts/example_battle.py joiner
```

**Note:** You may need to edit `example_battle.py` line 105 to change the host IP address if connecting from different machines.

### Option 3: Run Tests (No Network Required)

Test the system without needing two players:

```bash
python tests/test_suite.py
```

This runs 21 automated tests covering all components.

## Requirements

- Python 3.7 or higher
- No external dependencies (uses only Python standard library)

## Running on Different Machines

1. **Find the host's IP address:**
   - Windows: `ipconfig` (look for IPv4 Address)
   - Linux/Mac: `ifconfig` or `ip addr`

2. **Start the host first:**
   ```bash
   python scripts/interactive_battle.py host
   ```

3. **Start the joiner with the host's IP:**
   ```bash
   python scripts/interactive_battle.py joiner
   ```
   When prompted, enter the host's IP address (not `127.0.0.1`)

4. **Firewall:** Make sure UDP ports 8888 and 8889 are allowed through your firewall

## Available Commands

### Interactive Battle Script
```bash
python scripts/interactive_battle.py [host|joiner|spectator]
```

### Example Battle Script
```bash
python scripts/example_battle.py host      # Run as host
python scripts/example_battle.py joiner    # Run as joiner
python scripts/example_battle.py chat      # Test chat functionality
python scripts/example_battle.py pokemon    # List available Pokémon
python scripts/example_battle.py moves     # List available moves
```

## How It Works

1. **Host** starts listening on a port (default: 8888)
2. **Joiner** connects to the host's IP address
3. Both players select their Pokémon
4. Battle begins with turn-based combat
5. Players select moves when it's their turn
6. Damage is calculated synchronously on both sides
7. Battle continues until one Pokémon faints (HP ≤ 0)


## Troubleshooting

### Connection Issues
- Make sure the host is running **before** the joiner tries to connect
- Verify both machines are on the same network (or use port forwarding)
- Check firewall settings allow UDP traffic on ports 8888/8889
- Try `127.0.0.1` first for local testing

### Port Already in Use
- Change the port number when prompted
- Or close any other programs using those ports

### Can't Find Pokémon
- Use `python scripts/example_battle.py pokemon` to see available Pokémon
- Pokémon names are case-sensitive (e.g., "Pikachu" not "pikachu")

### Battle Hanging
- Check that both peers are running and connected
- Verify network connectivity and firewall settings
- Ensure both players have selected their Pokémon

## Project Structure

```
CCNETWK-MP-10/
├── src/              # Core implementation
│   ├── peer.py       # Host, Joiner, Spectator peers
│   ├── battle.py     # Battle state machine and damage calculator
│   ├── messages.py   # Protocol message types
│   └── game_data.py  # Pokémon and move databases
├── scripts/          # Example scripts
│   ├── interactive_battle.py  # User-friendly battle interface
│   └── example_battle.py      # Simple examples
├── tests/            # Test suite
│   └── test_suite.py # Automated tests
├── data/             # Pokémon data files
└── docs/             # Documentation

```

## More Information

- See `docs/TESTING_GUIDE.md` for detailed testing instructions
- See `docs/PROJECT_COMPLETE.md` for implementation details
- See `docs/RFC PokeProtocol.txt` for the protocol specification

## Example Session

**Host Terminal:**
```
=== Starting Host Peer ===
Waiting for joiner to connect...
✓ Joiner connected!
Select Your Pokémon: Pikachu
Starting battle with Pikachu...
BATTLE START!
Your turn! [Battle status shown]
Used Thunderbolt!
```

**Joiner Terminal:**
```
=== Starting Joiner Peer ===
Connecting to host at 127.0.0.1:8888...
✓ Connected to host!
Select Your Pokémon: Charmander
Starting battle with Charmander...
BATTLE START!
[Opponent's turn...]
Your turn! [Battle status shown]
Used Flame Thrower!
```

---

**Enjoy your Pokémon battles!** 🎮⚡🔥

