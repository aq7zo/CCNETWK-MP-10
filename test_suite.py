"""
Automated Test Suite for PokeProtocol

Provides unit tests and integration tests for the protocol implementation.
These tests can be run on a single machine without network setup.
"""

import unittest
from pokemon_data import PokemonDataLoader
from moves import MoveDatabase, Move
from messages import Message, MessageType
from reliability import ReliabilityLayer
from battle_state import BattleStateMachine, BattleState, BattlePokemon
from damage_calculator import DamageCalculator


class TestPokemonDataLoader(unittest.TestCase):
    """Test Pokemon data loading and lookup."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = PokemonDataLoader()
    
    def test_load_pokemon_success(self):
        """Test loading Pokemon by name."""
        pikachu = self.loader.get_pokemon("Pikachu")
        self.assertIsNotNone(pikachu)
        self.assertEqual(pikachu.name, "Pikachu")
        self.assertEqual(pikachu.type1, "electric")
    
    def test_pokemon_stats(self):
        """Test Pokemon stats are valid."""
        charizard = self.loader.get_pokemon("Charizard")
        self.assertIsNotNone(charizard)
        self.assertGreater(charizard.hp, 0)
        self.assertGreater(charizard.attack, 0)
        self.assertGreater(charizard.sp_attack, 0)
    
    def test_type_effectiveness(self):
        """Test type effectiveness calculation."""
        # Fire vs Grass should be super effective
        effectiveness = self.loader.get_type_effectiveness("Bulbasaur", "fire")
        self.assertGreater(effectiveness, 1.0)
        
        # Water vs Fire should be super effective
        effectiveness = self.loader.get_type_effectiveness("Charmander", "water")
        self.assertGreater(effectiveness, 1.0)


class TestMoveDatabase(unittest.TestCase):
    """Test move database functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.move_db = MoveDatabase()
    
    def test_move_lookup(self):
        """Test move lookup by name."""
        move = self.move_db.get_move("Thunderbolt")
        self.assertIsNotNone(move)
        self.assertEqual(move.name, "Thunderbolt")
        self.assertEqual(move.move_type, "electric")
    
    def test_move_power(self):
        """Test move power values."""
        thunderbolt = self.move_db.get_move("Thunderbolt")
        self.assertEqual(thunderbolt.power, 90)
        self.assertEqual(thunderbolt.damage_category, "special")
    
    def test_moves_by_type(self):
        """Test filtering moves by type."""
        electric_moves = self.move_db.get_moves_by_type("electric")
        self.assertGreater(len(electric_moves), 0)
        for move in electric_moves:
            self.assertEqual(move.move_type, "electric")


class TestMessageSerialization(unittest.TestCase):
    """Test message serialization and deserialization."""
    
    def test_attack_announce_serialization(self):
        """Test AttackAnnounce message round-trip."""
        from messages import AttackAnnounce
        
        original = AttackAnnounce("Thunderbolt", 5)
        data = original.serialize()
        
        # Deserialize
        parsed = Message.deserialize(data)
        self.assertEqual(parsed.move_name, "Thunderbolt")
        self.assertEqual(parsed.sequence_number, 5)
    
    def test_battle_setup_serialization(self):
        """Test BattleSetup message round-trip."""
        from messages import BattleSetup
        
        stat_boosts = {"special_attack_uses": 5, "special_defense_uses": 5}
        original = BattleSetup("P2P", "Pikachu", stat_boosts)
        data = original.serialize()
        
        # Deserialize
        parsed = Message.deserialize(data)
        self.assertEqual(parsed.communication_mode, "P2P")
        self.assertEqual(parsed.pokemon_name, "Pikachu")
    
    def test_chat_message_serialization(self):
        """Test ChatMessage serialization."""
        from messages import ChatMessage
        
        original = ChatMessage("Player1", "TEXT", message_text="Hello!", sequence_number=10)
        data = original.serialize()
        
        # Deserialize
        parsed = Message.deserialize(data)
        self.assertEqual(parsed.sender_name, "Player1")
        self.assertEqual(parsed.message_text, "Hello!")
    
    def test_ack_serialization(self):
        """Test ACK message serialization."""
        from messages import Ack
        
        original = Ack(42)
        data = original.serialize()
        
        # Deserialize
        parsed = Message.deserialize(data)
        self.assertEqual(parsed.ack_number, 42)


