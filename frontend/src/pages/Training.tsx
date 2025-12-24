import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { Card, CardStack } from '../components/Card';
import {
    Shuffle,
    CheckCircle,
    XCircle,
    Sparkles,
    Plus,
    Hand,
    Copy,
    Square,
    Flag,
    RefreshCw,
    AlertTriangle,
    DoorOpen,
    X,
} from 'lucide-react';

type Action = 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER';

/**
 * Training page - AUTO mode with casino-style game frame
 */
export function Training() {
    const navigate = useNavigate();
    const {
        state,
        endGame,
        dealNewHand,
        performAction,
        shuffleDeck,
        clearExit,
        accuracy,
    } = useGame();

    const [lastResult, setLastResult] = useState<{
        isCorrect: boolean;
        correctAction: string;
        outcome?: string;
    } | null>(null);

    // Redirect if no session
    useEffect(() => {
        if (!state.sessionId || state.gameMode !== 'AUTO') {
            navigate('/');
        }
    }, [state.sessionId, state.gameMode, navigate]);

    // Handle dealing new hand
    const handleDeal = async () => {
        setLastResult(null);
        await dealNewHand();
    };

    // Handle player action
    const handleAction = async (action: Action) => {
        const result = await performAction(action);
        if (result) {
            setLastResult({
                isCorrect: result.is_correct,
                correctAction: result.correct_action,
                outcome: result.outcome,
            });
        }
    };

    // Handle shuffle
    const handleShuffle = async () => {
        await shuffleDeck();
        setLastResult(null);
    };

    // Handle leaving
    const handleLeave = async () => {
        await endGame();
        navigate('/');
    };

    // Check if current hand allows split
    const canSplit =
        state.playerCards.length === 2 &&
        state.playerCards[0]?.charAt(0) === state.playerCards[1]?.charAt(0);
    const canDouble = state.playerCards.length === 2;
    const canSurrender = state.playerCards.length === 2;

    // Action button configs
    const actionButtons: {
        action: Action;
        label: string;
        icon: React.ReactNode;
        className: string;
        canUse: boolean;
    }[] = [
            {
                action: 'HIT',
                label: 'Hit',
                icon: <Plus className="w-5 h-5" />,
                className: 'action-btn-hit',
                canUse: true,
            },
            {
                action: 'STAND',
                label: 'Stand',
                icon: <Hand className="w-5 h-5" />,
                className: 'action-btn-stand',
                canUse: true,
            },
            {
                action: 'DOUBLE',
                label: 'Double',
                icon: <Copy className="w-5 h-5" />,
                className: 'action-btn-double',
                canUse: canDouble,
            },
            {
                action: 'SPLIT',
                label: 'Split',
                icon: <Square className="w-5 h-5" />,
                className: 'action-btn-split',
                canUse: canSplit,
            },
            {
                action: 'SURRENDER',
                label: 'Surrender',
                icon: <Flag className="w-5 h-5" />,
                className: 'action-btn-surrender',
                canUse: canSurrender,
            },
        ];

    return (
        <div className="max-w-5xl mx-auto">
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
                            <p className="text-[var(--rb-text-secondary)] mb-2">{state.exitReason}</p>
                            <p className="text-sm text-[var(--rb-text-muted)]">
                                Consider leaving the table to preserve your bankroll.
                            </p>
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
                    <div className="stat-value">{state.handsPlayed}</div>
                    <div className="stat-label">Hands</div>
                </div>
                <div className="stat-item">
                    <div
                        className={`stat-value ${accuracy >= 90
                                ? 'text-[var(--rb-green)]'
                                : accuracy >= 70
                                    ? 'text-[var(--rb-amber)]'
                                    : 'text-[var(--rb-red)]'
                            }`}
                    >
                        {accuracy}%
                    </div>
                    <div className="stat-label">Accuracy</div>
                </div>
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
                    <div className="stat-value text-[var(--rb-green)]">
                        ${state.recommendedBet}
                    </div>
                    <div className="stat-label">Rec. Bet</div>
                </div>
                <div className="ml-auto flex items-center gap-2">
                    <button onClick={handleShuffle} className="rb-btn rb-btn-ghost text-sm">
                        <Shuffle className="w-4 h-4" />
                        Shuffle
                    </button>
                </div>
            </div>

            {/* Game Frame */}
            <div className="game-frame">
                {/* Header */}
                <div className="game-frame-header">
                    <div>
                        <h2 className="text-lg font-bold text-[var(--rb-text)]">Training Mode</h2>
                        <p className="text-sm text-[var(--rb-text-muted)]">
                            Practice perfect basic strategy
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="count-box px-4 py-2">
                            <span className="text-[var(--rb-text-muted)] text-xs mr-2">RC:</span>
                            <span
                                className={`font-bold ${state.runningCount >= 0
                                        ? 'text-[var(--rb-green)]'
                                        : 'text-[var(--rb-red)]'
                                    }`}
                            >
                                {state.runningCount >= 0 ? '+' : ''}
                                {state.runningCount}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Game Content */}
                <div className="game-frame-content">
                    {/* Dealer Section */}
                    <div className="text-center mb-12">
                        <div className="text-xs text-[var(--rb-text-muted)] uppercase tracking-wider mb-4">
                            Dealer
                        </div>
                        <div className="flex justify-center gap-4">
                            {state.dealerCard ? (
                                <>
                                    <Card card={state.dealerCard} size="lg" animate />
                                    <Card card="" faceDown size="lg" />
                                </>
                            ) : (
                                <div className="w-[80px] h-[112px] border-2 border-dashed border-[var(--rb-border-light)] rounded-xl flex items-center justify-center text-[var(--rb-text-dim)]">
                                    <span className="text-xs uppercase">Waiting</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Divider */}
                    <div className="flex items-center gap-4 my-8">
                        <div className="flex-1 h-px bg-[var(--rb-border)]" />
                        <span className="text-[var(--rb-text-dim)] text-xs uppercase">vs</span>
                        <div className="flex-1 h-px bg-[var(--rb-border)]" />
                    </div>

                    {/* Player Section */}
                    <div className="text-center">
                        <div className="text-xs text-[var(--rb-text-muted)] uppercase tracking-wider mb-4">
                            Your Hand
                            {state.playerTotal > 0 && (
                                <span className="ml-2 text-[var(--rb-text)] font-bold text-sm">
                                    ({state.playerTotal})
                                </span>
                            )}
                        </div>
                        <div className="flex justify-center mb-6">
                            {state.playerCards.length > 0 ? (
                                <CardStack cards={state.playerCards} size="lg" overlap={45} />
                            ) : (
                                <div className="w-[80px] h-[112px] border-2 border-dashed border-[var(--rb-border-light)] rounded-xl flex items-center justify-center text-[var(--rb-text-dim)]">
                                    <span className="text-xs uppercase">Deal</span>
                                </div>
                            )}
                        </div>

                        {/* Blackjack notification */}
                        {state.isBlackjack && (
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--rb-amber)]/20 text-[var(--rb-amber)] font-bold mb-4 animate-fade-in">
                                <Sparkles className="w-5 h-5" />
                                BLACKJACK!
                            </div>
                        )}
                    </div>
                </div>

                {/* Action Feedback */}
                {lastResult && (
                    <div
                        className={`px-6 py-4 border-t border-[var(--rb-border)] animate-fade-in ${lastResult.isCorrect
                                ? 'bg-[var(--rb-green)]/10'
                                : 'bg-[var(--rb-red)]/10'
                            }`}
                    >
                        <div className="flex items-center gap-3">
                            {lastResult.isCorrect ? (
                                <CheckCircle className="w-8 h-8 text-[var(--rb-green)]" />
                            ) : (
                                <XCircle className="w-8 h-8 text-[var(--rb-red)]" />
                            )}
                            <div>
                                <div
                                    className={`font-bold ${lastResult.isCorrect
                                            ? 'text-[var(--rb-green)]'
                                            : 'text-[var(--rb-red)]'
                                        }`}
                                >
                                    {lastResult.isCorrect ? 'Correct!' : 'Incorrect'}
                                </div>
                                {!lastResult.isCorrect && (
                                    <div className="text-sm text-[var(--rb-text-muted)]">
                                        Optimal play was:{' '}
                                        <span className="font-semibold text-[var(--rb-text)]">
                                            {lastResult.correctAction}
                                        </span>
                                    </div>
                                )}
                                {lastResult.outcome && (
                                    <div
                                        className={`text-sm font-semibold ${lastResult.outcome === 'WIN'
                                                ? 'text-[var(--rb-green)]'
                                                : lastResult.outcome === 'LOSS' || lastResult.outcome === 'BUST'
                                                    ? 'text-[var(--rb-red)]'
                                                    : 'text-[var(--rb-text-muted)]'
                                            }`}
                                    >
                                        Result: {lastResult.outcome}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Controls */}
                <div className="game-frame-controls">
                    {state.handInProgress && !lastResult?.outcome ? (
                        <div className="action-buttons">
                            {actionButtons.map(({ action, label, icon, className, canUse }) => (
                                <button
                                    key={action}
                                    onClick={() => handleAction(action)}
                                    disabled={state.isLoading || !canUse}
                                    className={`action-btn ${className}`}
                                >
                                    {icon}
                                    {label}
                                </button>
                            ))}
                        </div>
                    ) : (
                        <div className="flex justify-center gap-4">
                            <button
                                onClick={handleDeal}
                                disabled={state.isLoading}
                                className="rb-btn rb-btn-green text-lg py-4 px-8"
                            >
                                {state.isLoading ? (
                                    <RefreshCw className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Plus className="w-5 h-5" />
                                )}
                                Deal New Hand
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Count Display */}
            <div className="mt-6 rb-surface p-6">
                <h3 className="text-sm font-semibold text-[var(--rb-text-muted)] uppercase tracking-wider mb-4">
                    Count Statistics
                </h3>
                <div className="count-display">
                    <div className="count-box">
                        <div className="count-box-label">Running Count</div>
                        <div
                            className={`count-box-value ${state.runningCount > 0
                                    ? 'positive'
                                    : state.runningCount < 0
                                        ? 'negative'
                                        : 'neutral'
                                }`}
                        >
                            {state.runningCount >= 0 ? '+' : ''}
                            {state.runningCount}
                        </div>
                    </div>
                    <div className="count-box">
                        <div className="count-box-label">True Count</div>
                        <div
                            className={`count-box-value ${state.trueCount >= 2
                                    ? 'positive'
                                    : state.trueCount <= -1
                                        ? 'negative'
                                        : 'neutral'
                                }`}
                        >
                            {state.trueCount >= 0 ? '+' : ''}
                            {state.trueCount.toFixed(1)}
                        </div>
                    </div>
                    <div className="count-box">
                        <div className="count-box-label">Recommended Bet</div>
                        <div className="count-box-value positive">${state.recommendedBet}</div>
                    </div>
                    <div className="count-box">
                        <div className="count-box-label">Bankroll</div>
                        <div className="count-box-value neutral">${state.bankroll}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Training;
