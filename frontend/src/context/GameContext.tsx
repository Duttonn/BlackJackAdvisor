import { createContext, useContext, useReducer, useCallback } from 'react';
import type { ReactNode } from 'react';
import * as api from '../lib/api';

// ----- State Interface -----

export interface GameState {
    // Session info
    sessionId: string | null;
    gameMode: 'AUTO' | 'MANUAL' | null;
    bankroll: number;

    // Count tracking
    runningCount: number;
    trueCount: number;
    recommendedBet: number;

    // Statistics
    handsPlayed: number;
    correctDecisions: number;
    totalDecisions: number;

    // Exit warning (Wong Out)
    shouldExit: boolean;
    exitReason: string | null;

    // UI State
    isLoading: boolean;
    error: string | null;

    // Current hand (AUTO mode)
    playerCards: string[];
    dealerCard: string | null;
    playerTotal: number;
    handInProgress: boolean;
    isBlackjack: boolean;

    // Last action result
    lastActionResult: api.ActionResponse | null;
}

// Initial state
const initialState: GameState = {
    sessionId: null,
    gameMode: null,
    bankroll: 1000,

    runningCount: 0,
    trueCount: 0,
    recommendedBet: 0,

    handsPlayed: 0,
    correctDecisions: 0,
    totalDecisions: 0,

    shouldExit: false,
    exitReason: null,

    isLoading: false,
    error: null,

    playerCards: [],
    dealerCard: null,
    playerTotal: 0,
    handInProgress: false,
    isBlackjack: false,

    lastActionResult: null,
};

// ----- Action Types -----

type GameAction =
    | { type: 'SET_LOADING'; payload: boolean }
    | { type: 'SET_ERROR'; payload: string | null }
    | { type: 'START_SESSION'; payload: { sessionId: string; mode: 'AUTO' | 'MANUAL'; bankroll: number } }
    | { type: 'END_SESSION' }
    | { type: 'UPDATE_STATS'; payload: { runningCount: number; trueCount: number; recommendedBet: number } }
    | { type: 'RECORD_DECISION'; payload: { isCorrect: boolean } }
    | { type: 'TRIGGER_EXIT'; payload: { reason: string } }
    | { type: 'CLEAR_EXIT' }
    | { type: 'SET_HAND'; payload: { playerCards: string[]; dealerCard: string; playerTotal: number; isBlackjack: boolean } }
    | { type: 'UPDATE_HAND'; payload: { playerCards?: string[]; playerTotal?: number } }
    | { type: 'CLEAR_HAND' }
    | { type: 'SET_ACTION_RESULT'; payload: api.ActionResponse }
    | { type: 'INCREMENT_HANDS' }
    | { type: 'RESET_GAME' };

// ----- Reducer -----

function gameReducer(state: GameState, action: GameAction): GameState {
    switch (action.type) {
        case 'SET_LOADING':
            return { ...state, isLoading: action.payload };

        case 'SET_ERROR':
            return { ...state, error: action.payload, isLoading: false };

        case 'START_SESSION':
            return {
                ...state,
                sessionId: action.payload.sessionId,
                gameMode: action.payload.mode,
                bankroll: action.payload.bankroll,
                error: null,
                isLoading: false,
                // Reset stats for new session
                handsPlayed: 0,
                correctDecisions: 0,
                totalDecisions: 0,
                runningCount: 0,
                trueCount: 0,
                recommendedBet: 0,
                shouldExit: false,
                exitReason: null,
            };

        case 'END_SESSION':
            return {
                ...initialState,
            };

        case 'UPDATE_STATS':
            return {
                ...state,
                runningCount: action.payload.runningCount,
                trueCount: action.payload.trueCount,
                recommendedBet: action.payload.recommendedBet,
            };

        case 'RECORD_DECISION':
            return {
                ...state,
                totalDecisions: state.totalDecisions + 1,
                correctDecisions: action.payload.isCorrect
                    ? state.correctDecisions + 1
                    : state.correctDecisions,
            };

        case 'TRIGGER_EXIT':
            return {
                ...state,
                shouldExit: true,
                exitReason: action.payload.reason,
            };

        case 'CLEAR_EXIT':
            return {
                ...state,
                shouldExit: false,
                exitReason: null,
            };

        case 'SET_HAND':
            return {
                ...state,
                playerCards: action.payload.playerCards,
                dealerCard: action.payload.dealerCard,
                playerTotal: action.payload.playerTotal,
                isBlackjack: action.payload.isBlackjack,
                handInProgress: true,
                lastActionResult: null,
            };

        case 'UPDATE_HAND':
            return {
                ...state,
                playerCards: action.payload.playerCards ?? state.playerCards,
                playerTotal: action.payload.playerTotal ?? state.playerTotal,
            };

        case 'CLEAR_HAND':
            return {
                ...state,
                playerCards: [],
                dealerCard: null,
                playerTotal: 0,
                handInProgress: false,
                isBlackjack: false,
                lastActionResult: null,
            };

        case 'SET_ACTION_RESULT':
            return {
                ...state,
                lastActionResult: action.payload,
                handInProgress: !action.payload.outcome, // Hand ends when outcome is present
            };

        case 'INCREMENT_HANDS':
            return {
                ...state,
                handsPlayed: state.handsPlayed + 1,
            };

        case 'RESET_GAME':
            return initialState;

        default:
            return state;
    }
}

