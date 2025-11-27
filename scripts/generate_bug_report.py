"""
Bug Report Generator for PokeProtocol

This script generates a comprehensive bug report by analyzing debug logs
from all peer instances (Host, Joiner, Spectator).
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Add src directory to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from debug_logger import get_all_loggers
except ImportError as e:
    print(f"ERROR: debug_logger module not found: {e}")
    print(f"Please ensure {src_path / 'debug_logger.py'} exists.")
    sys.exit(1)


class BugReportGenerator:
    """Generates comprehensive bug reports from debug logs."""
    
    def __init__(self):
        self.loggers = get_all_loggers()
        self.report_sections = []
    
    def generate_report(self) -> str:
        """Generate a complete bug report."""
        if not self.loggers:
            return self._generate_empty_report()
        
        report = []
        report.append("=" * 80)
        report.append("POKEPROTOCOL COMPREHENSIVE BUG REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Executive Summary
        report.extend(self._generate_executive_summary())
        report.append("")
        
        # Peer Overview
        report.extend(self._generate_peer_overview())
        report.append("")
        
        # Connection Analysis
        report.extend(self._generate_connection_analysis())
        report.append("")
        
        # Message Flow Analysis
        report.extend(self._generate_message_flow_analysis())
        report.append("")
        
        # Error Analysis
        report.extend(self._generate_error_analysis())
        report.append("")
        
        # Warning Analysis
        report.extend(self._generate_warning_analysis())
        report.append("")
        
        # Battle State Analysis
        report.extend(self._generate_battle_state_analysis())
        report.append("")
        
        # Timing Analysis
        report.extend(self._generate_timing_analysis())
        report.append("")
        
        # Network Analysis
        report.extend(self._generate_network_analysis())
        report.append("")
        
        # Chat Analysis
        report.extend(self._generate_chat_analysis())
        report.append("")
        
        # Spectator Analysis
        report.extend(self._generate_spectator_analysis())
        report.append("")
        
        # Recommendations
        report.extend(self._generate_recommendations())
        report.append("")
        
        # Detailed Event Log
        report.extend(self._generate_detailed_event_log())
        report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _generate_empty_report(self) -> str:
        """Generate a report when no loggers are available."""
        return f"""
{'=' * 80}
POKEPROTOCOL BUG REPORT
{'=' * 80}
Generated: {datetime.now().isoformat()}

WARNING: No debug loggers found. Debug logging may not be enabled.

