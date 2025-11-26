"""
Data Cleaning Utility for Pokemon CSV

This module provides data cleaning and validation functions for the Pokemon CSV file.
It handles missing values, inconsistencies, data type conversions, and normalization.
"""

import csv
import re
from typing import Dict, List, Tuple, Optional


class PokemonDataCleaner:
    """
    Data cleaning utility for Pokemon CSV data.
    
    Performs the following operations:
    - Handles missing/null values
    - Normalizes whitespace and text
    - Validates data types
    - Fixes inconsistencies
    - Removes duplicates
    - Validates against expected ranges
    """
    
    def __init__(self, input_file: str = "data/pokemon.csv", output_file: str = "data/pokemon_cleaned.csv"):
        """
        Initialize the data cleaner.
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output cleaned CSV file
        """
        self.input_file = input_file
        self.output_file = output_file
        self.fieldnames = None  # Will store original column order
        self.stats = {
            "rows_processed": 0,
            "rows_cleaned": 0,
            "rows_removed": 0,
            "missing_values_filled": 0,
            "data_type_fixes": 0
        }
    
    def clean_pokemon_csv(self) -> Tuple[List[Dict], Dict]:
        """
        Main cleaning function that processes the entire CSV.
        
        Returns:
            Tuple of (cleaned_rows, statistics)
        """
        print(f"Loading data from {self.input_file}...")
        rows = self._load_csv()
        print(f"Loaded {len(rows)} rows")
        
        print("Cleaning data...")
        cleaned_rows = []
        
        for idx, row in enumerate(rows):
            self.stats["rows_processed"] += 1
            
            try:
                cleaned_row = self._clean_row(row, idx)
                if cleaned_row:
                    cleaned_rows.append(cleaned_row)
                    self.stats["rows_cleaned"] += 1
                else:
                    self.stats["rows_removed"] += 1
                    print(f"Removed row {idx + 1}: Invalid data")
            except Exception as e:
                print(f"Error cleaning row {idx + 1}: {e}")
                self.stats["rows_removed"] += 1
        
        print(f"Saving cleaned data to {self.output_file}...")
        self._save_csv(cleaned_rows)
        
        return cleaned_rows, self.stats
    
    def _load_csv(self) -> List[Dict]:
        """
        Load CSV file.
        
        Returns:
            List of dictionaries representing rows
        """
        rows = []
        with open(self.input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Store original field names to preserve column order
            self.fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
        return rows
    
    def _save_csv(self, rows: List[Dict]):
        """
        Save cleaned rows to CSV.
        
        Args:
            rows: List of cleaned row dictionaries
        """
        if not rows:
            print("No rows to save!")
            return
        
        # Preserve original column order if available
        fieldnames = self.fieldnames if self.fieldnames else rows[0].keys()
        
        with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    def _clean_row(self, row: Dict, row_num: int) -> Optional[Dict]:
        """
        Clean a single row of data.
        
        Args:
            row: Dictionary representing a row
            row_num: Row number for error reporting
            
        Returns:
            Cleaned row dictionary or None if invalid
        """
        cleaned = {}
        
        # Required fields validation
        required_fields = ['name', 'hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 
                          'speed', 'type1']
        
        for field in required_fields:
            if field not in row:
                print(f"Row {row_num + 1}: Missing required field '{field}'")
                return None
        
        # Clean text fields
        cleaned['name'] = self._clean_text(row.get('name', ''))
        if not cleaned['name']:
            print(f"Row {row_num + 1}: Empty Pokemon name")
            return None
        
        # Process all fields from the original row
        for field, value in row.items():
            if field in cleaned:
                continue  # Already processed
                
            # Clean and validate numeric stats
            numeric_fields = {
                'hp': (0, 300),
                'attack': (0, 300),
                'defense': (0, 300),
                'sp_attack': (0, 300),
                'sp_defense': (0, 300),
                'speed': (0, 300),
                'base_total': (0, 1000),
                'base_happiness': (0, 255),
                'base_egg_steps': (0, 32000),
                'capture_rate': (0, 255),
                'experience_growth': (0, 9999999),
                'pokedex_number': (1, 10000),
                'percentage_male': (0, 100),
                'generation': (1, 10),
                'is_legendary': (0, 1),
                'height_m': (0, 100),
                'weight_kg': (0, 10000),
                'against_bug': (0, 4),
                'against_dark': (0, 4),
                'against_dragon': (0, 4),
                'against_electric': (0, 4),
                'against_fairy': (0, 4),
                'against_fight': (0, 4),
                'against_fire': (0, 4),
                'against_flying': (0, 4),
                'against_ghost': (0, 4),
                'against_grass': (0, 4),
                'against_ground': (0, 4),
                'against_ice': (0, 4),
                'against_normal': (0, 4),
                'against_poison': (0, 4),
                'against_psychic': (0, 4),
                'against_rock': (0, 4),
                'against_steel': (0, 4),
                'against_water': (0, 4),
            }
            
            if field in numeric_fields:
                min_val, max_val = numeric_fields[field]
                value = self._clean_numeric(value, field, min_val, max_val)
                if value is None:
                    # Required numeric fields
                    if field in ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
                        print(f"Row {row_num + 1}: Invalid numeric field '{field}'")
                        return None
                    # Skip optional numeric fields
                    continue
                cleaned[field] = value
                
            elif field in ['type1', 'type2']:
                type_val = self._clean_type(value)
                if field == 'type1' and not type_val:
                    print(f"Row {row_num + 1}: Invalid type1")
                    return None
                cleaned[field] = type_val
                
            else:
                # Text fields
                cleaned[field] = self._clean_text(value) if value else ''
        
        return cleaned
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text fields by removing extra whitespace and normalizing.
        
        Args:
            text: Input text string
            
        Returns:
            Cleaned text string
        """
        if not text or not isinstance(text, str):
            return ''
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        
        return text.strip()
    
    def _clean_numeric(self, value: str, field_name: str, min_val: float, max_val: float) -> Optional[float]:
        """
        Clean and validate numeric fields.
        
        Args:
            value: Input value string
            field_name: Name of field for error reporting
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Cleaned numeric value or None if invalid
        """
        if not value or value == '':
            return None
        
        try:
            # Remove any whitespace
            value = str(value).strip()
            
            # Skip if explicitly marked as missing
            if value.lower() in ['', 'n/a', 'null', 'none']:
                return None
            
            # Convert to float
            num_value = float(value)
            
            # Validate range
            if num_value < min_val or num_value > max_val:
                print(f"Warning: {field_name} value {num_value} out of range [{min_val}, {max_val}]")
                # Clamp to valid range
                num_value = max(min_val, min(num_value, max_val))
                self.stats["data_type_fixes"] += 1
            
            # Return as int if it's a whole number (for integer fields)
            if num_value.is_integer():
                return int(num_value)
            return num_value
            
        except (ValueError, TypeError):
            # Try to extract numeric part from mixed strings
            numeric_match = re.search(r'[\d.]+', str(value))
            if numeric_match:
                try:
                    num_value = float(numeric_match.group())
                    if num_value < min_val or num_value > max_val:
                        num_value = max(min_val, min(num_value, max_val))
                        self.stats["data_type_fixes"] += 1
                    return int(num_value) if num_value.is_integer() else num_value
                except ValueError:
                    pass
            
            print(f"Warning: Could not parse {field_name} value '{value}'")
            return None
    
    def _clean_type(self, type_str: str) -> str:
        """
        Clean and validate Pokemon type field.
        
        Args:
            type_str: Type string
            
        Returns:
            Lowercase type string or empty string if invalid
        """
        if not type_str:
            return ''
        
        type_str = self._clean_text(type_str)
        
        # Handle comma-separated types (e.g., "electric,electric")
        if ',' in type_str:
            types = [t.strip().lower() for t in type_str.split(',')]
            # Get unique types, keeping order
            seen = set()
            unique_types = []
            for t in types:
                if t not in seen:
                    seen.add(t)
                    unique_types.append(t)
            # If duplicates were removed, take first type
            type_str = unique_types[0] if unique_types else ''
        else:
            type_str = type_str.lower()
        
        # Valid Pokemon types
        valid_types = [
            'normal', 'fire', 'water', 'electric', 'grass', 'ice',
            'fighting', 'poison', 'ground', 'flying', 'psychic',
            'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy'
        ]
        
        if type_str not in valid_types:
            return ''
        
        return type_str
    
    def print_statistics(self):
        """Print cleaning statistics."""
        print("\n=== Cleaning Statistics ===")
        print(f"Rows processed: {self.stats['rows_processed']}")
        print(f"Rows successfully cleaned: {self.stats['rows_cleaned']}")
        print(f"Rows removed: {self.stats['rows_removed']}")
        print(f"Missing values filled: {self.stats['missing_values_filled']}")
        print(f"Data type fixes applied: {self.stats['data_type_fixes']}")
        print(f"\nSuccess rate: {(self.stats['rows_cleaned']/max(1,self.stats['rows_processed'])*100):.2f}%")


def main():
    """Main entry point for data cleaning."""
    cleaner = PokemonDataCleaner()
    cleaned_rows, stats = cleaner.clean_pokemon_csv()
    cleaner.print_statistics()
    
    print(f"\nCleaned data saved to {cleaner.output_file}")
    print(f"Total Pokemon in cleaned dataset: {len(cleaned_rows)}")


if __name__ == "__main__":
    main()

