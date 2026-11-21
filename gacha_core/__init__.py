"""Independent PostgreSQL game core for Velvet Gacha MVP-1.

No transport, grants or migrations execute on import.
"""
from .domain import (GameCore, GameError, InsufficientAttempts, MissingActiveCards,
                     BlockedPlayer, SpinResult, PlayerStatus, game_day_moscow,
                     choose_rarity)

__all__ = ['GameCore', 'GameError', 'InsufficientAttempts', 'MissingActiveCards',
           'BlockedPlayer', 'SpinResult', 'PlayerStatus', 'game_day_moscow',
           'choose_rarity']
