"""
Debug Logger for PokeProtocol

This module provides comprehensive logging and monitoring for debugging purposes.
It tracks all messages, state changes, errors, and network events.
"""

import time
import json
import traceback
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime


class EventType(Enum):
    """Types of events that can be logged."""
    MESSAGE_SENT = "MESSAGE_SENT"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    MESSAGE_ACK = "MESSAGE_ACK"
    STATE_CHANGE = "STATE_CHANGE"
    CONNECTION = "CONNECTION"
    DISCONNECTION = "DISCONNECTION"
    ERROR = "ERROR"
    WARNING = "WARNING"
    BATTLE_EVENT = "BATTLE_EVENT"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    SPECTATOR_JOIN = "SPECTATOR_JOIN"
    TIMEOUT = "TIMEOUT"
    RETRANSMISSION = "RETRANSMISSION"


@dataclass
class DebugEvent:
    """Represents a single debug event."""
    timestamp: float
    event_type: str
    peer_type: str
    peer_port: int
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp,
            "timestamp_human": datetime.fromtimestamp(self.timestamp).isoformat(),
            "event_type": self.event_type,
            "peer_type": self.peer_type,
            "peer_port": self.peer_port,
            "message": self.message,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.stack_trace:
            result["stack_trace"] = self.stack_trace
        return result


