"""
Interactive PokeProtocol Battle

This script provides an interactive interface for running Pokémon battles
between two peers with user-friendly prompts for IP addresses and ports.
"""

import time
import sys
import select
import threading
import atexit
import queue
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from peer import HostPeer, JoinerPeer, SpectatorPeer
from game_data import MoveDatabase, PokemonDataLoader


# Global flag to track if report should be generated
_should_generate_report = False
_host_peer_instance = None
_live_report_active = False
_live_report_thread = None
_live_report_filename = None

# Capture script directory at module load time (before atexit might lose __file__)
try:
    _SCRIPT_DIR = Path(__file__).parent
except NameError:
    # Fallback if __file__ is not available
    _SCRIPT_DIR = Path.cwd() / 'scripts'

# Global chat input queue and thread control
_chat_input_queue = queue.Queue()
_chat_thread_active = False
_chat_thread = None


def _live_report_thread():
    """Background thread that periodically updates the live bug report."""
    global _live_report_active, _live_report_filename
    
    try:
        # Import here to avoid circular dependencies
        script_dir = _SCRIPT_DIR
        sys.path.insert(0, str(script_dir))
        sys.path.insert(0, str(script_dir.parent / 'src'))
        from generate_bug_report import BugReportGenerator
        
        generator = BugReportGenerator()
        
        # Update every 5 seconds
        update_interval = 5.0
        
        while _live_report_active:
            try:
                generator.update_live_report(_live_report_filename)
            except Exception as e:
                # Silently handle errors to avoid disrupting the main program
                pass
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(update_interval * 10)):
                if not _live_report_active:
                    break
                time.sleep(0.1)
    except Exception:
        # Silently handle errors
        pass


def start_live_bug_report():
    """Start the live bug report thread."""
    global _live_report_active, _live_report_thread, _live_report_filename
    
    if _live_report_active:
        return  # Already running
    
    try:
        # Import here to avoid circular dependencies
        script_dir = _SCRIPT_DIR
        sys.path.insert(0, str(script_dir))
        sys.path.insert(0, str(script_dir.parent / 'src'))
        from generate_bug_report import BugReportGenerator
        from datetime import datetime
        
        # Create initial report
        generator = BugReportGenerator()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _live_report_filename = f"live_bug_report_{timestamp}.txt"
        
        generator.update_live_report(_live_report_filename)
        
        # Start background thread
        _live_report_active = True
        _live_report_thread = threading.Thread(target=_live_report_thread, daemon=True)
        _live_report_thread.start()
        
        print(f"\n📊 Live bug report started!")
        print(f"   File: {_live_report_filename}")
        print(f"   Status: Updating every 5 seconds")
        print(f"   (You can open this file to view real-time updates)")
        
    except Exception as e:
        print(f"\n⚠ Could not start live bug report: {e}")


def stop_live_bug_report():
    """Stop the live bug report thread."""
    global _live_report_active, _live_report_thread
    
    if not _live_report_active:
        return
    
    _live_report_active = False
    if _live_report_thread:
        _live_report_thread.join(timeout=1.0)


def update_live_bug_report_now():
    """Immediately update the live bug report (called after important events)."""
    global _live_report_active, _live_report_filename
    
    if not _live_report_active or not _live_report_filename:
        return
    
    try:
        script_dir = _SCRIPT_DIR
        sys.path.insert(0, str(script_dir))
        sys.path.insert(0, str(script_dir.parent / 'src'))
        from generate_bug_report import BugReportGenerator
        
        generator = BugReportGenerator()
        generator.update_live_report(_live_report_filename)
    except Exception:
        # Silently handle errors
        pass


