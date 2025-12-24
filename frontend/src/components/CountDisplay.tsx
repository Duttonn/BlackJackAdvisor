import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, DollarSign, RefreshCw } from 'lucide-react';

interface CountDisplayProps {
    runningCount: number;
    trueCount: number;
    recommendedBet: number;
    bankroll?: number;
    className?: string;
}

/**
 * Display component for card counting statistics
 * Shows Running Count, True Count, and Recommended Bet
 */
export function CountDisplay({
    runningCount,
    trueCount,
    recommendedBet,
    bankroll,
    className = '',
}: CountDisplayProps) {
    const [prevTrueCount, setPrevTrueCount] = useState(trueCount);
    const [countAnimation, setCountAnimation] = useState<'up' | 'down' | null>(null);

    // Animate count changes
    useEffect(() => {
        if (trueCount > prevTrueCount) {
            setCountAnimation('up');
        } else if (trueCount < prevTrueCount) {
            setCountAnimation('down');
        }
        setPrevTrueCount(trueCount);

        const timer = setTimeout(() => setCountAnimation(null), 300);
        return () => clearTimeout(timer);
    }, [trueCount, prevTrueCount]);

    // Determine count color based on value
    const getCountColor = (count: number) => {
        if (count >= 2) return 'text-emerald-400';
        if (count <= -2) return 'text-red-400';
        return 'text-gray-300';
    };

    // Determine count indicator icon
    const getCountIcon = (count: number) => {
        if (count >= 2) return <TrendingUp className="w-4 h-4" />;
        if (count <= -2) return <TrendingDown className="w-4 h-4" />;
        return <Minus className="w-4 h-4" />;
    };

    // Format bet amount
    const formatBet = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    return (
        <div className={`surface-elevated p-6 ${className}`}>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <RefreshCw className="w-4 h-4" />
                Count Statistics
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Running Count */}
                <div className="text-center p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                        Running Count
                    </div>
                    <div className={`text-3xl font-bold ${getCountColor(runningCount)}`}>
                        {runningCount >= 0 ? '+' : ''}{runningCount}
                    </div>
                </div>

                {/* True Count */}
                <div className="text-center p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                        True Count
                    </div>
                    <div
                        className={`
              text-3xl font-bold flex items-center justify-center gap-2
              ${getCountColor(trueCount)}
              ${countAnimation === 'up' ? 'count-positive' : ''}
              ${countAnimation === 'down' ? 'count-negative' : ''}
            `}
                    >
                        {trueCount >= 0 ? '+' : ''}{trueCount.toFixed(1)}
                        {getCountIcon(trueCount)}
                    </div>
                </div>

                {/* Recommended Bet */}
                <div className="text-center p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        Recommended Bet
                    </div>
                    <div className="text-3xl font-bold text-emerald-400">
                        {formatBet(recommendedBet)}
                    </div>
                </div>

                {/* Bankroll (if provided) */}
                {bankroll !== undefined && (
                    <div className="text-center p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                            Bankroll
                        </div>
                        <div className="text-3xl font-bold text-gray-300">
                            {formatBet(bankroll)}
                        </div>
                    </div>
                )}
            </div>

            {/* Count interpretation */}
            <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Edge Status:</span>
                    <span
                        className={`
              font-semibold
              ${trueCount >= 2 ? 'text-emerald-400' : trueCount <= -1 ? 'text-red-400' : 'text-gray-400'}
            `}
                    >
                        {trueCount >= 2
                            ? '🎯 Player Advantage'
                            : trueCount >= 0
                                ? '⚖️ Neutral'
                                : trueCount >= -1
                                    ? '⚠️ House Advantage'
                                    : '🚪 Consider Leaving'}
                    </span>
                </div>
            </div>
        </div>
    );
}

// Compact version for inline display
interface CompactCountProps {
    runningCount: number;
    trueCount: number;
    className?: string;
}

export function CompactCount({
    runningCount,
    trueCount,
    className = '',
}: CompactCountProps) {
    const getCountColor = (count: number) => {
        if (count >= 2) return 'text-emerald-400';
        if (count <= -2) return 'text-red-400';
        return 'text-gray-300';
    };

    return (
        <div className={`flex items-center gap-4 text-sm ${className}`}>
            <div className="flex items-center gap-1">
                <span className="text-gray-500">RC:</span>
                <span className={`font-bold ${getCountColor(runningCount)}`}>
                    {runningCount >= 0 ? '+' : ''}{runningCount}
                </span>
            </div>
            <div className="flex items-center gap-1">
                <span className="text-gray-500">TC:</span>
                <span className={`font-bold ${getCountColor(trueCount)}`}>
                    {trueCount >= 0 ? '+' : ''}{trueCount.toFixed(1)}
                </span>
            </div>
        </div>
    );
}

export default CountDisplay;