// ----- Context Interface -----

interface GameContextValue {
    state: GameState;

    // Session actions
    startGame: (mode: 'AUTO' | 'MANUAL', bankroll: number) => Promise<void>;
    endGame: () => Promise<void>;

    // Stats actions
    updateStats: (rc: number, tc: number, bet: number) => void;
    recordDecision: (isCorrect: boolean) => void;

    // Exit actions
    triggerExit: (reason: string) => void;
    clearExit: () => void;

    // Hand actions (AUTO mode)
    dealNewHand: () => Promise<api.DealResponse | null>;
    performAction: (action: 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER') => Promise<api.ActionResponse | null>;

    // Card input (MANUAL mode)
    submitCards: (cards: string[]) => Promise<api.InputCardsResponse | null>;
    getRecommendation: (playerCards: string[], dealerCard: string) => Promise<api.DecisionResponse | null>;

    // Deck actions
    shuffleDeck: () => Promise<void>;

    // Utility
    resetGame: () => void;
    clearError: () => void;

    // Computed values
    accuracy: number;
}

// Create context
const GameContext = createContext<GameContextValue | undefined>(undefined);

// ----- Provider Component -----

interface GameProviderProps {
    children: ReactNode;
}

export function GameProvider({ children }: GameProviderProps) {
    const [state, dispatch] = useReducer(gameReducer, initialState);

    // Calculate accuracy
    const accuracy = state.totalDecisions > 0
        ? Math.round((state.correctDecisions / state.totalDecisions) * 100)
        : 0;

    // ----- Session Actions -----

    const startGame = useCallback(async (mode: 'AUTO' | 'MANUAL', bankroll: number) => {
        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.startSession(mode, bankroll);
            dispatch({
                type: 'START_SESSION',
                payload: {
                    sessionId: response.session_id,
                    mode,
                    bankroll: response.bankroll,
                },
            });
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
        }
    }, []);

    const endGame = useCallback(async () => {
        if (state.sessionId) {
            try {
                await api.deleteSession(state.sessionId);
            } catch {
                // Ignore errors when ending session
            }
        }
        dispatch({ type: 'END_SESSION' });
    }, [state.sessionId]);

    // ----- Stats Actions -----

    const updateStats = useCallback((rc: number, tc: number, bet: number) => {
        dispatch({
            type: 'UPDATE_STATS',
            payload: { runningCount: rc, trueCount: tc, recommendedBet: bet },
        });
    }, []);

    const recordDecision = useCallback((isCorrect: boolean) => {
        dispatch({ type: 'RECORD_DECISION', payload: { isCorrect } });
    }, []);

    // ----- Exit Actions -----

    const triggerExit = useCallback((reason: string) => {
        dispatch({ type: 'TRIGGER_EXIT', payload: { reason } });
    }, []);

    const clearExit = useCallback(() => {
        dispatch({ type: 'CLEAR_EXIT' });
    }, []);

    // ----- Hand Actions (AUTO mode) -----

