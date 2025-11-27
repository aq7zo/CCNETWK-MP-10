"""
Protocol Messages Module

This module defines all message types for the PokeProtocol and provides
parsing and serialization functionality for protocol messages.
"""

from enum import Enum
from typing import Dict, Optional
import json
import base64


class MessageType(Enum):
    """Enumeration of all valid message types in the protocol."""
    HANDSHAKE_REQUEST = "HANDSHAKE_REQUEST"
    HANDSHAKE_RESPONSE = "HANDSHAKE_RESPONSE"
    SPECTATOR_REQUEST = "SPECTATOR_REQUEST"
    BATTLE_SETUP = "BATTLE_SETUP"
    ATTACK_ANNOUNCE = "ATTACK_ANNOUNCE"
    DEFENSE_ANNOUNCE = "DEFENSE_ANNOUNCE"
    CALCULATION_REPORT = "CALCULATION_REPORT"
    CALCULATION_CONFIRM = "CALCULATION_CONFIRM"
    RESOLUTION_REQUEST = "RESOLUTION_REQUEST"
    GAME_OVER = "GAME_OVER"
    REMATCH_REQUEST = "REMATCH_REQUEST"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    BOOST_ACTIVATION = "BOOST_ACTIVATION"
    ACK = "ACK"


class ContentType(Enum):
    """Enumeration of chat content types."""
    TEXT = "TEXT"
    STICKER = "STICKER"


class Message:
    """
    Base class for all protocol messages.
    
    Provides serialization and deserialization functionality for
    converting between protocol format and Python objects.
    """
    
    @staticmethod
    def deserialize(data: bytes) -> 'Message':
        """
        Parse a protocol message from bytes.
        
        Args:
            data: The raw message data
            
        Returns:
            A Message object of the appropriate type
        """
        try:
            text = data.decode('utf-8')
            lines = text.strip().split('\n')
            fields = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    fields[key] = value
            
            msg_type = MessageType(fields.get('message_type'))
            
            # Route to appropriate message class
            if msg_type == MessageType.HANDSHAKE_REQUEST:
                return HandshakeRequest.from_fields(fields)
            elif msg_type == MessageType.HANDSHAKE_RESPONSE:
                return HandshakeResponse.from_fields(fields)
            elif msg_type == MessageType.SPECTATOR_REQUEST:
                return SpectatorRequest.from_fields(fields)
            elif msg_type == MessageType.BATTLE_SETUP:
                return BattleSetup.from_fields(fields)
            elif msg_type == MessageType.ATTACK_ANNOUNCE:
                return AttackAnnounce.from_fields(fields)
            elif msg_type == MessageType.DEFENSE_ANNOUNCE:
                return DefenseAnnounce.from_fields(fields)
            elif msg_type == MessageType.CALCULATION_REPORT:
                return CalculationReport.from_fields(fields)
            elif msg_type == MessageType.CALCULATION_CONFIRM:
                return CalculationConfirm.from_fields(fields)
            elif msg_type == MessageType.RESOLUTION_REQUEST:
                return ResolutionRequest.from_fields(fields)
            elif msg_type == MessageType.GAME_OVER:
                return GameOver.from_fields(fields)
            elif msg_type == MessageType.REMATCH_REQUEST:
                return RematchRequest.from_fields(fields)
            elif msg_type == MessageType.CHAT_MESSAGE:
                return ChatMessage.from_fields(fields)
            elif msg_type == MessageType.BOOST_ACTIVATION:
                return BoostActivation.from_fields(fields)
            elif msg_type == MessageType.ACK:
                return Ack.from_fields(fields)
                
        except Exception as e:
            print(f"Error parsing message: {e}")
            raise ValueError(f"Invalid message format: {e}")
    
    def serialize(self) -> bytes:
        """
        Convert message to protocol format bytes.
        
        Returns:
            The serialized message as bytes
        """
        raise NotImplementedError("Subclasses must implement serialize()")
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'Message':
        """
        Create a message instance from parsed fields.
        
        Args:
            fields: Dictionary of message fields
            
        Returns:
            Message instance
        """
        raise NotImplementedError("Subclasses must implement from_fields()")


class HandshakeRequest(Message):
    """
    Message sent by Joiner Peer to initiate connection as a player.

    Attributes:
        message_type: Always HANDSHAKE_REQUEST
        sequence_number: Unique message sequence number
    """

    def __init__(self, sequence_number: int = 0):
        self.message_type = MessageType.HANDSHAKE_REQUEST
        self.sequence_number = sequence_number

    def serialize(self) -> bytes:
        """Serialize handshake request message."""
        return f"message_type: HANDSHAKE_REQUEST\nsequence_number: {self.sequence_number}\n".encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'HandshakeRequest':
        """Create from parsed fields."""
        sequence_number = int(fields.get('sequence_number', 0))
        return HandshakeRequest(sequence_number)


