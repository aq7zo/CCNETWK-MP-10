"""
PokeProtocol Peer Implementation

This module implements the main peer classes for the PokeProtocol:
- BasePeer: Core functionality for all peer types
- HostPeer: Host peer implementation
- JoinerPeer: Joiner peer implementation
- SpectatorPeer: Spectator peer implementation
"""

import socket
import select
import time
import random
from typing import Optional, Callable, Tuple, List
from pokemon_data import PokemonDataLoader, Pokemon
from moves import MoveDatabase, Move
from messages import Message, MessageType, Ack, HandshakeResponse
from reliability import ReliabilityLayer
from battle_state import BattleStateMachine, BattleState, BattlePokemon
from damage_calculator import DamageCalculator


class BasePeer:
    """
    Base class for all peer types (Host, Joiner, Spectator).
    
    Provides common functionality including:
    - UDP socket management
    - Message sending/receiving
    - Reliability layer integration
    - Chat message handling
    """
    
    def __init__(self, port: int = 8888):
        """
        Initialize the base peer.
        
        Args:
            port: UDP port to listen on
        """
        self.port = port
        self.socket = None
        self.peer_address: Optional[Tuple[str, int]] = None
        self.reliability = ReliabilityLayer()
        
        # Data management
        self.pokemon_loader = PokemonDataLoader()
        self.move_db = MoveDatabase()
        self.damage_calculator = DamageCalculator(self.pokemon_loader)
        
        # State
        self.connected = False
        self.battle_seed: Optional[int] = None
        
        # Callbacks
        self.on_chat_message: Optional[Callable[[str, str], None]] = None
        self.on_sticker_received: Optional[Callable[[str, str], None]] = None
        self.on_battle_update: Optional[Callable[[str], None]] = None
    
    def start_listening(self, enable_broadcast: bool = False):
        """
        Create and bind UDP socket for listening.

        Args:
            enable_broadcast: Enable broadcast mode for peer discovery
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', self.port))
        self.socket.setblocking(False)

        # Enable broadcast if requested
        if enable_broadcast:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"Listening on port {self.port} with broadcast enabled")
        else:
            print(f"Listening on port {self.port}")

    def _send_datagram(self, data: bytes, target: Tuple[str, int],
                       retries: int = 3, backoff: float = 0.02) -> None:
        """
        Best-effort sendto wrapper that absorbs temporary EWOULDBLOCK errors.

        UDP sockets are configured as non-blocking so Windows can raise
        BlockingIOError (WinError 10035) when the buffer is full. We retry a
        few times before giving up and letting the reliability layer trigger a
        later resend.
        """
        if not self.socket:
            raise RuntimeError("Socket not initialized")

        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                self.socket.sendto(data, target)
                return
            except BlockingIOError as exc:
                last_error = exc
                # Allow the socket buffer to drain before retrying
                time.sleep(backoff * (attempt + 1))

        if last_error:
            print(f"[warn] sendto deferred after {retries} attempts: {last_error}")
    
    def send_message(self, message: Message, address: Optional[Tuple[str, int]] = None) -> int:
        """
        Send a message with reliability guarantees.

        Args:
            message: Message to send
            address: Target address (uses peer_address if not provided)

        Returns:
            Sequence number assigned to message
        """
        if not self.socket:
            raise RuntimeError("Socket not initialized")

        target = address or self.peer_address
        if not target:
            raise RuntimeError("No target address specified")

        # Get sequence number and prepare for sending
        seq_num = self.reliability.send_message(message)

        # Serialize and send
        data = message.serialize()
        self._send_datagram(data, target)

        return seq_num

    def send_broadcast(self, message: Message, port: int = 8888):
        """
        Send a broadcast message to all peers on local network.

        Args:
            message: Message to broadcast
            port: Target port for broadcast

        Returns:
            Sequence number assigned to message
        """
        if not self.socket:
            raise RuntimeError("Socket not initialized")

        # Enable broadcast on socket if not already enabled
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        broadcast_address = ('<broadcast>', port)

        # Get sequence number and prepare for sending
        seq_num = self.reliability.send_message(message)

        # Serialize and send
        data = message.serialize()
        self._send_datagram(data, broadcast_address)

        return seq_num
    
    def send_ack(self, ack_number: int, address: Optional[Tuple[str, int]] = None):
        """
        Send an acknowledgment message.
        
        Args:
            ack_number: Sequence number being acknowledged
            address: Target address
        """
        ack = Ack(ack_number)
        self.send_message(ack, address)
    
    def receive_message(self, timeout: float = 0.1) -> Optional[Tuple[Message, Tuple[str, int]]]:
        """
        Receive a message with timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (Message, address) or None if timeout
        """
        if not self.socket:
            return None
        
        try:
            ready, _, _ = select.select([self.socket], [], [], timeout)
            if ready:
                data, address = self.socket.recvfrom(4096)
                message = Message.deserialize(data)
                return message, address
        except Exception as e:
            print(f"Error receiving message: {e}")
        
        return None
    
    def handle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle an incoming message.
        
        Args:
            message: Received message
            address: Sender's address
        """
        # Handle ACK
        if message.message_type == MessageType.ACK:
            self.reliability.receive_ack(message.ack_number)
            return
        
        # Send ACK for non-ACK messages
        if hasattr(message, 'sequence_number'):
            self.send_ack(message.sequence_number, address)
            
            # Check for duplicates
            if self.reliability.is_duplicate(message.sequence_number):
                return
            self.reliability.mark_received(message.sequence_number)
        
        # Route to appropriate handler
        if message.message_type == MessageType.CHAT_MESSAGE:
            self._handle_chat_message(message)
        else:
            self._handle_battle_message(message, address)
    
    def _handle_chat_message(self, message: Message):
        """
        Handle chat message.

        Args:
            message: Chat message
        """
        if message.content_type == "TEXT" and message.message_text:
            if self.on_chat_message:
                self.on_chat_message(message.sender_name, message.message_text)
        elif message.content_type == "STICKER" and message.sticker_data:
            # Validate sticker data
            if self._validate_sticker(message.sticker_data):
                if self.on_sticker_received:
                    self.on_sticker_received(message.sender_name, message.sticker_data)
            else:
                print(f"Invalid sticker received from {message.sender_name}")

    def _validate_sticker(self, sticker_data: str) -> bool:
        """
        Validate sticker data (Base64 format, size constraints).

        Args:
            sticker_data: Base64 encoded sticker data

        Returns:
            True if valid, False otherwise
        """
        try:
            import base64
            # Try to decode Base64
            decoded = base64.b64decode(sticker_data)
            # Check size constraint (10MB max)
            if len(decoded) > 10 * 1024 * 1024:
                return False
            # Note: Full image dimension validation (320x320) would require
            # an image library like PIL/Pillow, which is not imported here.
            # That validation should be done at the application level.
            return True
        except Exception:
            return False
    
    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle battle-related message (to be overridden).
        
        Args:
            message: Battle message
            address: Sender address
        """
        pass  # Overridden in subclasses
    
    def send_chat_message(self, sender_name: str, message_text: str):
        """
        Send a text chat message.

        Args:
            sender_name: Name of sender
            message_text: Message content
        """
        from messages import ChatMessage

        chat_msg = ChatMessage(
            sender_name=sender_name,
            content_type="TEXT",
            message_text=message_text
        )
        self.send_message(chat_msg)

    def send_sticker_message(self, sender_name: str, sticker_data: str):
        """
        Send a sticker message.

        Args:
            sender_name: Name of sender
            sticker_data: Base64 encoded sticker data

        Raises:
            ValueError: If sticker data is invalid
        """
        # Validate sticker before sending
        if not self._validate_sticker(sticker_data):
            raise ValueError("Invalid sticker data: must be valid Base64 and under 10MB")

        from messages import ChatMessage

        chat_msg = ChatMessage(
            sender_name=sender_name,
            content_type="STICKER",
            sticker_data=sticker_data
        )
        self.send_message(chat_msg)
    
    def process_reliability(self):
        """Process retransmissions and reliability layer updates."""
        # Check for messages needing retransmission
        retransmissions = self.reliability.check_retransmissions()
        for seq_num, message in retransmissions:
            self.send_message(message)
        
        # Cleanup old ACKs
        self.reliability.cleanup_old_acks()
    
    def use_move(self, move_name: str):
        """
        Execute a move during battle.
        
        Args:
            move_name: Name of the move to use
        """
        # This is a placeholder - actual implementation in subclasses
        pass
    
    def disconnect(self):
        """Close connection and cleanup resources."""
        self.connected = False
        if self.socket:
            self.socket.close()
        self.reliability.reset()


class HostPeer(BasePeer):
    """
    Host peer implementation.
    
    The host creates a listening socket and responds to connection requests
    from joiner peers. The host goes first in battles.
    """
    
    def __init__(self, port: int = 8888):
        """
        Initialize host peer.

        Args:
            port: Port to listen on
        """
        super().__init__(port)
        self.battle_state: Optional[BattleStateMachine] = None
        self.my_pokemon: Optional[BattlePokemon] = None
        self.my_stat_boosts = {"special_attack_uses": 5, "special_defense_uses": 5}
        self.spectators: List[Tuple[str, int]] = []  # List of spectator addresses
    
    def start_listening(self):
        """Start listening for connections."""
        super().start_listening()
        self.battle_state = BattleStateMachine(is_host=True)
        print("Host ready to accept connections")
    
    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle battle messages.
        
        Args:
            message: Battle message
            address: Sender address
        """
        if not self.connected:
            self.peer_address = address
        
        if message.message_type == MessageType.HANDSHAKE_REQUEST:
            self._handle_handshake_request(message, address)
        elif message.message_type == MessageType.SPECTATOR_REQUEST:
            self._handle_spectator_request(message, address)
        elif self.connected:
            if message.message_type == MessageType.BATTLE_SETUP:
                self._handle_battle_setup(message)
            elif message.message_type == MessageType.ATTACK_ANNOUNCE:
                self._handle_attack_announce(message)
            elif message.message_type == MessageType.DEFENSE_ANNOUNCE:
                self._handle_defense_announce(message)
            elif message.message_type == MessageType.CALCULATION_REPORT:
                self._handle_calculation_report(message)
            elif message.message_type == MessageType.CALCULATION_CONFIRM:
                self._handle_calculation_confirm(message)
            elif message.message_type == MessageType.RESOLUTION_REQUEST:
                self._handle_resolution_request(message)
            elif message.message_type == MessageType.GAME_OVER:
                self._handle_game_over(message)
    
    def _handle_handshake_request(self, message: Message, address: Tuple[str, int]):
        """Handle connection request from joiner."""
        self.peer_address = address

        # Generate and send seed
        self.battle_seed = random.randint(1, 99999)
        self.damage_calculator.set_seed(self.battle_seed)

        response = HandshakeResponse(self.battle_seed)
        self.send_message(response, address)

        # Mark as connected after successful handshake
        self.connected = True
        print(f"Connected to joiner at {address}")

    def _handle_spectator_request(self, message: Message, address: Tuple[str, int]):
        """
        Handle spectator join request.

        Args:
            message: Spectator request message
            address: Spectator's address
        """
        if address not in self.spectators:
            self.spectators.append(address)
            # Send battle seed to spectator for synchronization
            response = HandshakeResponse(self.battle_seed if self.battle_seed else 0)
            self.send_message(response, address)
            print(f"Spectator joined from {address}")

    def _broadcast_to_spectators(self, message: Message):
        """
        Broadcast a message to all spectators.

        Args:
            message: Message to broadcast
        """
        for spectator_addr in self.spectators:
            try:
                self.send_message(message, spectator_addr)
            except Exception as e:
                print(f"Failed to send to spectator {spectator_addr}: {e}")

    def _handle_battle_setup(self, message: Message):
        """Handle opponent's battle setup."""
        if self.battle_state and self.battle_state.state == BattleState.SETUP:
            # Use pokemon_data if provided, otherwise load from CSV
            if message.pokemon_data:
                opponent_pokemon = Pokemon(**message.pokemon_data)
            else:
                opponent_pokemon = self.pokemon_loader.get_pokemon(message.pokemon_name)

            if opponent_pokemon:
                self.battle_state.set_opponent_pokemon(
                    opponent_pokemon,
                    message.stat_boosts.get("special_attack_uses", 5),
                    message.stat_boosts.get("special_defense_uses", 5)
                )
                self.battle_state.advance_to_waiting()
                print(f"Opponent chose {message.pokemon_name}")
    
    def _handle_attack_announce(self, message: Message):
        """Handle opponent's attack announcement."""
        if self.battle_state and self.battle_state.state == BattleState.WAITING_FOR_MOVE:
            move = self.move_db.get_move(message.move_name)
            if move:
                self.battle_state.last_move = move
                self.battle_state.last_attacker = message.move_name
                
                # Send defense announce
                from messages import DefenseAnnounce
                defense = DefenseAnnounce(self.reliability.get_next_sequence_number())
                self.send_message(defense)
                
                # Advance to processing and calculate
                self.battle_state.advance_to_processing(move, self.battle_state.opponent_pokemon.pokemon.name)
                
                # Calculate damage
                outcome = self.damage_calculator.calculate_turn_outcome(
                    self.battle_state.opponent_pokemon.pokemon,
                    self.my_pokemon.pokemon,
                    self.battle_state.opponent_pokemon.current_hp,
                    self.my_pokemon.current_hp,
                    move
                )
                
                self.battle_state.record_my_calculation(outcome)
                self.battle_state.apply_calculation(outcome)
                
                # Send calculation report
                from messages import CalculationReport
                report = CalculationReport(
                    self.battle_state.opponent_pokemon.pokemon.name,
                    outcome["move_used"],
                    outcome.get("attacker_hp", self.battle_state.opponent_pokemon.current_hp),
                    outcome["damage_dealt"],
                    outcome["defender_hp_remaining"],
                    outcome["status_message"],
                    self.reliability.get_next_sequence_number()
                )
                self.send_message(report)
    
    def start_battle(self, pokemon_name: str, special_attack_uses: int = 5,
                    special_defense_uses: int = 5):
        """
        Initialize battle with chosen Pokémon.
        
        Args:
            pokemon_name: Name of Pokémon to use
            special_attack_uses: Special attack boosts
            special_defense_uses: Special defense boosts
        """
        pokemon = self.pokemon_loader.get_pokemon(pokemon_name)
        if not pokemon:
            raise ValueError(f"Pokémon {pokemon_name} not found")
        
        self.my_stat_boosts = {
            "special_attack_uses": special_attack_uses,
            "special_defense_uses": special_defense_uses
        }
        battle_pokemon: Optional[BattlePokemon] = None
        
        if self.battle_state:
            self.battle_state.set_pokemon(pokemon, special_attack_uses, special_defense_uses)
            battle_pokemon = self.battle_state.my_pokemon
        else:
            battle_pokemon = BattlePokemon(pokemon, special_attack_uses, special_defense_uses)
        
        self.my_pokemon = battle_pokemon
        
        # Send battle setup
        if self.peer_address:
            from messages import BattleSetup
            from dataclasses import asdict
            pokemon_data = asdict(pokemon) if pokemon else None
            setup_msg = BattleSetup("P2P", pokemon_name, self.my_stat_boosts, pokemon_data=pokemon_data)
            self.send_message(setup_msg)
            self.connected = True
    
    def _handle_defense_announce(self, message: Message):
        """Handle defense announcement (not needed for host)."""
        pass
    
    def _handle_calculation_report(self, message: Message):
        """Handle opponent's calculation report."""
        if self.battle_state and self.battle_state.state == BattleState.PROCESSING_TURN:
            self.battle_state.record_opponent_calculation({
                "damage_dealt": message.damage_dealt,
                "defender_hp_remaining": message.defender_hp_remaining
            })
            
            # Check if calculations match
            if self.battle_state.calculations_match():
                from messages import CalculationConfirm
                confirm = CalculationConfirm(message.sequence_number)
                self.send_message(confirm)
                self.battle_state.advance_to_complete()
            else:
                # Discrepancy - send resolution request
                from messages import ResolutionRequest
                resolution = ResolutionRequest(
                    self.battle_state.last_attacker,
                    message.move_used,
                    self.battle_state.my_calculation["damage_dealt"],
                    self.battle_state.my_calculation["defender_hp_remaining"],
                    self.reliability.get_next_sequence_number()
                )
                self.send_message(resolution)
    
    def _handle_calculation_confirm(self, message: Message):
        """Handle calculation confirmation."""
        if self.battle_state:
            self.battle_state.mark_calculation_confirmed()
            self.battle_state.advance_to_complete()
    
    def _handle_resolution_request(self, message: Message):
        """Handle resolution request from opponent."""
        if self.battle_state:
            # Accept opponent's values and update state
            self.battle_state.record_opponent_calculation({
                "damage_dealt": message.damage_dealt,
                "defender_hp_remaining": message.defender_hp_remaining
            })
            self.battle_state.apply_calculation(self.battle_state.opponent_calculation)
            self.send_ack(message.sequence_number)
    
    def _handle_game_over(self, message: Message):
        """Handle game over message."""
        if self.battle_state:
            self.battle_state.advance_to_game_over()
            print(f"Game Over! {message.winner} wins!")
    
    def use_move(self, move_name: str):
        """
        Execute a move during battle.
        
        Args:
            move_name: Name of the move to use
        """
        if not self.battle_state or not self.is_my_turn():
            print("Not your turn!")
            return
        
        move = self.move_db.get_move(move_name)
        if not move:
            print(f"Move {move_name} not found!")
            return
        
        # Send attack announcement
        from messages import AttackAnnounce, DefenseAnnounce, CalculationReport
        announce = AttackAnnounce(
            move.name,
            self.reliability.get_next_sequence_number()
        )
        self.send_message(announce)
        self.battle_state.last_move = move
        self.battle_state.last_attacker = self.my_pokemon.pokemon.name
        self.battle_state.advance_to_processing(move, self.my_pokemon.pokemon.name)
        
        # Wait for defense announce
        timeout = time.time() + 5.0
        while time.time() < timeout:
            result = self.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                self.handle_message(msg, addr)
            self.process_reliability()
            if self.battle_state.state != BattleState.PROCESSING_TURN:
                break
        
        # Perform calculation
        if self.battle_state.state == BattleState.PROCESSING_TURN:
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Send calculation report
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.my_pokemon.current_hp),
                outcome["damage_dealt"],
                outcome["defender_hp_remaining"],
                outcome["status_message"],
                self.reliability.get_next_sequence_number()
            )
            self.send_message(report)
            
            # Wait for confirmation or resolution
            timeout = time.time() + 5.0
            while time.time() < timeout:
                result = self.receive_message(timeout=0.5)
                if result:
                    msg, addr = result
                    self.handle_message(msg, addr)
                self.process_reliability()
                if self.battle_state.state != BattleState.PROCESSING_TURN:
                    break


