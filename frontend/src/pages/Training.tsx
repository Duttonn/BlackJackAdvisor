import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { Card, CardStack } from '../components/Card';
import { CountDisplay } from '../components/CountDisplay';
import { ActionButtons } from '../components/ActionButtons';
import { ExitWarning, ExitToast } from '../components/ExitWarning';
import {
    Spade,
    RefreshCw,
    Home,
    Trophy,
    Shuffle,
    CheckCircle,
    XCircle,
    Sparkles,
    TrendingUp,
} from 'lucide-react';

/**
 * Training page - AUTO mode gameplay
 * Engine deals hands, player practices decisions with feedback
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

    const [showExitToast, setShowExitToast] = useState(false);
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

    // Show exit toast when exit signal triggers
    useEffect(() => {
        if (state.shouldExit) {
            setShowExitToast(true);
        }
    }, [state.shouldExit]);

    // Handle dealing new hand
    const handleDeal = async () => {
        setLastResult(null);
        await dealNewHand();
    };

    // Handle player action
    const handleAction = async (action: 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER') => {
        const result = await performAction(action);
        if (result) {
            setLastResult({
                isCorrect: result.is_correct,
                correctAction: result.correct_action,
                outcome: result.outcome,
            });
        }
    };

    // Handle leaving the table
    const handleLeaveTable = async () => {
        await endGame();
        navigate('/');
    };

    // Handle shuffle
    const handleShuffle = async () => {
        await shuffleDeck();
        setLastResult(null);
    };

    // Check if current hand allows split (two cards of same rank)
    const canSplit = state.playerCards.length === 2 &&
        state.playerCards[0]?.charAt(0) === state.playerCards[1]?.charAt(0);

    // Can only double on first two cards
    const canDouble = state.playerCards.length === 2;

    // Can only surrender on first two cards
    const canSurrender = state.playerCards.length === 2;

    return (
        <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
            {/* Header */}
            <header className="border-b border-[var(--color-border)] py-4">
                <div className="container mx-auto px-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-500/20 rounded-lg">
                                <Spade className="w-6 h-6 text-emerald-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-white">Training Mode</h1>
                                <p className="text-xs text-gray-500">Practice Perfect Strategy</p>
                            </div>
                        </div>

                        {/* Stats */}
                        <div className="flex items-center gap-6">
                            <div className="text-center">
                                <div className="text-xs text-gray-500 uppercase">Hands</div>
                                <div className="text-xl font-bold text-white">{state.handsPlayed}</div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-gray-500 uppercase">Accuracy</div>
                                <div className={`text-xl font-bold ${accuracy >= 90 ? 'text-emerald-400' : accuracy >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                                    {accuracy}%
                                </div>
                            </div>
                            <button
                                onClick={handleLeaveTable}
                                className="btn btn-ghost text-sm"
                            >
                                <Home className="w-4 h-4" />
                                Exit
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main game area */}
            <main className="flex-1 container mx-auto px-6 py-8">
                <div className="max-w-4xl mx-auto space-y-6">

                    {/* Exit warning banner */}
                    {state.shouldExit && state.exitReason && (
                        <ExitWarning
                            reason={state.exitReason}
                            onDismiss={clearExit}
                            onExitTable={handleLeaveTable}
                        />
                    )}

                    {/* Count display */}
                    <CountDisplay
                        runningCount={state.runningCount}
                        trueCount={state.trueCount}
                        recommendedBet={state.recommendedBet}
                        bankroll={state.bankroll}
                    />

                    {/* Game table */}
                    <div className="surface-elevated p-8">
                        {/* Dealer section */}
                        <div className="text-center mb-8">
                            <h3 className="text-sm text-gray-500 uppercase tracking-wider mb-4">Dealer</h3>
                            <div className="flex justify-center">
                                {state.dealerCard ? (
                                    <div className="flex gap-3">
                                        <Card card={state.dealerCard} size="lg" />
                                        <Card card="" faceDown size="lg" />
                                    </div>
                                ) : (
                                    <div className="w-[90px] h-[130px] border-2 border-dashed border-gray-600 rounded-lg flex items-center justify-center text-gray-600">
                                        <span className="text-sm">Waiting</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Divider */}
                        <div className="border-t border-[var(--color-border)] my-8" />

                        {/* Player section */}
                        <div className="text-center">
                            <h3 className="text-sm text-gray-500 uppercase tracking-wider mb-4">
                                Your Hand
                                {state.playerTotal > 0 && (
                                    <span className="ml-2 text-white font-bold">({state.playerTotal})</span>
                                )}
                            </h3>
                            <div className="flex justify-center mb-6">
                                {state.playerCards.length > 0 ? (
                                    <CardStack cards={state.playerCards} size="lg" overlap={40} />
                                ) : (
                                    <div className="w-[90px] h-[130px] border-2 border-dashed border-gray-600 rounded-lg flex items-center justify-center text-gray-600">
                                        <span className="text-sm">Deal to start</span>
                                    </div>
                                )}
                            </div>

                            {/* Blackjack notification */}
                            {state.isBlackjack && (
                                <div className="mb-4 p-3 bg-amber-500/20 border border-amber-500/50 rounded-lg inline-flex items-center gap-2 text-amber-300">
                                    <Sparkles className="w-5 h-5" />
                                    <span className="font-bold">BLACKJACK!</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Action feedback */}
                    {lastResult && (
                        <div
                            className={`
                p-4 rounded-xl border fade-in
                ${lastResult.isCorrect
                                    ? 'bg-emerald-500/10 border-emerald-500/50'
                                    : 'bg-red-500/10 border-red-500/50'
                                }
              `}
                        >
                            <div className="flex items-center gap-3">
                                {lastResult.isCorrect ? (
                                    <CheckCircle className="w-8 h-8 text-emerald-400" />
                                ) : (
                                    <XCircle className="w-8 h-8 text-red-400" />
                                )}
                                <div>
                                    <div className={`font-bold ${lastResult.isCorrect ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {lastResult.isCorrect ? 'Correct!' : 'Incorrect'}
                                    </div>
                                    {!lastResult.isCorrect && (
                                        <div className="text-sm text-gray-400">
                                            Optimal play was: <span className="font-semibold text-white">{lastResult.correctAction}</span>
                                        </div>
                                    )}
                                    {lastResult.outcome && (
                                        <div className={`text-sm font-semibold ${lastResult.outcome === 'WIN' ? 'text-emerald-400' :
                                            lastResult.outcome === 'LOSS' || lastResult.outcome === 'BUST' ? 'text-red-400' :
                                                'text-gray-400'
                                            }`}>
                                            Hand Result: {lastResult.outcome}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Action buttons or deal button */}
                    {state.handInProgress && !lastResult?.outcome ? (
                        <ActionButtons
                            onAction={handleAction}
                            disabled={state.isLoading || !!lastResult?.outcome}
                            canSplit={canSplit}
                            canDouble={canDouble}
                            canSurrender={canSurrender}
                        />
                    ) : (
                        <div className="flex justify-center gap-4">
                            <button
                                onClick={handleDeal}
                                disabled={state.isLoading}
                                className="btn btn-primary text-lg px-8 py-4"
                            >
                                {state.isLoading ? (
                                    <RefreshCw className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Spade className="w-5 h-5" />
                                )}
                                Deal New Hand
                            </button>
                            <button
                                onClick={handleShuffle}
                                disabled={state.isLoading}
                                className="btn btn-outline text-lg px-6 py-4"
                            >
                                <Shuffle className="w-5 h-5" />
                                Shuffle
                            </button>
                        </div>
                    )}

                    {/* Progress tracker */}
                    <div className="surface-elevated p-6">
                        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <Trophy className="w-4 h-4" />
                            Session Progress
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                            <div>
                                <div className="text-2xl font-bold text-white">{state.handsPlayed}</div>
                                <div className="text-xs text-gray-500 uppercase">Hands Played</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-emerald-400">{state.correctDecisions}</div>
                                <div className="text-xs text-gray-500 uppercase">Correct</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-red-400">{state.totalDecisions - state.correctDecisions}</div>
                                <div className="text-xs text-gray-500 uppercase">Mistakes</div>
                            </div>
                            <div>
                                <div className={`text-2xl font-bold ${accuracy >= 90 ? 'text-emerald-400' : accuracy >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                                    {accuracy}%
                                </div>
                                <div className="text-xs text-gray-500 uppercase flex items-center justify-center gap-1">
                                    <TrendingUp className="w-3 h-3" />
                                    Accuracy
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Exit toast notification */}
            {showExitToast && state.exitReason && (
                <ExitToast
                    reason={state.exitReason}
                    onClose={() => setShowExitToast(false)}
                    autoClose={10000}
                />
            )}
        </div>
    );
}

export default Training;