class HandshakeResponse(Message):
    """
    Message sent by Host Peer to acknowledge connection request.

    Attributes:
        message_type: Always HANDSHAKE_RESPONSE
        seed: Random integer for RNG synchronization
        sequence_number: Unique message sequence number
    """

    def __init__(self, seed: int, sequence_number: int = 0):
        self.message_type = MessageType.HANDSHAKE_RESPONSE
        self.seed = seed
        self.sequence_number = sequence_number

    def serialize(self) -> bytes:
        """Serialize handshake response message."""
        return f"message_type: HANDSHAKE_RESPONSE\nseed: {self.seed}\nsequence_number: {self.sequence_number}\n".encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'HandshakeResponse':
        """Create from parsed fields."""
        seed = int(fields.get('seed', 0))
        sequence_number = int(fields.get('sequence_number', 0))
        return HandshakeResponse(seed, sequence_number)


class SpectatorRequest(Message):
    """
    Message sent by a peer to initiate connection as a spectator.

    Attributes:
        message_type: Always SPECTATOR_REQUEST
        sequence_number: Unique message sequence number
    """

    def __init__(self, sequence_number: int = 0):
        self.message_type = MessageType.SPECTATOR_REQUEST
        self.sequence_number = sequence_number

    def serialize(self) -> bytes:
        """Serialize spectator request message."""
        return f"message_type: SPECTATOR_REQUEST\nsequence_number: {self.sequence_number}\n".encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'SpectatorRequest':
        """Create from parsed fields."""
        sequence_number = int(fields.get('sequence_number', 0))
        return SpectatorRequest(sequence_number)