class JoinerPeer(BasePeer):
    """
    Joiner peer implementation.
    
    Connects to a host peer and joins an existing battle.
    """
    
    def __init__(self, port: int = 8889):
        """Initialize joiner peer."""
        super().__init__(port)
        self.battle_state: Optional[BattleStateMachine] = None
        self.my_pokemon: Optional[BattlePokemon] = None
        self.my_stat_boosts = {"special_attack_uses": 5, "special_defense_uses": 5}
    
    def connect(self, host_address: str, host_port: int):
        """
        Connect to a host peer.
        
        Args:
            host_address: Host IP address
            host_port: Host port
        """
        if not self.socket:
            self.start_listening()
        
        self.peer_address = (host_address, host_port)
        self.battle_state = BattleStateMachine(is_host=False)
        
        # Send handshake request
        from messages import HandshakeRequest
        request = HandshakeRequest()
        self.send_message(request, self.peer_address)
        
        # Wait for response
        timeout = time.time() + 5.0
        while time.time() < timeout:
            result = self.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                # IMPORTANT: Always call handle_message first to send ACK
                self.handle_message(msg, addr)
                if msg.message_type == MessageType.HANDSHAKE_RESPONSE:
                    self.battle_seed = msg.seed
                    self.damage_calculator.set_seed(msg.seed)
                    self.connected = True
                    print(f"Connected to host at {host_address}:{host_port}")
                    return
            # Process reliability layer for retransmissions
            self.process_reliability()
        
        raise ConnectionError("Failed to connect to host")
    
    def start_battle(self, pokemon_name: str, special_attack_uses: int = 5,
                    special_defense_uses: int = 5):
        """
        Initialize battle with chosen Pokémon.
        
        Args:
            pokemon_name: Name of Pokémon to use
            special_attack_uses: Special attack boosts
            special_defense_uses: Special defense boosts
        """
        pokemon = self.pokemon_loader.get_pokemon(pokemon_name)
        if not pokemon:
            raise ValueError(f"Pokémon {pokemon_name} not found")
        
        self.my_stat_boosts = {
            "special_attack_uses": special_attack_uses,
            "special_defense_uses": special_defense_uses
        }
        battle_pokemon: Optional[BattlePokemon] = None
        
        if self.battle_state:
            self.battle_state.set_pokemon(pokemon, special_attack_uses, special_defense_uses)
            battle_pokemon = self.battle_state.my_pokemon
        else:
            battle_pokemon = BattlePokemon(pokemon, special_attack_uses, special_defense_uses)
        
        self.my_pokemon = battle_pokemon
        
        # Send battle setup
        if self.peer_address:
            from messages import BattleSetup
            from dataclasses import asdict
            pokemon_data = asdict(pokemon) if pokemon else None
            setup = BattleSetup("P2P", pokemon_name, self.my_stat_boosts, pokemon_data=pokemon_data)
            self.send_message(setup)
    
    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """Handle battle messages."""
        if not self.connected:
            return
        
        if message.message_type == MessageType.BATTLE_SETUP:
            self._handle_battle_setup(message)
        elif message.message_type == MessageType.ATTACK_ANNOUNCE:
            self._handle_attack_announce(message)
        elif message.message_type == MessageType.CALCULATION_REPORT:
            self._handle_calculation_report(message)
        elif message.message_type == MessageType.CALCULATION_CONFIRM:
            self._handle_calculation_confirm(message)
        elif message.message_type == MessageType.RESOLUTION_REQUEST:
            self._handle_resolution_request(message)
        elif message.message_type == MessageType.GAME_OVER:
            self._handle_game_over(message)
    
    def _handle_battle_setup(self, message: Message):
        """Handle opponent's battle setup."""
        if self.battle_state and self.battle_state.state == BattleState.SETUP:
            # Use pokemon_data if provided, otherwise load from CSV
            if message.pokemon_data:
                opponent_pokemon = Pokemon(**message.pokemon_data)
            else:
                opponent_pokemon = self.pokemon_loader.get_pokemon(message.pokemon_name)

            if opponent_pokemon:
                self.battle_state.set_opponent_pokemon(
                    opponent_pokemon,
                    message.stat_boosts.get("special_attack_uses", 5),
                    message.stat_boosts.get("special_defense_uses", 5)
                )
                self.battle_state.advance_to_waiting()
                print(f"Opponent chose {message.pokemon_name}")
    
    def _handle_attack_announce(self, message: Message):
        """Handle opponent's attack announcement."""
        if self.battle_state and self.battle_state.state == BattleState.WAITING_FOR_MOVE:
            move = self.move_db.get_move(message.move_name)
            if move:
                self.battle_state.last_move = move
                self.battle_state.last_attacker = message.move_name  # Should be attacker name
                
                # Send defense announce
                from messages import DefenseAnnounce
                defense = DefenseAnnounce(self.reliability.get_next_sequence_number())
                self.send_message(defense)
                
                # Advance to processing and calculate
                self.battle_state.advance_to_processing(move, self.battle_state.opponent_pokemon.pokemon.name)
                
                # Calculate damage
                outcome = self.damage_calculator.calculate_turn_outcome(
                    self.battle_state.opponent_pokemon.pokemon,
                    self.my_pokemon.pokemon,
                    self.battle_state.opponent_pokemon.current_hp,
                    self.my_pokemon.current_hp,
                    move
                )
                
                self.battle_state.record_my_calculation(outcome)
                self.battle_state.apply_calculation(outcome)
                
                # Send calculation report
                from messages import CalculationReport
                report = CalculationReport(
                    self.battle_state.opponent_pokemon.pokemon.name,
                    outcome["move_used"],
                    outcome.get("attacker_hp", self.battle_state.opponent_pokemon.current_hp),
                    outcome["damage_dealt"],
                    outcome["defender_hp_remaining"],
                    outcome["status_message"],
                    self.reliability.get_next_sequence_number()
                )
                self.send_message(report)
    
    def _handle_calculation_report(self, message: Message):
        """Handle opponent's calculation report."""
        if self.battle_state and self.battle_state.state == BattleState.PROCESSING_TURN:
            self.battle_state.record_opponent_calculation({
                "damage_dealt": message.damage_dealt,
                "defender_hp_remaining": message.defender_hp_remaining
            })
            
            if self.battle_state.calculations_match():
                from messages import CalculationConfirm
                confirm = CalculationConfirm(message.sequence_number)
                self.send_message(confirm)
                self.battle_state.advance_to_complete()
    
    def _handle_calculation_confirm(self, message: Message):
        """Handle calculation confirmation."""
        if self.battle_state:
            self.battle_state.mark_calculation_confirmed()
            self.battle_state.advance_to_complete()
    
    def _handle_resolution_request(self, message: Message):
        """Handle resolution request."""
        if self.battle_state:
            self.battle_state.record_opponent_calculation({
                "damage_dealt": message.damage_dealt,
                "defender_hp_remaining": message.defender_hp_remaining
            })
            self.battle_state.apply_calculation(self.battle_state.opponent_calculation)
            self.send_ack(message.sequence_number)
    
    def _handle_game_over(self, message: Message):
        """Handle game over."""
        if self.battle_state:
            self.battle_state.advance_to_game_over()
            print(f"Game Over! {message.winner} wins!")
    
    def use_move(self, move_name: str):
        """
        Execute a move during battle.
        
        Args:
            move_name: Name of the move to use
        """
        if not self.battle_state or not self.is_my_turn():
            print("Not your turn!")
            return
        
        move = self.move_db.get_move(move_name)
        if not move:
            print(f"Move {move_name} not found!")
            return
        
        # Send attack announcement
        from messages import AttackAnnounce, DefenseAnnounce, CalculationReport
        announce = AttackAnnounce(
            move.name,
            self.reliability.get_next_sequence_number()
        )
        self.send_message(announce)
        self.battle_state.last_move = move
        self.battle_state.last_attacker = self.my_pokemon.pokemon.name
        self.battle_state.advance_to_processing(move, self.my_pokemon.pokemon.name)
        
        # Wait for defense announce
        timeout = time.time() + 5.0
        while time.time() < timeout:
            result = self.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                self.handle_message(msg, addr)
            self.process_reliability()
            if self.battle_state.state != BattleState.PROCESSING_TURN:
                break
        
        # Perform calculation
        if self.battle_state.state == BattleState.PROCESSING_TURN:
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Send calculation report
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.my_pokemon.current_hp),
                outcome["damage_dealt"],
                outcome["defender_hp_remaining"],
                outcome["status_message"],
                self.reliability.get_next_sequence_number()
            )
            self.send_message(report)
            
            # Wait for confirmation or resolution
            timeout = time.time() + 5.0
            while time.time() < timeout:
                result = self.receive_message(timeout=0.5)
                if result:
                    msg, addr = result
                    self.handle_message(msg, addr)
                self.process_reliability()
                if self.battle_state.state != BattleState.PROCESSING_TURN:
                    break