class TestReliabilityLayer(unittest.TestCase):
    """Test reliability layer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reliability = ReliabilityLayer()
    
    def test_sequence_numbers(self):
        """Test sequence number generation."""
        seq1 = self.reliability.get_next_sequence_number()
        seq2 = self.reliability.get_next_sequence_number()
        self.assertGreater(seq2, seq1)
    
    def test_pending_messages(self):
        """Test pending message tracking."""
        from messages import AttackAnnounce
        
        # Send a message that requires ACK (should be tracked)
        announce = AttackAnnounce("Thunderbolt", 0)
        seq = self.reliability.send_message(announce)
        self.assertTrue(self.reliability.has_pending_messages())
        
        # Receive ACK (should remove from pending)
        self.reliability.receive_ack(seq)
        self.assertFalse(self.reliability.has_pending_messages())
    
    def test_duplicate_detection(self):
        """Test duplicate message detection."""
        seq = 42
        self.assertFalse(self.reliability.is_duplicate(seq))
        
        self.reliability.mark_received(seq)
        self.assertTrue(self.reliability.is_duplicate(seq))


class TestBattleState(unittest.TestCase):
    """Test battle state machine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.battle_state = BattleStateMachine(is_host=True)
        self.pokemon_loader = PokemonDataLoader()
    
    def test_initial_state(self):
        """Test initial state is SETUP."""
        self.assertEqual(self.battle_state.state, BattleState.SETUP)
    
    def test_state_transitions(self):
        """Test state transition flow."""
        # Setup → Waiting
        pikachu = self.pokemon_loader.get_pokemon("Pikachu")
        self.battle_state.set_pokemon(pikachu)
        self.battle_state.advance_to_waiting()
        self.assertEqual(self.battle_state.state, BattleState.WAITING_FOR_MOVE)
        
        # Waiting → Processing
        from moves import Move
        move = Move("Thunderbolt", 90, "special", "electric")
        self.battle_state.advance_to_processing(move, "Pikachu")
        self.assertEqual(self.battle_state.state, BattleState.PROCESSING_TURN)
        
        # Processing → Waiting
        self.battle_state.advance_to_complete()
        self.assertEqual(self.battle_state.state, BattleState.WAITING_FOR_MOVE)
    
    def test_turn_order(self):
        """Test turn order management."""
        self.battle_state = BattleStateMachine(is_host=True)
        self.assertTrue(self.battle_state.my_turn)  # Host goes first
        
        self.battle_state = BattleStateMachine(is_host=False)
        self.assertFalse(self.battle_state.my_turn)  # Joiner waits


