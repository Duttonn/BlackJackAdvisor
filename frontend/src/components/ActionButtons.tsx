import type { ReactNode } from 'react';
import { Hand, Square, Copy, Flag, Plus } from 'lucide-react';

type Action = 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER';

interface ActionButtonsProps {
    onAction: (action: Action) => void;
    disabled?: boolean;
    canSplit?: boolean;
    canDouble?: boolean;
    canSurrender?: boolean;
    recommendedAction?: string;
    className?: string;
}

/**
 * Action buttons for blackjack gameplay
 * Shows HIT, STAND, DOUBLE, SPLIT, SURRENDER with visual feedback
 */
export function ActionButtons({
    onAction,
    disabled = false,
    canSplit = false,
    canDouble = true,
    canSurrender = true,
    recommendedAction,
    className = '',
}: ActionButtonsProps) {
    // Normalize recommended action for comparison
    const normalizedRecommended = recommendedAction?.toUpperCase();

    // Check if action is recommended
    const isRecommended = (action: Action) => {
        if (!normalizedRecommended) return false;

        // Handle variations in action names
        const actionMap: Record<string, string[]> = {
            HIT: ['HIT', 'H'],
            STAND: ['STAND', 'S'],
            DOUBLE: ['DOUBLE', 'DD', 'DH', 'DS', 'DOUBLE_DOWN'],
            SPLIT: ['SPLIT', 'SP', 'Y'],
            SURRENDER: ['SURRENDER', 'SUR', 'RS', 'N'],
        };

        return actionMap[action]?.includes(normalizedRecommended) || false;
    };

    // Action button configuration
    const actions: {
        action: Action;
        label: string;
        icon: ReactNode;
        baseClasses: string;
        canUse: boolean;
    }[] = [
            {
                action: 'HIT',
                label: 'Hit',
                icon: <Plus className="w-5 h-5" />,
                baseClasses: 'bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600',
                canUse: true,
            },
            {
                action: 'STAND',
                label: 'Stand',
                icon: <Hand className="w-5 h-5" />,
                baseClasses: 'bg-gradient-to-br from-gray-600 to-gray-700 hover:from-gray-500 hover:to-gray-600',
                canUse: true,
            },
            {
                action: 'DOUBLE',
                label: 'Double',
                icon: <Copy className="w-5 h-5" />,
                baseClasses: 'bg-gradient-to-br from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600',
                canUse: canDouble,
            },
            {
                action: 'SPLIT',
                label: 'Split',
                icon: <Square className="w-5 h-5" />,
                baseClasses: 'bg-gradient-to-br from-orange-600 to-orange-700 hover:from-orange-500 hover:to-orange-600',
                canUse: canSplit,
            },
            {
                action: 'SURRENDER',
                label: 'Surrender',
                icon: <Flag className="w-5 h-5" />,
                baseClasses: 'bg-gradient-to-br from-red-600 to-red-700 hover:from-red-500 hover:to-red-600',
                canUse: canSurrender,
            },
        ];

    return (
        <div className={`${className}`}>
            <div className="flex flex-wrap gap-3 justify-center">
                {actions.map(({ action, label, icon, baseClasses, canUse }) => {
                    const recommended = isRecommended(action);
                    const buttonDisabled = disabled || !canUse;

                    return (
                        <button
                            key={action}
                            onClick={() => onAction(action)}
                            disabled={buttonDisabled}
                            className={`
                relative flex items-center gap-2 px-6 py-3
                rounded-lg font-semibold text-white
                transition-all duration-200
                ${buttonDisabled
                                    ? 'opacity-40 cursor-not-allowed bg-gray-700'
                                    : baseClasses
                                }
                ${!buttonDisabled && 'hover:translate-y-[-2px] hover:shadow-lg active:translate-y-0'}
                ${recommended && !buttonDisabled && 'ring-2 ring-emerald-400 ring-offset-2 ring-offset-[var(--color-background)]'}
              `}
                        >
                            {icon}
                            <span className="uppercase tracking-wide text-sm">{label}</span>

                            {/* Recommended indicator */}
                            {recommended && !buttonDisabled && (
                                <span className="absolute -top-2 -right-2 px-2 py-0.5 text-xs font-bold bg-emerald-500 text-white rounded-full animate-pulse">
                                    ★
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Legend */}
            {recommendedAction && (
                <div className="mt-4 text-center text-sm text-gray-500">
                    <span className="inline-flex items-center gap-1">
                        <span className="w-3 h-3 bg-emerald-500 rounded-full" />
                        Recommended action: <span className="font-semibold text-emerald-400">{recommendedAction}</span>
                    </span>
                </div>
            )}
        </div>
    );
}

// Simplified action bar for quick actions
interface QuickActionsProps {
    onHit: () => void;
    onStand: () => void;
    disabled?: boolean;
    className?: string;
}

export function QuickActions({
    onHit,
    onStand,
    disabled = false,
    className = '',
}: QuickActionsProps) {
    return (
        <div className={`flex gap-3 ${className}`}>
            <button
                onClick={onHit}
                disabled={disabled}
                className={`
          flex-1 flex items-center justify-center gap-2 px-6 py-4
          rounded-lg font-bold text-lg text-white uppercase tracking-wider
          bg-gradient-to-br from-emerald-600 to-emerald-700
          ${disabled
                        ? 'opacity-40 cursor-not-allowed'
                        : 'hover:from-emerald-500 hover:to-emerald-600 hover:translate-y-[-2px] hover:shadow-lg active:translate-y-0'
                    }
          transition-all duration-200
        `}
            >
                <Plus className="w-6 h-6" />
                Hit
            </button>
            <button
                onClick={onStand}
                disabled={disabled}
                className={`
          flex-1 flex items-center justify-center gap-2 px-6 py-4
          rounded-lg font-bold text-lg text-white uppercase tracking-wider
          bg-gradient-to-br from-gray-600 to-gray-700
          ${disabled
                        ? 'opacity-40 cursor-not-allowed'
                        : 'hover:from-gray-500 hover:to-gray-600 hover:translate-y-[-2px] hover:shadow-lg active:translate-y-0'
                    }
          transition-all duration-200
        `}
            >
                <Hand className="w-6 h-6" />
                Stand
            </button>
        </div>
    );
}

export default ActionButtons;