def _generate_auto_bug_report():
    """Automatically generate bug report when host closes."""
    global _should_generate_report, _live_report_filename
    
    # Stop live report first
    stop_live_bug_report()
    
    if not _should_generate_report:
        return
    
    # Prevent multiple generations
    _should_generate_report = False
    
    try:
        # Import here to avoid circular dependencies
        # generate_bug_report.py is in the scripts directory
        script_dir = _SCRIPT_DIR
        sys.path.insert(0, str(script_dir))
        sys.path.insert(0, str(script_dir.parent / 'src'))  # Also add src for debug_logger
        from generate_bug_report import BugReportGenerator
        
        print("\n" + "="*60)
        print("  GENERATING FINAL BUG REPORT...")
        print("="*60)
        
        generator = BugReportGenerator()
        filename = generator.save_report()
        
        print(f"\n✓ Bug report generated successfully!")
        print(f"  File: {filename}")
        if _live_report_filename:
            print(f"  Live report was saved to: {_live_report_filename}")
        print("="*60)
        
    except ImportError as e:
        print(f"\n⚠ Could not generate bug report: {e}")
        print("  Make sure scripts/generate_bug_report.py exists")
    except Exception as e:
        print(f"\n⚠ Error generating bug report: {e}")
        import traceback
        traceback.print_exc()


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
    import sys
    loader = PokemonDataLoader()

    print("\n=== Select Your Pokémon ===")
    print("Enter a Pokémon name, or type 'list' to see available Pokémon")
    sys.stdout.flush()  # Ensure prompt is visible

    while True:
        pokemon_name = input("Pokémon name: ").strip()

        if pokemon_name.lower() == 'list':
            print("\nAvailable Pokémon (showing first 30):")
            names = loader.get_all_pokemon_names()
            for i, name in enumerate(names[:30], 1):
                print(f"{i}. {name}")
            print(f"\n... and {len(names) - 30} more")
            print()  # Add blank line before next prompt
            sys.stdout.flush()  # Ensure output is visible before next prompt
            continue

        pokemon = loader.get_pokemon(pokemon_name)
        if pokemon:
            print(f"Selected: {pokemon.name} (HP: {pokemon.hp}, Type: {pokemon.type1}/{pokemon.type2 or 'None'})")
            return pokemon.name
        else:
            print(f"Pokémon '{pokemon_name}' not found. Try again or type 'list'.")
            print()  # Add blank line before next prompt
            sys.stdout.flush()  # Ensure output is visible before next prompt


def select_move():
    """Allow user to select a move."""
    # Stop chat thread to avoid stdin conflicts
    stop_chat_input_thread()
    
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
            result = moves[idx]
            # Restart chat thread after input (chat is disabled during battle anyway)
            # start_chat_input_thread will check if already running
            return result
    except:
        pass

    result = moves[0]
    return result


def clear_input_stream():
    """Clear any pending input from stdin buffer."""
    try:
        import msvcrt
        # Windows: Clear stdin buffer more aggressively
        # Read all available characters from keyboard buffer
        cleared = 0
        while msvcrt.kbhit():
            try:
                msvcrt.getch()
                cleared += 1
            except:
                break
        # Also try to flush stdin if possible
        try:
            sys.stdin.flush()
        except:
            pass
    except ImportError:
        # Unix/Linux: Use termios to flush input
        try:
            import termios
            # Flush pending input (TCIOFLUSH flushes both input and output)
            termios.tcflush(sys.stdin, termios.TCIFLUSH)  # Only flush input
        except (ImportError, AttributeError):
            # Fallback: Try to read any available input non-blocking
            try:
                import select
                # Clear any available input
                while True:
                    ready, _, _ = select.select([sys.stdin], [], [], 0)
                    if not ready:
                        break
                    try:
                        # Read one character at a time until buffer is empty
                        char = sys.stdin.read(1)
                        if not char:
                            break
                    except:
                        break
            except:
                # If all else fails, try to flush stdin
                try:
                    sys.stdin.flush()
                except:
                    pass
    except Exception:
        # If clearing fails, just continue silently
        pass


def _chat_input_thread(peer, player_name):
    """
    Background thread that continuously reads input for chat messages.
    Looks for /chat <message> format and /endchat command.
    """
    global _chat_thread_active
    while _chat_thread_active:
        try:
            # Read input (this will block, but that's okay in a separate thread)
            user_input = input().strip()
            
            # Check for /endchat command
            if user_input.lower() == '/endchat':
                if hasattr(peer, 'chat_enabled') and peer.chat_enabled:
                    peer.chat_enabled = False
                    # Notify other players
                    if hasattr(peer, 'send_chat_state_notification'):
                        peer.send_chat_state_notification(player_name, "ended chat session")
                    print(f"\n[SYSTEM] You ended the chat session.")
                    # Clear input stream to prevent leftover input from interfering with battle
                    # Call multiple times to ensure buffer is fully cleared
                    clear_input_stream()
                    time.sleep(0.1)  # Small delay to allow buffer to settle
                    clear_input_stream()  # Clear again after delay
                    sys.stdout.flush()  # Ensure output is flushed
                else:
                    print(f"\n[SYSTEM] Chat is already disabled.")
                    # Still clear buffer even if chat wasn't enabled
                    clear_input_stream()
                continue
            
            # Check for /chat command
            if user_input.startswith('/chat '):
                message = user_input[6:].strip()  # Remove '/chat ' prefix
                if message:
                    # Check if chat is enabled
                    if hasattr(peer, 'chat_enabled') and not peer.chat_enabled:
                        print(f"\n[SYSTEM] Chat is disabled. Type '/startchat' to enable chat.")
                        continue
                    try:
                        peer.send_chat_message(player_name, message)
                        print(f"[You]: {message}")
                    except Exception as e:
                        print(f"Error sending chat: {e}")
            elif user_input.startswith('/chat'):
                # Handle /chat without space
                message = user_input[5:].strip()
                if message:
                    # Check if chat is enabled
                    if hasattr(peer, 'chat_enabled') and not peer.chat_enabled:
                        print(f"\n[SYSTEM] Chat is disabled. Type '/startchat' to enable chat.")
                        continue
                    try:
                        peer.send_chat_message(player_name, message)
                        print(f"[You]: {message}")
                    except Exception as e:
                        print(f"Error sending chat: {e}")
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            # Ignore other errors and continue
            pass


