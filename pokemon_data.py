"""
Pokémon Data Loader Module

This module handles loading and parsing Pokémon data from CSV files.
It provides data structures for Pokémon stats, type effectiveness, and damage calculation.
"""

import csv
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Pokemon:
    """
    Data class representing a Pokémon with all its base stats and type information.
    
    Attributes:
        name: The name of the Pokémon
        hp: Base HP stat
        attack: Base Attack stat
        defense: Base Defense stat
        sp_attack: Base Special Attack stat
        sp_defense: Base Special Defense stat
        speed: Base Speed stat
        type1: Primary type
        type2: Optional secondary type
        type_effectiveness: Dictionary mapping type names to effectiveness multipliers
    """
    name: str
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    type1: str
    type2: Optional[str]
    type_effectiveness: Dict[str, float]
    
    def __post_init__(self):
        """Normalize type names to lowercase and handle empty type2."""
        self.type1 = self.type1.lower()
        self.type2 = self.type2.lower() if self.type2 else None
        # Normalize effectiveness keys
        self.type_effectiveness = {k.lower(): v for k, v in self.type_effectiveness.items()}


class PokemonDataLoader:
    """
    Loads and manages Pokémon data from CSV files.
    
    This class provides functionality to:
    - Load Pokémon data from a CSV file
    - Look up Pokémon by name
    - Get type effectiveness information
    - Provide access to all available Pokémon
    """
    
    def __init__(self, csv_file: str = "pokemon_cleaned.csv"):
        """
        Initialize the data loader with a CSV file.
        
        Args:
            csv_file: Path to the Pokémon CSV file (defaults to cleaned version)
        """
        self.csv_file = csv_file
        self.pokemon_db: Dict[str, Pokemon] = {}
        self.type_mapping = {
            "bug": "against_bug",
            "dark": "against_dark",
            "dragon": "against_dragon",
            "electric": "against_electric",
            "fairy": "against_fairy",
            "fighting": "against_fight",
            "fire": "against_fire",
            "flying": "against_flying",
            "ghost": "against_ghost",
            "grass": "against_grass",
            "ground": "against_ground",
            "ice": "against_ice",
            "normal": "against_normal",
            "poison": "against_poison",
            "psychic": "against_psychic",
            "rock": "against_rock",
            "steel": "against_steel",
            "water": "against_water"
        }
        self._load_data()
    
    def _load_data(self):
        """
        Load Pokémon data from CSV file into memory.
        
        Reads the CSV, parses each row, and creates Pokemon objects
        with all necessary stats and type effectiveness data.
        """
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Extract Pokémon name
                    pokemon_name = row['name']
                    
                    # Extract base stats
                    hp = int(row['hp'])
                    attack = int(row['attack'])
                    defense = int(row['defense'])
                    sp_attack = int(row['sp_attack'])
                    sp_defense = int(row['sp_defense'])
                    speed = int(row['speed'])
                    
                    # Extract types
                    type1 = row['type1'].lower()
                    type2 = row.get('type2', '').strip().lower()
                    type2 = type2 if type2 else None
                    
                    # Extract type effectiveness data
                    type_effectiveness = {}
                    for pokemon_type, csv_key in self.type_mapping.items():
                        if csv_key in row and row[csv_key]:
                            try:
                                effectiveness = float(row[csv_key])
                                type_effectiveness[pokemon_type] = effectiveness
                            except ValueError:
                                # Skip invalid values
                                pass
                    
                    # Create Pokemon object
                    pokemon = Pokemon(
                        name=pokemon_name,
                        hp=hp,
                        attack=attack,
                        defense=defense,
                        sp_attack=sp_attack,
                        sp_defense=sp_defense,
                        speed=speed,
                        type1=type1,
                        type2=type2,
                        type_effectiveness=type_effectiveness
                    )
                    
                    # Store in database
                    self.pokemon_db[pokemon_name.lower()] = pokemon
                    
        except FileNotFoundError:
            print(f"Error: Could not find {self.csv_file}")
            raise
        except Exception as e:
            print(f"Error loading Pokémon data: {e}")
            raise
    
    def get_pokemon(self, name: str) -> Optional[Pokemon]:
        """
        Retrieve a Pokémon by name.
        
        Args:
            name: The name of the Pokémon (case-insensitive)
            
        Returns:
            Pokemon object if found, None otherwise
        """
        return self.pokemon_db.get(name.lower())
    
    def get_all_pokemon_names(self) -> List[str]:
        """
        Get a list of all available Pokémon names.
        
        Returns:
            List of Pokémon names
        """
        return [pokemon.name for pokemon in self.pokemon_db.values()]
    
    def get_type_effectiveness(self, pokemon_name: str, move_type: str) -> float:
        """
        Get the type effectiveness multiplier for a move against a Pokémon.
        
        For dual-type Pokémon, effectiveness is calculated as the product
        of effectiveness against both types.
        
        Args:
            pokemon_name: Name of the defending Pokémon
            move_type: Type of the attacking move
            
        Returns:
            Combined effectiveness multiplier
        """
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return 1.0
        
        move_type_lower = move_type.lower()
        
        # Get effectiveness against type1
        type1_effectiveness = pokemon.type_effectiveness.get(move_type_lower, 1.0)
        
        # Get effectiveness against type2 (if exists)
        type2_effectiveness = 1.0
        if pokemon.type2:
            type2_effectiveness = pokemon.type_effectiveness.get(move_type_lower, 1.0)
        
        # Multiply for dual-type
        return type1_effectiveness * type2_effectiveness

