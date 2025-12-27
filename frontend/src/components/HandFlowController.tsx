/**
 * HandFlowController.tsx
 * 
 * Phase 9: Auto-Flow State Machine with Split Support & Dealer Turn
 * 
 * A guided flow for entering cards during a hand:
 * - State A (DEAL): Input Player Card 1, Player Card 2, Dealer Upcard
 * - State B (DECISION): Receive recommendation, handle HIT/STAND/DOUBLE/SPLIT/SURRENDER
 * - State C (DEALER_TURN): Input dealer's hole card and any draws
 * - State D (SETTLED): Show outcome, display recommended bet for next hand
 * 
 * Key Features:
 * - Auto-keypad for HIT/DOUBLE decisions
 * - Re-evaluation loop after each HIT
 * - One-card-and-done for DOUBLE
 * - Dealer turn for hole card + additional draws
 * - Multi-hand support for SPLIT
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronRight,
    RotateCcw,
    Target,
    TrendingUp,
    AlertTriangle,
    Check,
    Sparkles,
    Layers,
    User,
    Crown
} from 'lucide-react';
import { CardInputGrid } from './CardInputGrid';
import { Card } from './Card';
import type { DecisionResponse } from '../lib/api';

// Flow states
export type FlowState =
    | 'IDLE'           // Waiting to start new hand
    | 'PLAYER_CARD_1'  // Entering first player card
    | 'PLAYER_CARD_2'  // Entering second player card
    | 'DEALER_UPCARD'  // Entering dealer's face-up card
    | 'DECISION'       // Showing recommendation, auto-keypad for HIT/DOUBLE
    | 'AWAITING_HIT'   // Waiting for HIT card (when user overrides to hit)
    | 'SPLIT_CARD'     // Entering card for split hand
    | 'DEALER_TURN'    // Entering dealer's hole card and additional draws
    | 'SETTLED';       // Hand complete, showing next bet

// Action outcomes
export type ActionOutcome = 'WIN' | 'LOSS' | 'PUSH' | 'BUST' | 'BLACKJACK' | 'SURRENDER';

// Single hand state
interface Hand {
    cards: string[];
    total: number;
    isBusted: boolean;
    isSettled: boolean;
    outcome: ActionOutcome | null;
}

interface HandFlowControllerProps {
    // Callbacks to GameContext
    onCardObserved: (card: string) => Promise<void>;
    onGetDecision: (playerCards: string[], dealerCard: string) => Promise<DecisionResponse | null>;

    // Current game stats (for display)
    trueCount: number;
    runningCount: number;
    recommendedBet: number;

    // Exit signal
    shouldExit: boolean;
    exitReason: string | null;

    // Loading state
    isLoading: boolean;
}

const FLOW_PROMPTS: Record<FlowState, string> = {
    IDLE: 'Tap "New Hand" to begin',
    PLAYER_CARD_1: 'Enter your first card',
    PLAYER_CARD_2: 'Enter your second card',
    DEALER_UPCARD: "Enter dealer's upcard",
    DECISION: 'Optimal play shown',
    AWAITING_HIT: 'Enter the card you received',
    SPLIT_CARD: 'Enter card for split hand',
    DEALER_TURN: "Enter dealer's cards",
    SETTLED: 'Hand complete',
};

// Calculate hand total from cards
function calculateTotal(cards: string[]): { total: number; isSoft: boolean } {
    let total = 0;
    let aces = 0;

    for (const card of cards) {
        const rank = card.charAt(0).toUpperCase();
        if (rank === 'A') {
            aces++;
            total += 11;
        } else if (['T', 'J', 'Q', 'K'].includes(rank) || rank === '1') {
            total += 10;
        } else {
            total += parseInt(rank, 10) || 0;
        }
    }

    // Adjust for aces
    while (total > 21 && aces > 0) {
        total -= 10;
        aces--;
    }

    return { total, isSoft: aces > 0 };
}

// Check if action recommends taking a card (HIT or DOUBLE both need card input)
function isHitAction(action: string): boolean {
    const upper = action.toUpperCase();
    // HIT, H, DOUBLE, D, DH, DS all require taking a card
    return ['HIT', 'H', 'DOUBLE', 'D', 'DH', 'DS'].some(a => upper.includes(a));
}

function isDoubleAction(action: string): boolean {
    const upper = action.toUpperCase();
    return upper.includes('DOUBLE') || upper === 'D' || upper === 'DH' || upper === 'DS';
}

function isStandAction(action: string): boolean {
    const upper = action.toUpperCase();
    return upper.includes('STAND') || upper === 'S';
}

function isSplitAction(action: string): boolean {
    const upper = action.toUpperCase();
    return upper.includes('SPLIT') || upper === 'P';
}

// Determine outcome based on player and dealer totals
function determineOutcome(playerTotal: number, dealerTotal: number, playerBusted: boolean): ActionOutcome {
    if (playerBusted) return 'BUST';
    if (dealerTotal > 21) return 'WIN'; // Dealer busts
    if (playerTotal > dealerTotal) return 'WIN';
    if (playerTotal < dealerTotal) return 'LOSS';
    return 'PUSH';
}

export function HandFlowController({
    onCardObserved,
    onGetDecision,
    trueCount,
    runningCount,
    recommendedBet,
    shouldExit,
    exitReason,
    isLoading,
}: HandFlowControllerProps) {
    // Core state
    const [flowState, setFlowState] = useState<FlowState>('IDLE');
    const [dealerCards, setDealerCards] = useState<string[]>([]); // All dealer cards (upcard + hole + draws)
    const [recommendation, setRecommendation] = useState<DecisionResponse | null>(null);
    const [lastAction, setLastAction] = useState<string | null>(null);
    const [handNumber, setHandNumber] = useState(1);

    // Multi-hand support (for splits)
    const [hands, setHands] = useState<Hand[]>([{ cards: [], total: 0, isBusted: false, isSettled: false, outcome: null }]);
    const [activeHandIndex, setActiveHandIndex] = useState(0);

    // Animation feedback
    const [showHitFeedback, setShowHitFeedback] = useState(false);

    // Get current active hand
    const activeHand = hands[activeHandIndex];
    const isSplitGame = hands.length > 1;

    // Calculate dealer total
    const dealerTotal = dealerCards.length > 0 ? calculateTotal(dealerCards).total : 0;
    const dealerBusted = dealerTotal > 21;

    // Progress indicator
    const progressPercent = (() => {
        switch (flowState) {
            case 'IDLE': return 0;
            case 'PLAYER_CARD_1': return 15;
            case 'PLAYER_CARD_2': return 30;
            case 'DEALER_UPCARD': return 45;
            case 'DECISION': return 60;
            case 'AWAITING_HIT': return 65;
            case 'SPLIT_CARD': return 65;
            case 'DEALER_TURN': return 85;
            case 'SETTLED': return 100;
            default: return 0;
        }
    })();

    // Start new hand
    const startNewHand = useCallback(() => {
        setHands([{ cards: [], total: 0, isBusted: false, isSettled: false, outcome: null }]);
        setActiveHandIndex(0);
        setDealerCards([]);
        setRecommendation(null);
        setLastAction(null);
        setFlowState('PLAYER_CARD_1');
    }, []);

    // Reset to idle
    const resetToIdle = useCallback(() => {
        setHands([{ cards: [], total: 0, isBusted: false, isSettled: false, outcome: null }]);
        setActiveHandIndex(0);
        setDealerCards([]);
        setRecommendation(null);
        setLastAction(null);
        setFlowState('IDLE');
    }, []);

    // Update hand with new card and calculate total
    const updateHandWithCard = useCallback((handIndex: number, card: string): Hand => {
        const hand = hands[handIndex];
        const newCards = [...hand.cards, card];
        const { total } = calculateTotal(newCards);
        const isBusted = total > 21;

        return {
            ...hand,
            cards: newCards,
            total,
            isBusted,
            outcome: isBusted ? 'BUST' : null,
        };
    }, [hands]);

    // Transition to dealer turn (after player is done)
    const goToDealerTurn = useCallback(() => {
        // Check if player busted - if so, skip dealer turn
        const allBusted = hands.every(h => h.isBusted);
        if (allBusted) {
            setFlowState('SETTLED');
        } else {
            setFlowState('DEALER_TURN');
        }
    }, [hands]);

    // Fetch decision and handle auto-progression
    const fetchAndProcessDecision = useCallback(async (playerCards: string[], dealer: string) => {
        const decision = await onGetDecision(playerCards, dealer);
        if (decision) {
            setRecommendation(decision);

            // Check if we should auto-stand (e.g., player has 21)
            const { total } = calculateTotal(playerCards);
            if (total === 21 && playerCards.length === 2) {
                // Blackjack!
                setHands(prev => {
                    const updated = [...prev];
                    updated[activeHandIndex] = {
                        ...updated[activeHandIndex],
                        isSettled: true,
                        outcome: 'BLACKJACK',
                    };
                    return updated;
                });
                // Check if more hands to play
                if (isSplitGame && activeHandIndex < hands.length - 1) {
                    setActiveHandIndex(prev => prev + 1);
                    setFlowState('SPLIT_CARD');
                } else {
                    goToDealerTurn();
                }
                return;
            }
        }
        setFlowState('DECISION');
    }, [onGetDecision, activeHandIndex, hands.length, isSplitGame, goToDealerTurn]);

    // Handle card input based on current flow state
    const handleCardInput = useCallback(async (card: string) => {
        // Submit to backend for counting
        await onCardObserved(card);

        switch (flowState) {
            case 'PLAYER_CARD_1': {
                const updatedHand = updateHandWithCard(0, card);
                setHands([updatedHand]);
                setFlowState('PLAYER_CARD_2');
                break;
            }

            case 'PLAYER_CARD_2': {
                const updatedHand = updateHandWithCard(0, card);
                setHands([updatedHand]);
                setFlowState('DEALER_UPCARD');
                break;
            }

            case 'DEALER_UPCARD': {
                setDealerCards([card]);
                // Fetch initial decision
                await fetchAndProcessDecision(activeHand.cards, card);
                break;
            }

            case 'AWAITING_HIT':
            case 'DECISION': {
                // User tapped a card = implicit HIT confirmation
                const wasDouble = lastAction === 'DOUBLE' || (recommendation && isDoubleAction(recommendation.recommended_action));
                setLastAction(wasDouble ? 'DOUBLE' : 'HIT');

                // Update hand
                const updatedHand = updateHandWithCard(activeHandIndex, card);
                setHands(prev => {
                    const updated = [...prev];
                    updated[activeHandIndex] = updatedHand;
                    return updated;
                });

                // Flash feedback
                setShowHitFeedback(true);
                setTimeout(() => setShowHitFeedback(false), 300);

                // Check bust
                if (updatedHand.isBusted) {
                    setHands(prev => {
                        const updated = [...prev];
                        updated[activeHandIndex] = { ...updatedHand, isSettled: true, outcome: 'BUST' };
                        return updated;
                    });

                    // Check if more hands to play (split scenario)
                    if (isSplitGame && activeHandIndex < hands.length - 1) {
                        setActiveHandIndex(prev => prev + 1);
                        setFlowState('SPLIT_CARD');
                    } else {
                        goToDealerTurn();
                    }
                    return;
                }

                // DOUBLE = one card and done
                if (wasDouble) {
                    setHands(prev => {
                        const updated = [...prev];
                        updated[activeHandIndex] = { ...updatedHand, isSettled: true };
                        return updated;
                    });

                    // Check if more hands to play
                    if (isSplitGame && activeHandIndex < hands.length - 1) {
                        setActiveHandIndex(prev => prev + 1);
                        setFlowState('SPLIT_CARD');
                    } else {
                        goToDealerTurn();
                    }
                    return;
                }

                // HIT = re-evaluate
                if (dealerCards.length > 0) {
                    const newDecision = await onGetDecision(updatedHand.cards, dealerCards[0]);
                    if (newDecision) {
                        setRecommendation(newDecision);

                        // Auto-stand if at 21 or strategy says STAND
                        if (updatedHand.total === 21 || isStandAction(newDecision.recommended_action)) {
                            setHands(prev => {
                                const updated = [...prev];
                                updated[activeHandIndex] = { ...updatedHand, isSettled: true };
                                return updated;
                            });

                            // Check if more hands to play
                            if (isSplitGame && activeHandIndex < hands.length - 1) {
                                setActiveHandIndex(prev => prev + 1);
                                setFlowState('SPLIT_CARD');
                            } else {
                                goToDealerTurn();
                            }
                            return;
                        }

                        // Continue playing (HIT again)
                        setFlowState('DECISION');
                    }
                }
                break;
            }

            case 'SPLIT_CARD': {
                // First card for split hand
                const updatedHand = updateHandWithCard(activeHandIndex, card);
                setHands(prev => {
                    const updated = [...prev];
                    updated[activeHandIndex] = updatedHand;
                    return updated;
                });

                // Fetch decision for this split hand
                if (dealerCards.length > 0) {
                    await fetchAndProcessDecision(updatedHand.cards, dealerCards[0]);
                }
                break;
            }

            case 'DEALER_TURN': {
                // Add card to dealer's hand
                const newDealerCards = [...dealerCards, card];
                setDealerCards(newDealerCards);

                // Calculate new dealer total
                const { total: newDealerTotal } = calculateTotal(newDealerCards);

                // Check if dealer is done (17+ or bust)
                if (newDealerTotal >= 17) {
                    // Auto-determine outcomes for all hands
                    setHands(prev => prev.map(hand => {
                        if (hand.outcome) return hand; // Already has outcome (bust, blackjack, surrender)
                        return {
                            ...hand,
                            isSettled: true,
                            outcome: determineOutcome(hand.total, newDealerTotal, hand.isBusted),
                        };
                    }));
                    setFlowState('SETTLED');
                }
                // Otherwise stay in DEALER_TURN for more cards
                break;
            }
        }
    }, [flowState, activeHand, activeHandIndex, dealerCards, hands, isSplitGame, lastAction, recommendation, onCardObserved, onGetDecision, updateHandWithCard, fetchAndProcessDecision, goToDealerTurn]);

    // Handle explicit action selection (STAND, SPLIT, SURRENDER)
    const handleActionSelect = useCallback((action: string) => {
        setLastAction(action);

        switch (action.toUpperCase()) {
            case 'STAND':
            case 'S':
                setHands(prev => {
                    const updated = [...prev];
                    updated[activeHandIndex] = { ...updated[activeHandIndex], isSettled: true };
                    return updated;
                });

                // Check if more hands to play
                if (isSplitGame && activeHandIndex < hands.length - 1) {
                    setActiveHandIndex(prev => prev + 1);
                    setFlowState('SPLIT_CARD');
                } else {
                    goToDealerTurn();
                }
                break;

            case 'SPLIT':
            case 'P':
                // Create two hands from original pair
                if (activeHand.cards.length >= 2) {
                    const card1 = activeHand.cards[0];
                    const card2 = activeHand.cards[1];
                    const { total: t1 } = calculateTotal([card1]);
                    const { total: t2 } = calculateTotal([card2]);

                    setHands([
                        { cards: [card1], total: t1, isBusted: false, isSettled: false, outcome: null },
                        { cards: [card2], total: t2, isBusted: false, isSettled: false, outcome: null },
                    ]);
                    setActiveHandIndex(0);
                    setFlowState('SPLIT_CARD');
                }
                break;

            case 'SURRENDER':
            case 'SUR':
                setHands(prev => {
                    const updated = [...prev];
                    updated[activeHandIndex] = { ...updated[activeHandIndex], isSettled: true, outcome: 'SURRENDER' };
                    return updated;
                });
                setFlowState('SETTLED');
                break;
        }
    }, [activeHand, activeHandIndex, hands.length, isSplitGame, goToDealerTurn]);

    // Skip dealer turn (for bust/surrender cases)
    const handleSkipDealerTurn = useCallback(() => {
        setFlowState('SETTLED');
    }, []);

    // Move to next hand
    const handleNextHand = useCallback(() => {
        setHandNumber(prev => prev + 1);
        startNewHand();
    }, [startNewHand]);


    // Determine if we should show keypad in DECISION state
    const shouldShowAutoKeypad = flowState === 'DECISION' && recommendation && isHitAction(recommendation.recommended_action);

    return (
        <div className="space-y-4">
            {/* Progress Bar */}
            <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                    className={`absolute inset-y-0 left-0 ${showHitFeedback ? 'bg-gradient-to-r from-blue-500 to-blue-400' : 'bg-gradient-to-r from-emerald-500 to-emerald-400'}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${progressPercent}%` }}
                    transition={{ duration: 0.3, ease: 'easeOut' }}
                />
            </div>

            {/* Status Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className={`
                        w-10 h-10 rounded-xl flex items-center justify-center
                        ${flowState === 'SETTLED' ? 'bg-emerald-500/20 text-emerald-400' :
                            flowState === 'DEALER_TURN' ? 'bg-amber-500/20 text-amber-400' :
                                flowState === 'DECISION' ? 'bg-blue-500/20 text-blue-400' :
                                    'bg-slate-700 text-slate-400'}
                    `}>
                        {flowState === 'SETTLED' ? (
                            <Check className="w-5 h-5" />
                        ) : flowState === 'DEALER_TURN' ? (
                            <Crown className="w-5 h-5" />
                        ) : flowState === 'DECISION' ? (
                            <Target className="w-5 h-5" />
                        ) : isSplitGame ? (
                            <Layers className="w-5 h-5" />
                        ) : (
                            <User className="w-5 h-5" />
                        )}
                    </div>
                    <div>
                        <div className="text-sm font-medium text-slate-300">
                            Hand #{handNumber}
                            {isSplitGame && <span className="text-purple-400 ml-2">(Split {activeHandIndex + 1}/{hands.length})</span>}
                        </div>
                        <div className="text-xs text-slate-500">
                            {FLOW_PROMPTS[flowState]}
                        </div>
                    </div>
                </div>

                {flowState !== 'IDLE' && (
                    <button
                        onClick={resetToIdle}
                        className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
                        title="Cancel hand"
                    >
                        <RotateCcw className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Cards Display */}
            <AnimatePresence mode="wait">
                {(activeHand.cards.length > 0 || dealerCards.length > 0) && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="p-4 rounded-xl bg-slate-800/50"
                    >
                        {/* Split Hands Display */}
                        {isSplitGame ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    {hands.map((hand, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-3 rounded-lg border-2 transition-all ${idx === activeHandIndex && flowState !== 'DEALER_TURN' && flowState !== 'SETTLED'
                                                ? 'border-purple-500 bg-purple-500/10'
                                                : hand.isSettled
                                                    ? 'border-slate-700 bg-slate-800/50 opacity-60'
                                                    : 'border-slate-700'
                                                }`}
                                        >
                                            <div className="text-xs text-slate-500 mb-2">
                                                Hand {idx + 1}
                                                {hand.isBusted && <span className="text-red-400 ml-2">BUST</span>}
                                                {hand.outcome === 'BLACKJACK' && <span className="text-amber-400 ml-2">BJ!</span>}
                                                {hand.outcome && !hand.isBusted && hand.outcome !== 'BLACKJACK' && (
                                                    <span className={`ml-2 ${hand.outcome === 'WIN' ? 'text-emerald-400' : hand.outcome === 'LOSS' ? 'text-red-400' : 'text-slate-400'}`}>
                                                        {hand.outcome}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex gap-1 flex-wrap">
                                                {hand.cards.map((card, i) => (
                                                    <Card key={`${card}-${i}`} card={card} size="sm" />
                                                ))}
                                            </div>
                                            {hand.total > 0 && (
                                                <div className={`mt-2 text-lg font-bold ${hand.isBusted ? 'text-red-400' : 'text-slate-200'}`}>
                                                    {hand.total}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>

                                {/* Dealer section for split */}
                                <div className="pt-3 border-t border-slate-700">
                                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                        <Crown className="w-3 h-3" />
                                        Dealer
                                    </div>
                                    <div className="flex gap-1">
                                        {dealerCards.map((card, i) => (
                                            <Card key={`d-${card}-${i}`} card={card} size="sm" />
                                        ))}
                                        {flowState === 'DEALER_TURN' && (
                                            <div className="w-10 h-14 rounded-lg border-2 border-dashed border-amber-500/50 flex items-center justify-center">
                                                <span className="text-amber-500/50 text-[10px]">+</span>
                                            </div>
                                        )}
                                    </div>
                                    {dealerTotal > 0 && (
                                        <div className={`mt-2 text-lg font-bold ${dealerBusted ? 'text-red-400' : 'text-amber-300'}`}>
                                            {dealerTotal}{dealerBusted && ' BUST'}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            /* Single Hand Display */
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                        <User className="w-3 h-3" />
                                        Your Hand
                                    </div>
                                    <div className="flex gap-1 flex-wrap">
                                        {activeHand.cards.map((card, i) => (
                                            <motion.div
                                                key={`${card}-${i}`}
                                                initial={{ scale: 0, rotate: -10 }}
                                                animate={{ scale: 1, rotate: 0 }}
                                                transition={{ delay: i * 0.1 }}
                                            >
                                                <Card card={card} size="sm" />
                                            </motion.div>
                                        ))}
                                        {['PLAYER_CARD_1', 'PLAYER_CARD_2', 'AWAITING_HIT'].includes(flowState) && (
                                            <div className="w-12 h-16 rounded-lg border-2 border-dashed border-emerald-500/50 flex items-center justify-center">
                                                <span className="text-emerald-500/50 text-xs">+</span>
                                            </div>
                                        )}
                                    </div>
                                    {activeHand.total > 0 && (
                                        <div className={`mt-2 text-lg font-bold ${activeHand.isBusted ? 'text-red-400' : 'text-slate-200'}`}>
                                            Total: {activeHand.total}
                                            {activeHand.isBusted && ' (BUST)'}
                                            {activeHand.outcome && !activeHand.isBusted && (
                                                <span className={`ml-2 text-sm ${activeHand.outcome === 'WIN' ? 'text-emerald-400' : activeHand.outcome === 'LOSS' ? 'text-red-400' : 'text-slate-400'}`}>
                                                    {activeHand.outcome}
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                        <Crown className="w-3 h-3" />
                                        Dealer
                                    </div>
                                    <div className="flex gap-1 flex-wrap">
                                        {dealerCards.map((card, i) => (
                                            <motion.div
                                                key={`d-${card}-${i}`}
                                                initial={{ scale: 0, rotate: 10 }}
                                                animate={{ scale: 1, rotate: 0 }}
                                                transition={{ delay: i * 0.1 }}
                                            >
                                                <Card card={card} size="sm" />
                                            </motion.div>
                                        ))}
                                        {flowState === 'DEALER_UPCARD' && (
                                            <div className="w-12 h-16 rounded-lg border-2 border-dashed border-amber-500/50 flex items-center justify-center">
                                                <span className="text-amber-500/50 text-xs">UP</span>
                                            </div>
                                        )}
                                        {flowState === 'DEALER_TURN' && (
                                            <div className="w-12 h-16 rounded-lg border-2 border-dashed border-amber-500/50 flex items-center justify-center animate-pulse">
                                                <span className="text-amber-500/50 text-xs">+</span>
                                            </div>
                                        )}
                                    </div>
                                    {dealerTotal > 0 && (
                                        <div className={`mt-2 text-lg font-bold ${dealerBusted ? 'text-red-400' : 'text-amber-300'}`}>
                                            Total: {dealerTotal}
                                            {dealerBusted && ' (BUST)'}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Content Area */}
            <AnimatePresence mode="wait">
                {/* IDLE State */}
                {flowState === 'IDLE' && (
                    <motion.div
                        key="idle"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="text-center py-8"
                    >
                        <div className="mb-6 p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                                Recommended Bet
                            </div>
                            <div className="text-3xl font-bold text-emerald-400">
                                ${recommendedBet}
                            </div>
                            <div className="text-sm text-slate-500 mt-1">
                                TC: {trueCount >= 0 ? '+' : ''}{trueCount.toFixed(1)} |
                                RC: {runningCount >= 0 ? '+' : ''}{runningCount}
                            </div>
                        </div>

                        {shouldExit && exitReason && (
                            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-2 text-red-400">
                                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                                <span className="text-sm">{exitReason}</span>
                            </div>
                        )}

                        <button
                            onClick={startNewHand}
                            className="
                                inline-flex items-center gap-2 px-6 py-3 rounded-xl
                                bg-gradient-to-r from-emerald-600 to-emerald-500
                                hover:from-emerald-500 hover:to-emerald-400
                                text-white font-semibold text-lg
                                transition-all duration-200 hover:scale-105
                                shadow-lg shadow-emerald-500/20
                            "
                        >
                            <Sparkles className="w-5 h-5" />
                            New Hand
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </motion.div>
                )}

                {/* Card Input States (Initial Deal) */}
                {['PLAYER_CARD_1', 'PLAYER_CARD_2', 'DEALER_UPCARD', 'AWAITING_HIT', 'SPLIT_CARD'].includes(flowState) && (
                    <motion.div
                        key="card-input"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <CardInputGrid
                            onCardSelect={handleCardInput}
                            prompt={FLOW_PROMPTS[flowState]}
                            disabled={isLoading}
                        />
                    </motion.div>
                )}

                {/* DECISION State - Auto-keypad for HIT/DOUBLE */}
                {flowState === 'DECISION' && recommendation && (
                    <motion.div
                        key="decision"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="space-y-4"
                    >
                        {/* Recommendation Banner */}
                        <div className={`
                            p-4 rounded-xl border-l-4 
                            ${isHitAction(recommendation.recommended_action)
                                ? 'bg-gradient-to-r from-emerald-500/20 to-emerald-600/5 border-emerald-500'
                                : isStandAction(recommendation.recommended_action)
                                    ? 'bg-gradient-to-r from-amber-500/20 to-amber-600/5 border-amber-500'
                                    : isSplitAction(recommendation.recommended_action)
                                        ? 'bg-gradient-to-r from-purple-500/20 to-purple-600/5 border-purple-500'
                                        : 'bg-gradient-to-r from-blue-500/20 to-blue-600/5 border-blue-500'
                            }
                        `}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-white/10">
                                        <Target className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <div className="text-[10px] text-white/60 uppercase tracking-wider">
                                            Optimal Play
                                        </div>
                                        <div className="text-2xl font-black text-white tracking-tight">
                                            {recommendation.recommended_action}
                                        </div>
                                    </div>
                                </div>

                                {/* Override button */}
                                {!isStandAction(recommendation.recommended_action) && (
                                    <button
                                        onClick={() => handleActionSelect('STAND')}
                                        className="px-2 py-1 rounded-lg bg-slate-800/80 text-[10px] text-slate-400 font-semibold border border-slate-700 hover:bg-slate-700"
                                    >
                                        STAND
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Auto-keypad for HIT/DOUBLE */}
                        {shouldShowAutoKeypad && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                <div className="text-center text-sm text-emerald-400 mb-2 animate-pulse">
                                    ↓ Tap the card you received ↓
                                </div>
                                <CardInputGrid
                                    onCardSelect={handleCardInput}
                                    prompt=""
                                    disabled={isLoading}
                                />
                            </motion.div>
                        )}

                        {/* STAND/SPLIT/SURRENDER buttons */}
                        {!shouldShowAutoKeypad && (
                            <div className="space-y-3">
                                <button
                                    onClick={() => handleActionSelect(recommendation.recommended_action)}
                                    className="w-full py-4 rounded-xl font-bold text-lg bg-gradient-to-r from-amber-500 to-amber-600 text-white hover:from-amber-400 hover:to-amber-500 transition-all shadow-lg"
                                >
                                    Confirm {recommendation.recommended_action}
                                </button>

                                {/* I hit anyway escape hatch */}
                                <button
                                    onClick={() => setFlowState('AWAITING_HIT')}
                                    className="w-full py-2 rounded-lg text-sm text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-all"
                                >
                                    I hit anyway...
                                </button>
                            </div>
                        )}

                        {/* Split option */}
                        {isSplitAction(recommendation.recommended_action) && !isSplitGame && (
                            <button
                                onClick={() => handleActionSelect('SPLIT')}
                                className="w-full py-3 rounded-xl font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30"
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <Layers className="w-5 h-5" />
                                    Split Hand
                                </div>
                            </button>
                        )}
                    </motion.div>
                )}

                {/* DEALER_TURN State */}
                {flowState === 'DEALER_TURN' && (
                    <motion.div
                        key="dealer-turn"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="space-y-4"
                    >
                        {/* Dealer Turn Banner */}
                        <div className="p-4 rounded-xl bg-gradient-to-r from-amber-500/20 to-amber-600/5 border-l-4 border-amber-500">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-amber-500/20">
                                    <Crown className="w-5 h-5 text-amber-400" />
                                </div>
                                <div>
                                    <div className="text-[10px] text-amber-200/60 uppercase tracking-wider">
                                        Dealer's Turn
                                    </div>
                                    <div className="text-lg font-bold text-amber-200">
                                        {dealerCards.length === 1 ? 'Enter hole card' : `Total: ${dealerTotal}`}
                                    </div>
                                </div>
                            </div>
                            {dealerTotal >= 17 && !dealerBusted && (
                                <div className="mt-2 text-sm text-amber-300">
                                    Dealer stands on {dealerTotal}
                                </div>
                            )}
                            {dealerBusted && (
                                <div className="mt-2 text-sm text-red-400 font-bold">
                                    Dealer BUSTS! 🎉
                                </div>
                            )}
                        </div>

                        {/* Keypad for dealer cards */}
                        <CardInputGrid
                            onCardSelect={handleCardInput}
                            prompt={dealerCards.length === 1 ? "Enter dealer's hole card" : "Enter dealer's next card (or skip if done)"}
                            disabled={isLoading}
                        />

                        {/* Skip button (if dealer done or all players busted) */}
                        <button
                            onClick={handleSkipDealerTurn}
                            className="w-full py-2 rounded-lg text-sm text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-all"
                        >
                            {hands.every(h => h.isBusted) ? 'All hands busted - Skip to results' : 'Dealer stands - Done'}
                        </button>
                    </motion.div>
                )}

                {/* SETTLED State */}
                {flowState === 'SETTLED' && (
                    <motion.div
                        key="settled"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="space-y-4"
                    >
                        {/* Results Summary */}
                        <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Results</div>
                            {hands.map((hand, idx) => (
                                <div key={idx} className={`flex items-center justify-between py-2 ${idx > 0 ? 'border-t border-slate-700' : ''}`}>
                                    <div className="flex items-center gap-2">
                                        {isSplitGame && <span className="text-xs text-slate-500">Hand {idx + 1}:</span>}
                                        <span className="font-bold text-slate-300">{hand.total}</span>
                                    </div>
                                    <span className={`font-bold px-3 py-1 rounded-lg ${hand.outcome === 'WIN' || hand.outcome === 'BLACKJACK' ? 'bg-emerald-500/20 text-emerald-400' :
                                        hand.outcome === 'LOSS' || hand.outcome === 'BUST' ? 'bg-red-500/20 text-red-400' :
                                            hand.outcome === 'PUSH' ? 'bg-slate-600/50 text-slate-300' :
                                                hand.outcome === 'SURRENDER' ? 'bg-amber-500/20 text-amber-400' :
                                                    'bg-slate-700 text-slate-400'
                                        }`}>
                                        {hand.outcome || 'N/A'}
                                    </span>
                                </div>
                            ))}
                            <div className="flex items-center justify-between pt-2 border-t border-slate-700 mt-2">
                                <span className="text-xs text-slate-500">Dealer</span>
                                <span className={`font-bold ${dealerBusted ? 'text-red-400' : 'text-amber-300'}`}>
                                    {dealerTotal}{dealerBusted && ' BUST'}
                                </span>
                            </div>
                        </div>

                        {/* Next Hand Bet */}
                        <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-xs text-slate-500 uppercase tracking-wider">
                                        Next Hand Bet
                                    </div>
                                    <div className="text-2xl font-bold text-emerald-400">
                                        ${recommendedBet}
                                    </div>
                                </div>
                                <div className="flex items-center gap-1 text-slate-500">
                                    <TrendingUp className="w-4 h-4" />
                                    <span className="text-sm">
                                        TC: {trueCount >= 0 ? '+' : ''}{trueCount.toFixed(1)}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Next Hand Button */}
                        <button
                            onClick={handleNextHand}
                            className="
                                w-full py-3 rounded-xl font-semibold
                                bg-gradient-to-r from-emerald-600 to-emerald-500
                                hover:from-emerald-500 hover:to-emerald-400
                                text-white transition-all duration-200
                                flex items-center justify-center gap-2
                            "
                        >
                            Next Hand
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default HandFlowController;
