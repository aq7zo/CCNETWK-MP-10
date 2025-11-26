"""
Debug-enabled Interactive Battle Script

This script runs the interactive battle with comprehensive debugging enabled.
Use this to diagnose battle hanging issues and generate bug reports.
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from peer import HostPeer, JoinerPeer
from game_data import MoveDatabase, PokemonDataLoader
from debug import get_debug_logger, DebugLevel, set_debug_enabled, set_debug_level

# Enable debug logging
set_debug_enabled(True)
set_debug_level(DebugLevel.DEBUG)
debug_logger = get_debug_logger()


def select_pokemon():
    """Allow user to select a Pokémon."""
    loader = PokemonDataLoader()
    
    print("\n=== Select Your Pokémon ===")
    print("Enter a Pokémon name, or type 'list' to see available Pokémon")
    
    while True:
        pokemon_name = input("Pokémon name: ").strip()
        
        if pokemon_name.lower() == 'list':
            print("\nAvailable Pokémon (showing first 30):")
            names = loader.get_all_pokemon_names()
            for i, name in enumerate(names[:30], 1):
                print(f"{i}. {name}")
            print(f"\n... and {len(names) - 30} more")
            continue
        
        pokemon = loader.get_pokemon(pokemon_name)
        if pokemon:
            print(f"Selected: {pokemon.name} (HP: {pokemon.hp}, Type: {pokemon.type1}/{pokemon.type2 or 'None'})")
            return pokemon.name
        else:
            print(f"Pokémon '{pokemon_name}' not found. Try again or type 'list'.")


def select_move():
    """Allow user to select a move."""
    move_db = MoveDatabase()
    
    print("\nYour turn! Select a move:")
    print("1. Quick Attack (Electric moves)")
    print("2. Strong Attack (Fire moves)")
    print("3. Special Attack (Water moves)")
    print("4. Custom move name")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        moves = ['Thunder Shock', 'Thunderbolt', 'Spark']
    elif choice == '2':
        moves = ['Ember', 'Flame Thrower', 'Fire Blast']
    elif choice == '3':
        moves = ['Water Gun', 'Bubble Beam', 'Hydro Pump']
    elif choice == '4':
        move_name = input("Enter move name: ").strip()
        return move_name
    else:
        print("Invalid choice, using Thunder Shock")
        return "Thunder Shock"
    
    for i, move_name in enumerate(moves, 1):
        move = move_db.get_move(move_name)
        if move:
            print(f"{i}. {move_name} (Power: {move.power}, Type: {move.move_type})")
    
    move_choice = input(f"Select move (1-{len(moves)}): ").strip()
    try:
        idx = int(move_choice) - 1
        if 0 <= idx < len(moves):
            return moves[idx]
    except:
        pass
    
    return moves[0]


def run_debug_host():
    """Run host with debug logging enabled."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - DEBUG MODE - HOST")
    print("="*60)
    print("Debug logging is ENABLED")
    print("="*60)
    
    port = input("Enter port to listen on (default: 8888): ").strip()
    if not port:
        port = 8888
    else:
        port = int(port)
    
    print(f"\nInitializing host on port {port}...")
    host = HostPeer(port=port, debug=True)
    host.start_listening()
    
    debug_logger.log(DebugLevel.INFO, 'SETUP', f"Host started on port {port}", {'port': port}, 'host')
    
    print("\n" + "="*60)
    print("  WAITING FOR JOINER TO CONNECT...")
    print("="*60)
    print(f"Tell the other player to connect to:")
    print(f"  IP Address: <your_ip_address>")
    print(f"  Port: {port}")
    print("\nWaiting...")
    
    timeout = time.time() + 60.0
    while not host.connected and time.time() < timeout:
        result = host.receive_message(timeout=0.5)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()
    
    if not host.connected:
        print("\nConnection timeout! No joiner connected.")
        debug_logger.log_error('CONNECTION_TIMEOUT', "No joiner connected within timeout", 'host')
        debug_logger.save_bug_report("bug_report_host_timeout.json", 
                                    "Host Connection Timeout",
                                    "Host failed to connect to joiner")
        return
    
    print("\n✓ Joiner connected!")
    
    # Select Pokémon
    pokemon_name = select_pokemon()
    
    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    host.start_battle(pokemon_name)
    debug_logger.log_state_transition('SETUP', 'WAITING_FOR_MOVE', 'host', 
                                     f"Started battle with {pokemon_name}")
    
    # Wait for opponent's Pokémon
    print("Waiting for opponent to select Pokémon...")
    timeout = time.time() + 30.0
    while host.battle_state.state.value == "SETUP" and time.time() < timeout:
        result = host.receive_message(timeout=0.5)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()
        time.sleep(0.1)
    
    if host.battle_state.state.value == "SETUP":
        print("Timeout waiting for opponent's Pokémon")
        debug_logger.log_error('SETUP_TIMEOUT', "Timeout waiting for opponent's Pokémon", 'host')
        debug_logger.save_bug_report("bug_report_host_setup_timeout.json",
                                    "Host Setup Timeout",
                                    "Host timed out waiting for opponent's Pokémon selection")
        return
    
    # Battle loop
    print("\n" + "="*60)
    print("  BATTLE START!")
    print("="*60)
    
    move_db = MoveDatabase()
    battle_active = True
    turn_count = 0
    
    try:
        while battle_active and not host.battle_state.is_game_over():
            # Process incoming messages
            result = host.receive_message(timeout=0.1)
            if result:
                msg, addr = result
                host.handle_message(msg, addr)
            
            host.process_reliability()
            
            # Log state periodically
            if host.battle_state and turn_count % 10 == 0:
                debug_logger.log(DebugLevel.VERBOSE, 'STATE_CHECK', 
                               f"Current state: {host.battle_state.state.value}, my_turn: {host.battle_state.my_turn}",
                               {'state': host.battle_state.state.value, 'my_turn': host.battle_state.my_turn},
                               'host')
            
            # Check for our turn
            if host.battle_state and host.battle_state.is_my_turn():
                turn_count += 1
                status = host.battle_state.get_battle_status()
                print(f"\n{'='*60}")
                print(f"  YOUR TURN! (Turn #{turn_count})")
                print(f"{'='*60}")
                print(f"{status}")
                
                move_name = select_move()
                move = move_db.get_move(move_name)
                
                if move and host.battle_state:
                    from messages import AttackAnnounce
                    announce = AttackAnnounce(
                        move.name,
                        host.reliability.get_next_sequence_number()
                    )
                    host.send_message(announce)
                    print(f"Used {move.name}!")
                    host.battle_state.mark_my_turn_taken(move)
                    debug_logger.log_state_transition('WAITING_FOR_MOVE', 'PROCESSING_TURN', 'host',
                                                     f"Used {move.name}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nBattle interrupted by user")
        debug_logger.log_warning("Battle interrupted by user", 'host')
    except Exception as e:
        print(f"\n\nERROR: {e}")
        debug_logger.log_error('BATTLE_ERROR', f"Error during battle: {e}", 'host', e)
        import traceback
        traceback.print_exc()
    
    # Game over
    if host.battle_state and host.battle_state.is_game_over():
        winner = host.battle_state.get_winner()
        print(f"\n" + "="*60)
        print(f"  BATTLE COMPLETE!")
        print(f"  Winner: {winner}")
        print("="*60)
    
    # Generate bug report
    print("\n" + "="*60)
    print("  GENERATING BUG REPORT...")
    print("="*60)
    debug_logger.print_summary()
    report_path = debug_logger.save_bug_report(
        f"bug_report_host_{int(time.time())}.json",
        "Host Battle Debug Report",
        f"Battle completed. Total turns: {turn_count}"
    )
    print(f"\nBug report saved to: {report_path}")
    
    print("\nDisconnecting...")
    host.disconnect()