def start_chat_input_thread(peer, player_name):
    """Start the background chat input thread."""
    global _chat_thread_active, _chat_thread
    
    if _chat_thread_active:
        return  # Already running
    
    _chat_thread_active = True
    _chat_thread = threading.Thread(target=_chat_input_thread, args=(peer, player_name), daemon=True)
    _chat_thread.start()


def run_pre_battle_chat(peer, player_name, opponent_name):
    """
    Run pre-battle chat session with voting.
    
    Args:
        peer: The peer (host or joiner)
        player_name: Name of this player
        opponent_name: Name of the opponent
    """
    print("\n" + "="*60)
    print("  PRE-BATTLE CHAT SESSION")
    print("="*60)
    print("Both players must agree to start chatting.")
    print("Type '/endchat' at any time to end the chat session.")
    print("="*60)
    
    # Ask if this player wants to enable chat
    response = input(f"\nDo you want to enable chat? (Y/N, default: N): ").strip().upper()
    if response == 'Y':
        peer.chat_enabled = True
        print(f"\n[SYSTEM] You enabled chat. Chat is now active!")
        print(f"[SYSTEM] Type '/chat <message>' to send messages.")
        print(f"[SYSTEM] Type '/endchat' to end the chat session.")
        
        # Restart chat thread now that chat is enabled
        start_chat_input_thread(peer, player_name)
        
        # Chat session loop (until battle starts or user ends chat)
        print(f"\n[SYSTEM] Chat session active. Waiting for battle to start...")
        while peer.chat_enabled:
            result = peer.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                peer.handle_message(msg, addr)
            peer.process_reliability()
            time.sleep(0.1)
        
        if not peer.chat_enabled:
            print(f"\n[SYSTEM] Chat session ended.")
    else:
        print(f"\n[SYSTEM] Chat disabled. Proceeding to battle setup...")
        peer.chat_enabled = False


def stop_chat_input_thread():
    """Stop the background chat input thread."""
    global _chat_thread_active
    _chat_thread_active = False


def check_chat_input(prompt="Type 'chat' to send a message, or press Enter to continue: "):
    """
    Check if user wants to send a chat message (non-blocking check).
    Returns message text if user wants to chat, None otherwise.
    """
    try:
        # On Windows, we can't use select on stdin, so we'll use a different approach
        # For simplicity, we'll make it a blocking call but with a clear prompt
        user_input = input(prompt).strip()
        if user_input.lower() == 'chat' or user_input.startswith('/'):
            if user_input.startswith('/'):
                # Allow /message format
                return user_input[1:].strip()
            else:
                chat_msg = input("Enter your chat message: ").strip()
                return chat_msg if chat_msg else None
        return None
    except (EOFError, KeyboardInterrupt):
        return None


