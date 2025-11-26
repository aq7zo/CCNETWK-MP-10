"""
Debug and Bug Report System for PokeProtocol

This module provides comprehensive debugging and bug reporting capabilities
to help diagnose issues with battle flow, message handling, and state management.
"""

import time
import json
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum
from pathlib import Path


class DebugLevel(Enum):
    """Debug logging levels."""
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    VERBOSE = 5


class DebugLogger:
    """
    Centralized debug logger for PokeProtocol.
    
    Provides structured logging with timestamps, message tracking,
    state transitions, and bug report generation.
    """
    
    def __init__(self, enabled: bool = True, level: DebugLevel = DebugLevel.DEBUG):
        """
        Initialize debug logger.
        
        Args:
            enabled: Whether debugging is enabled
            level: Minimum debug level to log
        """
        self.enabled = enabled
        self.level = level
        self.logs: List[Dict] = []
        self.message_trace: List[Dict] = []
        self.state_transitions: List[Dict] = []
        self.errors: List[Dict] = []
        self.start_time = time.time()
        
    def log(self, level: DebugLevel, category: str, message: str, 
            data: Optional[Dict] = None, peer_type: Optional[str] = None):
        """
        Log a debug message.
        
        Args:
            level: Debug level
            category: Category (e.g., 'MESSAGE', 'STATE', 'ERROR')
            message: Log message
            data: Additional data dictionary
            peer_type: Type of peer ('host', 'joiner', 'spectator')
        """
        if not self.enabled or level.value > self.level.value:
            return
            
        timestamp = time.time() - self.start_time
        log_entry = {
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'level': level.name,
            'category': category,
            'message': message,
            'peer_type': peer_type,
            'data': data or {}
        }
        
        self.logs.append(log_entry)
        
        # Print to console
        prefix = f"[{timestamp:.3f}s] [{level.name}] [{category}]"
        if peer_type:
            prefix += f" [{peer_type.upper()}]"
        print(f"{prefix} {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2, default=str)}")
    
    def log_message(self, direction: str, message_type: str, 
                   sequence_number: Optional[int] = None,
                   peer_type: Optional[str] = None,
                   details: Optional[Dict] = None):
        """
        Log a message send/receive event.
        
        Args:
            direction: 'SEND' or 'RECEIVE'
            message_type: Type of message
            sequence_number: Message sequence number
            peer_type: Type of peer
            details: Additional message details
        """
        self.log(
            DebugLevel.DEBUG,
            'MESSAGE',
            f"{direction} {message_type}",
            {
                'direction': direction,
                'message_type': message_type,
                'sequence_number': sequence_number,
                **{k: v for k, v in (details or {}).items()}
            },
            peer_type
        )
        
        self.message_trace.append({
            'timestamp': time.time() - self.start_time,
            'direction': direction,
            'message_type': message_type,
            'sequence_number': sequence_number,
            'peer_type': peer_type,
            'details': details or {}
        })
    
    def log_state_transition(self, old_state: str, new_state: str,
                           peer_type: Optional[str] = None,
                           reason: Optional[str] = None,
                           context: Optional[Dict] = None):
        """
        Log a state transition.
        
        Args:
            old_state: Previous state
            new_state: New state
            peer_type: Type of peer
            reason: Reason for transition
            context: Additional context
        """
        self.log(
            DebugLevel.INFO,
            'STATE',
            f"State transition: {old_state} -> {new_state}",
            {
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason,
                **{k: v for k, v in (context or {}).items()}
            },
            peer_type
        )
        
        self.state_transitions.append({
            'timestamp': time.time() - self.start_time,
            'old_state': old_state,
            'new_state': new_state,
            'peer_type': peer_type,
            'reason': reason,
            'context': context or {}
        })
    
    def log_error(self, error_type: str, message: str,
                 peer_type: Optional[str] = None,
                 exception: Optional[Exception] = None,
                 context: Optional[Dict] = None):
        """
        Log an error.
        
        Args:
            error_type: Type of error
            message: Error message
            peer_type: Type of peer
            exception: Exception object if any
            context: Additional context
        """
        error_data = {
            'error_type': error_type,
            'message': message,
            'context': context or {}
        }
        
        if exception:
            error_data['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': self._get_traceback(exception)
            }
        
        self.log(
            DebugLevel.ERROR,
            'ERROR',
            f"{error_type}: {message}",
            error_data,
            peer_type
        )
        
        self.errors.append({
            'timestamp': time.time() - self.start_time,
            'error_type': error_type,
            'message': message,
            'peer_type': peer_type,
            'exception': error_data.get('exception'),
            'context': context or {}
        })
    
    def log_warning(self, message: str, peer_type: Optional[str] = None,
                   context: Optional[Dict] = None):
        """Log a warning."""
        self.log(
            DebugLevel.WARNING,
            'WARNING',
            message,
            context or {},
            peer_type
        )
    
    def _get_traceback(self, exception: Exception) -> str:
        """Get traceback string from exception."""
        import traceback
        return ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))
    
    def get_message_flow_summary(self) -> Dict:
        """
        Get a summary of message flow.
        
        Returns:
            Dictionary with message flow statistics
        """
        if not self.message_trace:
            return {'total_messages': 0, 'by_type': {}, 'by_direction': {}}
        
        by_type = {}
        by_direction = {'SEND': 0, 'RECEIVE': 0}
        
        for msg in self.message_trace:
            msg_type = msg['message_type']
            direction = msg['direction']
            
            by_type[msg_type] = by_type.get(msg_type, {'SEND': 0, 'RECEIVE': 0})
            by_type[msg_type][direction] = by_type[msg_type].get(direction, 0) + 1
            by_direction[direction] = by_direction.get(direction, 0) + 1
        
        return {
            'total_messages': len(self.message_trace),
            'by_type': by_type,
            'by_direction': by_direction,
            'messages': self.message_trace
        }
    
    def get_state_summary(self) -> Dict:
        """
        Get a summary of state transitions.
        
        Returns:
            Dictionary with state transition statistics
        """
        if not self.state_transitions:
            return {'total_transitions': 0, 'transitions': []}
        
        return {
            'total_transitions': len(self.state_transitions),
            'transitions': self.state_transitions,
            'current_state': self.state_transitions[-1]['new_state'] if self.state_transitions else None
        }
    
    def generate_bug_report(self, title: str = "Battle Hanging Bug Report",
                          description: str = "") -> Dict:
        """
        Generate a comprehensive bug report.
        
        Args:
            title: Report title
            description: Additional description
            
        Returns:
            Dictionary containing bug report
        """
        report = {
            'title': title,
            'description': description,
            'generated_at': datetime.now().isoformat(),
            'duration': time.time() - self.start_time,
            'summary': {
                'total_logs': len(self.logs),
                'total_messages': len(self.message_trace),
                'total_state_transitions': len(self.state_transitions),
                'total_errors': len(self.errors)
            },
            'message_flow': self.get_message_flow_summary(),
            'state_transitions': self.get_state_summary(),
            'errors': self.errors,
            'recent_logs': self.logs[-50:] if len(self.logs) > 50 else self.logs,
            'full_logs': self.logs
        }
        
        return report
    
    def save_bug_report(self, filepath: Optional[str] = None,
                       title: str = "Battle Hanging Bug Report",
                       description: str = "") -> str:
        """
        Save bug report to file.
        
        Args:
            filepath: Path to save report (defaults to timestamped filename)
            title: Report title
            description: Additional description
            
        Returns:
            Path to saved report
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"bug_report_{timestamp}.json"
        
        report = self.generate_bug_report(title, description)
        
        # Ensure directory exists
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"Bug report saved to: {filepath}")
        print(f"{'='*60}")
        
        return str(path)
    
    def print_summary(self):
        """Print a summary of debug information."""
        print(f"\n{'='*60}")
        print("DEBUG SUMMARY")
        print(f"{'='*60}")
        print(f"Total logs: {len(self.logs)}")
        print(f"Total messages: {len(self.message_trace)}")
        print(f"Total state transitions: {len(self.state_transitions)}")
        print(f"Total errors: {len(self.errors)}")
        print(f"Duration: {time.time() - self.start_time:.2f}s")
        
        if self.message_trace:
            print(f"\nMessage Flow:")
            summary = self.get_message_flow_summary()
            print(f"  Total: {summary['total_messages']}")
            print(f"  Sent: {summary['by_direction'].get('SEND', 0)}")
            print(f"  Received: {summary['by_direction'].get('RECEIVE', 0)}")
            print(f"\n  By Type:")
            for msg_type, counts in summary['by_type'].items():
                print(f"    {msg_type}: SEND={counts.get('SEND', 0)}, RECEIVE={counts.get('RECEIVE', 0)}")
        
        if self.state_transitions:
            print(f"\nState Transitions:")
            for trans in self.state_transitions[-10:]:  # Last 10
                print(f"  [{trans['timestamp']:.3f}s] {trans['old_state']} -> {trans['new_state']}")
                if trans.get('reason'):
                    print(f"    Reason: {trans['reason']}")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  [{error['timestamp']:.3f}s] {error['error_type']}: {error['message']}")
        
        print(f"{'='*60}\n")
    
    def reset(self):
        """Reset all debug data."""
        self.logs.clear()
        self.message_trace.clear()
        self.state_transitions.clear()
        self.errors.clear()
        self.start_time = time.time()


# Global debug logger instance
_debug_logger: Optional[DebugLogger] = None


def get_debug_logger(enabled: bool = True, level: DebugLevel = DebugLevel.DEBUG) -> DebugLogger:
    """
    Get or create the global debug logger.
    
    Args:
        enabled: Whether debugging is enabled
        level: Minimum debug level
        
    Returns:
        DebugLogger instance
    """
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger(enabled=enabled, level=level)
    return _debug_logger


def set_debug_enabled(enabled: bool):
    """Enable or disable debugging."""
    logger = get_debug_logger()
    logger.enabled = enabled


def set_debug_level(level: DebugLevel):
    """Set debug level."""
    logger = get_debug_logger()
    logger.level = level

