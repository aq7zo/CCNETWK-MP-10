"""
Damage Calculation Module

This module implements the damage calculation formula for Pokémon battles,
ensuring synchronized calculations between peers.
"""

import random
from typing import Dict, Tuple
from pokemon_data import Pokemon, PokemonDataLoader
from moves import Move


class DamageCalculator:
    """
    Calculates Pokémon battle damage using the protocol's formula.
    
    Implements the synchronized damage calculation that ensures
    both peers arrive at identical results.
    """
    
    def __init__(self, pokemon_loader: PokemonDataLoader, seed: int = 0):
        """
        Initialize the damage calculator.
        
        Args:
            pokemon_loader: PokemonDataLoader instance for type effectiveness lookup
            seed: Random seed for damage randomization (ensures sync between peers)
        """
        self.pokemon_loader = pokemon_loader
        self.rng = random.Random(seed)
        self.stab_multiplier = 1.5  # Same Type Attack Bonus
    
    def set_seed(self, seed: int):
        """
        Set the random seed for synchronized calculations.
        
        Args:
            seed: New random seed value
        """
        self.rng = random.Random(seed)
    
    def calculate_damage(self, attacker: Pokemon, defender: Pokemon,
                        move: Move, level: int = 50,
                        attacker_boost: bool = False, defender_boost: bool = False) -> Tuple[int, str]:
        """
        Calculate damage dealt by an attack.

        Uses the protocol's damage formula which incorporates:
        - Attacker and defender stats
        - Move base power
        - Type effectiveness (super effective, not very effective, etc.)
        - STAB (Same Type Attack Bonus)
        - Random variation
        - Stat boosts (special attack/defense)

        Args:
            attacker: The attacking Pokémon
            defender: The defending Pokémon
            move: The move being used
            level: Pokémon level (default 50)
            attacker_boost: Whether attacker has special attack boost active
            defender_boost: Whether defender has special defense boost active

        Returns:
            Tuple of (damage_amount, status_message)
        """
        # Boost multiplier (1.5x when active)
        boost_multiplier = 1.5

        # Determine attack/defense stats based on move category
        if move.damage_category == "physical":
            attacker_stat = attacker.attack
            defender_stat = defender.defense
        else:  # special
            attacker_stat = attacker.sp_attack
            defender_stat = defender.sp_defense
            # Apply boosts for special moves
            if attacker_boost:
                attacker_stat = int(attacker_stat * boost_multiplier)
            if defender_boost:
                defender_stat = int(defender_stat * boost_multiplier)
        
        # Calculate type effectiveness
        type_effectiveness = self.pokemon_loader.get_type_effectiveness(
            defender.name, move.move_type
        )
        
        # Check for STAB (Same Type Attack Bonus)
        stab = self.stab_multiplier if (attacker.type1 == move.move_type or 
                                        attacker.type2 == move.move_type) else 1.0
        
        # Random factor between 0.85 and 1.0
        random_factor = self.rng.uniform(0.85, 1.0)
        
        # Damage formula: ((2 * Level / 5 + 2) * Power * A/D / 50 + 2) * Modifiers
        # Modifiers = Type * STAB * Random
        base_calculation = ((2 * level / 5 + 2) * move.power * 
                           attacker_stat / defender_stat / 50 + 2)
        
        damage = int(base_calculation * type_effectiveness * stab * random_factor)
        
        # Ensure minimum damage of 1
        damage = max(1, damage)
        
        # Generate status message
        status_message = self._generate_status_message(
            attacker.name, defender.name, move.name,
            type_effectiveness, damage
        )
        
        return damage, status_message
    
    def _generate_status_message(self, attacker_name: str, defender_name: str,
                                move_name: str, effectiveness: float,
                                damage: int) -> str:
        """
        Generate a descriptive status message for the attack.
        
        Args:
            attacker_name: Name of attacking Pokémon
            defender_name: Name of defending Pokémon
            move_name: Name of move used
            effectiveness: Type effectiveness multiplier
            damage: Calculated damage
            
        Returns:
            Descriptive status message
        """
        msg = f"{attacker_name} used {move_name}!"
        
        if effectiveness >= 2.0:
            msg += " It's super effective!"
        elif effectiveness <= 0.5:
            msg += " It's not very effective..."
        
        msg += f" {defender_name} took {damage} damage!"
        
        return msg
    
    def calculate_turn_outcome(self, attacker: Pokemon, defender: Pokemon,
                              attacker_hp: int, defender_hp: int,
                              move: Move, level: int = 50) -> Dict:
        """
        Calculate complete turn outcome including HP updates.
        
        Args:
            attacker: Attacking Pokémon
            defender: Defending Pokémon
            attacker_hp: Current HP of attacker
            defender_hp: Current HP of defender
            move: Move being used
            level: Pokémon level
            
        Returns:
            Dictionary with turn results including:
            - damage_dealt: Damage inflicted
            - defender_hp_remaining: Defender's HP after attack
            - status_message: Descriptive message
        """
        damage, status_msg = self.calculate_damage(attacker, defender, move, level)
        
        defender_hp_remaining = max(0, defender_hp - damage)
        
        return {
            "damage_dealt": damage,
            "defender_hp_remaining": defender_hp_remaining,
            "status_message": status_msg,
            "attacker": attacker.name,
            "move_used": move.name
        }
    
    def verify_calculation(self, attacker: str, move_name: str,
                          expected_damage: int, expected_defender_hp: int,
                          attacker_pokemon: Pokemon, defender_pokemon: Pokemon,
                          attacker_hp: int, defender_hp: int, move: Move) -> bool:
        """
        Verify if a reported calculation matches the local calculation.
        
        Used for discrepancy detection in the protocol.
        
        Args:
            attacker: Name of attacker
            move_name: Name of move
            expected_damage: Damage reported by peer
            expected_defender_hp: Defender HP reported by peer
            attacker_pokemon: Local attacker Pokémon data
            defender_pokemon: Local defender Pokémon data
            attacker_hp: Current attacker HP
            defender_hp: Current defender HP
            move: Move being used
            
        Returns:
            True if calculations match, False otherwise
        """
        outcome = self.calculate_turn_outcome(
            attacker_pokemon, defender_pokemon, attacker_hp, defender_hp, move
        )
        
        return (outcome["damage_dealt"] == expected_damage and
                outcome["defender_hp_remaining"] == expected_defender_hp)

