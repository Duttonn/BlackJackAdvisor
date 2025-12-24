import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { Card } from '../components/Card';
import { CountDisplay } from '../components/CountDisplay';
import { ExitWarning, InlineExitWarning } from '../components/ExitWarning';
import type { DecisionResponse } from '../lib/api';
import {
    Home,
    Eye,
    Plus,
    Send,
    Trash2,
    Shuffle,
    Target,
    AlertCircle,
} from 'lucide-react';

// Card ranks and suits for input
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'];
const SUITS = [
    { symbol: '♠', name: 'Spades', color: 'text-gray-300' },
    { symbol: '♥', name: 'Hearts', color: 'text-red-500' },
    { symbol: '♦', name: 'Diamonds', color: 'text-red-500' },
    { symbol: '♣', name: 'Clubs', color: 'text-gray-300' },
];

/**
 * Shadowing page - MANUAL mode for real casino play
 * User inputs observed cards and gets real-time count/recommendations
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

    // Decision request state
    const [playerHand, setPlayerHand] = useState<string[]>([]);
    const [dealerUpcard, setDealerUpcard] = useState<string | null>(null);
    const [selectingFor, setSelectingFor] = useState<'observe' | 'player' | 'dealer'>('observe');
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

    // Get decision recommendation
    const handleGetDecision = async () => {
        if (playerHand.length < 2 || !dealerUpcard) return;

        const result = await getRecommendation(playerHand, dealerUpcard);
        if (result) {
            setRecommendation(result);
        }
    };

    // Clear hand for new decision
    const handleClearHand = () => {
        setPlayerHand([]);
        setDealerUpcard(null);
        setRecommendation(null);
    };

    // Handle shuffle (new shoe)
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
        <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
            {/* Header */}
            <header className="border-b border-[var(--color-border)] py-4">
                <div className="container mx-auto px-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-indigo-500/20 rounded-lg">
                                <Eye className="w-6 h-6 text-indigo-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-white">Shadow Mode</h1>
                                <p className="text-xs text-gray-500">Real-Time Casino Companion</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleShuffle}
                                disabled={state.isLoading}
                                className="btn btn-outline text-sm"
                            >
                                <Shuffle className="w-4 h-4" />
                                New Shoe
                            </button>
                            <button
                                onClick={handleLeave}
                                className="btn btn-ghost text-sm"
                            >
                                <Home className="w-4 h-4" />
                                Exit
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="flex-1 container mx-auto px-6 py-8">
                <div className="max-w-5xl mx-auto space-y-6">

                    {/* Exit warning */}
                    {state.shouldExit && state.exitReason && (
                        <ExitWarning
                            reason={state.exitReason}
                            onDismiss={clearExit}
                            onExitTable={handleLeave}
                        />
                    )}

                    {/* Count display */}
                    <CountDisplay
                        runningCount={state.runningCount}
                        trueCount={state.trueCount}
                        recommendedBet={state.recommendedBet}
                        bankroll={state.bankroll}
                    />

                    <div className="grid lg:grid-cols-2 gap-6">
                        {/* Card Input Section */}
                        <div className="surface-elevated p-6">
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <Plus className="w-4 h-4" />
                                Card Input
                            </h3>

                            {/* Input mode selector */}
                            <div className="flex gap-2 mb-4">
                                <button
                                    onClick={() => setSelectingFor('observe')}
                                    className={`
                    flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                    ${selectingFor === 'observe'
                                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                                            : 'bg-gray-700/50 text-gray-400 hover:text-gray-300'
                                        }
                  `}
                                >
                                    Observe Cards
                                </button>
                                <button
                                    onClick={() => setSelectingFor('player')}
                                    className={`
                    flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                    ${selectingFor === 'player'
                                            ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                                            : 'bg-gray-700/50 text-gray-400 hover:text-gray-300'
                                        }
                  `}
                                >
                                    Your Hand
                                </button>
                                <button
                                    onClick={() => setSelectingFor('dealer')}
                                    className={`
                    flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                    ${selectingFor === 'dealer'
                                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                                            : 'bg-gray-700/50 text-gray-400 hover:text-gray-300'
                                        }
                  `}
                                >
                                    Dealer Card
                                </button>
                            </div>

                            {/* Rank selector */}
                            <div className="mb-4">
                                <div className="text-xs text-gray-500 mb-2">Select Rank</div>
                                <div className="flex flex-wrap gap-2">
                                    {RANKS.map((rank) => (
                                        <button
                                            key={rank}
                                            onClick={() => setSelectedRank(rank)}
                                            className={`
                        w-10 h-10 rounded-lg font-bold text-lg
                        transition-all duration-200
                        ${selectedRank === rank
                                                    ? 'bg-emerald-500 text-white scale-110'
                                                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                                }
                      `}
                                        >
                                            {rank}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Suit selector */}
                            <div className="mb-4">
                                <div className="text-xs text-gray-500 mb-2">
                                    {selectedRank ? `Select Suit for ${selectedRank}` : 'Select a rank first'}
                                </div>
                                <div className="flex gap-3">
                                    {SUITS.map((suit) => (
                                        <button
                                            key={suit.symbol}
                                            onClick={() => handleCardSelect(suit.symbol)}
                                            disabled={!selectedRank}
                                            className={`
                        flex-1 py-4 rounded-lg text-3xl
                        transition-all duration-200
                        ${!selectedRank
                                                    ? 'bg-gray-800 opacity-50 cursor-not-allowed'
                                                    : `bg-gray-700 hover:bg-gray-600 hover:scale-105 ${suit.color}`
                                                }
                      `}
                                        >
                                            {suit.symbol}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Pending cards (observe mode) */}
                            {selectingFor === 'observe' && (
                                <div className="border-t border-[var(--color-border)] pt-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs text-gray-500">Cards to Submit</span>
                                        {pendingCards.length > 0 && (
                                            <button
                                                onClick={() => setPendingCards([])}
                                                className="text-xs text-red-400 hover:text-red-300"
                                            >
                                                <Trash2 className="w-3 h-3 inline mr-1" />
                                                Clear
                                            </button>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap gap-2 min-h-[40px]">
                                        {pendingCards.length > 0 ? (
                                            pendingCards.map((card, i) => (
                                                <Card key={`${card}-${i}`} card={card} size="sm" />
                                            ))
                                        ) : (
                                            <div className="text-gray-600 text-sm">No cards selected</div>
                                        )}
                                    </div>
                                    <button
                                        onClick={handleSubmitCards}
                                        disabled={pendingCards.length === 0 || state.isLoading}
                                        className="btn btn-primary w-full mt-3"
                                    >
                                        <Send className="w-4 h-4" />
                                        Submit Cards ({pendingCards.length})
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* Decision Request Section */}
                        <div className="surface-elevated p-6">
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                Get Recommendation
                            </h3>

                            {/* Your hand */}
                            <div className="mb-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-gray-500">Your Hand</span>
                                    {playerHand.length > 0 && (
                                        <button
                                            onClick={() => setPlayerHand([])}
                                            className="text-xs text-red-400 hover:text-red-300"
                                        >
                                            Clear
                                        </button>
                                    )}
                                </div>
                                <div className="flex gap-2 min-h-[68px] p-3 bg-[var(--color-background)] rounded-lg border border-[var(--color-border)]">
                                    {playerHand.length > 0 ? (
                                        playerHand.map((card, i) => (
                                            <Card key={`player-${card}-${i}`} card={card} size="sm" />
                                        ))
                                    ) : (
                                        <div className="flex items-center text-gray-600 text-sm">
                                            Select "Your Hand" above, then pick cards
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Dealer upcard */}
                            <div className="mb-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-gray-500">Dealer Upcard</span>
                                    {dealerUpcard && (
                                        <button
                                            onClick={() => setDealerUpcard(null)}
                                            className="text-xs text-red-400 hover:text-red-300"
                                        >
                                            Clear
                                        </button>
                                    )}
                                </div>
                                <div className="flex gap-2 min-h-[68px] p-3 bg-[var(--color-background)] rounded-lg border border-[var(--color-border)]">
                                    {dealerUpcard ? (
                                        <Card card={dealerUpcard} size="sm" />
                                    ) : (
                                        <div className="flex items-center text-gray-600 text-sm">
                                            Select "Dealer Card" above, then pick a card
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Action buttons */}
                            <div className="flex gap-3">
                                <button
                                    onClick={handleGetDecision}
                                    disabled={playerHand.length < 2 || !dealerUpcard || state.isLoading}
                                    className="btn btn-accent flex-1"
                                >
                                    <Target className="w-4 h-4" />
                                    Get Decision
                                </button>
                                <button
                                    onClick={handleClearHand}
                                    className="btn btn-outline"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Recommendation result */}
                            {recommendation && (
                                <div className="mt-4 p-4 bg-[var(--color-background)] rounded-lg border border-emerald-500/50 fade-in">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="p-2 bg-emerald-500/20 rounded-lg">
                                            <Target className="w-6 h-6 text-emerald-400" />
                                        </div>
                                        <div>
                                            <div className="text-sm text-gray-400">Recommended Action</div>
                                            <div className="text-2xl font-bold text-emerald-400">
                                                {recommendation.recommended_action}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-sm text-gray-400">
                                        Hand Total: <span className="text-white font-semibold">{recommendation.player_total}</span>
                                    </div>

                                    {/* Exit warning in recommendation */}
                                    {recommendation.should_exit && recommendation.exit_reason && (
                                        <div className="mt-3">
                                            <InlineExitWarning reason={recommendation.exit_reason} />
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Error display */}
                    {state.error && (
                        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3 text-red-300">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span>{state.error}</span>
                        </div>
                    )}

                    {/* Instructions */}
                    <div className="surface p-6">
                        <h4 className="font-semibold text-white mb-3">Quick Guide</h4>
                        <div className="grid md:grid-cols-3 gap-4 text-sm text-gray-400">
                            <div>
                                <strong className="text-emerald-400">1. Observe Cards</strong>
                                <p>Input any cards you see dealt at the table to update the running count.</p>
                            </div>
                            <div>
                                <strong className="text-blue-400">2. Your Hand</strong>
                                <p>When it's your turn, input your cards and the dealer's upcard.</p>
                            </div>
                            <div>
                                <strong className="text-purple-400">3. Get Decision</strong>
                                <p>Receive the optimal play based on basic strategy and current count.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default Shadowing;
