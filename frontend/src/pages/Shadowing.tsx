import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { Card } from '../components/Card';
import { CardInputGrid } from '../components/CardInputGrid';
import { HandFlowController } from '../components/HandFlowController';
import type { DecisionResponse } from '../lib/api';
import {
    Shuffle,
    Send,
    Trash2,
    AlertTriangle,
    DoorOpen,
    X,
    AlertCircle,
    Zap,
    List,
} from 'lucide-react';

// Card ranks and suits for manual mode
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'];
const SUITS = [
    { symbol: '♠', color: 'text-[var(--rb-text)]' },
    { symbol: '♥', color: 'text-red-500' },
    { symbol: '♦', color: 'text-red-500' },
    { symbol: '♣', color: 'text-[var(--rb-text)]' },
];

type InputMode = 'flow' | 'manual';

/**
 * Shadowing page - MANUAL mode with two input interfaces:
 * 1. Flow Mode (default): Guided step-by-step card input with HandFlowController
 * 2. Manual Mode: Free-form card observation with CardInputGrid
 */
export function Shadowing() {
    const navigate = useNavigate();
    const {
        state,
        endGame,
        submitCards,
        getRecommendation,
        shuffleDeck,
        clearExit,
    } = useGame();

    // UI mode: 'flow' for guided hand input, 'manual' for free observation
    const [inputMode, setInputMode] = useState<InputMode>('flow');

    // Manual mode state
    const [selectedRank, setSelectedRank] = useState<string | null>(null);
    const [pendingCards, setPendingCards] = useState<string[]>([]);

    // Redirect if no session
    useEffect(() => {
        if (!state.sessionId || state.gameMode !== 'MANUAL') {
            navigate('/');
        }
    }, [state.sessionId, state.gameMode, navigate]);

    // Handle card selection (manual mode - legacy)
    const handleCardSelect = (suit: string) => {
        if (!selectedRank) return;
        const card = `${selectedRank}${suit}`;
        setPendingCards([...pendingCards, card]);
        setSelectedRank(null);
    };

    // Handle card from CardInputGrid (manual observe mode)
    const handleQuickCardInput = async (card: string) => {
        setPendingCards(prev => [...prev, card]);
    };

    // Submit observed cards
    const handleSubmitCards = async () => {
        if (pendingCards.length === 0) return;
        await submitCards(pendingCards);
        setPendingCards([]);
    };

    // Handle shuffle
    const handleShuffle = async () => {
        await shuffleDeck();
        setPendingCards([]);
    };

    // Handle leaving
    const handleLeave = async () => {
        await endGame();
        navigate('/');
    };

    // Wrapper for flow controller - submit single card to count
    const handleCardObserved = async (card: string) => {
        await submitCards([card]);
    };

    // Wrapper for flow controller - get decision
    const handleGetDecision = async (playerCards: string[], dealerCard: string): Promise<DecisionResponse | null> => {
        return await getRecommendation(playerCards, dealerCard);
    };

    return (
        <div className="max-w-4xl mx-auto">
            {/* Exit Warning */}
            {state.shouldExit && state.exitReason && (
                <div className="exit-warning mb-6 animate-fade-in">
                    <div className="flex items-start gap-4">
                        <div className="p-3 rounded-full bg-[var(--rb-red)]/20">
                            <AlertTriangle className="w-8 h-8 text-[var(--rb-red)]" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-xl font-bold text-[var(--rb-red)] mb-1 flex items-center gap-2">
                                <DoorOpen className="w-5 h-5" />
                                Wong Out Signal
                            </h3>
                            <p className="text-[var(--rb-text-secondary)]">{state.exitReason}</p>
                        </div>
                        <button
                            onClick={clearExit}
                            className="p-2 hover:bg-white/5 rounded-lg text-[var(--rb-text-muted)]"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                    <div className="flex gap-3 mt-4 pt-4 border-t border-[var(--rb-red)]/20">
                        <button onClick={handleLeave} className="rb-btn rb-btn-red">
                            <DoorOpen className="w-4 h-4" />
                            Leave Table
                        </button>
                        <button onClick={clearExit} className="rb-btn rb-btn-outline">
                            Continue Playing
                        </button>
                    </div>
                </div>
            )}

            {/* Stats Bar */}
            <div className="stats-bar mb-6">
                <div className="stat-item">
                    <div
                        className={`stat-value ${state.trueCount >= 2
                            ? 'text-[var(--rb-green)]'
                            : state.trueCount <= -1
                                ? 'text-[var(--rb-red)]'
                                : ''
                            }`}
                    >
                        {state.trueCount >= 0 ? '+' : ''}
                        {state.trueCount.toFixed(1)}
                    </div>
                    <div className="stat-label">True Count</div>
                </div>
                <div className="stat-item">
                    <div
                        className={`stat-value ${state.runningCount > 0
                            ? 'text-[var(--rb-green)]'
                            : state.runningCount < 0
                                ? 'text-[var(--rb-red)]'
                                : ''
                            }`}
                    >
                        {state.runningCount >= 0 ? '+' : ''}
                        {state.runningCount}
                    </div>
                    <div className="stat-label">Running Count</div>
                </div>
                <div className="stat-item">
                    <div className="stat-value text-[var(--rb-green)]">
                        ${state.recommendedBet}
                    </div>
                    <div className="stat-label">Rec. Bet</div>
                </div>
                <div className="ml-auto flex items-center gap-2">
                    <button onClick={handleShuffle} className="rb-btn rb-btn-ghost text-sm">
                        <Shuffle className="w-4 h-4" />
                        New Shoe
                    </button>
                </div>
            </div>

            {/* Mode Toggle */}
            <div className="flex items-center justify-center gap-2 mb-6 p-1 rounded-xl bg-slate-800/50">
                <button
                    onClick={() => setInputMode('flow')}
                    className={`
                        flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm
                        transition-all duration-200
                        ${inputMode === 'flow'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                        }
                    `}
                >
                    <Zap className="w-4 h-4" />
                    Auto-Flow
                </button>
                <button
                    onClick={() => setInputMode('manual')}
                    className={`
                        flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium text-sm
                        transition-all duration-200
                        ${inputMode === 'manual'
                            ? 'bg-slate-600/50 text-slate-200 border border-slate-500/30'
                            : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                        }
                    `}
                >
                    <List className="w-4 h-4" />
                    Observe Mode
                </button>
            </div>

            {/* Main Content */}
            <div className="game-frame">
                <div className="p-6">
                    {/* Auto-Flow Mode */}
                    {inputMode === 'flow' && (
                        <HandFlowController
                            onCardObserved={handleCardObserved}
                            onGetDecision={handleGetDecision}
                            trueCount={state.trueCount}
                            runningCount={state.runningCount}
                            recommendedBet={state.recommendedBet}
                            shouldExit={state.shouldExit}
                            exitReason={state.exitReason}
                            isLoading={state.isLoading}
                        />
                    )}

                    {/* Manual Observe Mode */}
                    {inputMode === 'manual' && (
                        <div className="space-y-6">
                            <div className="text-center mb-4">
                                <h3 className="text-lg font-semibold text-slate-200">Observe Cards</h3>
                                <p className="text-sm text-slate-500">
                                    Quickly input any cards you see at the table
                                </p>
                            </div>

                            {/* Quick Input Grid */}
                            <CardInputGrid
                                onCardSelect={handleQuickCardInput}
                                prompt="Tap rank, slide for suit"
                                disabled={state.isLoading}
                            />

                            {/* Pending Cards */}
                            <div className="border-t border-slate-700 pt-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-slate-500 uppercase tracking-wider">
                                        Cards to Submit ({pendingCards.length})
                                    </span>
                                    {pendingCards.length > 0 && (
                                        <button
                                            onClick={() => setPendingCards([])}
                                            className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
                                        >
                                            <Trash2 className="w-3 h-3" />
                                            Clear
                                        </button>
                                    )}
                                </div>
                                <div className="flex flex-wrap gap-2 min-h-[64px] p-3 rounded-xl bg-slate-800/50 border border-slate-700">
                                    {pendingCards.length > 0 ? (
                                        pendingCards.map((card, i) => (
                                            <Card key={`${card}-${i}`} card={card} size="sm" />
                                        ))
                                    ) : (
                                        <span className="text-slate-600 text-sm self-center">
                                            No cards selected
                                        </span>
                                    )}
                                </div>
                                <button
                                    onClick={handleSubmitCards}
                                    disabled={pendingCards.length === 0 || state.isLoading}
                                    className={`
                                        w-full mt-3 py-3 rounded-xl font-semibold
                                        flex items-center justify-center gap-2
                                        transition-all duration-200
                                        ${pendingCards.length > 0
                                            ? 'bg-emerald-500 hover:bg-emerald-400 text-white'
                                            : 'bg-slate-800 text-slate-600 cursor-not-allowed'
                                        }
                                    `}
                                >
                                    <Send className="w-4 h-4" />
                                    Submit Cards ({pendingCards.length})
                                </button>
                            </div>

                            {/* Legacy Rank/Suit Selector (fallback) */}
                            <details className="group">
                                <summary className="text-xs text-slate-600 cursor-pointer hover:text-slate-400 flex items-center gap-1">
                                    <span>↳ Classic input (tap rank, tap suit)</span>
                                </summary>
                                <div className="mt-3 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                                    {/* Rank selector */}
                                    <div className="mb-4">
                                        <div className="text-xs text-slate-600 mb-2 uppercase">
                                            Rank
                                        </div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {RANKS.map((rank) => (
                                                <button
                                                    key={rank}
                                                    onClick={() => setSelectedRank(rank)}
                                                    className={`w-9 h-9 rounded-lg font-bold text-sm transition-all ${selectedRank === rank
                                                        ? 'bg-emerald-500 text-white scale-110'
                                                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                                                        }`}
                                                >
                                                    {rank}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Suit selector */}
                                    <div>
                                        <div className="text-xs text-slate-600 mb-2 uppercase">
                                            {selectedRank ? `Suit for ${selectedRank}` : 'Select rank first'}
                                        </div>
                                        <div className="flex gap-2">
                                            {SUITS.map((suit) => (
                                                <button
                                                    key={suit.symbol}
                                                    onClick={() => handleCardSelect(suit.symbol)}
                                                    disabled={!selectedRank}
                                                    className={`flex-1 py-3 rounded-lg text-2xl transition-all ${!selectedRank
                                                        ? 'bg-slate-800 opacity-50 cursor-not-allowed'
                                                        : `bg-slate-700 hover:bg-slate-600 hover:scale-105 ${suit.color}`
                                                        }`}
                                                >
                                                    {suit.symbol}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </details>
                        </div>
                    )}
                </div>
            </div>

            {/* Error display */}
            {state.error && (
                <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    <span>{state.error}</span>
                </div>
            )}

            {/* Quick Tips */}
            <div className="mt-6 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-medium text-slate-300">Speed Tips</span>
                </div>
                <div className="grid md:grid-cols-2 gap-3 text-xs text-slate-500">
                    <div className="flex items-start gap-2">
                        <span className="text-emerald-400">•</span>
                        <span><strong>Auto-Flow:</strong> Guided hand-by-hand input with instant decisions</span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-slate-400">•</span>
                        <span><strong>Observe Mode:</strong> Quickly log cards you see dealt to others</span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-blue-400">•</span>
                        <span><strong>Swipe Input:</strong> Tap rank → slide UP(♠) RIGHT(♥) DOWN(♣) LEFT(♦)</span>
                    </div>
                    <div className="flex items-start gap-2">
                        <span className="text-amber-400">•</span>
                        <span><strong>New Shoe:</strong> Tap when dealer shuffles to reset count</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Shadowing;
