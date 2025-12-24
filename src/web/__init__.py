"""
Web API module for Blackjack Strategy Trainer.
FastAPI-based REST API exposing the decision engine.
"""

from .app import app, create_app
from .manager import SessionManager, GameSession

__all__ = [
    'app',
    'create_app',
    'SessionManager',
    'GameSession',
]
