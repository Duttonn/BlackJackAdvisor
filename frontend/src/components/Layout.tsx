import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { healthCheck } from '../lib/api';
import { useState, useEffect } from 'react';
import {
    Spade,
    Gamepad2,
    Eye,
    Wifi,
    WifiOff,
    BarChart3,
    Settings,
    HelpCircle,
    LogOut,
} from 'lucide-react';

/**
 * Main application layout with header and sidebar
 * Mimics Rainbet's shell structure
 */
export function Layout() {
    const location = useLocation();
    const { state, endGame } = useGame();
    const [isConnected, setIsConnected] = useState<boolean | null>(null);

    // Check API connection
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
        const interval = setInterval(checkConnection, 5000);
        return () => clearInterval(interval);
    }, []);

    // Handle exit from active session
    const handleExitSession = async () => {
        if (state.sessionId) {
            await endGame();
        }
    };

    return (
        <div className="app-layout">
            {/* Header */}
            <header className="app-header">
                <div className="flex items-center justify-between w-full">
                    {/* Logo */}
                    <div className="logo">
                        <div className="logo-icon">
                            <Spade className="w-5 h-5" />
                        </div>
                        <span>Blackjack Advisor</span>
                    </div>

                    {/* Right side - Connection Status & Session Info */}
                    <div className="flex items-center gap-4">
                        {/* Session stats (when active) */}
                        {state.sessionId && (
                            <div className="hidden md:flex items-center gap-4 mr-4">
                                <div className="text-center">
                                    <div className="text-xs text-[var(--rb-text-muted)]">Mode</div>
                                    <div className="text-sm font-semibold">{state.gameMode}</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-xs text-[var(--rb-text-muted)]">Hands</div>
                                    <div className="text-sm font-semibold">{state.handsPlayed}</div>
                                </div>
                                <button
                                    onClick={handleExitSession}
                                    className="rb-btn-ghost p-2 rounded-lg hover:bg-white/5"
                                    title="Exit Session"
                                >
                                    <LogOut className="w-4 h-4 text-[var(--rb-text-muted)]" />
                                </button>
                            </div>
                        )}

                        {/* Connection status */}
                        <div
                            className={`connection-status ${isConnected === true
                                    ? 'connected'
                                    : isConnected === false
                                        ? 'disconnected'
                                        : 'connecting'
                                }`}
                        >
                            {isConnected === true ? (
                                <>
                                    <Wifi className="w-4 h-4" />
                                    <span className="hidden sm:inline">Connected</span>
                                </>
                            ) : isConnected === false ? (
                                <>
                                    <WifiOff className="w-4 h-4" />
                                    <span className="hidden sm:inline">Offline</span>
                                </>
                            ) : (
                                <>
                                    <Wifi className="w-4 h-4 animate-pulse" />
                                    <span className="hidden sm:inline">Connecting...</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            {/* Sidebar */}
            <aside className="app-sidebar">
                {/* Main Navigation */}
                <div className="nav-section-title">Game Modes</div>

                <NavLink
                    to="/"
                    end
                    className={({ isActive }) =>
                        `nav-item relative ${isActive && location.pathname === '/' ? 'active' : ''}`
                    }
                >
                    <Gamepad2 className="w-5 h-5" />
                    <span>Home</span>
                </NavLink>

                <NavLink
                    to="/training"
                    className={({ isActive }) => `nav-item relative ${isActive ? 'active' : ''}`}
                >
                    <Gamepad2 className="w-5 h-5" />
                    <span>Training Mode</span>
                    <span className="ml-auto px-2 py-0.5 text-[10px] font-semibold bg-[var(--rb-primary)]/20 text-[var(--rb-primary-light)] rounded">
                        AUTO
                    </span>
                </NavLink>

                <NavLink
                    to="/shadowing"
                    className={({ isActive }) => `nav-item relative ${isActive ? 'active' : ''}`}
                >
                    <Eye className="w-5 h-5" />
                    <span>Shadow Mode</span>
                    <span className="ml-auto px-2 py-0.5 text-[10px] font-semibold bg-[var(--rb-green)]/20 text-[var(--rb-green)] rounded">
                        MANUAL
                    </span>
                </NavLink>

                {/* Stats Section */}
                <div className="nav-section-title mt-6">Statistics</div>

                <div className="nav-item cursor-default">
                    <BarChart3 className="w-5 h-5" />
                    <span>Session Stats</span>
                </div>

                {/* Current session stats */}
                {state.sessionId && (
                    <div className="mx-4 mt-2 p-4 rounded-lg bg-[var(--rb-bg)] border border-[var(--rb-border)]">
                        <div className="grid grid-cols-2 gap-3 text-center">
                            <div>
                                <div className="text-xl font-bold text-[var(--rb-text)]">
                                    {state.handsPlayed}
                                </div>
                                <div className="text-[10px] text-[var(--rb-text-muted)] uppercase">
                                    Hands
                                </div>
                            </div>
                            <div>
                                <div
                                    className={`text-xl font-bold ${state.totalDecisions > 0
                                            ? (state.correctDecisions / state.totalDecisions) >= 0.9
                                                ? 'text-[var(--rb-green)]'
                                                : (state.correctDecisions / state.totalDecisions) >= 0.7
                                                    ? 'text-[var(--rb-amber)]'
                                                    : 'text-[var(--rb-red)]'
                                            : 'text-[var(--rb-text)]'
                                        }`}
                                >
                                    {state.totalDecisions > 0
                                        ? Math.round((state.correctDecisions / state.totalDecisions) * 100)
                                        : 0}
                                    %
                                </div>
                                <div className="text-[10px] text-[var(--rb-text-muted)] uppercase">
                                    Accuracy
                                </div>
                            </div>
                            <div>
                                <div
                                    className={`text-xl font-bold ${state.trueCount >= 2
                                            ? 'text-[var(--rb-green)]'
                                            : state.trueCount <= -1
                                                ? 'text-[var(--rb-red)]'
                                                : 'text-[var(--rb-text)]'
                                        }`}
                                >
                                    {state.trueCount >= 0 ? '+' : ''}
                                    {state.trueCount.toFixed(1)}
                                </div>
                                <div className="text-[10px] text-[var(--rb-text-muted)] uppercase">
                                    True Count
                                </div>
                            </div>
                            <div>
                                <div className="text-xl font-bold text-[var(--rb-green)]">
                                    ${state.recommendedBet}
                                </div>
                                <div className="text-[10px] text-[var(--rb-text-muted)] uppercase">
                                    Rec. Bet
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Bottom section */}
                <div className="mt-auto pt-6 border-t border-[var(--rb-border)] mx-4">
                    <div className="nav-item">
                        <HelpCircle className="w-5 h-5" />
                        <span>Help & Info</span>
                    </div>
                    <div className="nav-item">
                        <Settings className="w-5 h-5" />
                        <span>Settings</span>
                    </div>
                </div>

                {/* Strategy info at bottom */}
                <div className="mx-4 mt-4 p-3 rounded-lg bg-[var(--rb-bg)] text-[11px] text-[var(--rb-text-muted)]">
                    <div className="font-semibold text-[var(--rb-text-secondary)] mb-1">
                        Strategy Config
                    </div>
                    <div className="space-y-1">
                        <div>Hi-Lo Counting System</div>
                        <div>Illustrious 18 + Fab 4</div>
                        <div>Half-Kelly Betting</div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="app-main">
                <Outlet />
            </main>
        </div>
    );
}

export default Layout;