class SpectatorPeer(BasePeer):
    """
    Spectator peer implementation - can observe but not participate.

    Spectators can:
    - Join an active battle
    - Receive all battle updates
    - Send and receive chat messages
    """

    def __init__(self, port: int = 8890):
        """
        Initialize spectator peer.

        Args:
            port: Port to listen on
        """
        super().__init__(port)
        self.battle_seed: Optional[int] = None

    def connect(self, host_address: str, host_port: int):
        """
        Connect to a host as a spectator.

        Args:
            host_address: Host IP address
            host_port: Host port
        """
        if not self.socket:
            self.start_listening()

        self.peer_address = (host_address, host_port)

        # Send spectator request
        from messages import SpectatorRequest
        request = SpectatorRequest()
        self.send_message(request, self.peer_address)

        # Wait for response
        timeout = time.time() + 5.0
        while time.time() < timeout:
            result = self.receive_message(timeout=0.5)
            if result:
                msg, addr = result
                # IMPORTANT: Always call handle_message first to send ACK
                self.handle_message(msg, addr)
                if msg.message_type == MessageType.HANDSHAKE_RESPONSE:
                    self.battle_seed = msg.seed
                    self.damage_calculator.set_seed(msg.seed)
                    self.connected = True
                    print(f"Connected to host as spectator at {host_address}:{host_port}")
                    return
            # Process reliability layer for retransmissions
            self.process_reliability()

        raise ConnectionError("Failed to connect as spectator")

    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle battle messages as a spectator.

        Args:
            message: Battle message
            address: Sender address
        """
        # Spectators just observe, so we trigger callbacks but don't respond
        if self.on_battle_update:
            update_str = self._format_battle_update(message)
            if update_str:
                self.on_battle_update(update_str)

    def _format_battle_update(self, message: Message) -> Optional[str]:
        """
        Format a battle message for display.

        Args:
            message: Battle message

        Returns:
            Formatted string or None
        """
        if message.message_type == MessageType.BATTLE_SETUP:
            return f"Battle starting: {message.pokemon_name} joins the battle!"
        elif message.message_type == MessageType.ATTACK_ANNOUNCE:
            return f"Attack announced: {message.move_name}"
        elif message.message_type == MessageType.CALCULATION_REPORT:
            return f"{message.status_message} (Damage: {message.damage_dealt}, Defender HP: {message.defender_hp_remaining})"
        elif message.message_type == MessageType.GAME_OVER:
            return f"Game Over! {message.winner} wins!"
        return None

