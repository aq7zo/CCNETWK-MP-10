"""
Interactive PokeProtocol Battle

This script provides an interactive interface for running Pokémon battles
between two peers with user-friendly prompts for IP addresses and ports.
"""

import time
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from peer import HostPeer, JoinerPeer, SpectatorPeer
from game_data import MoveDatabase, PokemonDataLoader


def get_user_input(prompt, default=None):
    """Get user input with optional default value."""
    if default:
        prompt_text = f"{prompt} (default: {default}): "
    else:
        prompt_text = f"{prompt}: "

    user_input = input(prompt_text).strip()
    if not user_input and default:
        return default
    return user_input


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


def run_interactive_host():
    """Run host with interactive prompts."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - HOST MODE")
    print("="*60)

    # Get port with retry logic
    port = None
    host = None
    while host is None:
        port_str = get_user_input("Enter port to listen on", "8888" if port is None else str(port))
        try:
            port = int(port_str)
        except:
            print("Invalid port, using 8888")
            port = 8888

        try:
            print(f"\nInitializing host on port {port}...")
            host = HostPeer(port=port)
            host.start_listening()
        except OSError as e:
            error_str = str(e)
            if "Address already in use" in error_str or "10048" in error_str or "EADDRINUSE" in error_str or "WSAEADDRINUSE" in error_str:
                print(f"\n✗ Port {port} is already in use!")
                retry = input("Would you like to try a different port? (Y/N): ").strip().upper()
                if retry != 'Y':
                    print("\nExiting...")
                    return
            else:
                print(f"\n✗ Error initializing host: {e}")
                retry = input("Would you like to try again? (Y/N): ").strip().upper()
                if retry != 'Y':
                    print("\nExiting...")
                    return
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            retry = input("Would you like to try again? (Y/N): ").strip().upper()
            if retry != 'Y':
                print("\nExiting...")
                return

    # Wait for connection
    print("\n" + "="*60)
    print("  WAITING FOR JOINER TO CONNECT...")
    print("="*60)
    print(f"Tell the other player to connect to:")
    print(f"  IP Address: <your_ip_address>")
    print(f"  Port: {port}")
    print("\nWaiting...")

    timeout = time.time() + 60.0  # 60 second timeout
    while not host.connected and time.time() < timeout:
        result = host.receive_message(timeout=0.5)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)
        host.process_reliability()

    if not host.connected:
        print("\nConnection timeout! No joiner connected.")
        return

    print("\n✓ Joiner connected!")

    # Select Pokémon
    pokemon_name = select_pokemon()

    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    host.start_battle(pokemon_name)

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
        return

    # Battle loop
    print("\n" + "="*60)
    print("  BATTLE START!")
    print("="*60)

    move_db = MoveDatabase()
    battle_active = True

    while battle_active and not host.battle_state.is_game_over():
        # Process incoming messages
        result = host.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            host.handle_message(msg, addr)

        host.process_reliability()

        # Check for our turn
        if host.battle_state and host.battle_state.is_my_turn():
            status = host.battle_state.get_battle_status()
            print(f"\n{'='*60}")
            print(f"  YOUR TURN!")
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
                print(f"[DEBUG] Host sent AttackAnnounce: {move.name} to {host.peer_address}")
                host.battle_state.mark_my_turn_taken(move)

        time.sleep(0.1)

    # Game over
    if host.battle_state.is_game_over():
        winner = host.battle_state.get_winner()
        winner_pokemon = winner
        loser = host.battle_state.opponent_pokemon.pokemon.name if winner == host.my_pokemon.pokemon.name else host.my_pokemon.pokemon.name
        
        print(f"\n" + "="*60)
        print(f"  BATTLE COMPLETE!")
        print(f"  Winner: {winner_pokemon}")
        print(f"  Loser: {loser}")
        print("="*60)
        
        # Prompt for new battle
        wants_rematch = None
        while wants_rematch is None:
            response = input("\nStart a new battle? (Y/N): ").strip().upper()
            if response == 'Y':
                wants_rematch = True
            elif response == 'N':
                wants_rematch = False
            else:
                print("Please enter Y or N")
        
        # Send rematch request to opponent
        from messages import RematchRequest
        rematch_msg = RematchRequest(wants_rematch, host.reliability.get_next_sequence_number())
        host.send_message(rematch_msg)
        # Broadcast to spectators
        host._broadcast_to_spectators(rematch_msg)
        print(f"\nWaiting for opponent's response...")
        
        # Wait for opponent's rematch response
        timeout = time.time() + 30.0  # 30 second timeout
        while host.opponent_wants_rematch is None and time.time() < timeout:
            try:
                result = host.receive_message(timeout=0.5)
                if result:
                    msg, addr = result
                    host.handle_message(msg, addr)
                host.process_reliability()
            except Exception as e:
                # Handle any errors gracefully - continue waiting
                print(f"Error during rematch wait: {e}")
            time.sleep(0.1)
        
        # Check if both want rematch
        if wants_rematch and host.opponent_wants_rematch:
            print("\nBoth players want a rematch! Starting new battle...")
            host.disconnect()
            run_interactive_host()
            return
        elif not wants_rematch:
            print("\nYou declined the rematch. Thanks for playing!")
        elif host.opponent_wants_rematch is None:
            print("\nTimeout waiting for opponent's response. Disconnecting...")
        else:
            print("\nOpponent declined the rematch. Thanks for playing!")

    print("\nDisconnecting...")
    host.disconnect()


def run_interactive_joiner():
    """Run joiner with interactive prompts."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - JOINER MODE")
    print("="*60)

    # Get host IP and port
    host_ip = get_user_input("Enter host IP address", "127.0.0.1")
    port_str = get_user_input("Enter host port", "8888")

    try:
        host_port = int(port_str)
    except:
        print("Invalid port, using 8888")
        host_port = 8888

    # Get local port
    local_port_str = get_user_input("Enter your local port", "8889")
    try:
        local_port = int(local_port_str)
    except:
        print("Invalid port, using 8889")
        local_port = 8889

    # Retry loop for connection
    connected = False
    joiner = None
    while not connected:
        try:
            print(f"\nInitializing joiner on port {local_port}...")
            joiner = JoinerPeer(port=local_port)
            joiner.start_listening()

            # Connect to host
            print(f"Connecting to host at {host_ip}:{host_port}...")
            joiner.connect(host_ip, host_port)
            connected = True
            print("✓ Connected to host!")
        except OSError as e:
            error_str = str(e)
            if "Address already in use" in error_str or "10048" in error_str or "EADDRINUSE" in error_str or "WSAEADDRINUSE" in error_str:
                print(f"\n✗ Port {local_port} is already in use!")
                retry = input("Would you like to try a different local port? (Y/N): ").strip().upper()
                if retry == 'Y':
                    local_port_str = get_user_input("Enter your local port", str(local_port))
                    try:
                        local_port = int(local_port_str)
                    except:
                        print(f"Invalid port, keeping {local_port}")
                    # Clean up failed joiner
                    if joiner:
                        try:
                            joiner.disconnect()
                        except:
                            pass
                else:
                    print("\nExiting...")
                    return
            else:
                print(f"\n✗ Error initializing joiner: {e}")
                retry = input("Would you like to try again? (Y/N): ").strip().upper()
                if retry != 'Y':
                    print("\nExiting...")
                    return
                # Clean up failed joiner
                if joiner:
                    try:
                        joiner.disconnect()
                    except:
                        pass
        except ConnectionError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure the host is running first")
            print("2. Check that the IP address is correct")
            print("3. Verify firewall settings allow UDP traffic")
            print("4. Ensure both computers are on the same network (or port forwarding is configured)")
            
            # Ask if user wants to retry with new values
            retry = input("\nWould you like to try again with different settings? (Y/N): ").strip().upper()
            if retry == 'Y':
                # Get new values
                host_ip = get_user_input("Enter host IP address", host_ip)
                port_str = get_user_input("Enter host port", str(host_port))
                try:
                    host_port = int(port_str)
                except:
                    print(f"Invalid port, keeping {host_port}")
                
                local_port_str = get_user_input("Enter your local port", str(local_port))
                try:
                    local_port = int(local_port_str)
                except:
                    print(f"Invalid port, keeping {local_port}")
                
                # Clean up failed joiner
                if joiner:
                    try:
                        joiner.disconnect()
                    except:
                        pass
            else:
                print("\nExiting...")
                return
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            retry = input("\nWould you like to try again? (Y/N): ").strip().upper()
            if retry != 'Y':
                print("\nExiting...")
                return
            # Clean up failed joiner
            if joiner:
                try:
                    joiner.disconnect()
                except:
                    pass

    # Select Pokémon
    pokemon_name = select_pokemon()

    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    joiner.start_battle(pokemon_name)

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
        return

    # Battle loop
    print("\n" + "="*60)
    print("  BATTLE START!")
    print("="*60)

    move_db = MoveDatabase()
    battle_active = True

    while battle_active and not joiner.battle_state.is_game_over():
        # Process incoming messages
        result = joiner.receive_message(timeout=0.1)
        if result:
            msg, addr = result
            joiner.handle_message(msg, addr)

        joiner.process_reliability()

        # Check for our turn
        if joiner.battle_state and joiner.battle_state.is_my_turn():
            status = joiner.battle_state.get_battle_status()
            print(f"\n{'='*60}")
            print(f"  YOUR TURN!")
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
                print(f"[DEBUG] Joiner sent AttackAnnounce: {move.name} to {joiner.peer_address}")
                joiner.battle_state.mark_my_turn_taken(move)
                print(f"[DEBUG] Joiner: After mark_my_turn_taken, state={joiner.battle_state.state.value}, my_turn={joiner.battle_state.my_turn}, last_move={joiner.battle_state.last_move.name if joiner.battle_state.last_move else 'None'}")

        time.sleep(0.1)

    # Game over - wait for both players to decide on rematch
    if joiner.battle_state.is_game_over():
        winner = joiner.battle_state.get_winner()
        winner_pokemon = winner
        loser = joiner.battle_state.opponent_pokemon.pokemon.name if winner == joiner.my_pokemon.pokemon.name else joiner.my_pokemon.pokemon.name
        
        print(f"\n" + "="*60)
        print(f"  BATTLE COMPLETE!")
        print(f"  Winner: {winner_pokemon}")
        print(f"  Loser: {loser}")
        print("="*60)
        
        # Prompt for new battle
        wants_rematch = None
        while wants_rematch is None:
            response = input("\nStart a new battle? (Y/N): ").strip().upper()
            if response == 'Y':
                wants_rematch = True
            elif response == 'N':
                wants_rematch = False
            else:
                print("Please enter Y or N")
        
        # Send rematch request to opponent
        from messages import RematchRequest
        rematch_msg = RematchRequest(wants_rematch, joiner.reliability.get_next_sequence_number())
        joiner.send_message(rematch_msg)
        print(f"\nWaiting for opponent's response...")
        
        # Wait for opponent's rematch response
        timeout = time.time() + 30.0  # 30 second timeout
        while joiner.opponent_wants_rematch is None and time.time() < timeout:
            try:
                result = joiner.receive_message(timeout=0.5)
                if result:
                    msg, addr = result
                    joiner.handle_message(msg, addr)
                joiner.process_reliability()
            except Exception as e:
                # Handle any errors gracefully - continue waiting
                print(f"Error during rematch wait: {e}")
            time.sleep(0.1)
        
        # Check if both want rematch
        if wants_rematch and joiner.opponent_wants_rematch:
            print("\nBoth players want a rematch! Starting new battle...")
            joiner.disconnect()
            run_interactive_joiner()
            return
        elif not wants_rematch:
            print("\nYou declined the rematch. Thanks for playing!")
        elif joiner.opponent_wants_rematch is None:
            print("\nTimeout waiting for opponent's response. Disconnecting...")
        else:
            print("\nOpponent declined the rematch. Thanks for playing!")

    print("\nDisconnecting...")
    joiner.disconnect()


