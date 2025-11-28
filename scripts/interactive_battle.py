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


def get_user_input(prompt, default=None, validator_func=None):
    """Get user input with optional default value and validation."""
    if validator_func:
        return get_validated_input(prompt, validator_func, default=default)
    
    if default:
        prompt_text = f"{prompt} (default: {default}): "
    else:
        prompt_text = f"{prompt}: "

    user_input = input(prompt_text).strip()
    if not user_input and default:
        return default
    return user_input


def get_validated_input(prompt, validator_func, error_message="Invalid input. Please try again.", default=None):
    """
    Get user input with validation.
    
    Args:
        prompt: The prompt to display
        validator_func: Function that takes input string and returns (is_valid, value_or_error)
        error_message: Message to display on invalid input
        default: Default value if input is empty
        
    Returns:
        Validated input value
    """
    while True:
        try:
            if default:
                prompt_text = f"{prompt} (default: {default}): "
            else:
                prompt_text = f"{prompt}: "
            
            user_input = input(prompt_text).strip()
            
            # Use default if empty and default provided
            if not user_input and default is not None:
                return default
            
            # Validate input
            is_valid, result = validator_func(user_input)
            if is_valid:
                return result
            else:
                print(f"✗ {error_message if error_message else result}")
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as e:
            print(f"✗ Error: {e}. Please try again.")


def validate_integer(input_str, min_val=None, max_val=None):
    """Validate integer input within optional range."""
    try:
        value = int(input_str)
        if min_val is not None and value < min_val:
            return False, f"Value must be at least {min_val}"
        if max_val is not None and value > max_val:
            return False, f"Value must be at most {max_val}"
        return True, value
    except ValueError:
        return False, "Please enter a valid integer"


def validate_choice(input_str, valid_choices, case_sensitive=False):
    """Validate input is one of the valid choices."""
    if not case_sensitive:
        input_str = input_str.upper()
        valid_choices = [c.upper() if isinstance(c, str) else c for c in valid_choices]
    
    if input_str in valid_choices:
        return True, input_str
    return False, f"Please enter one of: {', '.join(str(c) for c in valid_choices)}"


def validate_port(input_str):
    """Validate port number (1-65535)."""
    return validate_integer(input_str, min_val=1, max_val=65535)


def validate_yes_no(input_str):
    """Validate Y/N input."""
    upper_input = input_str.upper()
    if upper_input in ['Y', 'YES', 'N', 'NO']:
        return True, upper_input in ['Y', 'YES']
    return False, "Please enter Y or N"


def validate_non_empty(input_str):
    """Validate input is not empty."""
    if input_str.strip():
        return True, input_str.strip()
    return False, "Input cannot be empty"


