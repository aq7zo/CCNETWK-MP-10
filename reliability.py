"""
Reliability Layer Module

This module implements the reliability layer on top of UDP, providing:
- Sequence numbers for message ordering
- Acknowledgements (ACKs)
- Retransmission with timeout handling
- Message queue management
"""

import time
from typing import Dict, Optional, Deque
from collections import deque
from messages import Message, MessageType


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

