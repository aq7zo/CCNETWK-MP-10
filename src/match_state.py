"""
Centralized shared match state manager.

This module provides a file-based shared state that both host and joiner
can read/write to synchronize Pokémon selection during rematches.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock


class MatchStateManager:
    """Manages shared match state between host and joiner."""
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize match state manager.
        
        Args:
            state_file: Path to state file. If None, uses default location.
        """
        if state_file is None:
            # Use a default location in the project root
            project_root = Path(__file__).parent.parent
            state_file = str(project_root / ".match_state.json")
        
        self.state_file = Path(state_file)
        self._lock = Lock()
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Ensure state file exists with default values."""
        if not self.state_file.exists():
            self._write_state({
                "phase": "SELECTING",
                "host_selected": False,
                "joiner_selected": False,
                "host_pokemon": None,
                "joiner_pokemon": None
            })
    
    def _read_state(self) -> Dict[str, Any]:
        """Read state from file."""
        try:
            if not self.state_file.exists():
                return {
                    "phase": "SELECTING",
                    "host_selected": False,
                    "joiner_selected": False,
                    "host_pokemon": None,
                    "joiner_pokemon": None
                }
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Return default state if file is corrupted or unreadable
            return {
                "phase": "SELECTING",
                "host_selected": False,
                "joiner_selected": False,
                "host_pokemon": None,
                "joiner_pokemon": None
            }
    
    def _write_state(self, state: Dict[str, Any]):
        """Write state to file atomically."""
        try:
            # Write to temporary file first, then rename (atomic on most systems)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.state_file)
        except IOError as e:
            # If write fails, log but don't crash
            print(f"Warning: Failed to write match state: {e}")
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load current state.
        
        Returns:
            Dictionary with state fields
        """
        with self._lock:
            return self._read_state()
    
    def update_state(self, **kwargs):
        """
        Update state fields atomically.
        
        Args:
            **kwargs: State fields to update
        """
        with self._lock:
            state = self._read_state()
            state.update(kwargs)
            self._write_state(state)
    
    def reset_for_rematch(self):
        """Reset state for a new rematch."""
        with self._lock:
            self._write_state({
                "phase": "SELECTING",
                "host_selected": False,
                "joiner_selected": False,
                "host_pokemon": None,
                "joiner_pokemon": None
            })
    
    def mark_host_selected(self, pokemon_name: str):
        """Mark host as having selected a Pokémon."""
        self.update_state(
            host_selected=True,
            host_pokemon=pokemon_name
        )
    
    def mark_joiner_selected(self, pokemon_name: str):
        """Mark joiner as having selected a Pokémon."""
        self.update_state(
            joiner_selected=True,
            joiner_pokemon=pokemon_name
        )
    
    def set_phase(self, phase: str):
        """Set the current phase (SELECTING or BATTLE)."""
        self.update_state(phase=phase)
    
    def wait_for_both_selected(self, timeout: float = 60.0) -> bool:
        """
        Wait until both players have selected Pokémon.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if both selected, False if timeout
        """
        start_time = time.time()
        while time.time() < start_time + timeout:
            state = self.load_state()
            if state.get("host_selected") and state.get("joiner_selected"):
                return True
            time.sleep(0.2)
        return False


# Global instance
_match_state_manager = None


def get_match_state_manager() -> MatchStateManager:
    """Get the global match state manager instance."""
    global _match_state_manager
    if _match_state_manager is None:
        _match_state_manager = MatchStateManager()
    return _match_state_manager

