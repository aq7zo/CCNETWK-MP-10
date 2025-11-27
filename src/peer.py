"""
PokeProtocol Peer Implementation

This module implements the main peer classes for the PokeProtocol:
- BasePeer: Core functionality for all peer types
- HostPeer: Host peer implementation
- JoinerPeer: Joiner peer implementation
- SpectatorPeer: Spectator peer implementation
- ReliabilityLayer: Reliability services on top of UDP
"""

import socket
import select
import time
import random
from typing import Optional, Callable, Tuple, List, Dict, Deque
from collections import deque
from game_data import PokemonDataLoader, Pokemon, MoveDatabase, Move
from messages import Message, MessageType, Ack, HandshakeResponse
from battle import BattleStateMachine, BattleState, BattlePokemon, DamageCalculator

# Import debug logger (optional - won't break if not available)
try:
    from debug_logger import get_logger, EventType
    DEBUG_LOGGING_ENABLED = True
except ImportError:
    DEBUG_LOGGING_ENABLED = False
    def get_logger(*args, **kwargs):
        return None

# ============================================================================
# Reliability Layer
# ============================================================================

class PendingMessage:
    """
    Represents a message waiting for acknowledgment.
    
    Attributes:
        message: The message being sent
        sequence_number: Sequence number of the message
        retry_count: Number of retransmission attempts
        timestamp: When the message was first sent
        timeout: Timeout duration in seconds
    """
    
    def __init__(self, message: Message, sequence_number: int, timeout: float = 0.5):
        """
        Initialize pending message.
        
        Args:
            message: The message to send
            sequence_number: Message sequence number
            timeout: Timeout in seconds before retry
        """
        self.message = message
        self.sequence_number = sequence_number
        self.retry_count = 0
        self.timestamp = time.time()
        self.timeout = timeout
    
    def should_retry(self, max_retries: int = 3) -> bool:
        """
        Check if message should be retransmitted.
        
        Args:
            max_retries: Maximum number of retries allowed
            
        Returns:
            True if should retry, False otherwise
        """
        if self.retry_count >= max_retries:
            return False
        
        elapsed = time.time() - self.timestamp
        return elapsed >= self.timeout
    
    def retry(self):
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.timestamp = time.time()