class TestDamageCalculator(unittest.TestCase):
    """Test damage calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pokemon_loader = PokemonDataLoader()
        self.calculator = DamageCalculator(self.pokemon_loader, seed=12345)
        self.move_db = MoveDatabase()
    
    def test_damage_calculation(self):
        """Test basic damage calculation."""
        pikachu = self.pokemon_loader.get_pokemon("Pikachu")
        charmander = self.pokemon_loader.get_pokemon("Charmander")
        thunderbolt = self.move_db.get_move("Thunderbolt")
        
        damage, status_msg = self.calculator.calculate_damage(
            pikachu, charmander, thunderbolt
        )
        
        self.assertGreater(damage, 0)
        self.assertIn("Pikachu", status_msg)
        self.assertIn("Thunderbolt", status_msg)
    
    def test_synchronized_calculations(self):
        """Test that same seed produces same damage."""
        # Calculate with seed 42
        calc1 = DamageCalculator(self.pokemon_loader, seed=42)
        pikachu = self.pokemon_loader.get_pokemon("Pikachu")
        charmander = self.pokemon_loader.get_pokemon("Charmander")
        thunderbolt = self.move_db.get_move("Thunderbolt")
        
        damage1, _ = calc1.calculate_damage(pikachu, charmander, thunderbolt)
        
        # Calculate again with same seed
        calc2 = DamageCalculator(self.pokemon_loader, seed=42)
        damage2, _ = calc2.calculate_damage(pikachu, charmander, thunderbolt)
        
        self.assertEqual(damage1, damage2)  # Should be identical
    
    def test_type_effectiveness(self):
        """Test type effectiveness in damage."""
        pikachu = self.pokemon_loader.get_pokemon("Pikachu")
        squirtle = self.pokemon_loader.get_pokemon("Squirtle")
        thunderbolt = self.move_db.get_move("Thunderbolt")
        
        # Electric vs Water should be super effective
        damage, status_msg = self.calculator.calculate_damage(
            pikachu, squirtle, thunderbolt
        )
        
        self.assertGreater(damage, 0)
        self.assertIn("super effective", status_msg)
    
    def test_stab_calculation(self):
        """Test Same Type Attack Bonus."""
        pikachu = self.pokemon_loader.get_pokemon("Pikachu")
        charmander = self.pokemon_loader.get_pokemon("Charmander")
        
        # Electric move from Electric Pokemon (STAB)
        thunderbolt = self.move_db.get_move("Thunderbolt")
        damage_stab, _ = self.calculator.calculate_damage(
            pikachu, charmander, thunderbolt
        )
        
        # Non-electric move from Electric Pokemon (no STAB)
        swift = self.move_db.get_move("Swift")
        damage_no_stab, _ = self.calculator.calculate_damage(
            pikachu, charmander, swift
        )
        
        # STAB damage should generally be higher
        self.assertGreater(damage_stab, damage_no_stab)


class TestIntegration(unittest.TestCase):
    """Integration tests for full system."""
    
    def test_complete_battle_flow(self):
        """Test a complete battle flow without network."""
        # Setup
        pokemon_loader = PokemonDataLoader()
        move_db = MoveDatabase()
        damage_calc = DamageCalculator(pokemon_loader, seed=999)
        
        pikachu = pokemon_loader.get_pokemon("Pikachu")
        charmander = pokemon_loader.get_pokemon("Charmander")
        
        # Create battle state
        battle_state = BattleStateMachine(is_host=True)
        battle_state.set_pokemon(pikachu)
        battle_state.set_opponent_pokemon(charmander)
        battle_state.advance_to_waiting()
        
        # Host's turn
        self.assertTrue(battle_state.is_my_turn())
        thunderbolt = move_db.get_move("Thunderbolt")
        battle_state.advance_to_processing(thunderbolt, "Pikachu")
        
        # Calculate damage
        outcome = damage_calc.calculate_turn_outcome(
            pikachu, charmander,
            battle_state.my_pokemon.current_hp,
            battle_state.opponent_pokemon.current_hp,
            thunderbolt
        )
        
        # Apply damage
        battle_state.record_my_calculation(outcome)
        battle_state.record_opponent_calculation(outcome)  # Simulate opponent
        battle_state.apply_calculation(outcome)
        
        # Complete turn
        battle_state.advance_to_complete()
        
        # Verify HP reduced
        self.assertLess(battle_state.opponent_pokemon.current_hp,
                       battle_state.opponent_pokemon.max_hp)
        
        # Turn should have switched
        self.assertFalse(battle_state.is_my_turn())


def run_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("PokeProtocol Test Suite")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPokemonDataLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestMoveDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageSerialization))
    suite.addTests(loader.loadTestsFromTestCase(TestReliabilityLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestBattleState))
    suite.addTests(loader.loadTestsFromTestCase(TestDamageCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print("\nSOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(run_tests())

