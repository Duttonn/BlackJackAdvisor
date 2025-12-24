import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import {
    Gamepad2,
    Eye,
    DollarSign,
    Sparkles,
    TrendingUp,
    Target,
    Zap,
    ArrowRight,
} from 'lucide-react';

/**
 * Home page - Game mode selection with Rainbet-style game cards
 */
export function Home() {
    const navigate = useNavigate();
    const { startGame, state } = useGame();

    const [selectedMode, setSelectedMode] = useState<'AUTO' | 'MANUAL' | null>(null);
    const [bankroll, setBankroll] = useState('1000');
    const [isStarting, setIsStarting] = useState(false);

    // Handle game start
    const handleStart = async () => {
        if (!selectedMode || !bankroll) return;

        setIsStarting(true);
        await startGame(selectedMode, parseFloat(bankroll));
        setIsStarting(false);

        if (selectedMode === 'AUTO') {
            navigate('/training');
        } else {
            navigate('/shadowing');
        }
    };

    // Quick start with preset mode
    const handleQuickStart = async (mode: 'AUTO' | 'MANUAL') => {
        setIsStarting(true);
        await startGame(mode, parseFloat(bankroll) || 1000);
        setIsStarting(false);
        navigate(mode === 'AUTO' ? '/training' : '/shadowing');
    };

    return (
        <div className="max-w-6xl mx-auto">
            {/* Page Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-[var(--rb-text)] mb-2">
                    Welcome to Blackjack Advisor
                </h1>
                <p className="text-[var(--rb-text-muted)]">
                    Select a game mode to start practicing perfect blackjack strategy
                </p>
            </div>

            {/* Featured Games Grid */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-[var(--rb-text-secondary)]">
                        Game Modes
                    </h2>
                    <div className="flex items-center gap-2 text-sm text-[var(--rb-text-muted)]">
                        <Sparkles className="w-4 h-4 text-[var(--rb-amber)]" />
                        <span>Recommended for you</span>
                    </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    {/* Training Mode Card */}
                    <button
                        onClick={() => setSelectedMode('AUTO')}
                        className={`game-card text-left ${selectedMode === 'AUTO'
                                ? 'ring-2 ring-[var(--rb-primary)] border-[var(--rb-primary)]/30'
                                : ''
                            }`}
                    >
                        <div className="game-card-image bg-gradient-to-br from-[#0066b8] to-[#003d6d]">
                            <div className="flex flex-col items-center">
                                <div className="w-20 h-20 rounded-2xl bg-white/10 flex items-center justify-center mb-3">
                                    <Gamepad2 className="w-10 h-10 text-white" />
                                </div>
                                <div className="flex gap-1">
                                    {['♠', '♥', '♦', '♣'].map((suit, i) => (
                                        <span
                                            key={i}
                                            className={`text-2xl ${suit === '♥' || suit === '♦' ? 'text-red-400' : 'text-white'
                                                }`}
                                        >
                                            {suit}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="game-card-content">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="game-card-title">Training Mode</h3>
                                <span className="rb-badge rb-badge-primary">AUTO</span>
                            </div>
                            <p className="game-card-subtitle mb-3">
                                Practice with simulated hands from a virtual 6-deck shoe
                            </p>
                            <div className="flex items-center gap-4 text-xs text-[var(--rb-text-muted)]">
                                <span className="flex items-center gap-1">
                                    <Target className="w-3 h-3" />
                                    Decision Feedback
                                </span>
                                <span className="flex items-center gap-1">
                                    <TrendingUp className="w-3 h-3" />
                                    Track Accuracy
                                </span>
                            </div>
                        </div>
                    </button>

                    {/* Shadow Mode Card */}
                    <button
                        onClick={() => setSelectedMode('MANUAL')}
                        className={`game-card text-left ${selectedMode === 'MANUAL'
                                ? 'ring-2 ring-[var(--rb-green)] border-[var(--rb-green)]/30'
                                : ''
                            }`}
                    >
                        <div className="game-card-image bg-gradient-to-br from-[#1a7a3a] to-[#0d4f22]">
                            <div className="flex flex-col items-center">
                                <div className="w-20 h-20 rounded-2xl bg-white/10 flex items-center justify-center mb-3">
                                    <Eye className="w-10 h-10 text-white" />
                                </div>
                                <div className="flex gap-2">
                                    <div className="px-3 py-1 rounded-full bg-white/10 text-xs text-white">
                                        Live Count
                                    </div>
                                    <div className="px-3 py-1 rounded-full bg-white/10 text-xs text-white">
                                        Real-Time
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="game-card-content">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="game-card-title">Shadow Mode</h3>
                                <span className="rb-badge rb-badge-green">MANUAL</span>
                            </div>
                            <p className="game-card-subtitle mb-3">
                                Input cards from live play and get real-time recommendations
                            </p>
                            <div className="flex items-center gap-4 text-xs text-[var(--rb-text-muted)]">
                                <span className="flex items-center gap-1">
                                    <Zap className="w-3 h-3" />
                                    Live Counting
                                </span>
                                <span className="flex items-center gap-1">
                                    <Eye className="w-3 h-3" />
                                    Casino Ready
                                </span>
                            </div>
                        </div>
                    </button>
                </div>
            </div>

            {/* Configuration Panel */}
            <div className="rb-surface p-6 mb-8">
                <h3 className="text-lg font-semibold text-[var(--rb-text)] mb-4 flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-[var(--rb-green)]" />
                    Session Configuration
                </h3>

                <div className="grid md:grid-cols-2 gap-6">
                    {/* Bankroll Input */}
                    <div>
                        <label className="block text-sm font-medium text-[var(--rb-text-secondary)] mb-2">
                            Starting Bankroll
                        </label>
                        <div className="relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--rb-text-muted)]">
                                $
                            </span>
                            <input
                                type="number"
                                value={bankroll}
                                onChange={(e) => setBankroll(e.target.value)}
                                min="100"
                                step="100"
                                className="rb-input pl-8 text-xl font-bold"
                                placeholder="1000"
                            />
                        </div>
                        <p className="mt-2 text-xs text-[var(--rb-text-muted)]">
                            Used for Half-Kelly bet sizing recommendations
                        </p>
                    </div>

                    {/* Mode Selection Summary */}
                    <div>
                        <label className="block text-sm font-medium text-[var(--rb-text-secondary)] mb-2">
                            Selected Mode
                        </label>
                        <div className="h-[52px] flex items-center px-4 rounded-lg bg-[var(--rb-bg)] border border-[var(--rb-border)]">
                            {selectedMode ? (
                                <div className="flex items-center gap-3">
                                    {selectedMode === 'AUTO' ? (
                                        <Gamepad2 className="w-5 h-5 text-[var(--rb-primary)]" />
                                    ) : (
                                        <Eye className="w-5 h-5 text-[var(--rb-green)]" />
                                    )}
                                    <span className="font-semibold">
                                        {selectedMode === 'AUTO' ? 'Training Mode' : 'Shadow Mode'}
                                    </span>
                                    <span
                                        className={`rb-badge ${selectedMode === 'AUTO' ? 'rb-badge-primary' : 'rb-badge-green'
                                            }`}
                                    >
                                        {selectedMode}
                                    </span>
                                </div>
                            ) : (
                                <span className="text-[var(--rb-text-muted)]">
                                    Click a game mode above to select
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Start Button */}
                <button
                    onClick={handleStart}
                    disabled={!selectedMode || !bankroll || isStarting}
                    className={`
            w-full mt-6 rb-btn text-lg py-4
            ${selectedMode === 'AUTO'
                            ? 'rb-btn-primary'
                            : selectedMode === 'MANUAL'
                                ? 'rb-btn-green'
                                : 'bg-[var(--rb-surface-hover)] text-[var(--rb-text-muted)] cursor-not-allowed'
                        }
          `}
                >
                    {isStarting ? (
                        <>
                            <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                            Starting Session...
                        </>
                    ) : (
                        <>
                            Start{' '}
                            {selectedMode === 'AUTO'
                                ? 'Training'
                                : selectedMode === 'MANUAL'
                                    ? 'Shadowing'
                                    : 'Session'}
                            <ArrowRight className="w-5 h-5" />
                        </>
                    )}
                </button>

                {/* Error display */}
                {state.error && (
                    <div className="mt-4 p-4 rounded-lg bg-[var(--rb-red)]/10 border border-[var(--rb-red)]/30 text-[var(--rb-red)]">
                        {state.error}
                    </div>
                )}
            </div>

            {/* Quick Start Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
                <button
                    onClick={() => handleQuickStart('AUTO')}
                    disabled={isStarting}
                    className="flex-1 rb-btn rb-btn-outline py-3"
                >
                    <Zap className="w-4 h-4" />
                    Quick Start: Training
                </button>
                <button
                    onClick={() => handleQuickStart('MANUAL')}
                    disabled={isStarting}
                    className="flex-1 rb-btn rb-btn-outline py-3"
                >
                    <Zap className="w-4 h-4" />
                    Quick Start: Shadowing
                </button>
            </div>

            {/* Strategy Info */}
            <div className="mt-8 rb-surface p-6">
                <h4 className="font-semibold text-[var(--rb-text)] mb-4">
                    Strategy Configuration
                </h4>
                <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: 'Counting System', value: 'Hi-Lo' },
                        { label: 'Bet Sizing', value: 'Half-Kelly (0.5×)' },
                        { label: 'Index Play', value: 'Illustrious 18 + Fab 4' },
                        { label: 'Wong Out', value: 'TC < -1.0' },
                    ].map((item, i) => (
                        <div key={i} className="text-center p-4 rounded-lg bg-[var(--rb-bg)]">
                            <div className="text-[var(--rb-text-muted)] text-xs uppercase tracking-wider mb-1">
                                {item.label}
                            </div>
                            <div className="font-semibold text-[var(--rb-text)]">{item.value}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default Home;