    const dealNewHand = useCallback(async (): Promise<api.DealResponse | null> => {
        if (!state.sessionId) return null;

        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.dealHand(state.sessionId);

            dispatch({
                type: 'SET_HAND',
                payload: {
                    playerCards: response.player_cards,
                    dealerCard: response.dealer_card,
                    playerTotal: response.player_total,
                    isBlackjack: response.is_blackjack,
                },
            });

            dispatch({
                type: 'UPDATE_STATS',
                payload: {
                    runningCount: response.running_count,
                    trueCount: response.true_count,
                    recommendedBet: response.recommended_bet,
                },
            });

            dispatch({ type: 'SET_LOADING', payload: false });
            return response;
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
            return null;
        }
    }, [state.sessionId]);

    const performAction = useCallback(async (
        action: 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER'
    ): Promise<api.ActionResponse | null> => {
        if (!state.sessionId) return null;

        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.sendAction(state.sessionId, action);

            dispatch({ type: 'SET_ACTION_RESULT', payload: response });
            dispatch({ type: 'RECORD_DECISION', payload: { isCorrect: response.is_correct } });

            // Update hand if new card was added
            if (response.new_card) {
                dispatch({
                    type: 'UPDATE_HAND',
                    payload: {
                        playerCards: [...state.playerCards, response.new_card],
                        playerTotal: response.new_total,
                    },
                });
            }

            // Check for exit signal
            if (response.should_exit && response.exit_reason) {
                dispatch({ type: 'TRIGGER_EXIT', payload: { reason: response.exit_reason } });
            }

            // If hand is complete, increment hands played
            if (response.outcome) {
                dispatch({ type: 'INCREMENT_HANDS' });
            }

            dispatch({ type: 'SET_LOADING', payload: false });
            return response;
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
            return null;
        }
    }, [state.sessionId, state.playerCards]);

    // ----- Card Input (MANUAL mode) -----

    const submitCards = useCallback(async (cards: string[]): Promise<api.InputCardsResponse | null> => {
        if (!state.sessionId) return null;

        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.inputCards(state.sessionId, cards);

            dispatch({
                type: 'UPDATE_STATS',
                payload: {
                    runningCount: response.running_count,
                    trueCount: response.true_count,
                    recommendedBet: response.recommended_bet,
                },
            });

            dispatch({ type: 'SET_LOADING', payload: false });
            return response;
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
            return null;
        }
    }, [state.sessionId]);

    const getRecommendation = useCallback(async (
        playerCards: string[],
        dealerCard: string
    ): Promise<api.DecisionResponse | null> => {
        if (!state.sessionId) return null;

        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.getDecision(state.sessionId, playerCards, dealerCard);

            dispatch({
                type: 'UPDATE_STATS',
                payload: {
                    runningCount: response.running_count,
                    trueCount: response.true_count,
                    recommendedBet: response.recommended_bet,
                },
            });

            // Check for exit signal
            if (response.should_exit && response.exit_reason) {
                dispatch({ type: 'TRIGGER_EXIT', payload: { reason: response.exit_reason } });
            }

            dispatch({ type: 'SET_LOADING', payload: false });
            return response;
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
            return null;
        }
    }, [state.sessionId]);

    // ----- Deck Actions -----

    const shuffleDeck = useCallback(async () => {
        if (!state.sessionId) return;

        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        try {
            const response = await api.shuffleDeck(state.sessionId);

            dispatch({
                type: 'UPDATE_STATS',
                payload: {
                    runningCount: response.running_count,
                    trueCount: response.true_count,
                    recommendedBet: 0,
                },
            });

            dispatch({ type: 'CLEAR_HAND' });
            dispatch({ type: 'CLEAR_EXIT' });
            dispatch({ type: 'SET_LOADING', payload: false });
        } catch (error) {
            const apiError = error as api.ApiError;
            dispatch({ type: 'SET_ERROR', payload: apiError.message });
        }
    }, [state.sessionId]);

    // ----- Utility Actions -----

    const resetGame = useCallback(() => {
        dispatch({ type: 'RESET_GAME' });
    }, []);

    const clearError = useCallback(() => {
        dispatch({ type: 'SET_ERROR', payload: null });
    }, []);

    // ----- Context Value -----

    const value: GameContextValue = {
        state,
        startGame,
        endGame,
        updateStats,
        recordDecision,
        triggerExit,
        clearExit,
        dealNewHand,
        performAction,
        submitCards,
        getRecommendation,
        shuffleDeck,
        resetGame,
        clearError,
        accuracy,
    };

    return (
        <GameContext.Provider value={value}>
            {children}
        </GameContext.Provider>
    );
}

// ----- Custom Hook -----

export function useGame(): GameContextValue {
    const context = useContext(GameContext);

    if (context === undefined) {
        throw new Error('useGame must be used within a GameProvider');
    }

    return context;
}

// Export types
export type { GameContextValue };
