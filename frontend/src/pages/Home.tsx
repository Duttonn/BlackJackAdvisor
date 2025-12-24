import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { healthCheck } from '../lib/api';
import {
    Spade,
    Target,
    Eye,
    DollarSign,
    Wifi,
    WifiOff,
    ArrowRight,
    Info,
    Sparkles,
} from 'lucide-react';

/**
 * Home page - Mode selection and game initialization
 */
export function Home() {
    const navigate = useNavigate();
    const { startGame, state } = useGame();

    const [selectedMode, setSelectedMode] = useState<'AUTO' | 'MANUAL' | null>(null);
    const [bankroll, setBankroll] = useState('1000');
    const [isConnected, setIsConnected] = useState<boolean | null>(null);
    const [isStarting, setIsStarting] = useState(false);

    // Check API connection on mount
    useEffect(() => {
        const checkConnection = async () => {
            try {
                await healthCheck();
                setIsConnected(true);
            } catch {
                setIsConnected(false);
            }
        };

        checkConnection();

        // Re-check every 5 seconds
        const interval = setInterval(checkConnection, 5000);
        return () => clearInterval(interval);
    }, []);

    // Handle game start
    const handleStart = async () => {
        if (!selectedMode || !bankroll) return;

        setIsStarting(true);
        await startGame(selectedMode, parseFloat(bankroll));
        setIsStarting(false);

        // Navigate to appropriate page
        if (selectedMode === 'AUTO') {
            navigate('/training');
        } else {
            navigate('/shadowing');
        }
    };

    return (
        <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
            {/* Header */}
            <header className="border-b border-[var(--color-border)] py-6">
                <div className="container mx-auto px-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-500/20 rounded-lg">
                                <Spade className="w-8 h-8 text-emerald-400" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold gradient-text">Blackjack Advisor</h1>
                                <p className="text-sm text-gray-500">Real-Time Decision Engine</p>
                            </div>
                        </div>

                        {/* Connection status */}
                        <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-sm
              ${isConnected === true
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : isConnected === false
                                    ? 'bg-red-500/20 text-red-400'
                                    : 'bg-gray-500/20 text-gray-400'
                            }
            `}>
                            {isConnected === true ? (
                                <>
                                    <Wifi className="w-4 h-4" />
                                    <span>API Connected</span>
                                </>
                            ) : isConnected === false ? (
                                <>
                                    <WifiOff className="w-4 h-4" />
                                    <span>API Offline</span>
                                </>
                            ) : (
                                <>
                                    <Wifi className="w-4 h-4 animate-pulse" />
                                    <span>Connecting...</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="flex-1 container mx-auto px-6 py-12">
                <div className="max-w-4xl mx-auto">
                    {/* Welcome section */}
                    <div className="text-center mb-12">
                        <h2 className="text-4xl font-bold text-white mb-4">
                            Master the <span className="gradient-text">Art of Counting</span>
                        </h2>
                        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                            Train your decision-making with our AI-powered engine featuring Hi-Lo counting,
                            Illustrious 18 deviations, and Half-Kelly betting recommendations.
                        </p>
                    </div>

                    {/* Mode selection */}
                    <div className="grid md:grid-cols-2 gap-6 mb-8">
                        {/* AUTO Mode */}
                        <button
                            onClick={() => setSelectedMode('AUTO')}
                            className={`
                relative overflow-hidden surface-elevated p-6 text-left
                transition-all duration-300 cursor-pointer group
                ${selectedMode === 'AUTO'
                                    ? 'ring-2 ring-emerald-500 border-emerald-500/50'
                                    : 'hover:border-gray-600'
                                }
              `}
                        >
                            {/* Glow effect when selected */}
                            {selectedMode === 'AUTO' && (
                                <div className="absolute inset-0 bg-emerald-500/5 pointer-events-none" />
                            )}

                            <div className="relative z-10">
                                <div className="flex items-start gap-4 mb-4">
                                    <div className={`
                    p-3 rounded-xl
                    ${selectedMode === 'AUTO'
                                            ? 'bg-emerald-500/20 text-emerald-400'
                                            : 'bg-gray-700 text-gray-400 group-hover:text-emerald-400'
                                        }
                    transition-colors
                  `}>
                                        <Target className="w-8 h-8" />
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
                                            Training Mode
                                            <span className="badge badge-primary text-xs">AUTO</span>
                                        </h3>
                                        <p className="text-gray-400 text-sm">
                                            Practice perfect strategy with simulated hands
                                        </p>
                                    </div>
                                </div>

                                <ul className="space-y-2 text-sm text-gray-400">
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Engine deals from virtual 6-deck shoe
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Get instant feedback on every decision
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Track accuracy and improve over time
                                    </li>
                                </ul>
                            </div>
                        </button>

                        {/* MANUAL Mode */}
                        <button
                            onClick={() => setSelectedMode('MANUAL')}
                            className={`
                relative overflow-hidden surface-elevated p-6 text-left
                transition-all duration-300 cursor-pointer group
                ${selectedMode === 'MANUAL'
                                    ? 'ring-2 ring-indigo-500 border-indigo-500/50'
                                    : 'hover:border-gray-600'
                                }
              `}
                        >
                            {/* Glow effect when selected */}
                            {selectedMode === 'MANUAL' && (
                                <div className="absolute inset-0 bg-indigo-500/5 pointer-events-none" />
                            )}

                            <div className="relative z-10">
                                <div className="flex items-start gap-4 mb-4">
                                    <div className={`
                    p-3 rounded-xl
                    ${selectedMode === 'MANUAL'
                                            ? 'bg-indigo-500/20 text-indigo-400'
                                            : 'bg-gray-700 text-gray-400 group-hover:text-indigo-400'
                                        }
                    transition-colors
                  `}>
                                        <Eye className="w-8 h-8" />
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
                                            Shadow Mode
                                            <span className="badge badge-accent text-xs">MANUAL</span>
                                        </h3>
                                        <p className="text-gray-400 text-sm">
                                            Real-time advice for live casino play
                                        </p>
                                    </div>
                                </div>

                                <ul className="space-y-2 text-sm text-gray-400">
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Input cards as you observe them
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Get running & true count in real-time
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-amber-400" />
                                        Receive optimal action recommendations
                                    </li>
                                </ul>
                            </div>
                        </button>
                    </div>

                    {/* Bankroll input */}
                    <div className="surface-elevated p-6 mb-8">
                        <label className="block text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            <DollarSign className="w-4 h-4 inline mr-1" />
                            Starting Bankroll
                        </label>
                        <div className="relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">$</span>
                            <input
                                type="number"
                                value={bankroll}
                                onChange={(e) => setBankroll(e.target.value)}
                                min="100"
                                step="100"
                                className="input pl-8 text-2xl font-bold"
                                placeholder="1000"
                            />
                        </div>
                        <p className="mt-2 text-sm text-gray-500">
                            Used for Half-Kelly bet sizing recommendations
                        </p>
                    </div>

                    {/* Start button */}
                    <button
                        onClick={handleStart}
                        disabled={!selectedMode || !bankroll || !isConnected || isStarting}
                        className={`
              w-full flex items-center justify-center gap-3
              px-8 py-5 rounded-xl
              text-lg font-bold uppercase tracking-wider
              transition-all duration-300
              ${selectedMode
                                ? selectedMode === 'AUTO'
                                    ? 'btn-primary'
                                    : 'btn-accent'
                                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            }
            `}
                    >
                        {isStarting ? (
                            <>
                                <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Starting Session...
                            </>
                        ) : (
                            <>
                                Start {selectedMode === 'AUTO' ? 'Training' : selectedMode === 'MANUAL' ? 'Shadowing' : 'Session'}
                                <ArrowRight className="w-6 h-6" />
                            </>
                        )}
                    </button>

                    {/* Error display */}
                    {state.error && (
                        <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">
                            {state.error}
                        </div>
                    )}

                    {/* Info box */}
                    <div className="mt-8 p-6 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl">
                        <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                            <Info className="w-5 h-5 text-blue-400" />
                            Strategy Information
                        </h4>
                        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-400">
                            <div>
                                <strong className="text-gray-300">Counting System:</strong> Hi-Lo
                            </div>
                            <div>
                                <strong className="text-gray-300">Bet Sizing:</strong> Half-Kelly (0.5×)
                            </div>
                            <div>
                                <strong className="text-gray-300">Index Play:</strong> Illustrious 18 + Fab 4
                            </div>
                            <div>
                                <strong className="text-gray-300">Wong Out:</strong> True Count &lt; -1.0
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-[var(--color-border)] py-4">
                <div className="container mx-auto px-6 text-center text-sm text-gray-500">
                    For educational purposes only. Please gamble responsibly.
                </div>
            </footer>
        </div>
    );
}

export default Home;