class ReliabilityLayer:
    """
    Provides reliability services on top of UDP.
    
    Implements:
    - Sequence number generation and tracking
    - Message acknowledgments
    - Retransmission logic
    - Duplicate detection
    """
    
    def __init__(self, max_retries: int = 3, timeout: float = 0.5):
        """
        Initialize the reliability layer.
        
        Args:
            max_retries: Maximum retransmission attempts
            timeout: Timeout before retry (seconds)
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.sequence_counter = 0
        self.pending_messages: Dict[int, PendingMessage] = {}
        self.received_sequences: Deque[int] = deque(maxlen=1000)  # Prevent duplicates
        self.last_ack_time: Dict[int, float] = {}
    
    def get_next_sequence_number(self) -> int:
        """
        Get the next sequence number.
        
        Returns:
            Next sequence number
        """
        self.sequence_counter += 1
        return self.sequence_counter
    
    def send_message(self, message: Message, set_sequence: bool = True) -> int:
        """
        Prepare a message for sending with reliability guarantees.
        
        Args:
            message: Message to send
            set_sequence: Whether to set sequence number on message
            
        Returns:
            Assigned sequence number
        """
        seq_num = self.get_next_sequence_number()
        
        # Set sequence number if message supports it
        if set_sequence and hasattr(message, 'sequence_number'):
            message.sequence_number = seq_num
        
        # Track as pending if it requires acknowledgment
        if self._requires_ack(message):
            self.pending_messages[seq_num] = PendingMessage(message, seq_num, self.timeout)
        
        return seq_num
    
    def receive_ack(self, ack_number: int):
        """
        Handle an incoming ACK message.
        
        Args:
            ack_number: The acknowledged sequence number
        """
        if ack_number in self.pending_messages:
            del self.pending_messages[ack_number]
            self.last_ack_time[ack_number] = time.time()
    
    def check_retransmissions(self) -> list:
        """
        Check for messages that need retransmission.
        
        Returns:
            List of (sequence_number, message) tuples needing retry
        """
        retransmissions = []
        
        # Get all sequence numbers to avoid modification during iteration
        seq_nums = list(self.pending_messages.keys())
        
        for seq_num in seq_nums:
            pending = self.pending_messages[seq_num]
            
            if pending.should_retry(self.max_retries):
                pending.retry()
                retransmissions.append((seq_num, pending.message))
            elif pending.retry_count >= self.max_retries:
                # Exceeded max retries - remove from pending
                del self.pending_messages[seq_num]
        
        return retransmissions
    
    def is_duplicate(self, sequence_number: int) -> bool:
        """
        Check if a sequence number was already processed.
        
        Args:
            sequence_number: Sequence number to check
            
        Returns:
            True if duplicate, False otherwise
        """
        return sequence_number in self.received_sequences
    
    def mark_received(self, sequence_number: int):
        """
        Mark a sequence number as received.
        
        Args:
            sequence_number: Received sequence number
        """
        self.received_sequences.append(sequence_number)
    
    def has_pending_messages(self) -> bool:
        """
        Check if there are pending messages waiting for ACK.
        
        Returns:
            True if there are pending messages
        """
        return len(self.pending_messages) > 0
    
    def _requires_ack(self, message: Message) -> bool:
        """
        Determine if a message type requires acknowledgment.
        
        Args:
            message: Message to check
            
        Returns:
            True if message requires ACK
        """
        # ACK messages themselves don't need ACK
        if message.message_type == MessageType.ACK:
            return False
        
        # All other messages require acknowledgment
        return True
    
    def cleanup_old_acks(self, max_age: float = 60.0):
        """
        Remove old ACK timestamps to prevent memory leak.
        
        Args:
            max_age: Maximum age in seconds
        """
        current_time = time.time()
        old_acks = [
            seq for seq, timestamp in self.last_ack_time.items()
            if current_time - timestamp > max_age
        ]
        for seq in old_acks:
            del self.last_ack_time[seq]
    
    def reset(self):
        """Reset the reliability layer state."""
        self.sequence_counter = 0
        self.pending_messages.clear()
        self.received_sequences.clear()
        self.last_ack_time.clear()


# ============================================================================
# Peer Classes
# ============================================================================


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
        self.opponent_wants_rematch: Optional[bool] = None
        
        # Callbacks
        self.on_chat_message: Optional[Callable[[str, str], None]] = None
        self.on_sticker_received: Optional[Callable[[str, str], None]] = None
        self.on_battle_update: Optional[Callable[[str], None]] = None
        
        # Debug logging
        self.debug_logger = None
        if DEBUG_LOGGING_ENABLED:
            peer_type = self.__class__.__name__
            self.debug_logger = get_logger(peer_type, port)
    
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
        
        # Debug logging
        if self.debug_logger:
            self.debug_logger.log_message_sent(
                message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type),
                target,
                seq_num,
                message
            )

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
                
                # Debug logging
                if self.debug_logger:
                    seq_num = getattr(message, 'sequence_number', None)
                    self.debug_logger.log_message_received(
                        message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type),
                        address,
                        seq_num,
                        message
                    )
                
                return message, address
        except OSError as e:
            # Handle network errors gracefully (connection closed, etc.)
            if "10054" not in str(e):  # Don't spam for "connection forcibly closed"
                if self.debug_logger:
                    self.debug_logger.log_error(f"Error receiving message: {e}", e, {"timeout": timeout})
                print(f"Error receiving message: {e}")
            return None
        except Exception as e:
            if self.debug_logger:
                self.debug_logger.log_error(f"Error receiving message: {e}", e, {"timeout": timeout})
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
                # Duplicate message, ignore
                return
            self.reliability.mark_received(message.sequence_number)
        
        # Route to appropriate handler
        if message.message_type == MessageType.CHAT_MESSAGE:
            # Pass address for potential broadcasting (HostPeer will override)
            if hasattr(self, '_handle_chat_message_with_broadcast'):
                self._handle_chat_message_with_broadcast(message, address)
            else:
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
            # Skip our own messages (they're already displayed as "[You]: message")
            if hasattr(self, '_my_sender_name') and message.sender_name == self._my_sender_name:
                return
            
            if self.debug_logger:
                self.debug_logger.log_chat(message.sender_name, message.message_text, "RECEIVED")
            if self.on_chat_message:
                self.on_chat_message(message.sender_name, message.message_text)
        elif message.content_type == "STICKER" and message.sticker_data:
            # Validate sticker data
            if self._validate_sticker(message.sticker_data):
                if self.on_sticker_received:
                    self.on_sticker_received(message.sender_name, message.sticker_data)
            else:
                if self.debug_logger:
                    self.debug_logger.log_warning(f"Invalid sticker received from {message.sender_name}")
                print(f"Invalid sticker received from {message.sender_name}")
    
    def _handle_chat_message_with_broadcast(self, message: Message, address: Tuple[str, int]):
        """
        Handle chat message with broadcasting (for HostPeer override).
        
        Args:
            message: Chat message
            address: Sender address
        """
        # Call base handler first
        self._handle_chat_message(message)
        # Broadcasting will be handled in HostPeer override

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
        # Check if chat is enabled (for joiner)
        if hasattr(self, 'chat_enabled') and not self.chat_enabled:
            return
        
        from messages import ChatMessage

        chat_msg = ChatMessage(
            sender_name=sender_name,
            content_type="TEXT",
            message_text=message_text,
            sequence_number=self.reliability.get_next_sequence_number()
        )
        
        # Store our own sender name to avoid processing our own messages
        if not hasattr(self, '_my_sender_name'):
            self._my_sender_name = sender_name
        
        self.send_message(chat_msg)
        
        # Debug logging
        if self.debug_logger:
            self.debug_logger.log_chat(sender_name, message_text, "SENT")
    
    def send_chat_state_notification(self, sender_name: str, state: str):
        """
        Send a chat state notification (e.g., when someone ends chat).
        
        Args:
            sender_name: Name of sender
            state: State message (e.g., "ended chat session")
        """
        from messages import ChatMessage
        
        # Send notification even if chat is disabled (this is a system message)
        chat_msg = ChatMessage(
            sender_name="SYSTEM",
            content_type="TEXT",
            message_text=f"{sender_name} {state}",
            sequence_number=self.reliability.get_next_sequence_number()
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
            # Retransmit with ORIGINAL sequence number (don't create new one)
            target = self.peer_address
            if target:
                # Ensure message has the original sequence number
                if hasattr(message, 'sequence_number'):
                    message.sequence_number = seq_num
                data = message.serialize()
                self._send_datagram(data, target)
        
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
        if self.debug_logger:
            self.debug_logger.log_disconnection(self.peer_address)
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
        self.chat_enabled: bool = False  # Chat is disabled by default, must be enabled by both players
    
    def start_listening(self):
        """Start listening for connections."""
        super().start_listening()
        self.battle_state = BattleStateMachine(is_host=True)
        print("Host ready to accept connections")
    
    def send_chat_message(self, sender_name: str, message_text: str):
        """
        Send a text chat message to joiner and broadcast to all spectators.

        Args:
            sender_name: Name of sender
            message_text: Message content
        """
        # Check if chat is enabled
        if not self.chat_enabled:
            return
        
        from messages import ChatMessage

        chat_msg = ChatMessage(
            sender_name=sender_name,
            content_type="TEXT",
            message_text=message_text,
            sequence_number=self.reliability.get_next_sequence_number()
        )
        
        # Store our own sender name to avoid processing our own messages
        if not hasattr(self, '_my_sender_name'):
            self._my_sender_name = sender_name
        
        # Send to joiner (if connected)
        if self.peer_address:
            self.send_message(chat_msg, self.peer_address)
        
        # Broadcast to all spectators
        self._broadcast_to_spectators(chat_msg)
        
        # Don't trigger our own callback - we already printed "[You]: message"
        # The callback will be triggered when others receive it
    
    def send_chat_state_notification(self, sender_name: str, state: str):
        """
        Send a chat state notification (e.g., when someone ends chat).
        
        Args:
            sender_name: Name of sender
            state: State message (e.g., "ended chat session")
        """
        from messages import ChatMessage
        
        # Send notification even if chat is disabled (this is a system message)
        chat_msg = ChatMessage(
            sender_name="SYSTEM",
            content_type="TEXT",
            message_text=f"{sender_name} {state}",
            sequence_number=self.reliability.get_next_sequence_number()
        )
        
        # Send to joiner (if connected)
        if self.peer_address:
            self.send_message(chat_msg, self.peer_address)
        
        # Broadcast to all spectators
        self._broadcast_to_spectators(chat_msg)
    
    def _handle_chat_message_with_broadcast(self, message: Message, address: Tuple[str, int]):
        """
        Handle chat message and broadcast to all participants.
        
        Args:
            message: Chat message
            address: Sender address
        """
        # Skip our own messages (they're already displayed as "[You]: message")
        if hasattr(self, '_my_sender_name') and message.sender_name == self._my_sender_name:
            # This is our own message, don't process it again
            # It was already sent to joiner and spectators in send_chat_message
            return
        
        # Determine sender type based on address
        is_from_joiner = (address == self.peer_address) if self.peer_address else False
        is_from_spectator = address in self.spectators if hasattr(self, 'spectators') else False
        
        # Call base handler to trigger callback (shows the message with correct sender name)
        # This will display the message on the host's terminal
        self._handle_chat_message(message)
        
        # Broadcast to all spectators (except the sender if they're a spectator)
        # This ensures spectators receive messages from joiner, and other spectators receive messages from a spectator
        if hasattr(self, 'spectators') and self.spectators:
            for spectator_addr in self.spectators:
                if spectator_addr != address:  # Don't send back to sender
                    try:
                        # Create a new message with a new sequence number to avoid duplicate detection issues
                        # The original sender_name is preserved so recipients know who sent it
                        from messages import ChatMessage
                        broadcast_msg = ChatMessage(
                            sender_name=message.sender_name,
                            content_type=message.content_type,
                            message_text=getattr(message, 'message_text', None),
                            sticker_data=getattr(message, 'sticker_data', None),
                            sequence_number=self.reliability.get_next_sequence_number()
                        )
                        self.send_message(broadcast_msg, spectator_addr)
                    except Exception as e:
                        print(f"Failed to send to spectator {spectator_addr}: {e}")
        
        # Forward to joiner if message is from spectator (joiner needs to see spectator messages)
        if is_from_spectator and self.peer_address:
            # Forward spectator's message to joiner (preserving original sender_name)
            # Use a new sequence number to avoid duplicate detection issues
            from messages import ChatMessage
            forward_msg = ChatMessage(
                sender_name=message.sender_name,
                content_type=message.content_type,
                message_text=getattr(message, 'message_text', None),
                sticker_data=getattr(message, 'sticker_data', None),
                sequence_number=self.reliability.get_next_sequence_number()
            )
            self.send_message(forward_msg, self.peer_address)
        # If message is from joiner, spectators already received it above
    
    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle battle messages.
        
        Args:
            message: Battle message
            address: Sender address
        """
        if not self.connected:
            self.peer_address = address
        
        # Handle connection requests (always, even if already connected to joiner)
        if message.message_type == MessageType.HANDSHAKE_REQUEST:
            self._handle_handshake_request(message, address)
        elif message.message_type == MessageType.SPECTATOR_REQUEST:
            # Spectators can join at any time, even during battle
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
            elif message.message_type == MessageType.REMATCH_REQUEST:
                self._handle_rematch_request(message)
    
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
            if self.debug_logger:
                self.debug_logger.log_spectator_join(address)
        
        # Send battle seed to spectator for synchronization (always send, even if already in list)
        seed = self.battle_seed if self.battle_seed else 0
        response = HandshakeResponse(seed, sequence_number=self.reliability.get_next_sequence_number())
        self.send_message(response, address)
        if address not in self.spectators or len(self.spectators) == 1:
            print(f"✓ Spectator joined from {address}")

    def _broadcast_to_spectators(self, message: Message):
        """
        Broadcast a message to all spectators.

        Args:
            message: Message to broadcast
        """
        for spectator_addr in self.spectators:
            try:
                # For chat messages, create a new message with a new sequence number
                # to avoid duplicate detection issues and ensure each recipient gets a unique message
                if message.message_type == MessageType.CHAT_MESSAGE:
                    from messages import ChatMessage
                    broadcast_msg = ChatMessage(
                        sender_name=message.sender_name,
                        content_type=message.content_type,
                        message_text=getattr(message, 'message_text', None),
                        sticker_data=getattr(message, 'sticker_data', None),
                        sequence_number=self.reliability.get_next_sequence_number()
                    )
                    self.send_message(broadcast_msg, spectator_addr)
                else:
                    # For non-chat messages, send the original message
                    self.send_message(message, spectator_addr)
            except Exception as e:
                print(f"Failed to send to spectator {spectator_addr}: {e}")

    def _handle_battle_setup(self, message: Message):
        """Handle opponent's battle setup."""
        # Only process if we're still in SETUP state (ignore duplicates/retransmissions)
        if not self.battle_state or self.battle_state.state != BattleState.SETUP:
            return
            
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
            # Broadcast joiner's BattleSetup to spectators
            self._broadcast_to_spectators(message)
    
    def _handle_attack_announce(self, message: Message):
        """Handle opponent's attack announcement."""
        
        if not self.battle_state:
            return
            
        if self.battle_state.state != BattleState.WAITING_FOR_MOVE:
            return
            
        move = self.move_db.get_move(message.move_name)
        if not move:
            return
            
        self.battle_state.last_move = move
        self.battle_state.last_attacker = message.move_name
        
        # Broadcast joiner's AttackAnnounce to spectators
        self._broadcast_to_spectators(message)
        
        # Send defense announce
        from messages import DefenseAnnounce
        defense = DefenseAnnounce(self.reliability.get_next_sequence_number())
        self.send_message(defense)
        # Broadcast DefenseAnnounce to spectators
        self._broadcast_to_spectators(defense)
        
        # Advance to processing and calculate
        self.battle_state.advance_to_processing(move, self.battle_state.opponent_pokemon.pokemon.name)
        
        # Calculate damage - use battle_state.my_pokemon for consistency
        if not self.battle_state.my_pokemon:
            return
        outcome = self.damage_calculator.calculate_turn_outcome(
            self.battle_state.opponent_pokemon.pokemon,
            self.battle_state.my_pokemon.pokemon,
            self.battle_state.opponent_pokemon.current_hp,
            self.battle_state.my_pokemon.current_hp,
            move
        )
        
        self.battle_state.record_my_calculation(outcome)
        self.battle_state.apply_calculation(outcome)
        
        # Check for game over
        if self.battle_state.is_game_over():
            winner = self.battle_state.get_winner()
            loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
            from messages import GameOver
            game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
            self.send_message(game_over_msg)
            # Broadcast to spectators
            self._broadcast_to_spectators(game_over_msg)
        
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
        # Broadcast to spectators
        self._broadcast_to_spectators(report)
    
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
            # Broadcast to spectators
            self._broadcast_to_spectators(setup_msg)
    
    def _handle_defense_announce(self, message: Message):
        """Handle defense announcement after sending attack."""
        
        # Broadcast joiner's DefenseAnnounce to spectators
        self._broadcast_to_spectators(message)
        
        # When host sends attack and receives defense announce, calculate and send report
        if not self.battle_state:
            return
            
        # Check if we're processing our own attack (we sent AttackAnnounce, now got DefenseAnnounce)
        if (self.battle_state.state == BattleState.PROCESSING_TURN and
            self.battle_state.last_move):
            
            move = self.battle_state.last_move
            
            # Calculate damage - use battle_state.my_pokemon for consistency
            if not self.battle_state.my_pokemon:
                return
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.battle_state.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.battle_state.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Display damage calculation
            print(f"\n{outcome['status_message']}")
            print(f"{self.battle_state.get_battle_status()}")
            
            # Check for game over
            if self.battle_state.is_game_over():
                winner = self.battle_state.get_winner()
                loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                from messages import GameOver
                game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                self.send_message(game_over_msg)
                # Broadcast to spectators
                self._broadcast_to_spectators(game_over_msg)
            
            # Send calculation report
            from messages import CalculationReport
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.battle_state.my_pokemon.current_hp if self.battle_state.my_pokemon else 0),
                outcome["damage_dealt"],
                outcome["defender_hp_remaining"],
                outcome["status_message"],
                self.reliability.get_next_sequence_number()
            )
            self.send_message(report)
            # Broadcast to spectators
            self._broadcast_to_spectators(report)
    
    def _handle_calculation_report(self, message: Message):
        """Handle opponent's calculation report."""
        
        # Broadcast to spectators
        self._broadcast_to_spectators(message)
        
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
                
                # Check for game over after turn completes
                if self.battle_state.is_game_over():
                    winner = self.battle_state.get_winner()
                    loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                    from messages import GameOver
                    game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                    self.send_message(game_over_msg)
                else:
                    # Show updated status after turn completes
                    print(f"\nTurn complete! {self.battle_state.get_battle_status()}")
            else:
                # Discrepancy - send resolution request
                print(f"\n⚠ Calculation mismatch detected! Resolving...")
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
            # Only advance if we're still processing the OPPONENT's turn (not our own)
            # If my_turn=True, we're processing our own attack, so don't advance
            if self.battle_state.state == BattleState.PROCESSING_TURN and not self.battle_state.my_turn:
                self.battle_state.advance_to_complete()
                
                # Check for game over after turn completes
                if self.battle_state.is_game_over():
                    winner = self.battle_state.get_winner()
                    loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                    from messages import GameOver
                    game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                    self.send_message(game_over_msg)
                else:
                    # Show updated status after turn completes
                    print(f"\nTurn complete! {self.battle_state.get_battle_status()}")
    
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
        # Broadcast to spectators
        self._broadcast_to_spectators(message)
        
        if self.battle_state:
            self.battle_state.advance_to_game_over()
            print(f"\n" + "="*60)
            print(f"  GAME OVER!")
            print(f"  Winner: {message.winner}")
            print(f"  Loser: {message.loser}")
            print("="*60)
    
    def _handle_rematch_request(self, message: Message):
        """Handle rematch request from opponent."""
        # Broadcast to spectators
        self._broadcast_to_spectators(message)
        
        # Store opponent's rematch decision
        self.opponent_wants_rematch = message.wants_rematch
        if message.wants_rematch:
            print(f"\nOpponent wants a rematch!")
        else:
            print(f"\nOpponent does not want a rematch.")
    
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
        if not self.battle_state.my_pokemon:
            return
        self.battle_state.last_attacker = self.battle_state.my_pokemon.pokemon.name
        self.battle_state.advance_to_processing(move, self.battle_state.my_pokemon.pokemon.name)
        
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
            if not self.battle_state.my_pokemon:
                return
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.battle_state.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.battle_state.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Send calculation report
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.battle_state.my_pokemon.current_hp if self.battle_state.my_pokemon else 0),
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
        """
        Initialize joiner peer.
        
        Args:
            port: Port to listen on
        """
        super().__init__(port)
        self.battle_state: Optional[BattleStateMachine] = None
        self.my_pokemon: Optional[BattlePokemon] = None
        self.my_stat_boosts = {"special_attack_uses": 5, "special_defense_uses": 5}
        self.chat_enabled: bool = False  # Chat is disabled by default, must be enabled by both players
    
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
        msg_type = message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type)
        seq_num = getattr(message, 'sequence_number', None)
        
        if not self.connected:
            return
        
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
        elif message.message_type == MessageType.REMATCH_REQUEST:
            self._handle_rematch_request(message)
    
    def _handle_battle_setup(self, message: Message):
        """Handle opponent's battle setup."""
        # Only process if we're still in SETUP state (ignore duplicates/retransmissions)
        if not self.battle_state or self.battle_state.state != BattleState.SETUP:
            return
            
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
        if not self.battle_state:
            return
            
        if self.battle_state.state != BattleState.WAITING_FOR_MOVE:
            return
            
        move = self.move_db.get_move(message.move_name)
        if not move:
            return
            
        self.battle_state.last_move = move
        self.battle_state.last_attacker = message.move_name  # Should be attacker name
        
        # Send defense announce
        from messages import DefenseAnnounce
        defense = DefenseAnnounce(self.reliability.get_next_sequence_number())
        self.send_message(defense)
        
        # Advance to processing and calculate
        self.battle_state.advance_to_processing(move, self.battle_state.opponent_pokemon.pokemon.name)
        
        # Calculate damage - use battle_state.my_pokemon for consistency
        if not self.battle_state.my_pokemon:
            return
        outcome = self.damage_calculator.calculate_turn_outcome(
            self.battle_state.opponent_pokemon.pokemon,
            self.battle_state.my_pokemon.pokemon,
            self.battle_state.opponent_pokemon.current_hp,
            self.battle_state.my_pokemon.current_hp,
            move
        )
        
        self.battle_state.record_my_calculation(outcome)
        self.battle_state.apply_calculation(outcome)
        
        # Display damage calculation
        print(f"\nOpponent used {move.name}!")
        print(f"{outcome['status_message']}")
        print(f"{self.battle_state.get_battle_status()}")
        
        # Check for game over
        if self.battle_state.is_game_over():
            winner = self.battle_state.get_winner()
            loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
            from messages import GameOver
            game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
            self.send_message(game_over_msg)
        
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
    
    def _handle_defense_announce(self, message: Message):
        """Handle defense announcement after sending attack."""
        
        # When joiner sends attack and receives defense announce, calculate and send report
        if not self.battle_state:
            return
            
        # Check if we're processing our own attack (we sent AttackAnnounce, now got DefenseAnnounce)
        if (self.battle_state.state == BattleState.PROCESSING_TURN and
            self.battle_state.last_move):
            
            move = self.battle_state.last_move
            
            # Calculate damage - use battle_state.my_pokemon for consistency
            if not self.battle_state.my_pokemon:
                return
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.battle_state.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.battle_state.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Display damage calculation
            print(f"\n{outcome['status_message']}")
            print(f"{self.battle_state.get_battle_status()}")
            
            # Check for game over
            if self.battle_state.is_game_over():
                winner = self.battle_state.get_winner()
                loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                from messages import GameOver
                game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                self.send_message(game_over_msg)
            
            # Send calculation report
            from messages import CalculationReport
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.battle_state.my_pokemon.current_hp if self.battle_state.my_pokemon else 0),
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
                
                # Check for game over after turn completes
                if self.battle_state.is_game_over():
                    winner = self.battle_state.get_winner()
                    loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                    from messages import GameOver
                    game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                    self.send_message(game_over_msg)
                else:
                    # Show updated status after turn completes
                    print(f"\nTurn complete! {self.battle_state.get_battle_status()}")
            else:
                # Discrepancy - send resolution request
                print(f"\n⚠ Calculation mismatch detected! Resolving...")
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
            # Only advance if we're still processing the OPPONENT's turn (not our own)
            # If my_turn=True, we're processing our own attack, so don't advance
            if self.battle_state.state == BattleState.PROCESSING_TURN and not self.battle_state.my_turn:
                self.battle_state.advance_to_complete()
                
                # Check for game over after turn completes
                if self.battle_state.is_game_over():
                    winner = self.battle_state.get_winner()
                    loser = self.battle_state.opponent_pokemon.pokemon.name if winner == self.battle_state.my_pokemon.pokemon.name else self.battle_state.my_pokemon.pokemon.name
                    from messages import GameOver
                    game_over_msg = GameOver(winner, loser, self.reliability.get_next_sequence_number())
                    self.send_message(game_over_msg)
                else:
                    # Show updated status after turn completes
                    print(f"\nTurn complete! {self.battle_state.get_battle_status()}")
    
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
            print(f"\n" + "="*60)
            print(f"  GAME OVER!")
            print(f"  Winner: {message.winner}")
            print(f"  Loser: {message.loser}")
            print("="*60)
    
    def _handle_rematch_request(self, message: Message):
        """Handle rematch request from opponent."""
        # Store opponent's rematch decision
        self.opponent_wants_rematch = message.wants_rematch
        if message.wants_rematch:
            print(f"\nOpponent wants a rematch!")
        else:
            print(f"\nOpponent does not want a rematch.")
    
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
        if not self.battle_state.my_pokemon:
            return
        self.battle_state.last_attacker = self.battle_state.my_pokemon.pokemon.name
        self.battle_state.advance_to_processing(move, self.battle_state.my_pokemon.pokemon.name)
        
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
            if not self.battle_state.my_pokemon:
                return
            outcome = self.damage_calculator.calculate_turn_outcome(
                self.battle_state.my_pokemon.pokemon,
                self.battle_state.opponent_pokemon.pokemon,
                self.battle_state.my_pokemon.current_hp,
                self.battle_state.opponent_pokemon.current_hp,
                move
            )
            
            self.battle_state.record_my_calculation(outcome)
            self.battle_state.apply_calculation(outcome)
            
            # Send calculation report
            report = CalculationReport(
                outcome["attacker"],
                outcome["move_used"],
                outcome.get("attacker_hp", self.battle_state.my_pokemon.current_hp if self.battle_state.my_pokemon else 0),
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
        # Track battle state for spectators
        self.host_pokemon: Optional[str] = None
        self.joiner_pokemon: Optional[str] = None
        self.host_hp: Optional[int] = None
        self.joiner_hp: Optional[int] = None
        self.last_attacker: Optional[str] = None  # "host" or "joiner"
        self.last_move: Optional[str] = None
        self.game_over: bool = False
        self.winner: Optional[str] = None
        self.loser: Optional[str] = None
        self.rematch_decisions: Dict[str, Optional[bool]] = {"host": None, "joiner": None}

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
        request = SpectatorRequest(sequence_number=self.reliability.get_next_sequence_number())
        self.send_message(request, self.peer_address)

        # Wait for response
        timeout = time.time() + 10.0  # Increased timeout to 10 seconds
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
                    if self.debug_logger:
                        self.debug_logger.log_connection((host_address, host_port), "Host")
                        self.debug_logger.log_battle_event("Battle seed received", {"seed": msg.seed})
                    print(f"Connected to host as spectator at {host_address}:{host_port}")
                    return
            # Process reliability layer for retransmissions
            self.process_reliability()

        raise ConnectionError("Failed to connect as spectator - host may not be running or not accepting spectators")

    def _handle_battle_message(self, message: Message, address: Tuple[str, int]):
        """
        Handle battle messages as a spectator.

        Args:
            message: Battle message
            address: Sender address
        """
        
        # Update internal battle state tracking
        self._update_battle_state(message, address)
        
        # Spectators just observe, so we trigger callbacks but don't respond
        if self.on_battle_update:
            update_str = self._format_battle_update(message)
            if update_str:
                self.on_battle_update(update_str)

    def _update_battle_state(self, message: Message, address: Tuple[str, int]):
        """
        Update internal battle state tracking for spectator display.
        
        Args:
            message: Battle message
            address: Sender address (to determine if host or joiner)
        """
        # Determine if message is from host (usually the peer_address matches)
        is_from_host = (address == self.peer_address) if self.peer_address else False
        
        if message.message_type == MessageType.BATTLE_SETUP:
            # Determine if this is host or joiner based on message order or address
            if self.host_pokemon is None:
                self.host_pokemon = message.pokemon_name
                if hasattr(message, 'pokemon_data') and message.pokemon_data:
                    self.host_hp = message.pokemon_data.get('hp', None)
            else:
                self.joiner_pokemon = message.pokemon_name
                if hasattr(message, 'pokemon_data') and message.pokemon_data:
                    self.joiner_hp = message.pokemon_data.get('hp', None)
        elif message.message_type == MessageType.ATTACK_ANNOUNCE:
            # Try to determine attacker based on address or message flow
            # If we have pokemon names, we can infer from context
            self.last_move = message.move_name
            # We'll determine attacker when we see the calculation report
        elif message.message_type == MessageType.CALCULATION_REPORT:
            # Update HP and determine attacker
            attacker_name = getattr(message, 'attacker', None)
            if attacker_name:
                # Match attacker to pokemon to determine if host or joiner
                if self.host_pokemon and attacker_name == self.host_pokemon:
                    self.last_attacker = "host"
                    self.joiner_hp = message.defender_hp_remaining
                elif self.joiner_pokemon and attacker_name == self.joiner_pokemon:
                    self.last_attacker = "joiner"
                    self.host_hp = message.defender_hp_remaining
                else:
                    # If we can't match, try to infer from context
                    # If we already know one pokemon, the attacker must be the other
                    if self.host_pokemon and not self.joiner_pokemon:
                        self.last_attacker = "joiner"
                        self.host_hp = message.defender_hp_remaining
                    elif self.joiner_pokemon and not self.host_pokemon:
                        self.last_attacker = "host"
                        self.joiner_hp = message.defender_hp_remaining
            else:
                # Fallback: use address to determine (less reliable)
                if is_from_host:
                    self.last_attacker = "host"
                    self.joiner_hp = message.defender_hp_remaining
                else:
                    self.last_attacker = "joiner"
                    self.host_hp = message.defender_hp_remaining
        elif message.message_type == MessageType.GAME_OVER:
            self.game_over = True
            self.winner = message.winner
            self.loser = message.loser
        elif message.message_type == MessageType.REMATCH_REQUEST:
            # Track rematch decisions
            if is_from_host:
                self.rematch_decisions["host"] = message.wants_rematch
            else:
                self.rematch_decisions["joiner"] = message.wants_rematch

    def _format_battle_update(self, message: Message) -> Optional[str]:
        """
        Format a battle message for display with detailed information.

        Args:
            message: Battle message

        Returns:
            Formatted string or None
        """
        if message.message_type == MessageType.BATTLE_SETUP:
            pokemon_name = message.pokemon_name
            if self.host_pokemon is None:
                self.host_pokemon = pokemon_name
                return f"\n{'='*60}\n  BATTLE STARTING!\n{'='*60}\n  HOST chose: {pokemon_name}"
            else:
                self.joiner_pokemon = pokemon_name
                return f"  JOINER chose: {pokemon_name}\n{'='*60}\n"
        elif message.message_type == MessageType.ATTACK_ANNOUNCE:
            move_name = message.move_name
            attacker = self.last_attacker if self.last_attacker else "Unknown"
            attacker_pokemon = self.host_pokemon if attacker == "host" else self.joiner_pokemon
            return f"\n{'─'*60}\n  {attacker.upper()} ({attacker_pokemon}) is using: {move_name}\n{'─'*60}"
        elif message.message_type == MessageType.CALCULATION_REPORT:
            attacker_name = getattr(message, 'attacker', 'Unknown')
            move_used = getattr(message, 'move_used', self.last_move or 'Unknown Move')
            damage = message.damage_dealt
            defender_hp = message.defender_hp_remaining
            status_msg = getattr(message, 'status_message', '')
            
            # Determine attacker and defender pokemon
            if self.last_attacker == "host":
                attacker_pokemon = self.host_pokemon or attacker_name
                defender_pokemon = self.joiner_pokemon or "Opponent"
            elif self.last_attacker == "joiner":
                attacker_pokemon = self.joiner_pokemon or attacker_name
                defender_pokemon = self.host_pokemon or "Opponent"
            else:
                # Fallback: use attacker name from message
                attacker_pokemon = attacker_name
                defender_pokemon = self.joiner_pokemon if attacker_name == self.host_pokemon else (self.host_pokemon if attacker_name == self.joiner_pokemon else "Opponent")
            
            result = f"\n{'─'*60}\n"
            result += f"  {attacker_pokemon} ({self.last_attacker.upper() if self.last_attacker else 'ATTACKER'}) used {move_used}!\n"
            result += f"  {status_msg}\n"
            result += f"  Damage dealt: {damage} HP\n"
            result += f"  {defender_pokemon} HP remaining: {defender_hp}\n"
            result += f"{'─'*60}\n"
            
            # Show current battle status
            if self.host_pokemon and self.joiner_pokemon:
                result += f"\n  Current Battle Status:\n"
                result += f"    {self.host_pokemon} (Host): {self.host_hp if self.host_hp is not None else '?'} HP\n"
                result += f"    {self.joiner_pokemon} (Joiner): {self.joiner_hp if self.joiner_hp is not None else '?'} HP\n"
            
            return result
        elif message.message_type == MessageType.GAME_OVER:
            winner_pokemon = self.winner if self.winner else message.winner
            loser_pokemon = self.loser if self.loser else message.loser
            return f"\n{'='*60}\n  BATTLE ENDED!\n{'='*60}\n  Winner: {winner_pokemon}\n  Loser: {loser_pokemon}\n{'='*60}\n"
        elif message.message_type == MessageType.REMATCH_REQUEST:
            wants_rematch = message.wants_rematch
            player = "Host" if self.rematch_decisions["host"] is None else "Joiner"
            decision = "wants" if wants_rematch else "does NOT want"
            return f"\n  {player} {decision} a rematch..."
        return None

