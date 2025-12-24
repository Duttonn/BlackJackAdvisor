"""
FastAPI Web Application for Blackjack Strategy Trainer.

Exposes the decision engine via REST API for web frontend integration.

Run with:
    uvicorn src.web.app:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .manager import SessionManager, SessionMode, GameSession


# =============================================================================
# Pydantic Models (Request/Response Schemas)
# =============================================================================

class StartSessionRequest(BaseModel):
    """Request body for starting a new session."""
    mode: str = Field(..., description="AUTO (training) or MANUAL (shadowing)")
    bankroll: float = Field(default=10000.0, ge=100.0, le=1000000.0)


class StartSessionResponse(BaseModel):
    """Response for session creation."""
    session_id: str
    mode: str
    status: str = "active"
    bankroll: float


class DealResponse(BaseModel):
    """Response for deal endpoint."""
    player_cards: List[str]
    player_total: int
    dealer_card: str
    running_count: int
    true_count: float
    recommended_bet: float
    is_blackjack: bool


class ActionRequest(BaseModel):
    """Request body for player action."""
    action: str = Field(..., description="HIT, STAND, DOUBLE, SPLIT, SURRENDER")


class ActionResponse(BaseModel):
    """Response for action endpoint."""
    action_taken: str
    correct_action: str
    is_correct: bool
    player_total: int
    new_card: Optional[str] = None
    new_total: Optional[int] = None
    is_bust: Optional[bool] = None
    outcome: Optional[str] = None
    dealer_total: Optional[int] = None
    should_exit: bool = False
    exit_reason: Optional[str] = None


class InputCardsRequest(BaseModel):
    """Request body for inputting observed cards."""
    cards: List[str] = Field(..., description="List of card strings, e.g., ['Ah', 'Kd', '5s']")


class InputCardsResponse(BaseModel):
    """Response for input cards endpoint."""
    cards_observed: List[str]
    running_count: int
    true_count: float
    decks_remaining: float
    penetration: float
    recommended_bet: float


class GetDecisionRequest(BaseModel):
    """Request body for getting a decision."""
    player_cards: List[str] = Field(..., description="Player cards, e.g., ['Ah', '7d']")
    dealer_card: str = Field(..., description="Dealer up card, e.g., '10s'")


class GetDecisionResponse(BaseModel):
    """Response for decision endpoint."""
    player_cards: List[str]
    player_total: int
    dealer_card: str
    recommended_action: str
    running_count: int
    true_count: float
    should_exit: bool
    exit_reason: Optional[str] = None
    recommended_bet: float


class SessionStatusResponse(BaseModel):
    """Response for session status."""
    session_id: str
    mode: str
    hand_in_progress: bool
    running_count: int
    true_count: float
    recommended_bet: float


class ShuffleResponse(BaseModel):
    """Response for shuffle endpoint."""
    status: str
    running_count: int
    true_count: float


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


# =============================================================================
# FastAPI Application
# =============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Blackjack Strategy Trainer API",
        description="REST API for the Blackjack Decision Engine. Supports training mode (AUTO) and shadowing mode (MANUAL).",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Session manager instance
    manager = SessionManager()
    
    # =========================================================================
    # Root & Health Check
    # =========================================================================
    
    @app.get("/", tags=["System"])
    async def root():
        """API root - provides info and links."""
        return {
            "name": "Blackjack Strategy Trainer API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "start_session": "POST /api/session/start",
                "deal_hand": "POST /api/session/{id}/deal",
                "submit_action": "POST /api/session/{id}/action",
                "input_cards": "POST /api/session/{id}/input",
                "get_decision": "POST /api/session/{id}/decision"
            }
        }
    
    @app.get("/health", tags=["System"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "blackjack-trainer"}
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    @app.post(
        "/api/session/start",
        response_model=StartSessionResponse,
        tags=["Session"],
        summary="Start a new game session"
    )
    async def start_session(request: StartSessionRequest):
        """
        Create a new game session.
        
        - **AUTO mode**: Training mode with simulated shoe. Engine deals cards.
        - **MANUAL mode**: Shadowing mode. User inputs cards from real game.
        """
        try:
            mode = SessionMode(request.mode.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode: {request.mode}. Use AUTO or MANUAL."
            )
        
        session = manager.create_session(mode=mode, bankroll=request.bankroll)
        
        return StartSessionResponse(
            session_id=session.session_id,
            mode=session.mode.value,
            status="active",
            bankroll=request.bankroll
        )
    
    @app.get(
        "/api/session/{session_id}",
        response_model=SessionStatusResponse,
        tags=["Session"],
        summary="Get session status"
    )
    async def get_session_status(session_id: str):
        """Get current status of a session."""
        session = manager.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired"
            )
        
        metrics = session.live_session.state_manager.get_metrics()
        
        return SessionStatusResponse(
            session_id=session.session_id,
            mode=session.mode.value,
            hand_in_progress=session.hand_in_progress,
            running_count=metrics.running_count,
            true_count=round(metrics.true_count, 2),
            recommended_bet=round(session.live_session.get_bet(), 2)
        )
    
    @app.delete(
        "/api/session/{session_id}",
        tags=["Session"],
        summary="End a session"
    )
    async def end_session(session_id: str):
        """End and delete a session."""
        if manager.delete_session(session_id):
            return {"status": "deleted", "session_id": session_id}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    @app.post(
        "/api/session/{session_id}/shuffle",
        response_model=ShuffleResponse,
        tags=["Session"],
        summary="Shuffle the deck (new shoe)"
    )
    async def shuffle_deck(session_id: str):
        """Reset the shoe and count."""
        result = manager.reset_shoe(session_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return ShuffleResponse(**result)
    
    # =========================================================================
    # AUTO Mode Endpoints (Training)
    # =========================================================================
    
    @app.post(
        "/api/session/{session_id}/deal",
        response_model=DealResponse,
        tags=["Training (AUTO)"],
        summary="Deal a new hand"
    )
    async def deal_hand(session_id: str):
        """
        Deal a new hand from the simulated shoe.
        
        Only available in AUTO mode.
        """
        result = manager.deal_hand(session_id)
        if result is None:
            session = manager.get_session(session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deal only available in AUTO mode"
            )
        return DealResponse(**result)
    
    @app.post(
        "/api/session/{session_id}/action",
        response_model=ActionResponse,
        tags=["Training (AUTO)"],
        summary="Submit player action"
    )
    async def submit_action(session_id: str, request: ActionRequest):
        """
        Submit a player action and get training feedback.
        
        Returns whether the action was correct and the outcome.
        Only available in AUTO mode.
        """
        result = manager.process_action(session_id, request.action)
        if result is None:
            session = manager.get_session(session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action only available in AUTO mode"
            )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return ActionResponse(**result)
    
    # =========================================================================
    # MANUAL Mode Endpoints (Shadowing)
    # =========================================================================
    
    @app.post(
        "/api/session/{session_id}/input",
        response_model=InputCardsResponse,
        tags=["Shadowing (MANUAL)"],
        summary="Input observed cards"
    )
    async def input_cards(session_id: str, request: InputCardsRequest):
        """
        Input cards observed at a real table.
        
        Updates the running count and true count.
        Only available in MANUAL mode.
        """
        result = manager.input_cards(session_id, request.cards)
        if result is None:
            session = manager.get_session(session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input only available in MANUAL mode"
            )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return InputCardsResponse(**result)
    
    @app.post(
        "/api/session/{session_id}/decision",
        response_model=GetDecisionResponse,
        tags=["Shadowing (MANUAL)"],
        summary="Get decision for a hand"
    )
    async def get_decision(session_id: str, request: GetDecisionRequest):
        """
        Get the recommended action for a specific hand.
        
        Uses the current count state to determine deviations.
        Only available in MANUAL mode.
        """
        result = manager.get_decision_for_hand(
            session_id,
            request.player_cards,
            request.dealer_card
        )
        if result is None:
            session = manager.get_session(session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision only available in MANUAL mode"
            )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return GetDecisionResponse(**result)
    
    return app


# Create the app instance
app = create_app()


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