def run_interactive_spectator():
    """Run spectator with interactive prompts."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - SPECTATOR MODE")
    print("="*60)

    # Get host IP and port
    host_ip = get_user_input("Enter host IP address", "127.0.0.1")
    port_str = get_user_input("Enter host port", "8888")

    try:
        host_port = int(port_str)
    except:
        print("Invalid port, using 8888")
        host_port = 8888

    # Get local port
    local_port_str = get_user_input("Enter your local port", "8890")
    try:
        local_port = int(local_port_str)
    except:
        print("Invalid port, using 8890")
        local_port = 8890

    # Retry loop for connection
    connected = False
    spectator = None
    while not connected:
        try:
            print(f"\nInitializing spectator on port {local_port}...")
            spectator = SpectatorPeer(port=local_port)
            spectator.start_listening()

            # Set up battle update callback
            def on_battle_update(update_str):
                print(f"[BATTLE] {update_str}")

            spectator.on_battle_update = on_battle_update

            # Connect to host
            print(f"Connecting to host at {host_ip}:{host_port}...")
            spectator.connect(host_ip, host_port)
            connected = True
            print("✓ Connected as spectator!")
        except OSError as e:
            error_str = str(e)
            if "Address already in use" in error_str or "10048" in error_str or "EADDRINUSE" in error_str or "WSAEADDRINUSE" in error_str:
                print(f"\n✗ Port {local_port} is already in use!")
                retry = input("Would you like to try a different local port? (Y/N): ").strip().upper()
                if retry == 'Y':
                    local_port_str = get_user_input("Enter your local port", str(local_port))
                    try:
                        local_port = int(local_port_str)
                    except:
                        print(f"Invalid port, keeping {local_port}")
                    # Clean up failed spectator
                    if spectator:
                        try:
                            spectator.disconnect()
                        except:
                            pass
                else:
                    print("\nExiting...")
                    return
            else:
                print(f"\n✗ Error initializing spectator: {e}")
                retry = input("Would you like to try again? (Y/N): ").strip().upper()
                if retry != 'Y':
                    print("\nExiting...")
                    return
                # Clean up failed spectator
                if spectator:
                    try:
                        spectator.disconnect()
                    except:
                        pass
        except ConnectionError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure the host is running first")
            print("2. Check that the IP address is correct")
            print("3. Verify firewall settings allow UDP traffic")
            print("4. Ensure both computers are on the same network (or port forwarding is configured)")
            
            # Ask if user wants to retry with new values
            retry = input("\nWould you like to try again with different settings? (Y/N): ").strip().upper()
            if retry == 'Y':
                # Get new values
                host_ip = get_user_input("Enter host IP address", host_ip)
                port_str = get_user_input("Enter host port", str(host_port))
                try:
                    host_port = int(port_str)
                except:
                    print(f"Invalid port, keeping {host_port}")
                
                local_port_str = get_user_input("Enter your local port", str(local_port))
                try:
                    local_port = int(local_port_str)
                except:
                    print(f"Invalid port, keeping {local_port}")
                
                # Clean up failed spectator
                if spectator:
                    try:
                        spectator.disconnect()
                    except:
                        pass
            else:
                print("\nExiting...")
                return
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            retry = input("\nWould you like to try again? (Y/N): ").strip().upper()
            if retry != 'Y':
                print("\nExiting...")
                return
            # Clean up failed spectator
            if spectator:
                try:
                    spectator.disconnect()
                except:
                    pass
    print("\nWatching battle... (Press Ctrl+C to exit)")

    # Observation loop
    try:
        while True:
            result = spectator.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                spectator.handle_message(msg, addr)
                
                # Check for game over and rematch status
                if spectator.game_over:
                    # Wait for rematch decisions
                    print("\nWaiting for players to decide on rematch...")
                    timeout = time.time() + 30.0  # 30 second timeout
                    while (spectator.rematch_decisions["host"] is None or 
                           spectator.rematch_decisions["joiner"] is None) and time.time() < timeout:
                        result = spectator.receive_message(timeout=0.5)
                        if result:
                            msg, addr = result
                            spectator.handle_message(msg, addr)
                        spectator.process_reliability()
                        time.sleep(0.1)
                    
                    # Display rematch results
                    host_wants = spectator.rematch_decisions["host"]
                    joiner_wants = spectator.rematch_decisions["joiner"]
                    
                    if host_wants is not None and joiner_wants is not None:
                        if host_wants and joiner_wants:
                            print("\n✓ Both players want a rematch! Battle will restart...")
                            # Reset game over state and wait for new battle
                            spectator.game_over = False
                            spectator.winner = None
                            spectator.loser = None
                            spectator.rematch_decisions = {"host": None, "joiner": None}
                            spectator.host_hp = None
                            spectator.joiner_hp = None
                            print("\nWaiting for new battle to start...")
                        else:
                            print("\n✗ Rematch declined. Battle ended.")
                            if not host_wants:
                                print("  Host declined rematch")
                            if not joiner_wants:
                                print("  Joiner declined rematch")
                            break
                    elif time.time() >= timeout:
                        print("\n✗ Timeout waiting for rematch decisions. Battle ended.")
                        break
                    else:
                        # Still waiting, continue loop
                        continue
                        
            spectator.process_reliability()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nExiting spectator mode...")

    spectator.disconnect()


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - INTERACTIVE BATTLE CLIENT")
    print("="*60)

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("\nSelect mode:")
        print("1. Host - Start a battle and wait for others to join")
        print("2. Joiner - Connect to an existing battle")
        print("3. Spectator - Watch an ongoing battle")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == '1':
            mode = 'host'
        elif choice == '2':
            mode = 'joiner'
        elif choice == '3':
            mode = 'spectator'
        else:
            print("Invalid choice")
            return

    if mode == 'host':
        run_interactive_host()
    elif mode == 'joiner':
        run_interactive_joiner()
    elif mode == 'spectator':
        run_interactive_spectator()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python interactive_battle.py [host|joiner|spectator]")


if __name__ == "__main__":
    main()