def run_interactive_host():
    """Run host with interactive prompts."""
    global _should_generate_report, _host_peer_instance
    
    # Enable automatic bug report generation
    _should_generate_report = True
    
    # Start live bug report
    start_live_bug_report()
    
    # Register cleanup function to generate report on exit
    atexit.register(_generate_auto_bug_report)
    
    print("\n" + "="*60)
    print("  POKEPROTOCOL - HOST MODE")
    print("="*60)
    print("  (Live bug report is updating in real-time)")
    print("  (Final bug report will be generated on exit)")
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
            _host_peer_instance = host  # Store for cleanup
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
                    print("\nGenerating bug report...")
                    _generate_auto_bug_report()
                    return
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            retry = input("Would you like to try again? (Y/N): ").strip().upper()
            if retry != 'Y':
                print("\nExiting...")
                return

    # Set up chat callback
    def on_chat_received(sender_name, message_text):
        # Only show chat messages if chat is enabled
        if sender_name == "SYSTEM" or (hasattr(host, 'chat_enabled') and host.chat_enabled):
            print(f"\n[CHAT] {sender_name}: {message_text}")
    
    host.on_chat_message = on_chat_received

    # Don't start chat thread yet - it will be started only if chat is enabled
    # This prevents stdin conflicts with other input operations
    player_name = "Host"

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
        host.disconnect()
        print("\nGenerating bug report...")
        _generate_auto_bug_report()
        return

    print("\n✓ Joiner connected!")
    
    # Update live bug report after connection
    update_live_bug_report_now()
    
    # Pre-battle chat session
    run_pre_battle_chat(host, "Host", "Joiner")
    
    # Disable chat before battle starts
    host.chat_enabled = False
    
    # Clear input stream before battle to prevent leftover input
    clear_input_stream()
    
    # Select Pokémon (chat thread not running, so no conflict)
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
        host.disconnect()
        print("\nGenerating bug report...")
        _generate_auto_bug_report()
        return

    # Battle loop
    print("\n" + "="*60)
    print("  BATTLE START!")
    print("="*60)
    print("[SYSTEM] Chat is disabled during battle.")

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
        
        # Update live bug report when battle ends
        update_live_bug_report_now()
        
        # Stop chat thread before input prompts
        stop_chat_input_thread()
        
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
        
        # Re-enable chat after battle (if players want to chat)
        print(f"\n[SYSTEM] Battle ended. Chat can be re-enabled.")
        response = input("Do you want to enable chat? (Y/N, default: N): ").strip().upper()
        if response == 'Y':
            host.chat_enabled = True
            # Start chat thread now that chat is enabled
            start_chat_input_thread(host, "Host")
            print(f"\n[SYSTEM] Chat enabled! Type '/chat <message>' to send messages.")
            print(f"[SYSTEM] Type '/endchat' to end the chat session.")
        
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
            # Don't disconnect or generate report - we're continuing to a new battle
            # The report will be generated when the final battle ends
            run_interactive_host()
            return
        elif not wants_rematch:
            print("\nYou declined the rematch. Thanks for playing!")
        elif host.opponent_wants_rematch is None:
            print("\nTimeout waiting for opponent's response. Disconnecting...")
        else:
            print("\nOpponent declined the rematch. Thanks for playing!")

    # Stop chat thread
    stop_chat_input_thread()
    
    print("\nDisconnecting...")
    host.disconnect()
    
    # Generate bug report automatically when host closes
    print("\nGenerating bug report...")
    _generate_auto_bug_report()


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

    # Set up chat callback
    def on_chat_received(sender_name, message_text):
        print(f"\n[CHAT] {sender_name}: {message_text}")
    
    # Retry loop for connection
    connected = False
    joiner = None
    while not connected:
        try:
            print(f"\nInitializing joiner on port {local_port}...")
            if joiner is None:
                joiner = JoinerPeer(port=local_port)
                joiner.on_chat_message = on_chat_received
                joiner.start_listening()

            # Connect to host
            print(f"Connecting to host at {host_ip}:{host_port}...")
            joiner.connect(host_ip, host_port)
            connected = True
            print("✓ Connected to host!")
            
            # Start chat input thread (but chat is disabled by default)
            player_name = "Joiner"
            start_chat_input_thread(joiner, player_name)
            
            # Pre-battle chat session
            run_pre_battle_chat(joiner, "Joiner", "Host")
            
            # Disable chat before battle starts
            joiner.chat_enabled = False
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
                    print("\nGenerating bug report...")
                    _generate_auto_bug_report()
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

    # Clear input stream before battle to prevent leftover input
    clear_input_stream()
    
    # Select Pokémon (chat thread not running, so no conflict)
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
    print("[SYSTEM] Chat is disabled during battle.")

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
                joiner.battle_state.mark_my_turn_taken(move)
        else:
            # Not our turn - allow chat input (simplified for Windows compatibility)
            pass

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
        
        # Stop chat thread before input prompts
        stop_chat_input_thread()
        
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
        
        # Re-enable chat after battle (if players want to chat)
        print(f"\n[SYSTEM] Battle ended. Chat can be re-enabled.")
        response = input("Do you want to enable chat? (Y/N, default: N): ").strip().upper()
        if response == 'Y':
            joiner.chat_enabled = True
            # Start chat thread now that chat is enabled
            start_chat_input_thread(joiner, "Joiner")
            print(f"\n[SYSTEM] Chat enabled! Type '/chat <message>' to send messages.")
            print(f"[SYSTEM] Type '/endchat' to end the chat session.")
        
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

    # Stop chat thread
    stop_chat_input_thread()
    
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
            
            # Set up chat callback
            def on_chat_received(sender_name, message_text):
                print(f"\n[CHAT] {sender_name}: {message_text}")

            spectator.on_battle_update = on_battle_update
            spectator.on_chat_message = on_chat_received

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
                    print("\nGenerating bug report...")
                    _generate_auto_bug_report()
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
    print("\nWatching battle... (Type '/chat <message>' to send a message, Press Ctrl+C to exit)")
    player_name = "Spectator"

    # Start chat input thread for continuous chat
    start_chat_input_thread(spectator, player_name)

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
    
    # Stop chat thread
    stop_chat_input_thread()
    
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
