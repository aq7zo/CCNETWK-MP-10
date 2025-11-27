"""
PokeProtocol Core Modules

This package contains the core protocol implementation.
"""

from .peer import BasePeer, HostPeer, JoinerPeer, SpectatorPeer, ReliabilityLayer
from .battle import BattleState, BattlePokemon, BattleStateMachine, DamageCalculator
from .game_data import Pokemon, PokemonDataLoader, Move, MoveDatabase
from .messages import (
    Message, MessageType, ContentType,
    HandshakeRequest, HandshakeResponse, SpectatorRequest,
    BattleSetup, AttackAnnounce, DefenseAnnounce,
    CalculationReport, CalculationConfirm, ResolutionRequest,
    GameOver, ChatMessage, BoostActivation, Ack
)

__all__ = [
    # Peer classes
    'BasePeer', 'HostPeer', 'JoinerPeer', 'SpectatorPeer', 'ReliabilityLayer',
    # Battle classes
    'BattleState', 'BattlePokemon', 'BattleStateMachine', 'DamageCalculator',
    # Game data classes
    'Pokemon', 'PokemonDataLoader', 'Move', 'MoveDatabase',
    # Message classes
    'Message', 'MessageType', 'ContentType',
    'HandshakeRequest', 'HandshakeResponse', 'SpectatorRequest',
    'BattleSetup', 'AttackAnnounce', 'DefenseAnnounce',
    'CalculationReport', 'CalculationConfirm', 'ResolutionRequest',
    'GameOver', 'ChatMessage', 'BoostActivation', 'Ack',
]


