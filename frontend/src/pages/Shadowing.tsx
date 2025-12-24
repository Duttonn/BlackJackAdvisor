import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { Card } from '../components/Card';
import type { DecisionResponse } from '../lib/api';
import {
    Shuffle,
    Send,
    Trash2,
    Target,
    AlertTriangle,
    DoorOpen,
    X,
    AlertCircle,
} from 'lucide-react';

// Card ranks and suits
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'];
const SUITS = [
    { symbol: '♠', color: 'text-[var(--rb-text)]' },
    { symbol: '♥', color: 'text-red-500' },
    { symbol: '♦', color: 'text-red-500' },
    { symbol: '♣', color: 'text-[var(--rb-text)]' },
];

/**
 * Shadowing page - MANUAL mode with casino-style interface
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

    // Card input state
    const [selectedRank, setSelectedRank] = useState<string | null>(null);
    const [pendingCards, setPendingCards] = useState<string[]>([]);

    // Decision state
    const [playerHand, setPlayerHand] = useState<string[]>([]);
    const [dealerUpcard, setDealerUpcard] = useState<string | null>(null);
    const [selectingFor, setSelectingFor] = useState<'observe' | 'player' | 'dealer'>(
        'observe'
    );
    const [recommendation, setRecommendation] = useState<DecisionResponse | null>(null);

    // Redirect if no session
    useEffect(() => {
        if (!state.sessionId || state.gameMode !== 'MANUAL') {
            navigate('/');
        }
    }, [state.sessionId, state.gameMode, navigate]);

    // Handle card selection
    const handleCardSelect = (suit: string) => {
        if (!selectedRank) return;

        const card = `${selectedRank}${suit}`;

        switch (selectingFor) {
            case 'observe':
                setPendingCards([...pendingCards, card]);
                break;
            case 'player':
                setPlayerHand([...playerHand, card]);
                break;
            case 'dealer':
                setDealerUpcard(card);
                setSelectingFor('observe');
                break;
        }

        setSelectedRank(null);
    };

    // Submit observed cards
    const handleSubmitCards = async () => {
        if (pendingCards.length === 0) return;
        await submitCards(pendingCards);
        setPendingCards([]);
    };

    // Get decision
    const handleGetDecision = async () => {
        if (playerHand.length < 2 || !dealerUpcard) return;
        const result = await getRecommendation(playerHand, dealerUpcard);
        if (result) {
            setRecommendation(result);
        }
    };

    // Clear hand
    const handleClearHand = () => {
        setPlayerHand([]);
        setDealerUpcard(null);
        setRecommendation(null);
    };

    // Handle shuffle
    const handleShuffle = async () => {
        await shuffleDeck();
        setPendingCards([]);
        handleClearHand();
    };

    // Handle leaving
    const handleLeave = async () => {
        await endGame();
        navigate('/');
    };

    return (
        <div className="max-w-6xl mx-auto">
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

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Card Input Panel */}
                <div className="game-frame">
                    <div className="game-frame-header">
                        <div>
                            <h2 className="text-lg font-bold text-[var(--rb-text)]">Card Input</h2>
                            <p className="text-sm text-[var(--rb-text-muted)]">
                                Tap rank, then suit to add cards
                            </p>
                        </div>
                    </div>

                    <div className="p-6">
                        {/* Input mode tabs */}
                        <div className="flex gap-2 mb-6 p-1 rounded-lg bg-[var(--rb-bg)]">
                            {[
                                { key: 'observe', label: 'Observe', color: 'var(--rb-primary)' },
                                { key: 'player', label: 'Your Hand', color: 'var(--rb-green)' },
                                { key: 'dealer', label: 'Dealer', color: 'var(--rb-amber)' },
                            ].map((tab) => (
                                <button
                                    key={tab.key}
                                    onClick={() => setSelectingFor(tab.key as typeof selectingFor)}
                                    className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${selectingFor === tab.key
                                        ? 'bg-[var(--rb-surface)] text-[var(--rb-text)]'
                                        : 'text-[var(--rb-text-muted)] hover:text-[var(--rb-text)]'
                                        }`}
                                    style={{
                                        borderLeft:
                                            selectingFor === tab.key ? `3px solid ${tab.color}` : 'none',
                                    }}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Rank selector */}
                        <div className="mb-4">
                            <div className="text-xs text-[var(--rb-text-muted)] mb-2 uppercase tracking-wider">
                                Select Rank
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {RANKS.map((rank) => (
                                    <button
                                        key={rank}
                                        onClick={() => setSelectedRank(rank)}
                                        className={`w-10 h-10 rounded-lg font-bold text-lg transition-all ${selectedRank === rank
                                            ? 'bg-[var(--rb-primary)] text-white scale-110'
                                            : 'bg-[var(--rb-bg)] text-[var(--rb-text)] hover:bg-[var(--rb-surface-hover)]'
                                            }`}
                                    >
                                        {rank}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Suit selector */}
                        <div className="mb-6">
                            <div className="text-xs text-[var(--rb-text-muted)] mb-2 uppercase tracking-wider">
                                {selectedRank ? `Select Suit for ${selectedRank}` : 'Select a rank first'}
                            </div>
                            <div className="flex gap-3">
                                {SUITS.map((suit) => (
                                    <button
                                        key={suit.symbol}
                                        onClick={() => handleCardSelect(suit.symbol)}
                                        disabled={!selectedRank}
                                        className={`flex-1 py-4 rounded-lg text-3xl transition-all ${!selectedRank
                                            ? 'bg-[var(--rb-bg)] opacity-50 cursor-not-allowed'
                                            : `bg-[var(--rb-bg)] hover:bg-[var(--rb-surface-hover)] hover:scale-105 ${suit.color}`
                                            }`}
                                    >
                                        {suit.symbol}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Pending cards (observe mode) */}
                        {selectingFor === 'observe' && (
                            <div className="border-t border-[var(--rb-border)] pt-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-[var(--rb-text-muted)] uppercase">
                                        Cards to Submit
                                    </span>
                                    {pendingCards.length > 0 && (
                                        <button
                                            onClick={() => setPendingCards([])}
                                            className="text-xs text-[var(--rb-red)] hover:text-[var(--rb-red-hover)] flex items-center gap-1"
                                        >
                                            <Trash2 className="w-3 h-3" />
                                            Clear
                                        </button>
                                    )}
                                </div>
                                <div className="flex flex-wrap gap-2 min-h-[48px] p-3 rounded-lg bg-[var(--rb-bg)]">
                                    {pendingCards.length > 0 ? (
                                        pendingCards.map((card, i) => (
                                            <Card key={`${card}-${i}`} card={card} size="sm" />
                                        ))
                                    ) : (
                                        <span className="text-[var(--rb-text-dim)] text-sm">
                                            No cards selected
                                        </span>
                                    )}
                                </div>
                                <button
                                    onClick={handleSubmitCards}
                                    disabled={pendingCards.length === 0 || state.isLoading}
                                    className="rb-btn rb-btn-primary w-full mt-3"
                                >
                                    <Send className="w-4 h-4" />
                                    Submit Cards ({pendingCards.length})
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Decision Panel */}
                <div className="game-frame">
                    <div className="game-frame-header">
                        <div>
                            <h2 className="text-lg font-bold text-[var(--rb-text)]">
                                Get Recommendation
                            </h2>
                            <p className="text-sm text-[var(--rb-text-muted)]">
                                Enter your hand and dealer's upcard
                            </p>
                        </div>
                    </div>

                    <div className="p-6">
                        {/* Your hand */}
                        <div className="mb-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-[var(--rb-text-muted)] uppercase">
                                    Your Hand
                                </span>
                                {playerHand.length > 0 && (
                                    <button
                                        onClick={() => setPlayerHand([])}
                                        className="text-xs text-[var(--rb-red)]"
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>
                            <div className="flex gap-2 min-h-[80px] p-3 rounded-lg bg-[var(--rb-bg)] border border-[var(--rb-border)]">
                                {playerHand.length > 0 ? (
                                    playerHand.map((card, i) => (
                                        <Card key={`player-${card}-${i}`} card={card} size="sm" />
                                    ))
                                ) : (
                                    <span className="text-[var(--rb-text-dim)] text-sm self-center">
                                        Select "Your Hand" tab, then pick cards
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Dealer upcard */}
                        <div className="mb-6">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-[var(--rb-text-muted)] uppercase">
                                    Dealer Upcard
                                </span>
                                {dealerUpcard && (
                                    <button
                                        onClick={() => setDealerUpcard(null)}
                                        className="text-xs text-[var(--rb-red)]"
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>
                            <div className="flex gap-2 min-h-[80px] p-3 rounded-lg bg-[var(--rb-bg)] border border-[var(--rb-border)]">
                                {dealerUpcard ? (
                                    <Card card={dealerUpcard} size="sm" />
                                ) : (
                                    <span className="text-[var(--rb-text-dim)] text-sm self-center">
                                        Select "Dealer" tab, then pick a card
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex gap-3">
                            <button
                                onClick={handleGetDecision}
                                disabled={playerHand.length < 2 || !dealerUpcard || state.isLoading}
                                className="rb-btn rb-btn-green flex-1"
                            >
                                <Target className="w-4 h-4" />
                                Get Decision
                            </button>
                            <button onClick={handleClearHand} className="rb-btn rb-btn-outline">
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Recommendation result */}
                        {recommendation && (
                            <div className="mt-6 p-4 rounded-lg bg-[var(--rb-bg)] border border-[var(--rb-green)]/30 animate-fade-in">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="p-2 rounded-lg bg-[var(--rb-green)]/20">
                                        <Target className="w-6 h-6 text-[var(--rb-green)]" />
                                    </div>
                                    <div>
                                        <div className="text-sm text-[var(--rb-text-muted)]">
                                            Recommended Action
                                        </div>
                                        <div className="text-2xl font-bold text-[var(--rb-green)]">
                                            {recommendation.recommended_action}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-sm text-[var(--rb-text-muted)]">
                                    Hand Total:{' '}
                                    <span className="text-[var(--rb-text)] font-semibold">
                                        {recommendation.player_total}
                                    </span>
                                </div>

                                {recommendation.should_exit && recommendation.exit_reason && (
                                    <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--rb-red)]/10 border border-[var(--rb-red)]/30 text-[var(--rb-red)] text-sm">
                                        <AlertTriangle className="w-4 h-4" />
                                        {recommendation.exit_reason}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Error display */}
            {state.error && (
                <div className="mt-6 p-4 rounded-lg bg-[var(--rb-red)]/10 border border-[var(--rb-red)]/30 flex items-center gap-3 text-[var(--rb-red)]">
                    <AlertCircle className="w-5 h-5" />
                    <span>{state.error}</span>
                </div>
            )}

            {/* Quick Guide */}
            <div className="mt-6 rb-surface p-6">
                <h4 className="font-semibold text-[var(--rb-text)] mb-4">Quick Guide</h4>
                <div className="grid md:grid-cols-3 gap-4 text-sm">
                    <div className="p-4 rounded-lg bg-[var(--rb-bg)]">
                        <div className="font-semibold text-[var(--rb-primary)] mb-2">
                            1. Observe Cards
                        </div>
                        <p className="text-[var(--rb-text-muted)]">
                            Input any cards you see dealt at the table to update the running count.
                        </p>
                    </div>
                    <div className="p-4 rounded-lg bg-[var(--rb-bg)]">
                        <div className="font-semibold text-[var(--rb-green)] mb-2">
                            2. Your Hand
                        </div>
                        <p className="text-[var(--rb-text-muted)]">
                            When it's your turn, input your cards and the dealer's upcard.
                        </p>
                    </div>
                    <div className="p-4 rounded-lg bg-[var(--rb-bg)]">
                        <div className="font-semibold text-[var(--rb-amber)] mb-2">
                            3. Get Decision
                        </div>
                        <p className="text-[var(--rb-text-muted)]">
                            Receive the optimal play based on basic strategy and current count.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Shadowing;