def select_pokemon():
    """Allow user to select a Pokémon with pagination support."""
    import sys
    loader = PokemonDataLoader()
    names = loader.get_all_pokemon_names()
    total_pokemon = len(names)
    items_per_page = 30

    print("\n=== Select Your Pokémon ===")
    print("Enter a Pokémon name, or type 'list' to see available Pokémon")
    sys.stdout.flush()  # Ensure prompt is visible

    while True:
        pokemon_input = input("Pokémon name: ").strip()

        if pokemon_input.lower() == 'list':
            # Pagination mode
            current_page = 0
            total_pages = (total_pokemon + items_per_page - 1) // items_per_page
            
            while True:
                start_idx = current_page * items_per_page
                end_idx = min(start_idx + items_per_page, total_pokemon)
                page_names = names[start_idx:end_idx]
                
                print(f"\n=== Available Pokémon (Page {current_page + 1} of {total_pages}) ===")
                for i, name in enumerate(page_names, start=start_idx + 1):
                    print(f"{i}. {name}")
                
                # Show navigation options
                nav_options = []
                if current_page > 0:
                    nav_options.append("P or Previous - Go to previous page")
                if current_page < total_pages - 1:
                    nav_options.append("N or Next - Go to next page")
                nav_options.append(f"# - Select Pokémon by index (1-{total_pokemon})")
                nav_options.append("Q or Quit - Exit list view")
                
                print(f"\nNavigation:")
                for opt in nav_options:
                    print(f"  {opt}")
                
                nav_input = input("\nEnter command: ").strip()
                
                nav_upper = nav_input.upper()
                
                # Handle navigation commands (circular pagination)
                if nav_upper in ['N', 'NEXT']:
                    current_page = (current_page + 1) % total_pages
                elif nav_upper in ['P', 'PREVIOUS', 'PREV']:
                    current_page = (current_page - 1) % total_pages
                elif nav_upper in ['Q', 'QUIT', 'EXIT']:
                    print("Exiting list view.")
                    break
                elif nav_input.isdigit():
                    # User entered a number - try to select Pokémon
                    idx = int(nav_input)
                    if 1 <= idx <= total_pokemon:
                        selected_name = names[idx - 1]
                        pokemon = loader.get_pokemon(selected_name)
                        if pokemon:
                            print(f"\nSelected: {pokemon.name} (HP: {pokemon.hp}, Type: {pokemon.type1}/{pokemon.type2 or 'None'})")
                            return pokemon.name
                        else:
                            print(f"✗ Pokémon at index {idx} not found.")
                    else:
                        print(f"✗ Please enter a number between 1 and {total_pokemon}.")
                else:
                    # Try to interpret as Pokémon name
                    pokemon = loader.get_pokemon(nav_input)
                    if pokemon:
                        print(f"\nSelected: {pokemon.name} (HP: {pokemon.hp}, Type: {pokemon.type1}/{pokemon.type2 or 'None'})")
                        return pokemon.name
                    else:
                        print(f"✗ Invalid command or Pokémon name. Please try again.")
            
            # After exiting list view, continue to main loop
            continue

        # Try to find Pokémon by name
        pokemon = loader.get_pokemon(pokemon_input)
        if pokemon:
            print(f"Selected: {pokemon.name} (HP: {pokemon.hp}, Type: {pokemon.type1}/{pokemon.type2 or 'None'})")
            return pokemon.name
        else:
            print(f"✗ Pokémon '{pokemon_input}' not found. Try again or type 'list'.")
            print()  # Add blank line before next prompt
            sys.stdout.flush()  # Ensure output is visible before next prompt


def select_move(pokemon_name=None):
    """Allow user to select a move."""
    # Stop chat thread to avoid stdin conflicts
    stop_chat_input_thread()
    
    move_db = MoveDatabase()
    loader = PokemonDataLoader()

    # Get Pokémon data if provided
    pokemon = None
    if pokemon_name:
        pokemon = loader.get_pokemon(pokemon_name)
    
    # Filter moves based on Pokémon types if Pokémon is provided
    available_moves = []
    if pokemon:
        # Get moves matching Pokémon's types
        type1_moves = move_db.get_moves_by_type(pokemon.type1)
        available_moves.extend(type1_moves)
        
        if pokemon.type2:
            type2_moves = move_db.get_moves_by_type(pokemon.type2)
            # Add type2 moves, avoiding duplicates
            for move in type2_moves:
                if move not in available_moves:
                    available_moves.append(move)
        
        # If no moves found for Pokémon types, fall back to all moves
        if not available_moves:
            available_moves = [move_db.get_move(name) for name in move_db.get_all_move_names()]
            available_moves = [m for m in available_moves if m is not None]
    
    # If no Pokémon provided or no matching moves, show all moves grouped by type
    if not available_moves:
        print("\nYour turn! Select a move:")
        print("1. Quick Attack (Electric moves)")
        print("2. Strong Attack (Fire moves)")
        print("3. Special Attack (Water moves)")
        print("4. Custom move name")

        choice = get_validated_input(
            "Enter choice (1-4)",
            lambda x: validate_integer(x, min_val=1, max_val=4),
            "Please enter a number between 1 and 4"
        )

        if choice == 1:
            moves = ['Thunder Shock', 'Thunderbolt', 'Spark']
        elif choice == 2:
            moves = ['Ember', 'Flame Thrower', 'Fire Blast']
        elif choice == 3:
            moves = ['Water Gun', 'Bubble Beam', 'Hydro Pump']
        elif choice == 4:
            move_name = get_validated_input(
                "Enter move name",
                validate_non_empty,
                "Move name cannot be empty"
            )
            return move_name

        for i, move_name in enumerate(moves, 1):
            move = move_db.get_move(move_name)
            if move:
                print(f"{i}. {move_name} (Power: {move.power}, Type: {move.move_type})")

        move_choice = get_validated_input(
            f"Select move (1-{len(moves)})",
            lambda x: validate_integer(x, min_val=1, max_val=len(moves)),
            f"Please enter a number between 1 and {len(moves)}"
        )
        
        result = moves[move_choice - 1]
        return result
    else:
        # Show moves matching Pokémon types
        print(f"\nYour turn! Select a move for {pokemon.name}:")
        print(f"Available moves (matching {pokemon.type1}" + (f"/{pokemon.type2}" if pokemon.type2 else "") + " types):")
        
        # Limit to first 20 moves to avoid overwhelming the user
        display_moves = available_moves[:20]
        for i, move in enumerate(display_moves, 1):
            print(f"{i}. {move.name} (Power: {move.power}, Type: {move.move_type})")
        
        if len(available_moves) > 20:
            print(f"... and {len(available_moves) - 20} more moves")
            print("(You can also type the move name directly)")
        
        print(f"{len(display_moves) + 1}. Enter custom move name")
        
        move_choice = get_validated_input(
            f"Select move (1-{len(display_moves) + 1})",
            lambda x: validate_integer(x, min_val=1, max_val=len(display_moves) + 1),
            f"Please enter a number between 1 and {len(display_moves) + 1}"
        )
        
        if move_choice <= len(display_moves):
            return display_moves[move_choice - 1].name
        else:
            # Custom move name option
            move_name = get_validated_input(
                "Enter move name",
                validate_non_empty,
                "Move name cannot be empty"
            )
            move = move_db.get_move(move_name)
            if move:
                return move.name
            else:
                print(f"✗ Move '{move_name}' not found, using {display_moves[0].name}")
                return display_moves[0].name


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
    response = get_validated_input(
        "\nDo you want to enable chat? (Y/N)",
        validate_yes_no,
        "Please enter Y or N",
        default=False
    )
    if response:
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
    global _chat_thread_active, _chat_thread
    _chat_thread_active = False
    # Give the thread a moment to exit (it's waiting on input() which will raise EOFError)
    if _chat_thread and _chat_thread.is_alive():
        # Small delay to allow thread to exit gracefully
        import time
        time.sleep(0.1)


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

