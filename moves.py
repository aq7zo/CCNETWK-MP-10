"""
Pokémon Moves Module

This module defines available moves for Pokémon with their properties
including power, damage category (physical/special), and type.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Move:
    """
    Data class representing a Pokémon move.
    
    Attributes:
        name: The name of the move
        power: Base power of the move
        damage_category: "physical" or "special"
        move_type: The type of the move (e.g., "fire", "water", "electric")
    """
    name: str
    power: int
    damage_category: str
    move_type: str
    
    def __init__(self, name: str, power: int, damage_category: str, move_type: str):
        """
        Initialize a move.
        
        Args:
            name: Move name
            power: Base power
            damage_category: "physical" or "special"
            move_type: Move's type
        """
        self.name = name
        self.power = power
        self.damage_category = damage_category.lower()
        self.move_type = move_type.lower()


class MoveDatabase:
    """
    Database of available Pokémon moves.
    
    Provides access to moves organized by type and Pokémon.
    This is a simplified implementation - in a real system, moves would
    be more extensive and Pokémon-specific.
    """
    
    def __init__(self):
        """Initialize the move database with default moves."""
        self.moves: Dict[str, Move] = {}
        self._populate_default_moves()
    
    def _populate_default_moves(self):
        """Populate the database with default moves across all types."""
        # Fire-type moves
        self.moves["Ember"] = Move("Ember", 40, "special", "fire")
        self.moves["Flame Thrower"] = Move("Flame Thrower", 90, "special", "fire")
        self.moves["Fire Blast"] = Move("Fire Blast", 110, "special", "fire")
        self.moves["Flame Charge"] = Move("Flame Charge", 50, "physical", "fire")
        self.moves["Fire Fang"] = Move("Fire Fang", 65, "physical", "fire")
        
        # Water-type moves
        self.moves["Water Gun"] = Move("Water Gun", 40, "special", "water")
        self.moves["Hydro Pump"] = Move("Hydro Pump", 110, "special", "water")
        self.moves["Surf"] = Move("Surf", 90, "special", "water")
        self.moves["Aqua Tail"] = Move("Aqua Tail", 90, "physical", "water")
        self.moves["Waterfall"] = Move("Waterfall", 80, "physical", "water")
        
        # Electric-type moves
        self.moves["Thunder Shock"] = Move("Thunder Shock", 40, "special", "electric")
        self.moves["Thunderbolt"] = Move("Thunderbolt", 90, "special", "electric")
        self.moves["Thunder"] = Move("Thunder", 110, "special", "electric")
        self.moves["Wild Charge"] = Move("Wild Charge", 90, "physical", "electric")
        self.moves["Thunder Punch"] = Move("Thunder Punch", 75, "physical", "electric")
        
        # Grass-type moves
        self.moves["Vine Whip"] = Move("Vine Whip", 45, "physical", "grass")
        self.moves["Solar Beam"] = Move("Solar Beam", 120, "special", "grass")
        self.moves["Leaf Blade"] = Move("Leaf Blade", 90, "physical", "grass")
        self.moves["Energy Ball"] = Move("Energy Ball", 90, "special", "grass")
        self.moves["Seed Bomb"] = Move("Seed Bomb", 80, "physical", "grass")
        
        # Psychic-type moves
        self.moves["Confusion"] = Move("Confusion", 50, "special", "psychic")
        self.moves["Psychic"] = Move("Psychic", 90, "special", "psychic")
        self.moves["Psyshock"] = Move("Psyshock", 80, "special", "psychic")
        self.moves["Zen Headbutt"] = Move("Zen Headbutt", 80, "physical", "psychic")
        self.moves["Psycho Cut"] = Move("Psycho Cut", 70, "physical", "psychic")
        
        # Normal-type moves
        self.moves["Tackle"] = Move("Tackle", 40, "physical", "normal")
        self.moves["Body Slam"] = Move("Body Slam", 85, "physical", "normal")
        self.moves["Hyper Beam"] = Move("Hyper Beam", 150, "special", "normal")
        self.moves["Return"] = Move("Return", 102, "physical", "normal")
        self.moves["Swift"] = Move("Swift", 60, "special", "normal")
        
        # Fighting-type moves
        self.moves["Karate Chop"] = Move("Karate Chop", 50, "physical", "fighting")
        self.moves["Close Combat"] = Move("Close Combat", 120, "physical", "fighting")
        self.moves["Aura Sphere"] = Move("Aura Sphere", 80, "special", "fighting")
        self.moves["Brick Break"] = Move("Brick Break", 75, "physical", "fighting")
        self.moves["Focus Blast"] = Move("Focus Blast", 120, "special", "fighting")
        
        # Poison-type moves
        self.moves["Poison Sting"] = Move("Poison Sting", 15, "physical", "poison")
        self.moves["Sludge Bomb"] = Move("Sludge Bomb", 90, "special", "poison")
        self.moves["Gunk Shot"] = Move("Gunk Shot", 120, "physical", "poison")
        self.moves["Acid"] = Move("Acid", 40, "special", "poison")
        self.moves["Cross Poison"] = Move("Cross Poison", 70, "physical", "poison")
        
        # Bug-type moves
        self.moves["Bug Bite"] = Move("Bug Bite", 60, "physical", "bug")
        self.moves["X-Scissor"] = Move("X-Scissor", 80, "physical", "bug")
        self.moves["Bug Buzz"] = Move("Bug Buzz", 90, "special", "bug")
        self.moves["Signal Beam"] = Move("Signal Beam", 75, "special", "bug")
        self.moves["Megahorn"] = Move("Megahorn", 120, "physical", "bug")
        
        # Dark-type moves
        self.moves["Bite"] = Move("Bite", 60, "physical", "dark")
        self.moves["Crunch"] = Move("Crunch", 80, "physical", "dark")
        self.moves["Dark Pulse"] = Move("Dark Pulse", 80, "special", "dark")
        self.moves["Foul Play"] = Move("Foul Play", 95, "physical", "dark")
        self.moves["Night Slash"] = Move("Night Slash", 70, "physical", "dark")
        
        # Dragon-type moves
        self.moves["Dragon Breath"] = Move("Dragon Breath", 60, "special", "dragon")
        self.moves["Dragon Claw"] = Move("Dragon Claw", 80, "physical", "dragon")
        self.moves["Dragon Pulse"] = Move("Dragon Pulse", 85, "special", "dragon")
        self.moves["Outrage"] = Move("Outrage", 120, "physical", "dragon")
        
        # Fairy-type moves
        self.moves["Fairy Wind"] = Move("Fairy Wind", 40, "special", "fairy")
        self.moves["Moonblast"] = Move("Moonblast", 95, "special", "fairy")
        self.moves["Play Rough"] = Move("Play Rough", 90, "physical", "fairy")
        self.moves["Dazzling Gleam"] = Move("Dazzling Gleam", 80, "special", "fairy")
        
        # Flying-type moves
        self.moves["Peck"] = Move("Peck", 35, "physical", "flying")
        self.moves["Aerial Ace"] = Move("Aerial Ace", 60, "physical", "flying")
        self.moves["Fly"] = Move("Fly", 90, "physical", "flying")
        self.moves["Air Slash"] = Move("Air Slash", 75, "special", "flying")
        self.moves["Brave Bird"] = Move("Brave Bird", 120, "physical", "flying")
        
        # Ghost-type moves
        self.moves["Lick"] = Move("Lick", 30, "physical", "ghost")
        self.moves["Shadow Ball"] = Move("Shadow Ball", 80, "special", "ghost")
        self.moves["Shadow Punch"] = Move("Shadow Punch", 60, "physical", "ghost")
        self.moves["Shadow Claw"] = Move("Shadow Claw", 70, "physical", "ghost")
        self.moves["Hex"] = Move("Hex", 65, "special", "ghost")
        
        # Ground-type moves
        self.moves["Mud Slap"] = Move("Mud Slap", 20, "special", "ground")
        self.moves["Earthquake"] = Move("Earthquake", 100, "physical", "ground")
        self.moves["Earth Power"] = Move("Earth Power", 90, "special", "ground")
        self.moves["Bulldoze"] = Move("Bulldoze", 60, "physical", "ground")
        self.moves["Stomping Tantrum"] = Move("Stomping Tantrum", 75, "physical", "ground")
        
        # Ice-type moves
        self.moves["Ice Beam"] = Move("Ice Beam", 90, "special", "ice")
        self.moves["Ice Punch"] = Move("Ice Punch", 75, "physical", "ice")
        self.moves["Blizzard"] = Move("Blizzard", 110, "special", "ice")
        self.moves["Ice Shard"] = Move("Ice Shard", 40, "physical", "ice")
        self.moves["Avalanche"] = Move("Avalanche", 60, "physical", "ice")
        
        # Rock-type moves
        self.moves["Rock Throw"] = Move("Rock Throw", 50, "physical", "rock")
        self.moves["Rock Slide"] = Move("Rock Slide", 75, "physical", "rock")
        self.moves["Stone Edge"] = Move("Stone Edge", 100, "physical", "rock")
        self.moves["Power Gem"] = Move("Power Gem", 80, "special", "rock")
        self.moves["Ancient Power"] = Move("Ancient Power", 60, "special", "rock")
        
        # Steel-type moves
        self.moves["Metal Claw"] = Move("Metal Claw", 50, "physical", "steel")
        self.moves["Iron Head"] = Move("Iron Head", 80, "physical", "steel")
        self.moves["Flash Cannon"] = Move("Flash Cannon", 80, "special", "steel")
        self.moves["Steel Wing"] = Move("Steel Wing", 70, "physical", "steel")
        self.moves["Meteor Mash"] = Move("Meteor Mash", 90, "physical", "steel")
    
    def get_move(self, name: str) -> Optional[Move]:
        """
        Retrieve a move by name.
        
        Args:
            name: The name of the move (case-insensitive)
            
        Returns:
            Move object if found, None otherwise
        """
        return self.moves.get(name)
    
    def get_all_move_names(self) -> list:
        """
        Get a list of all available move names.
        
        Returns:
            List of move names
        """
        return list(self.moves.keys())
    
    def get_moves_by_type(self, move_type: str) -> list:
        """
        Get all moves of a specific type.
        
        Args:
            move_type: The type to filter by
            
        Returns:
            List of Move objects of that type
        """
        move_type_lower = move_type.lower()
        return [move for move in self.moves.values() if move.move_type == move_type_lower]