class BattleSetup(Message):
    """
    Message sent by both playing peers to exchange initial Pokémon data.

    Attributes:
        message_type: Always BATTLE_SETUP
        communication_mode: "P2P" or "BROADCAST"
        pokemon_name: Name of the chosen Pokémon
        pokemon_data: Full Pokemon stats object (serialized as JSON)
        stat_boosts: Dictionary with special_attack_uses and special_defense_uses
        sequence_number: Unique message sequence number
    """

    def __init__(self, communication_mode: str, pokemon_name: str, stat_boosts: Dict[str, int], sequence_number: int = 0, pokemon_data: Optional[Dict] = None):
        self.message_type = MessageType.BATTLE_SETUP
        self.communication_mode = communication_mode
        self.pokemon_name = pokemon_name
        self.stat_boosts = stat_boosts
        self.sequence_number = sequence_number
        self.pokemon_data = pokemon_data  # Full Pokemon object as dict

    def serialize(self) -> bytes:
        """Serialize battle setup message."""
        boosts_str = json.dumps(self.stat_boosts)
        pokemon_data_str = json.dumps(self.pokemon_data) if self.pokemon_data else "{}"
        return (f"message_type: BATTLE_SETUP\n"
                f"communication_mode: {self.communication_mode}\n"
                f"pokemon_name: {self.pokemon_name}\n"
                f"stat_boosts: {boosts_str}\n"
                f"pokemon: {pokemon_data_str}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'BattleSetup':
        """Create from parsed fields."""
        communication_mode = fields.get('communication_mode', 'P2P')
        pokemon_name = fields.get('pokemon_name', '')
        stat_boosts_str = fields.get('stat_boosts', '{}')
        stat_boosts = json.loads(stat_boosts_str)
        sequence_number = int(fields.get('sequence_number', 0))
        # RFC uses "pokemon:" but support both for backward compatibility
        pokemon_data_str = fields.get('pokemon', fields.get('pokemon_data', '{}'))
        pokemon_data = json.loads(pokemon_data_str) if pokemon_data_str != '{}' else None
        return BattleSetup(communication_mode, pokemon_name, stat_boosts, sequence_number, pokemon_data)


class AttackAnnounce(Message):
    """
    Message sent by attacking peer to announce move choice.
    
    Attributes:
        message_type: Always ATTACK_ANNOUNCE
        move_name: Name of the chosen move
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, move_name: str, sequence_number: int):
        self.message_type = MessageType.ATTACK_ANNOUNCE
        self.move_name = move_name
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize attack announce message."""
        return (f"message_type: ATTACK_ANNOUNCE\n"
                f"move_name: {self.move_name}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'AttackAnnounce':
        """Create from parsed fields."""
        move_name = fields.get('move_name', '')
        sequence_number = int(fields.get('sequence_number', 0))
        return AttackAnnounce(move_name, sequence_number)


class DefenseAnnounce(Message):
    """
    Message sent by defending peer to acknowledge attack announcement.
    
    Attributes:
        message_type: Always DEFENSE_ANNOUNCE
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, sequence_number: int):
        self.message_type = MessageType.DEFENSE_ANNOUNCE
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize defense announce message."""
        return (f"message_type: DEFENSE_ANNOUNCE\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'DefenseAnnounce':
        """Create from parsed fields."""
        sequence_number = int(fields.get('sequence_number', 0))
        return DefenseAnnounce(sequence_number)


class CalculationReport(Message):
    """
    Message sent by both players to report damage calculation results.
    
    Attributes:
        message_type: Always CALCULATION_REPORT
        attacker: Name of attacking Pokémon
        move_used: Name of move used
        remaining_health: Attacking Pokémon's remaining HP
        damage_dealt: Amount of damage inflicted
        defender_hp_remaining: Defender's remaining HP
        status_message: Descriptive turn events
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, attacker: str, move_used: str, remaining_health: int,
                 damage_dealt: int, defender_hp_remaining: int,
                 status_message: str, sequence_number: int):
        self.message_type = MessageType.CALCULATION_REPORT
        self.attacker = attacker
        self.move_used = move_used
        self.remaining_health = remaining_health
        self.damage_dealt = damage_dealt
        self.defender_hp_remaining = defender_hp_remaining
        self.status_message = status_message
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize calculation report message."""
        return (f"message_type: CALCULATION_REPORT\n"
                f"attacker: {self.attacker}\n"
                f"move_used: {self.move_used}\n"
                f"remaining_health: {self.remaining_health}\n"
                f"damage_dealt: {self.damage_dealt}\n"
                f"defender_hp_remaining: {self.defender_hp_remaining}\n"
                f"status_message: {self.status_message}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'CalculationReport':
        """Create from parsed fields."""
        attacker = fields.get('attacker', '')
        move_used = fields.get('move_used', '')
        remaining_health = int(fields.get('remaining_health', 0))
        damage_dealt = int(fields.get('damage_dealt', 0))
        defender_hp_remaining = int(fields.get('defender_hp_remaining', 0))
        status_message = fields.get('status_message', '')
        sequence_number = int(fields.get('sequence_number', 0))
        return CalculationReport(attacker, move_used, remaining_health,
                                damage_dealt, defender_hp_remaining,
                                status_message, sequence_number)


class CalculationConfirm(Message):
    """
    Message sent to confirm matching damage calculations.
    
    Attributes:
        message_type: Always CALCULATION_CONFIRM
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, sequence_number: int):
        self.message_type = MessageType.CALCULATION_CONFIRM
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize calculation confirm message."""
        return (f"message_type: CALCULATION_CONFIRM\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'CalculationConfirm':
        """Create from parsed fields."""
        sequence_number = int(fields.get('sequence_number', 0))
        return CalculationConfirm(sequence_number)


class ResolutionRequest(Message):
    """
    Message sent when calculation discrepancy is detected.
    
    Attributes:
        message_type: Always RESOLUTION_REQUEST
        attacker: Name of attacking Pokémon
        move_used: Name of move used
        damage_dealt: Calculated damage amount
        defender_hp_remaining: Calculated defender HP
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, attacker: str, move_used: str, damage_dealt: int,
                 defender_hp_remaining: int, sequence_number: int):
        self.message_type = MessageType.RESOLUTION_REQUEST
        self.attacker = attacker
        self.move_used = move_used
        self.damage_dealt = damage_dealt
        self.defender_hp_remaining = defender_hp_remaining
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize resolution request message."""
        return (f"message_type: RESOLUTION_REQUEST\n"
                f"attacker: {self.attacker}\n"
                f"move_used: {self.move_used}\n"
                f"damage_dealt: {self.damage_dealt}\n"
                f"defender_hp_remaining: {self.defender_hp_remaining}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'ResolutionRequest':
        """Create from parsed fields."""
        attacker = fields.get('attacker', '')
        move_used = fields.get('move_used', '')
        damage_dealt = int(fields.get('damage_dealt', 0))
        defender_hp_remaining = int(fields.get('defender_hp_remaining', 0))
        sequence_number = int(fields.get('sequence_number', 0))
        return ResolutionRequest(attacker, move_used, damage_dealt,
                                defender_hp_remaining, sequence_number)


class GameOver(Message):
    """
    Message sent when a Pokémon faints, ending the battle.
    
    Attributes:
        message_type: Always GAME_OVER
        winner: Name of winning Pokémon
        loser: Name of fainted Pokémon
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, winner: str, loser: str, sequence_number: int):
        self.message_type = MessageType.GAME_OVER
        self.winner = winner
        self.loser = loser
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize game over message."""
        return (f"message_type: GAME_OVER\n"
                f"winner: {self.winner}\n"
                f"loser: {self.loser}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'GameOver':
        """Create from parsed fields."""
        winner = fields.get('winner', '')
        loser = fields.get('loser', '')
        sequence_number = int(fields.get('sequence_number', 0))
        return GameOver(winner, loser, sequence_number)


class RematchRequest(Message):
    """
    Message sent to request or respond to a rematch after game over.
    
    Attributes:
        message_type: Always REMATCH_REQUEST
        wants_rematch: True if peer wants rematch, False otherwise
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, wants_rematch: bool, sequence_number: int):
        self.message_type = MessageType.REMATCH_REQUEST
        self.wants_rematch = wants_rematch
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize rematch request message."""
        return (f"message_type: REMATCH_REQUEST\n"
                f"wants_rematch: {str(self.wants_rematch).lower()}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'RematchRequest':
        """Create from parsed fields."""
        wants_rematch = fields.get('wants_rematch', 'false').lower() == 'true'
        sequence_number = int(fields.get('sequence_number', 0))
        return RematchRequest(wants_rematch, sequence_number)


class ChatMessage(Message):
    """
    Message for peer-to-peer text chat or sticker exchange.
    
    Attributes:
        message_type: Always CHAT_MESSAGE
        sender_name: Name of sending peer
        content_type: "TEXT" or "STICKER"
        message_text: Text content (optional)
        sticker_data: Base64 encoded sticker (optional)
        sequence_number: Unique message sequence number
    """
    
    def __init__(self, sender_name: str, content_type: str,
                 message_text: Optional[str] = None,
                 sticker_data: Optional[str] = None,
                 sequence_number: int = 0):
        self.message_type = MessageType.CHAT_MESSAGE
        self.sender_name = sender_name
        self.content_type = content_type
        self.message_text = message_text
        self.sticker_data = sticker_data
        self.sequence_number = sequence_number
    
    def serialize(self) -> bytes:
        """Serialize chat message."""
        lines = [
            "message_type: CHAT_MESSAGE",
            f"sender_name: {self.sender_name}",
            f"content_type: {self.content_type}",
        ]
        
        if self.content_type == ContentType.TEXT.value and self.message_text:
            lines.append(f"message_text: {self.message_text}")
        elif self.content_type == ContentType.STICKER.value and self.sticker_data:
            lines.append(f"sticker_data: {self.sticker_data}")
        
        lines.append(f"sequence_number: {self.sequence_number}")
        
        return '\n'.join(lines).encode('utf-8')
    
    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'ChatMessage':
        """Create from parsed fields."""
        sender_name = fields.get('sender_name', '')
        content_type = fields.get('content_type', 'TEXT')
        message_text = fields.get('message_text')
        sticker_data = fields.get('sticker_data')
        sequence_number = int(fields.get('sequence_number', 0))
        return ChatMessage(sender_name, content_type, message_text,
                          sticker_data, sequence_number)


class BoostActivation(Message):
    """
    Message sent to activate a stat boost (special attack or special defense).

    Attributes:
        message_type: Always BOOST_ACTIVATION
        boost_type: "SPECIAL_ATTACK" or "SPECIAL_DEFENSE"
        sequence_number: Unique message sequence number
    """

    def __init__(self, boost_type: str, sequence_number: int):
        self.message_type = MessageType.BOOST_ACTIVATION
        self.boost_type = boost_type  # "SPECIAL_ATTACK" or "SPECIAL_DEFENSE"
        self.sequence_number = sequence_number

    def serialize(self) -> bytes:
        """Serialize boost activation message."""
        return (f"message_type: BOOST_ACTIVATION\n"
                f"boost_type: {self.boost_type}\n"
                f"sequence_number: {self.sequence_number}\n").encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'BoostActivation':
        """Create from parsed fields."""
        boost_type = fields.get('boost_type', '')
        sequence_number = int(fields.get('sequence_number', 0))
        return BoostActivation(boost_type, sequence_number)


class Ack(Message):
    """
    Acknowledgment message for reliability layer.

    Attributes:
        message_type: Always ACK
        ack_number: Sequence number being acknowledged
    """

    def __init__(self, ack_number: int):
        self.message_type = MessageType.ACK
        self.ack_number = ack_number

    def serialize(self) -> bytes:
        """Serialize ACK message."""
        return (f"message_type: ACK\n"
                f"ack_number: {self.ack_number}\n").encode('utf-8')

    @staticmethod
    def from_fields(fields: Dict[str, str]) -> 'Ack':
        """Create from parsed fields."""
        ack_number = int(fields.get('ack_number', 0))
        return Ack(ack_number)