def run_debug_joiner():
    """Run joiner with debug logging enabled."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - DEBUG MODE - JOINER")
    print("="*60)
    print("Debug logging is ENABLED")
    print("="*60)
    
    host_ip = input("Enter host IP address (default: 127.0.0.1): ").strip()
    if not host_ip:
        host_ip = "127.0.0.1"
    
    port_str = input("Enter host port (default: 8888): ").strip()
    if not port_str:
        host_port = 8888
    else:
        host_port = int(port_str)
    
    local_port_str = input("Enter your local port (default: 8889): ").strip()
    if not local_port_str:
        local_port = 8889
    else:
        local_port = int(local_port_str)
    
    print(f"\nInitializing joiner on port {local_port}...")
    joiner = JoinerPeer(port=local_port, debug=True)
    
    debug_logger.log(DebugLevel.INFO, 'SETUP', f"Joiner initializing, connecting to {host_ip}:{host_port}",
                     {'host_ip': host_ip, 'host_port': host_port, 'local_port': local_port}, 'joiner')
    
    # Connect to host
    print(f"Connecting to host at {host_ip}:{host_port}...")
    try:
        joiner.connect(host_ip, host_port)
    except ConnectionError as e:
        print(f"\n✗ Connection failed: {e}")
        debug_logger.log_error('CONNECTION_FAILED', f"Failed to connect to host: {e}", 'joiner', e)
        debug_logger.save_bug_report("bug_report_joiner_connection_failed.json",
                                    "Joiner Connection Failed",
                                    f"Failed to connect to {host_ip}:{host_port}")
        return
    
    print("✓ Connected to host!")
    
    # Select Pokémon
    pokemon_name = select_pokemon()
    
    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    joiner.start_battle(pokemon_name)
    debug_logger.log_state_transition('SETUP', 'WAITING_FOR_MOVE', 'joiner',
                                     f"Started battle with {pokemon_name}")
    
    # Wait for opponent's Pokémon
    print("Waiting for opponent to select Pokémon...")
    timeout = time.time() + 30.0
    while joiner.battle_state.state.value == "SETUP" and time.time() < timeout:
        result = joiner.receive_message(timeout=0.5)
        if result:
            msg, addr = result
            joiner.handle_message(msg, addr)
        joiner.process_reliability()
        time.sleep(0.1)
    
    if joiner.battle_state.state.value == "SETUP":
        print("Timeout waiting for opponent's Pokémon")
        debug_logger.log_error('SETUP_TIMEOUT', "Timeout waiting for opponent's Pokémon", 'joiner')
        debug_logger.save_bug_report("bug_report_joiner_setup_timeout.json",
                                    "Joiner Setup Timeout",
                                    "Joiner timed out waiting for opponent's Pokémon selection")
        return
    
    # Battle loop
    print("\n" + "="*60)
    print("  BATTLE START!")
    print("="*60)
    
    move_db = MoveDatabase()
    battle_active = True
    turn_count = 0
    
    try:
        while battle_active and not joiner.battle_state.is_game_over():
            # Process incoming messages
            result = joiner.receive_message(timeout=0.1)
            if result:
                msg, addr = result
                joiner.handle_message(msg, addr)
            
            joiner.process_reliability()
            
            # Log state periodically
            if joiner.battle_state and turn_count % 10 == 0:
                debug_logger.log(DebugLevel.VERBOSE, 'STATE_CHECK',
                               f"Current state: {joiner.battle_state.state.value}, my_turn: {joiner.battle_state.my_turn}",
                               {'state': joiner.battle_state.state.value, 'my_turn': joiner.battle_state.my_turn},
                               'joiner')
            
            # Check for our turn
            if joiner.battle_state and joiner.battle_state.is_my_turn():
                turn_count += 1
                status = joiner.battle_state.get_battle_status()
                print(f"\n{'='*60}")
                print(f"  YOUR TURN! (Turn #{turn_count})")
                print(f"{'='*60}")
                print(f"{status}")
                
                move_name = select_move()
                move = move_db.get_move(move_name)
                
                if move and joiner.battle_state:
                    from messages import AttackAnnounce
                    announce = AttackAnnounce(
                        move.name,
                        joiner.reliability.get_next_sequence_number()
                    )
                    joiner.send_message(announce)
                    print(f"Used {move.name}!")
                    joiner.battle_state.mark_my_turn_taken(move)
                    debug_logger.log_state_transition('WAITING_FOR_MOVE', 'PROCESSING_TURN', 'joiner',
                                                     f"Used {move.name}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nBattle interrupted by user")
        debug_logger.log_warning("Battle interrupted by user", 'joiner')
    except Exception as e:
        print(f"\n\nERROR: {e}")
        debug_logger.log_error('BATTLE_ERROR', f"Error during battle: {e}", 'joiner', e)
        import traceback
        traceback.print_exc()
    
    # Game over
    if joiner.battle_state and joiner.battle_state.is_game_over():
        winner = joiner.battle_state.get_winner()
        print(f"\n" + "="*60)
        print(f"  BATTLE COMPLETE!")
        print(f"  Winner: {winner}")
        print("="*60)
    
    # Generate bug report
    print("\n" + "="*60)
    print("  GENERATING BUG REPORT...")
    print("="*60)
    debug_logger.print_summary()
    report_path = debug_logger.save_bug_report(
        f"bug_report_joiner_{int(time.time())}.json",
        "Joiner Battle Debug Report",
        f"Battle completed. Total turns: {turn_count}"
    )
    print(f"\nBug report saved to: {report_path}")
    
    print("\nDisconnecting...")
    joiner.disconnect()


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - DEBUG MODE")
    print("="*60)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("\nSelect mode:")
        print("1. Host - Start a battle and wait for others to join")
        print("2. Joiner - Connect to an existing battle")
        
        choice = input("\nEnter choice (1-2): ").strip()
        
        if choice == '1':
            mode = 'host'
        elif choice == '2':
            mode = 'joiner'
        else:
            print("Invalid choice")
            return
    
    if mode == 'host':
        run_debug_host()
    elif mode == 'joiner':
        run_debug_joiner()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python debug_battle.py [host|joiner]")


if __name__ == "__main__":
    main()