def run_host_battle_loop(host):
    """Run a single battle loop for the host. Can be called multiple times for rematches."""
    # Pre-battle chat session (only on first battle)
    if not hasattr(host, '_battle_count') or host._battle_count == 0:
        run_pre_battle_chat(host, "Host", "Joiner")
        host._battle_count = 0
    
    host._battle_count += 1
    
    # Disable chat before battle starts
    host.chat_enabled = False
    
    # Stop chat thread before battle to prevent stdin conflicts
    stop_chat_input_thread()
    # Clear input stream before battle to prevent leftover input
    clear_input_stream()
    
    # Select Pokémon (chat thread not running, so no conflict)
    pokemon_name = select_pokemon()

    # Check if opponent already selected (they might have sent BattleSetup while we were in chat)
    # Preserve if opponent_pokemon exists and state is SETUP or WAITING_FOR_MOVE (not GAME_OVER from previous battle)
    opponent_already_selected = (host.battle_state and 
                                  host.battle_state.opponent_pokemon is not None and
                                  host.battle_state.state.value != "GAME_OVER")
    
    # Preserve opponent_pokemon if it exists before resetting
    preserved_opponent = None
    if opponent_already_selected:
        preserved_opponent = host.battle_state.opponent_pokemon

    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    host.start_battle(pokemon_name)
    
    # Restore opponent_pokemon if it was preserved (opponent selected before us)
    # Reset HP to full when restoring to prevent fainted Pokémon from previous battle
    if preserved_opponent and host.battle_state:
        # Create a fresh BattlePokemon with full HP
        from battle import BattlePokemon
        fresh_opponent = BattlePokemon(
            preserved_opponent.pokemon,
            preserved_opponent.special_attack_uses,
            preserved_opponent.special_defense_uses
        )
        host.battle_state.opponent_pokemon = fresh_opponent
        host.battle_state.advance_to_waiting()

    # Wait for opponent's Pokémon - check if both Pokémon are set (via network messages)
    if not (host.battle_state and 
            host.battle_state.my_pokemon and 
            host.battle_state.opponent_pokemon):
        print("Waiting for opponent to select Pokémon...")
        timeout = time.time() + 60.0
        while time.time() < timeout:
            # Check if both Pokémon are set (indicates both players have selected and exchanged messages)
            if (host.battle_state and 
                host.battle_state.my_pokemon and 
                host.battle_state.opponent_pokemon):
                # Both Pokémon are set, we're ready
                break
            
            # Process messages while waiting (this handles receiving opponent's BattleSetup)
            result = host.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                host.handle_message(msg, addr)
            host.process_reliability()
            time.sleep(0.1)
        
        # Verify both Pokémon are set
        if not (host.battle_state and 
                host.battle_state.my_pokemon and 
                host.battle_state.opponent_pokemon):
            print("Timeout waiting for opponent's Pokémon")
            return False

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

            move_name = select_move(host.my_pokemon.pokemon.name if host.my_pokemon else None)
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
        wants_rematch = get_validated_input(
            "\nStart a new battle? (Y/N)",
            validate_yes_no,
            "Please enter Y or N"
        )
        
        # Send rematch request to opponent
        from messages import RematchRequest
        rematch_msg = RematchRequest(wants_rematch, host.reliability.get_next_sequence_number())
        host.send_message(rematch_msg)
        # Broadcast to spectators
        host._broadcast_to_spectators(rematch_msg)
        print(f"\nWaiting for opponent's response...")
        
        # Re-enable chat after battle (if players want to chat)
        print(f"\n[SYSTEM] Battle ended. Chat can be re-enabled.")
        response = get_validated_input(
            "Do you want to enable chat? (Y/N)",
            validate_yes_no,
            "Please enter Y or N",
            default=False
        )
        if response:
            host.chat_enabled = True
            # Start chat thread now that chat is enabled
            start_chat_input_thread(host, "Host")
            print(f"\n[SYSTEM] Chat enabled! Type '/chat <message>' to send messages.")
            print(f"[SYSTEM] Type '/endchat' to end the chat session.")
        
        # Wait for opponent's rematch response
        timeout = time.time() + 60.0  # 60 second timeout
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
            # Reset rematch flags for next battle
            host.opponent_wants_rematch = None
            # Restart battle loop without re-initializing connection
            return run_host_battle_loop(host)
        elif not wants_rematch:
            print("\nYou declined the rematch.")
            # If chat is enabled, keep the session alive
            if host.chat_enabled:
                print("Chat session is active. Type '/endchat' to end the session and disconnect.")
                # Keep processing messages while chat is active
                while host.chat_enabled:
                    try:
                        result = host.receive_message(timeout=0.5)
                        if result:
                            msg, addr = result
                            host.handle_message(msg, addr)
                        host.process_reliability()
                        time.sleep(0.1)
                    except (EOFError, KeyboardInterrupt):
                        break
                print("\nChat session ended. Thanks for playing!")
            else:
                print("Thanks for playing!")
            return False
        elif host.opponent_wants_rematch is None:
            print("\nTimeout waiting for opponent's response. Disconnecting...")
            return False
        else:
            print("\nOpponent declined the rematch.")
            # If chat is enabled, keep the session alive
            if host.chat_enabled:
                print("Chat session is active. Type '/endchat' to end the session and disconnect.")
                # Keep processing messages while chat is active
                while host.chat_enabled:
                    try:
                        result = host.receive_message(timeout=0.5)
                        if result:
                            msg, addr = result
                            host.handle_message(msg, addr)
                        host.process_reliability()
                        time.sleep(0.1)
                    except (EOFError, KeyboardInterrupt):
                        break
                print("\nChat session ended. Thanks for playing!")
            else:
                print("Thanks for playing!")
            return False
    
    return False

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
        port = get_user_input(
            "Enter port to listen on",
            "8888" if port is None else str(port),
            validator_func=lambda x: validate_port(x)
        )

        try:
            print(f"\nInitializing host on port {port}...")
            host = HostPeer(port=port)
            _host_peer_instance = host  # Store for cleanup
            host.start_listening()
        except OSError as e:
            error_str = str(e)
            if "Address already in use" in error_str or "10048" in error_str or "EADDRINUSE" in error_str or "WSAEADDRINUSE" in error_str:
                print(f"\n✗ Port {port} is already in use!")
                retry = get_validated_input(
                    "Would you like to try a different port? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if not retry:
                    print("\nExiting...")
                    return
            else:
                print(f"\n✗ Error initializing host: {e}")
                retry = get_validated_input(
                    "Would you like to try again? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if not retry:
                    print("\nExiting...")
                    print("\nGenerating bug report...")
                    _generate_auto_bug_report()
                    return
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            retry = get_validated_input(
                "Would you like to try again? (Y/N)",
                validate_yes_no,
                "Please enter Y or N"
            )
            if not retry:
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

    timeout = time.time() + 120.0  # 120 second timeout
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
    
    # Initialize battle count
    host._battle_count = 0
    
    # Run battle loop (will handle rematches internally)
    run_host_battle_loop(host)

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
    host_port = get_user_input(
        "Enter host port",
        "8888",
        validator_func=lambda x: validate_port(x)
    )

    # Get local port
    local_port = get_user_input(
        "Enter your local port",
        "8889",
        validator_func=lambda x: validate_port(x)
    )

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
        except OSError as e:
            error_str = str(e)
            if "Address already in use" in error_str or "10048" in error_str or "EADDRINUSE" in error_str or "WSAEADDRINUSE" in error_str:
                print(f"\n✗ Port {local_port} is already in use!")
                retry = get_validated_input(
                    "Would you like to try a different local port? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if retry:
                    local_port = get_user_input(
                        "Enter your local port",
                        str(local_port),
                        validator_func=lambda x: validate_port(x)
                    )
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
                retry = get_validated_input(
                    "Would you like to try again? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if not retry:
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

    # Initialize battle count
    joiner._battle_count = 0
    
    # Run battle loop (will handle rematches internally)
    run_joiner_battle_loop(joiner)

    # Stop chat thread
    stop_chat_input_thread()
    
    print("\nDisconnecting...")
    joiner.disconnect()


def run_joiner_battle_loop(joiner):
    """Run a single battle loop for the joiner. Can be called multiple times for rematches."""
    # Pre-battle chat session (only on first battle)
    if not hasattr(joiner, '_battle_count') or joiner._battle_count == 0:
        run_pre_battle_chat(joiner, "Joiner", "Host")
        joiner._battle_count = 0
    
    joiner._battle_count += 1
    
    # Disable chat before battle starts
    joiner.chat_enabled = False
    
    # Stop chat thread before battle to prevent stdin conflicts
    stop_chat_input_thread()
    # Clear input stream before battle to prevent leftover input
    clear_input_stream()
    
    # Select Pokémon (chat thread not running, so no conflict)
    pokemon_name = select_pokemon()

    # Check if opponent already selected (they might have sent BattleSetup while we were in chat)
    # Preserve if opponent_pokemon exists and state is SETUP or WAITING_FOR_MOVE (not GAME_OVER from previous battle)
    opponent_already_selected = (joiner.battle_state and 
                                  joiner.battle_state.opponent_pokemon is not None and
                                  joiner.battle_state.state.value != "GAME_OVER")
    
    # Preserve opponent_pokemon if it exists before resetting
    preserved_opponent = None
    if opponent_already_selected:
        preserved_opponent = joiner.battle_state.opponent_pokemon

    # Start battle
    print(f"\nStarting battle with {pokemon_name}...")
    joiner.start_battle(pokemon_name)
    
    # Restore opponent_pokemon if it was preserved (opponent selected before us)
    # Reset HP to full when restoring to prevent fainted Pokémon from previous battle
    if preserved_opponent and joiner.battle_state:
        # Create a fresh BattlePokemon with full HP
        from battle import BattlePokemon
        fresh_opponent = BattlePokemon(
            preserved_opponent.pokemon,
            preserved_opponent.special_attack_uses,
            preserved_opponent.special_defense_uses
        )
        joiner.battle_state.opponent_pokemon = fresh_opponent
        joiner.battle_state.advance_to_waiting()

    # Wait for opponent's Pokémon - check if both Pokémon are set (via network messages)
    if not (joiner.battle_state and 
            joiner.battle_state.my_pokemon and 
            joiner.battle_state.opponent_pokemon):
        print("Waiting for opponent to select Pokémon...")
        timeout = time.time() + 60.0
        while time.time() < timeout:
            # Check if both Pokémon are set (indicates both players have selected and exchanged messages)
            if (joiner.battle_state and 
                joiner.battle_state.my_pokemon and 
                joiner.battle_state.opponent_pokemon):
                # Both Pokémon are set, we're ready
                break
            
            # Process messages while waiting (this handles receiving opponent's BattleSetup)
            result = joiner.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                joiner.handle_message(msg, addr)
            joiner.process_reliability()
            time.sleep(0.1)
        
        # Verify both Pokémon are set
        if not (joiner.battle_state and 
                joiner.battle_state.my_pokemon and 
                joiner.battle_state.opponent_pokemon):
            print("Timeout waiting for opponent's Pokémon")
            return False

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

            move_name = select_move(joiner.my_pokemon.pokemon.name if joiner.my_pokemon else None)
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
        wants_rematch = get_validated_input(
            "\nStart a new battle? (Y/N)",
            validate_yes_no,
            "Please enter Y or N"
        )
        
        # Send rematch request to opponent
        from messages import RematchRequest
        rematch_msg = RematchRequest(wants_rematch, joiner.reliability.get_next_sequence_number())
        joiner.send_message(rematch_msg)
        print(f"\nWaiting for opponent's response...")
        
        # Re-enable chat after battle (if players want to chat)
        print(f"\n[SYSTEM] Battle ended. Chat can be re-enabled.")
        response = get_validated_input(
            "Do you want to enable chat? (Y/N)",
            validate_yes_no,
            "Please enter Y or N",
            default=False
        )
        if response:
            joiner.chat_enabled = True
            # Start chat thread now that chat is enabled
            start_chat_input_thread(joiner, "Joiner")
            print(f"\n[SYSTEM] Chat enabled! Type '/chat <message>' to send messages.")
            print(f"[SYSTEM] Type '/endchat' to end the chat session.")
        
        # Wait for opponent's rematch response
        timeout = time.time() + 60.0  # 60 second timeout
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
            # Reset rematch flags for next battle
            joiner.opponent_wants_rematch = None
            # Restart battle loop without re-initializing connection
            return run_joiner_battle_loop(joiner)
        elif not wants_rematch:
            print("\nYou declined the rematch.")
            # If chat is enabled, keep the session alive
            if joiner.chat_enabled:
                print("Chat session is active. Type '/endchat' to end the session and disconnect.")
                # Keep processing messages while chat is active
                while joiner.chat_enabled:
                    try:
                        result = joiner.receive_message(timeout=0.5)
                        if result:
                            msg, addr = result
                            joiner.handle_message(msg, addr)
                        joiner.process_reliability()
                        time.sleep(0.1)
                    except (EOFError, KeyboardInterrupt):
                        break
                print("\nChat session ended. Thanks for playing!")
            else:
                print("Thanks for playing!")
            return False
        elif joiner.opponent_wants_rematch is None:
            print("\nTimeout waiting for opponent's response. Disconnecting...")
            return False
        else:
            print("\nOpponent declined the rematch.")
            # If chat is enabled, keep the session alive
            if joiner.chat_enabled:
                print("Chat session is active. Type '/endchat' to end the session and disconnect.")
                # Keep processing messages while chat is active
                while joiner.chat_enabled:
                    try:
                        result = joiner.receive_message(timeout=0.5)
                        if result:
                            msg, addr = result
                            joiner.handle_message(msg, addr)
                        joiner.process_reliability()
                        time.sleep(0.1)
                    except (EOFError, KeyboardInterrupt):
                        break
                print("\nChat session ended. Thanks for playing!")
            else:
                print("Thanks for playing!")
            return False
    
    return False


def run_interactive_spectator():
    """Run spectator with interactive prompts."""
    print("\n" + "="*60)
    print("  POKEPROTOCOL - SPECTATOR MODE")
    print("="*60)

    # Get host IP and port
    host_ip = get_user_input("Enter host IP address", "127.0.0.1")
    host_port = get_user_input(
        "Enter host port",
        "8888",
        validator_func=lambda x: validate_port(x)
    )

    # Get local port
    local_port = get_user_input(
        "Enter your local port",
        "8890",
        validator_func=lambda x: validate_port(x)
    )

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
                retry = get_validated_input(
                    "Would you like to try a different local port? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if retry:
                    local_port = get_user_input(
                        "Enter your local port",
                        str(local_port),
                        validator_func=lambda x: validate_port(x)
                    )
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
                retry = get_validated_input(
                    "Would you like to try again? (Y/N)",
                    validate_yes_no,
                    "Please enter Y or N"
                )
                if not retry:
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
                    timeout = time.time() + 60.0  # 60 second timeout
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

    # Stop chat thread before menu to prevent stdin conflicts
    stop_chat_input_thread()
    clear_input_stream()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("\nSelect mode:")
        print("1. Host - Start a battle and wait for others to join")
        print("2. Joiner - Connect to an existing battle")
        print("3. Spectator - Watch an ongoing battle")

        choice = get_validated_input(
            "\nEnter choice (1-3)",
            lambda x: validate_integer(x, min_val=1, max_val=3),
            "Please enter a number between 1 and 3"
        )

        if choice == 1:
            mode = 'host'
        elif choice == 2:
            mode = 'joiner'
        elif choice == 3:
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