class DebugLogger:
    """
    Comprehensive debug logger for tracking all peer activities.
    
    This logger captures:
    - All messages sent and received
    - Connection/disconnection events
    - State changes
    - Errors and exceptions
    - Network events
    - Battle events
    - Timing information
    """
    
    def __init__(self, peer_type: str, peer_port: int):
        """
        Initialize debug logger.
        
        Args:
            peer_type: Type of peer (Host, Joiner, Spectator)
            peer_port: Port the peer is listening on
        """
        self.peer_type = peer_type
        self.peer_port = peer_port
        self.events: List[DebugEvent] = []
        self.start_time = time.time()
        self.message_sequence: List[Tuple[str, str, float]] = []  # (direction, msg_type, timestamp)
        self.errors: List[DebugEvent] = []
        self.warnings: List[DebugEvent] = []
        self.connections: List[Dict] = []
        self.disconnections: List[Dict] = []
        
    def log_event(self, event_type: EventType, message: str, 
                  data: Optional[Dict] = None, error: Optional[Exception] = None):
        """
        Log an event.
        
        Args:
            event_type: Type of event
            message: Description of the event
            data: Additional data dictionary
            error: Exception if this is an error event
        """
        timestamp = time.time()
        error_str = None
        stack_trace = None
        
        if error:
            error_str = str(error)
            stack_trace = traceback.format_exc()
        
        event = DebugEvent(
            timestamp=timestamp,
            event_type=event_type.value,
            peer_type=self.peer_type,
            peer_port=self.peer_port,
            message=message,
            data=data,
            error=error_str,
            stack_trace=stack_trace
        )
        
        self.events.append(event)
        
        # Categorize events
        if event_type == EventType.ERROR:
            self.errors.append(event)
        elif event_type == EventType.WARNING:
            self.warnings.append(event)
        elif event_type == EventType.CONNECTION:
            if data:
                self.connections.append(data)
        elif event_type == EventType.DISCONNECTION:
            if data:
                self.disconnections.append(data)
        
        # Track message sequence
        if event_type in [EventType.MESSAGE_SENT, EventType.MESSAGE_RECEIVED]:
            direction = "SENT" if event_type == EventType.MESSAGE_SENT else "RECEIVED"
            msg_type = data.get("message_type", "UNKNOWN") if data else "UNKNOWN"
            self.message_sequence.append((direction, msg_type, timestamp))
    
    def log_message_sent(self, message_type: str, target: Optional[Tuple[str, int]] = None,
                        sequence_number: Optional[int] = None, message_obj: Any = None):
        """Log a message being sent."""
        data = {"message_type": message_type}
        if target:
            data["target_address"] = target[0]
            data["target_port"] = target[1]
        if sequence_number is not None:
            data["sequence_number"] = sequence_number
        if message_obj:
            try:
                # Try to extract relevant fields
                if hasattr(message_obj, 'pokemon_name'):
                    data["pokemon_name"] = message_obj.pokemon_name
                if hasattr(message_obj, 'move_name'):
                    data["move_name"] = message_obj.move_name
                if hasattr(message_obj, 'sender_name'):
                    data["sender_name"] = message_obj.sender_name
                if hasattr(message_obj, 'winner'):
                    data["winner"] = message_obj.winner
                    data["loser"] = message_obj.loser
            except:
                pass
        
        self.log_event(EventType.MESSAGE_SENT, f"Sent {message_type}", data)
    
    def log_message_received(self, message_type: str, source: Optional[Tuple[str, int]] = None,
                            sequence_number: Optional[int] = None, message_obj: Any = None):
        """Log a message being received."""
        data = {"message_type": message_type}
        if source:
            data["source_address"] = source[0]
            data["source_port"] = source[1]
        if sequence_number is not None:
            data["sequence_number"] = sequence_number
        if message_obj:
            try:
                if hasattr(message_obj, 'pokemon_name'):
                    data["pokemon_name"] = message_obj.pokemon_name
                if hasattr(message_obj, 'move_name'):
                    data["move_name"] = message_obj.move_name
                if hasattr(message_obj, 'sender_name'):
                    data["sender_name"] = message_obj.sender_name
                if hasattr(message_obj, 'winner'):
                    data["winner"] = message_obj.winner
                    data["loser"] = message_obj.loser
            except:
                pass
        
        self.log_event(EventType.MESSAGE_RECEIVED, f"Received {message_type}", data)
    
    def log_state_change(self, old_state: str, new_state: str, context: Optional[str] = None):
        """Log a state change."""
        data = {"old_state": old_state, "new_state": new_state}
        if context:
            data["context"] = context
        self.log_event(EventType.STATE_CHANGE, 
                       f"State changed: {old_state} -> {new_state}", data)
    
    def log_connection(self, address: Tuple[str, int], peer_type: Optional[str] = None):
        """Log a connection."""
        data = {
            "address": address[0],
            "port": address[1],
            "peer_type": peer_type
        }
        self.log_event(EventType.CONNECTION, 
                      f"Connected to {address[0]}:{address[1]}", data)
    
    def log_disconnection(self, address: Optional[Tuple[str, int]] = None):
        """Log a disconnection."""
        data = {}
        if address:
            data["address"] = address[0]
            data["port"] = address[1]
        self.log_event(EventType.DISCONNECTION, "Disconnected", data)
    
    def log_error(self, message: str, error: Exception, context: Optional[Dict] = None):
        """Log an error."""
        data = context or {}
        self.log_event(EventType.ERROR, message, data, error)
    
    def log_warning(self, message: str, context: Optional[Dict] = None):
        """Log a warning."""
        data = context or {}
        self.log_event(EventType.WARNING, message, data)
    
    def log_battle_event(self, event: str, data: Optional[Dict] = None):
        """Log a battle-specific event."""
        self.log_event(EventType.BATTLE_EVENT, event, data)
    
    def log_chat(self, sender: str, message: str, direction: str = "SENT"):
        """Log a chat message."""
        data = {"sender": sender, "message": message, "direction": direction}
        self.log_event(EventType.CHAT_MESSAGE, 
                      f"Chat {direction}: {sender}: {message}", data)
    
    def log_spectator_join(self, address: Tuple[str, int]):
        """Log a spectator joining."""
        data = {"address": address[0], "port": address[1]}
        self.log_event(EventType.SPECTATOR_JOIN, 
                      f"Spectator joined from {address[0]}:{address[1]}", data)
    
    def log_timeout(self, timeout_type: str, context: Optional[Dict] = None):
        """Log a timeout event."""
        data = context or {}
        data["timeout_type"] = timeout_type
        self.log_event(EventType.TIMEOUT, f"Timeout: {timeout_type}", data)
    
    def log_retransmission(self, sequence_number: int, retry_count: int):
        """Log a message retransmission."""
        data = {"sequence_number": sequence_number, "retry_count": retry_count}
        self.log_event(EventType.RETRANSMISSION, 
                      f"Retransmitting message {sequence_number} (attempt {retry_count})", data)
    
    def get_statistics(self) -> Dict:
        """Get statistics about logged events."""
        total_time = time.time() - self.start_time
        
        event_counts = {}
        for event in self.events:
            event_type = event.event_type
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        message_counts = {}
        for direction, msg_type, _ in self.message_sequence:
            key = f"{direction}_{msg_type}"
            message_counts[key] = message_counts.get(key, 0) + 1
        
        return {
            "total_time_seconds": total_time,
            "total_events": len(self.events),
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "total_connections": len(self.connections),
            "total_disconnections": len(self.disconnections),
            "event_type_counts": event_counts,
            "message_counts": message_counts,
            "messages_sent": sum(1 for d, _, _ in self.message_sequence if d == "SENT"),
            "messages_received": sum(1 for d, _, _ in self.message_sequence if d == "RECEIVED"),
        }
    
    def export_to_dict(self) -> Dict:
        """Export all logged data to a dictionary."""
        return {
            "peer_type": self.peer_type,
            "peer_port": self.peer_port,
            "start_time": self.start_time,
            "start_time_human": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": time.time(),
            "end_time_human": datetime.fromtimestamp(time.time()).isoformat(),
            "statistics": self.get_statistics(),
            "events": [event.to_dict() for event in self.events],
            "errors": [event.to_dict() for event in self.errors],
            "warnings": [event.to_dict() for event in self.warnings],
            "connections": self.connections,
            "disconnections": self.disconnections,
            "message_sequence": [
                {"direction": d, "message_type": m, "timestamp": t} 
                for d, m, t in self.message_sequence
            ]
        }
    
    def export_to_json(self, filename: Optional[str] = None) -> str:
        """
        Export all logged data to JSON.
        
        Args:
            filename: Optional filename to write to. If None, returns JSON string.
        
        Returns:
            JSON string
        """
        data = self.export_to_dict()
        json_str = json.dumps(data, indent=2, default=str)
        
        if filename:
            with open(filename, 'w') as f:
                f.write(json_str)
        
        return json_str


# Global loggers for each peer type
_loggers: Dict[str, DebugLogger] = {}


def get_logger(peer_type: str, peer_port: int) -> DebugLogger:
    """
    Get or create a debug logger for a peer.
    
    Args:
        peer_type: Type of peer (Host, Joiner, Spectator)
        peer_port: Port the peer is listening on
    
    Returns:
        DebugLogger instance
    """
    key = f"{peer_type}_{peer_port}"
    if key not in _loggers:
        _loggers[key] = DebugLogger(peer_type, peer_port)
    return _loggers[key]


def get_all_loggers() -> Dict[str, DebugLogger]:
    """Get all active loggers."""
    return _loggers.copy()


def clear_loggers():
    """Clear all loggers (useful for testing)."""
    _loggers.clear()

