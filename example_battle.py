"""
Example PokeProtocol Battle

This script demonstrates how to use the PokeProtocol implementation
to run a Pokémon battle between two peers.
"""

import time
from peer import HostPeer, JoinerPeer
from moves import MoveDatabase


def run_host_example():
    """
    Run host peer example.
    
    Creates a host, waits for connection, selects a Pokémon,
    and manages the battle loop.
    """
    print("\n=== Starting Host Peer ===")
    
    # Initialize host
    host = HostPeer(port=8888)
    host.start_listening()
    
    # Wait for joiner to connect
    print("Waiting for joiner to connect...")
    timeout = time.time() + 30.0
    while not host.connected and time.time() < timeout:
        result = host.receive_message(timeout=0.5)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()
    
    if not host.connected:
        print("Timed out waiting for connection")
        return
    
    # Start battle with Pikachu
    print("Starting battle with Pikachu")
    host.start_battle("Pikachu")
    
    # Battle loop
    print("Entering battle loop...")
    battle_active = True
    move_db = MoveDatabase()
    
    while battle_active and not host.battle_state.is_game_over():
        # Process incoming messages
        result = host.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        
        host.process_reliability()
        
        # Check for turn
        if host.battle_state and host.battle_state.is_my_turn():
            print(f"Your turn! {host.battle_state.get_battle_status()}")
            print("Available moves: Thunderbolt, Thunder Shock, Thunder")
            
            # Example: use Thunderbolt
            move = move_db.get_move("Thunderbolt")
            if move and host.battle_state:
                from messages import AttackAnnounce
                announce = AttackAnnounce(
                    move.name,
                    host.reliability.get_next_sequence_number()
                )
                host.send_message(announce)
                print(f"Used {move.name}!")
        
        time.sleep(0.1)
    
    # Game over
    if host.battle_state.is_game_over():
        winner = host.battle_state.get_winner()
        print(f"\nBattle complete! Winner: {winner}")
    
    host.disconnect()


def run_joiner_example():
    """
    Run joiner peer example.
    
    Creates a joiner, connects to host, selects a Pokémon,
    and manages the battle loop.
    """
    print("\n=== Starting Joiner Peer ===")
    
    # Initialize joiner
    joiner = JoinerPeer(port=8889)
    
    # Connect to host
    try:
        print("Connecting to host at 127.0.0.1:8888...")
        joiner.connect("192.168.243.32", 8888)
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        return
    
    # Start battle with Charmander
    print("Starting battle with Charmander")
    joiner.start_battle("Charmander")
    
    # Battle loop
    print("Entering battle loop...")
    battle_active = True
    move_db = MoveDatabase()
    
    while battle_active and not joiner.battle_state.is_game_over():
        # Process incoming messages
        result = joiner.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            joiner.handle_message(msg, addr)
        
        joiner.process_reliability()
        
        # Check for turn
        if joiner.battle_state and joiner.battle_state.is_my_turn():
            print(f"Your turn! {joiner.battle_state.get_battle_status()}")
            print("Available moves: Flame Thrower, Fire Blast, Ember")
            
            # Example: use Flame Thrower
            move = move_db.get_move("Flame Thrower")
            if move and joiner.battle_state:
                from messages import AttackAnnounce
                announce = AttackAnnounce(
                    move.name,
                    joiner.reliability.get_next_sequence_number()
                )
                joiner.send_message(announce)
                print(f"Used {move.name}!")
        
        time.sleep(0.1)
    
    # Game over
    if joiner.battle_state.is_game_over():
        winner = joiner.battle_state.get_winner()
        print(f"\nBattle complete! Winner: {winner}")
    
    joiner.disconnect()


def run_chat_example():
    """Demonstrate chat functionality."""
    print("\n=== Chat Example ===")
    
    host = HostPeer(port=8890)
    host.start_listening()
    
    joiner = JoinerPeer(port=8891)
    joiner.connect("127.0.0.1", 8890)
    
    # Set up chat handlers
    def host_on_chat(name, message):
        print(f"[Host] {name}: {message}")
    
    def joiner_on_chat(name, message):
        print(f"[Joiner] {name}: {message}")
    
    host.on_chat_message = host_on_chat
    joiner.on_chat_message = joiner_on_chat
    
    # Send messages
    time.sleep(0.5)
    host.send_chat_message("Player1", "Good luck!")
    time.sleep(0.5)
    
    # Process messages
    for i in range(10):
        result = host.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()
    
    result = joiner.receive_message(timeout=0.5)
    if result:
        msg, addr = result
        joiner.handle_message(msg, addr)
    joiner.process_reliability()
    
    joiner.send_chat_message("Player2", "Thanks, you too!")
    time.sleep(0.5)
    
    for i in range(10):
        result = host.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()
    
    host.disconnect()
    joiner.disconnect()


def list_available_pokemon():
    """List all available Pokémon."""
    from pokemon_data import PokemonDataLoader
    
    print("\n=== Available Pokémon ===")
    loader = PokemonDataLoader()
    pokemon_names = loader.get_all_pokemon_names()
    
    # Display first 20
    for i, name in enumerate(pokemon_names[:20]):
        print(f"{i+1}. {name}")
    
    print(f"\nTotal: {len(pokemon_names)} Pokémon available")


def list_available_moves():
    """List all available moves."""
    print("\n=== Available Moves ===")
    move_db = MoveDatabase()
    move_names = move_db.get_all_move_names()
    
    # Group by type
    by_type = {}
    for move_name in move_names:
        move = move_db.get_move(move_name)
        if move:
            if move.move_type not in by_type:
                by_type[move.move_type] = []
            by_type[move.move_type].append(move_name)
    
    for move_type, moves in sorted(by_type.items()):
        print(f"\n{move_type.upper()}:")
        for move in moves[:5]:  # Show first 5 per type
            print(f"  - {move}")
        if len(moves) > 5:
            print(f"  ... and {len(moves) - 5} more")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python example_battle.py host    - Run as host")
        print("  python example_battle.py joiner  - Run as joiner")
        print("  python example_battle.py chat    - Run chat example")
        print("  python example_battle.py pokemon - List available Pokémon")
        print("  python example_battle.py moves   - List available moves")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "host":
        run_host_example()
    elif mode == "joiner":
        run_joiner_example()
    elif mode == "chat":
        run_chat_example()
    elif mode == "pokemon":
        list_available_pokemon()
    elif mode == "moves":
        list_available_moves()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

