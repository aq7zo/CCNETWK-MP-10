"""
Battle State Machine Module

This module implements the battle state machine and game flow logic
for the PokeProtocol, managing transitions between states.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
from pokemon_data import Pokemon
from moves import Move


class BattleState(Enum):
    """Enumeration of all battle states in the state machine."""
    SETUP = "SETUP"
    WAITING_FOR_MOVE = "WAITING_FOR_MOVE"
    PROCESSING_TURN = "PROCESSING_TURN"
    GAME_OVER = "GAME_OVER"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class BattlePokemon:
    """
    Represents a Pokémon in battle with current HP and stat boosts.
    
    Attributes:
        pokemon: Base Pokémon data
        current_hp: Current HP in battle
        max_hp: Maximum HP
        special_attack_uses: Remaining special attack boosts
        special_defense_uses: Remaining special defense boosts
    """
    pokemon: Pokemon
    current_hp: int
    max_hp: int
    special_attack_uses: int
    special_defense_uses: int
    
    def __init__(self, pokemon: Pokemon, special_attack_uses: int = 5,
                 special_defense_uses: int = 5):
        """
        Initialize a battle Pokémon.
        
        Args:
            pokemon: Base Pokémon data
            special_attack_uses: Number of special attack boosts available
            special_defense_uses: Number of special defense boosts available
        """
        self.pokemon = pokemon
        self.max_hp = pokemon.hp
        self.current_hp = pokemon.hp
        self.special_attack_uses = special_attack_uses
        self.special_defense_uses = special_defense_uses
    
    def take_damage(self, damage: int) -> int:
        """
        Apply damage to this Pokémon.
        
        Args:
            damage: Damage to apply
            
        Returns:
            Remaining HP after damage
        """
        self.current_hp = max(0, self.current_hp - damage)
        return self.current_hp
    
    def is_fainted(self) -> bool:
        """
        Check if Pokémon has fainted.

        Returns:
            True if HP is 0 or less
        """
        return self.current_hp <= 0

    def can_use_special_attack_boost(self) -> bool:
        """
        Check if special attack boost is available.

        Returns:
            True if boost uses remain
        """
        return self.special_attack_uses > 0

    def can_use_special_defense_boost(self) -> bool:
        """
        Check if special defense boost is available.

        Returns:
            True if boost uses remain
        """
        return self.special_defense_uses > 0

    def use_special_attack_boost(self) -> bool:
        """
        Consume one special attack boost use.

        Returns:
            True if boost was consumed, False if none available
        """
        if self.can_use_special_attack_boost():
            self.special_attack_uses -= 1
            return True
        return False

    def use_special_defense_boost(self) -> bool:
        """
        Consume one special defense boost use.

        Returns:
            True if boost was consumed, False if none available
        """
        if self.can_use_special_defense_boost():
            self.special_defense_uses -= 1
            return True
        return False


class BattleStateMachine:
    """
    Manages the battle state and flow.
    
    Handles transitions between states, tracks Pokémon, manages turns,
    and coordinates the four-step handshake for each turn.
    """
    
    def __init__(self, is_host: bool):
        """
        Initialize the battle state machine.
        
        Args:
            is_host: True if this peer is the host, False if joiner
        """
        self.is_host = is_host
        self.state = BattleState.SETUP
        
        # Battle participants
        self.my_pokemon: Optional[BattlePokemon] = None
        self.opponent_pokemon: Optional[BattlePokemon] = None
        
        # Turn management
        self.my_turn = is_host  # Host goes first
        self.last_move: Optional[Move] = None
        self.last_attacker: Optional[str] = None
        
        # Calculation tracking
        self.my_calculation: Optional[Dict] = None
        self.opponent_calculation: Optional[Dict] = None
        self.calculation_confirmed = False
    
    def set_pokemon(self, pokemon: Pokemon, special_attack_uses: int = 5,
                   special_defense_uses: int = 5):
        """
        Set the player's Pokémon for battle.
        
        Args:
            pokemon: Pokémon to use
            special_attack_uses: Special attack boosts available
            special_defense_uses: Special defense boosts available
        """
        self.my_pokemon = BattlePokemon(pokemon, special_attack_uses, special_defense_uses)
    
    def set_opponent_pokemon(self, pokemon: Pokemon, special_attack_uses: int = 5,
                            special_defense_uses: int = 5):
        """
        Set the opponent's Pokémon for battle.
        
        Args:
            pokemon: Opponent's Pokémon
            special_attack_uses: Opponent's special attack boosts
            special_defense_uses: Opponent's special defense boosts
        """
        self.opponent_pokemon = BattlePokemon(pokemon, special_attack_uses, special_defense_uses)
    
    def advance_to_waiting(self):
        """Transition from SETUP to WAITING_FOR_MOVE state."""
        if self.state == BattleState.SETUP:
            self.state = BattleState.WAITING_FOR_MOVE
    
    def advance_to_processing(self, move: Move, attacker_name: str):
        """
        Transition from WAITING_FOR_MOVE to PROCESSING_TURN.
        
        Args:
            move: The move being used
            attacker_name: Name of attacking Pokémon
        """
        if self.state == BattleState.WAITING_FOR_MOVE:
            self.state = BattleState.PROCESSING_TURN
            self.last_move = move
            self.last_attacker = attacker_name
            self.my_calculation = None
            self.opponent_calculation = None
            self.calculation_confirmed = False
    
    def mark_my_turn_taken(self, move: Optional[Move] = None,
                           attacker_name: Optional[str] = None):
        """
        Manually transition into processing once we've initiated a move.

        Used by interactive flows that send AttackAnnounce directly instead of
        going through peer.use_move().
        """
        if self.state != BattleState.WAITING_FOR_MOVE or not self.my_turn:
            return

        attacker = attacker_name
        if attacker is None and self.my_pokemon:
            attacker = self.my_pokemon.pokemon.name

        if move and attacker:
            self.advance_to_processing(move, attacker)
            return

        # Fall back to a minimal transition when move data is unavailable
        self.state = BattleState.PROCESSING_TURN
        self.my_calculation = None
        self.opponent_calculation = None
        self.calculation_confirmed = False
        if attacker:
            self.last_attacker = attacker
    
    def advance_to_complete(self):
        """
        Complete current turn and transition back to WAITING_FOR_MOVE.
        
        Switches turn order and resets calculation tracking.
        """
        if self.state == BattleState.PROCESSING_TURN:
            self.state = BattleState.WAITING_FOR_MOVE
            self.my_turn = not self.my_turn  # Switch turns
            self.last_move = None
            self.last_attacker = None
    
    def advance_to_game_over(self):
        """Transition to GAME_OVER state."""
        self.state = BattleState.GAME_OVER
    
    def mark_disconnected(self):
        """Mark battle as disconnected."""
        self.state = BattleState.DISCONNECTED
    
    def record_my_calculation(self, calculation: Dict):
        """
        Record the local damage calculation.
        
        Args:
            calculation: Calculation results dictionary
        """
        self.my_calculation = calculation
    
    def record_opponent_calculation(self, calculation: Dict):
        """
        Record the opponent's reported calculation.
        
        Args:
            calculation: Opponent's calculation results
        """
        self.opponent_calculation = calculation
    
    def calculations_match(self) -> bool:
        """
        Check if calculations match between peers.
        
        Returns:
            True if calculations match, False otherwise
        """
        if not self.my_calculation or not self.opponent_calculation:
            return False
        
        my = self.my_calculation
        opp = self.opponent_calculation
        
        return (my["damage_dealt"] == opp["damage_dealt"] and
                my["defender_hp_remaining"] == opp["defender_hp_remaining"])
    
    def mark_calculation_confirmed(self):
        """Mark that calculations have been confirmed as matching."""
        self.calculation_confirmed = True
    
    def is_my_turn(self) -> bool:
        """
        Check if it's the player's turn to act.
        
        Returns:
            True if it's the player's turn
        """
        return self.my_turn and self.state == BattleState.WAITING_FOR_MOVE
    
    def is_game_over(self) -> bool:
        """
        Check if battle is over.
        
        Returns:
            True if battle is over
        """
        return self.state == BattleState.GAME_OVER
    
    def get_winner(self) -> Optional[str]:
        """
        Determine the winner of the battle.
        
        Returns:
            Name of winning Pokémon, or None if battle isn't over
        """
        if not self.is_game_over():
            return None
        
        if self.my_pokemon and self.opponent_pokemon:
            if self.my_pokemon.is_fainted():
                return self.opponent_pokemon.pokemon.name
            elif self.opponent_pokemon.is_fainted():
                return self.my_pokemon.pokemon.name
        
        return None
    
    def apply_calculation(self, calculation: Dict):
        """
        Apply a damage calculation to update battle state.
        
        Args:
            calculation: Calculation results to apply
        """
        attacker_name = calculation["attacker"]
        
        if attacker_name == self.my_pokemon.pokemon.name:
            # My Pokémon attacked opponent
            damage = calculation["damage_dealt"]
            self.opponent_pokemon.take_damage(damage)
        else:
            # Opponent attacked my Pokémon
            damage = calculation["damage_dealt"]
            self.my_pokemon.take_damage(damage)
    
    def get_current_state_info(self) -> str:
        """
        Get a human-readable description of current state.
        
        Returns:
            State description string
        """
        state_map = {
            BattleState.SETUP: "Setting up battle",
            BattleState.WAITING_FOR_MOVE: "Waiting for move" if not self.my_turn else "Your turn to move",
            BattleState.PROCESSING_TURN: "Processing turn",
            BattleState.GAME_OVER: "Game Over",
            BattleState.DISCONNECTED: "Disconnected"
        }
        return state_map.get(self.state, "Unknown state")
    
    def get_battle_status(self) -> str:
        """
        Get current battle status summary.
        
        Returns:
            Status summary string
        """
        if not self.my_pokemon or not self.opponent_pokemon:
            return "Battle not initialized"
        
        my_status = f"{self.my_pokemon.pokemon.name}: {self.my_pokemon.current_hp}/{self.my_pokemon.max_hp} HP"
        opp_status = f"{self.opponent_pokemon.pokemon.name}: {self.opponent_pokemon.current_hp}/{self.opponent_pokemon.max_hp} HP"
        
        return f"{my_status} vs {opp_status}"