To enable debug logging, ensure debug_logger.py is available and
DEBUG_LOGGING_ENABLED is True in peer.py.
"""
    
    def _generate_executive_summary(self) -> List[str]:
        """Generate executive summary section."""
        lines = []
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        
        total_events = sum(len(logger.events) for logger in self.loggers.values())
        total_errors = sum(len(logger.errors) for logger in self.loggers.values())
        total_warnings = sum(len(logger.warnings) for logger in self.loggers.values())
        total_peers = len(self.loggers)
        
        lines.append(f"Total Peers Monitored: {total_peers}")
        lines.append(f"Total Events Logged: {total_events}")
        lines.append(f"Total Errors: {total_errors}")
        lines.append(f"Total Warnings: {total_warnings}")
        
        if total_errors > 0:
            lines.append("")
            lines.append("WARNING: ERRORS DETECTED - Review Error Analysis section")
        else:
            lines.append("")
            lines.append("[OK] No errors detected")
        
        if total_warnings > 0:
            lines.append(f"WARNING: {total_warnings} warnings detected - Review Warning Analysis section")
        else:
            lines.append("[OK] No warnings detected")
        
        # Calculate total runtime
        if self.loggers:
            start_times = [logger.start_time for logger in self.loggers.values()]
            end_times = [time.time() for logger in self.loggers.values()]
            total_runtime = max(end_times) - min(start_times)
            lines.append(f"Total Runtime: {total_runtime:.2f} seconds")
        
        return lines
    
    def _generate_peer_overview(self) -> List[str]:
        """Generate peer overview section."""
        lines = []
        lines.append("PEER OVERVIEW")
        lines.append("-" * 80)
        
        for key, logger in self.loggers.items():
            stats = logger.get_statistics()
            lines.append(f"\n{logger.peer_type} (Port {logger.peer_port}):")
            lines.append(f"  Total Events: {stats['total_events']}")
            lines.append(f"  Messages Sent: {stats['messages_sent']}")
            lines.append(f"  Messages Received: {stats['messages_received']}")
            lines.append(f"  Errors: {stats['total_errors']}")
            lines.append(f"  Warnings: {stats['total_warnings']}")
            lines.append(f"  Connections: {stats['total_connections']}")
            lines.append(f"  Disconnections: {stats['total_disconnections']}")
            lines.append(f"  Runtime: {stats['total_time_seconds']:.2f} seconds")
        
        return lines
    
    def _generate_connection_analysis(self) -> List[str]:
        """Generate connection analysis section."""
        lines = []
        lines.append("CONNECTION ANALYSIS")
        lines.append("-" * 80)
        
        all_connections = []
        all_disconnections = []
        
        for logger in self.loggers.values():
            all_connections.extend(logger.connections)
            all_disconnections.extend(logger.disconnections)
        
        lines.append(f"Total Connections: {len(all_connections)}")
        lines.append(f"Total Disconnections: {len(all_disconnections)}")
        
        if all_connections:
            lines.append("\nConnections:")
            for conn in all_connections:
                lines.append(f"  - {conn.get('peer_type', 'Unknown')} at {conn.get('address', '?')}:{conn.get('port', '?')}")
        
        if all_disconnections:
            lines.append("\nDisconnections:")
            for disc in all_disconnections:
                if disc.get('address'):
                    lines.append(f"  - {disc.get('address', '?')}:{disc.get('port', '?')}")
                else:
                    lines.append(f"  - General disconnection")
        
        # Check for connection issues
        if len(all_connections) == 0:
            lines.append("\nWARNING: No connections detected!")
        elif len(all_connections) != len(all_disconnections):
            lines.append(f"\nWARNING: Connection/disconnection mismatch ({len(all_connections)} connections, {len(all_disconnections)} disconnections)")
        
        return lines
    
    def _generate_message_flow_analysis(self) -> List[str]:
        """Generate message flow analysis section."""
        lines = []
        lines.append("MESSAGE FLOW ANALYSIS")
        lines.append("-" * 80)
        
        # Aggregate message counts
        message_counts = defaultdict(int)
        message_types = set()
        
        for logger in self.loggers.values():
            for direction, msg_type, _ in logger.message_sequence:
                key = f"{direction}_{msg_type}"
                message_counts[key] += 1
                message_types.add(msg_type)
        
        lines.append(f"Unique Message Types: {len(message_types)}")
        lines.append(f"Total Messages: {sum(message_counts.values())}")
        
        lines.append("\nMessage Breakdown:")
        for key in sorted(message_counts.keys()):
            count = message_counts[key]
            lines.append(f"  {key}: {count}")
        
        # Check for message flow issues
        sent_counts = {k: v for k, v in message_counts.items() if k.startswith("SENT_")}
        received_counts = {k: v for k, v in message_counts.items() if k.startswith("RECEIVED_")}
        
        # Check for unacknowledged messages
        for msg_type in message_types:
            sent_key = f"SENT_{msg_type}"
            received_key = f"RECEIVED_{msg_type}"
            sent = sent_counts.get(sent_key, 0)
            received = received_counts.get(received_key, 0)
            
            # Some messages don't need responses (like ACK)
            if msg_type not in ["ACK", "HANDSHAKE_RESPONSE"] and sent > 0:
                if received == 0:
                    lines.append(f"\nWARNING: {msg_type} sent but never received")
                elif abs(sent - received) > 2:  # Allow some tolerance
                    lines.append(f"\nWARNING: {msg_type} count mismatch (sent: {sent}, received: {received})")
        
        return lines
    
    def _generate_error_analysis(self) -> List[str]:
        """Generate error analysis section."""
        lines = []
        lines.append("ERROR ANALYSIS")
        lines.append("-" * 80)
        
        all_errors = []
        for logger in self.loggers.values():
            all_errors.extend(logger.errors)
        
        if not all_errors:
            lines.append("[OK] No errors detected")
            return lines
        
        lines.append(f"Total Errors: {len(all_errors)}")
        lines.append("")
        
        # Group errors by type
        error_types = defaultdict(list)
        for error in all_errors:
            error_msg = error.message
            error_types[error_msg].append(error)
        
        lines.append("Error Summary:")
        for error_msg, errors in error_types.items():
            lines.append(f"  {error_msg}: {len(errors)} occurrence(s)")
        
        lines.append("\nDetailed Errors:")
        for i, error in enumerate(all_errors, 1):
            lines.append(f"\n  Error #{i}:")
            lines.append(f"    Time: {datetime.fromtimestamp(error.timestamp).isoformat()}")
            lines.append(f"    Peer: {error.peer_type} (Port {error.peer_port})")
            lines.append(f"    Message: {error.message}")
            if error.error:
                lines.append(f"    Exception: {error.error}")
            if error.stack_trace:
                lines.append(f"    Stack Trace:")
                for line in error.stack_trace.split('\n'):
                    lines.append(f"      {line}")
            if error.data:
                lines.append(f"    Context: {json.dumps(error.data, indent=6)}")
        
        return lines
    
    def _generate_warning_analysis(self) -> List[str]:
        """Generate warning analysis section."""
        lines = []
        lines.append("WARNING ANALYSIS")
        lines.append("-" * 80)
        
        all_warnings = []
        for logger in self.loggers.values():
            all_warnings.extend(logger.warnings)
        
        if not all_warnings:
            lines.append("[OK] No warnings detected")
            return lines
        
        lines.append(f"Total Warnings: {len(all_warnings)}")
        lines.append("")
        
        # Group warnings by type
        warning_types = defaultdict(list)
        for warning in all_warnings:
            warning_types[warning.message].append(warning)
        
        lines.append("Warning Summary:")
        for warning_msg, warnings in warning_types.items():
            lines.append(f"  {warning_msg}: {len(warnings)} occurrence(s)")
        
        lines.append("\nDetailed Warnings:")
        for i, warning in enumerate(all_warnings, 1):
            lines.append(f"\n  Warning #{i}:")
            lines.append(f"    Time: {datetime.fromtimestamp(warning.timestamp).isoformat()}")
            lines.append(f"    Peer: {warning.peer_type} (Port {warning.peer_port})")
            lines.append(f"    Message: {warning.message}")
            if warning.data:
                lines.append(f"    Context: {json.dumps(warning.data, indent=6)}")
        
        return lines
    
    def _generate_battle_state_analysis(self) -> List[str]:
        """Generate battle state analysis section."""
        lines = []
        lines.append("BATTLE STATE ANALYSIS")
        lines.append("-" * 80)
        
        battle_events = []
        for logger in self.loggers.values():
            for event in logger.events:
                if event.event_type == "BATTLE_EVENT" or event.event_type == "STATE_CHANGE":
                    battle_events.append(event)
        
        if not battle_events:
            lines.append("No battle state changes detected")
            return lines
        
        lines.append(f"Total Battle Events: {len(battle_events)}")
        lines.append("")
        lines.append("Battle Event Timeline:")
        
        # Sort by timestamp
        battle_events.sort(key=lambda e: e.timestamp)
        
        for event in battle_events:
            time_str = datetime.fromtimestamp(event.timestamp).isoformat()
            lines.append(f"  [{time_str}] {event.peer_type}: {event.message}")
            if event.data:
                lines.append(f"    Data: {json.dumps(event.data, indent=6)}")
        
        return lines
    
    def _generate_timing_analysis(self) -> List[str]:
        """Generate timing analysis section."""
        lines = []
        lines.append("TIMING ANALYSIS")
        lines.append("-" * 80)
        
        # Analyze message timing
        timeouts = []
        retransmissions = []
        
        for logger in self.loggers.values():
            for event in logger.events:
                if event.event_type == "TIMEOUT":
                    timeouts.append(event)
                elif event.event_type == "RETRANSMISSION":
                    retransmissions.append(event)
        
        lines.append(f"Total Timeouts: {len(timeouts)}")
        lines.append(f"Total Retransmissions: {len(retransmissions)}")
        
        if timeouts:
            lines.append("\nTimeout Events:")
            for timeout in timeouts:
                lines.append(f"  - {timeout.message} at {datetime.fromtimestamp(timeout.timestamp).isoformat()}")
        
        if retransmissions:
            lines.append("\nRetransmission Events:")
            retry_counts = defaultdict(int)
            for retrans in retransmissions:
                if retrans.data:
                    retry_count = retrans.data.get("retry_count", 0)
                    retry_counts[retry_count] += 1
            for retry_count, count in sorted(retry_counts.items()):
                lines.append(f"  Retry attempt {retry_count}: {count} messages")
        
        # Calculate message round-trip times (if possible)
        # This would require matching sent/received messages by sequence number
        
        return lines
    
    def _generate_network_analysis(self) -> List[str]:
        """Generate network analysis section."""
        lines = []
        lines.append("NETWORK ANALYSIS")
        lines.append("-" * 80)
        
        # Analyze connection stability
        connection_durations = []
        
        for logger in self.loggers.values():
            if logger.connections and logger.disconnections:
                # Simple analysis - could be improved
                conn_count = len(logger.connections)
                disc_count = len(logger.disconnections)
                lines.append(f"{logger.peer_type} (Port {logger.peer_port}):")
                lines.append(f"  Connections: {conn_count}")
                lines.append(f"  Disconnections: {disc_count}")
        
        # Check for network issues
        total_retransmissions = sum(
            len([e for e in logger.events if e.event_type == "RETRANSMISSION"])
            for logger in self.loggers.values()
        )
        
        if total_retransmissions > 10:
            lines.append(f"\nWARNING: High number of retransmissions ({total_retransmissions})")
            lines.append("    This may indicate network instability or packet loss")
        
        return lines
    
    def _generate_chat_analysis(self) -> List[str]:
        """Generate chat analysis section."""
        lines = []
        lines.append("CHAT ANALYSIS")
        lines.append("-" * 80)
        
        chat_messages = []
        for logger in self.loggers.values():
            for event in logger.events:
                if event.event_type == "CHAT_MESSAGE":
                    chat_messages.append(event)
        
        if not chat_messages:
            lines.append("No chat messages detected")
            return lines
        
        lines.append(f"Total Chat Messages: {len(chat_messages)}")
        lines.append("")
        lines.append("Chat Message Timeline:")
        
        # Sort by timestamp
        chat_messages.sort(key=lambda e: e.timestamp)
        
        for event in chat_messages:
            time_str = datetime.fromtimestamp(event.timestamp).isoformat()
            direction = event.data.get("direction", "UNKNOWN") if event.data else "UNKNOWN"
            sender = event.data.get("sender", "Unknown") if event.data else "Unknown"
            message = event.data.get("message", "") if event.data else ""
            lines.append(f"  [{time_str}] {direction} - {sender}: {message}")
        
        return lines
    
    def _generate_spectator_analysis(self) -> List[str]:
        """Generate spectator analysis section."""
        lines = []
        lines.append("SPECTATOR ANALYSIS")
        lines.append("-" * 80)
        
        spectator_joins = []
        for logger in self.loggers.values():
            for event in logger.events:
                if event.event_type == "SPECTATOR_JOIN":
                    spectator_joins.append(event)
        
        if not spectator_joins:
            lines.append("No spectator join events detected")
            return lines
        
        lines.append(f"Total Spectator Joins: {len(spectator_joins)}")
        lines.append("")
        lines.append("Spectator Join Timeline:")
        
        for event in spectator_joins:
            time_str = datetime.fromtimestamp(event.timestamp).isoformat()
            lines.append(f"  [{time_str}] {event.message}")
            if event.data:
                lines.append(f"    Address: {event.data.get('address', '?')}:{event.data.get('port', '?')}")
        
        # Check if spectators received battle updates
        spectator_loggers = [logger for logger in self.loggers.values() if logger.peer_type == "SpectatorPeer"]
        if spectator_loggers:
            lines.append("\nSpectator Message Reception:")
            for logger in spectator_loggers:
                stats = logger.get_statistics()
                lines.append(f"  {logger.peer_type} (Port {logger.peer_port}):")
                lines.append(f"    Messages Received: {stats['messages_received']}")
                lines.append(f"    Battle Events: {stats['event_type_counts'].get('BATTLE_EVENT', 0)}")
        
        return lines
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations section."""
        lines = []
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        
        # Analyze issues and provide recommendations
        all_errors = []
        all_warnings = []
        total_retransmissions = 0
        
        for logger in self.loggers.values():
            all_errors.extend(logger.errors)
            all_warnings.extend(logger.warnings)
            total_retransmissions += len([e for e in logger.events if e.event_type == "RETRANSMISSION"])
        
        recommendations = []
        
        if all_errors:
            recommendations.append("1. Review all errors in the Error Analysis section")
            recommendations.append("2. Check network connectivity and firewall settings")
            recommendations.append("3. Verify that all peers are using compatible protocol versions")
        
        if total_retransmissions > 10:
            recommendations.append("4. High retransmission rate detected - check network stability")
            recommendations.append("5. Consider increasing timeout values if network is slow")
        
        if not recommendations:
            recommendations.append("[OK] No critical issues detected")
            recommendations.append("System appears to be functioning normally")
        
        for rec in recommendations:
            lines.append(rec)
        
        return lines
    
    def _generate_detailed_event_log(self) -> List[str]:
        """Generate detailed event log section."""
        lines = []
        lines.append("DETAILED EVENT LOG")
        lines.append("-" * 80)
        lines.append("(Chronological order across all peers)")
        lines.append("")
        
        # Collect all events from all loggers
        all_events = []
        for logger in self.loggers.values():
            for event in logger.events:
                all_events.append((event.timestamp, logger.peer_type, logger.peer_port, event))
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x[0])
        
        lines.append(f"Total Events: {len(all_events)}")
        lines.append("")
        
        for timestamp, peer_type, peer_port, event in all_events:
            time_str = datetime.fromtimestamp(timestamp).isoformat()
            lines.append(f"[{time_str}] {peer_type} (Port {peer_port}) - {event.event_type}: {event.message}")
            if event.data:
                lines.append(f"  Data: {json.dumps(event.data, indent=4, default=str)}")
            if event.error:
                lines.append(f"  Error: {event.error}")
        
        return lines
    
    def save_report(self, filename: str = None, append: bool = False):
        """Generate and save the bug report to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bug_report_{timestamp}.txt"
        
        report = self.generate_report()
        
        # Use UTF-8 encoding to handle any special characters
        try:
            mode = 'a' if append else 'w'
            with open(filename, mode, encoding='utf-8') as f:
                if append:
                    f.write("\n" + "="*80 + "\n")
                    f.write(f"UPDATED: {datetime.now().isoformat()}\n")
                    f.write("="*80 + "\n\n")
                f.write(report)
        except UnicodeEncodeError:
            # Fallback to ASCII-safe encoding if UTF-8 fails
            mode = 'a' if append else 'w'
            with open(filename, mode, encoding='ascii', errors='replace') as f:
                if append:
                    f.write("\n" + "="*80 + "\n")
                    f.write(f"UPDATED: {datetime.now().isoformat()}\n")
                    f.write("="*80 + "\n\n")
                f.write(report)
        
        if not append:
            print(f"Bug report saved to: {filename}")
        return filename
    
    def update_live_report(self, filename: str):
        """Update the live bug report file (overwrites previous content)."""
        report = self.generate_report()
        
        # Add "LIVE" indicator at the top
        live_report = []
        live_report.append("=" * 80)
        live_report.append("POKEPROTOCOL LIVE BUG REPORT (UPDATING IN REAL-TIME)")
        live_report.append("=" * 80)
        live_report.append(f"Last Updated: {datetime.now().isoformat()}")
        live_report.append(f"Status: ACTIVE - Report updates automatically")
        live_report.append("")
        live_report.append(report)
        
        # Use UTF-8 encoding to handle any special characters
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(live_report))
        except UnicodeEncodeError:
            # Fallback to ASCII-safe encoding if UTF-8 fails
            with open(filename, 'w', encoding='ascii', errors='replace') as f:
                f.write('\n'.join(live_report))


def main():
    """Main entry point."""
    print("Generating bug report...")
    
    generator = BugReportGenerator()
    filename = generator.save_report()
    
    print(f"\nReport generated successfully!")
    print(f"File: {filename}")
    print(f"\nTo view the report, open: {filename}")


if __name__ == "__main__":
    main()

