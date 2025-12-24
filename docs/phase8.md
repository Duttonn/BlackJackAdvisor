# Phase 8: Frontend Setup (React + Tailwind)

## Context from Previous Phases

We have built a **Real-Time Blackjack Decision Engine** with the following architecture:

### Backend (Python - Complete)
- **Core Engine** (`src/`): Hi-Lo counting, Illustrious 18/Fab 4 deviations, Half-Kelly betting
- **FastAPI Web API** (`src/web/`): REST endpoints at `http://localhost:8000`
- **Research-Validated Defaults**:
  - `kelly_fraction: 0.5` (Half-Kelly for safety)
  - `deviation_threshold_margin: 0.0` (optimal per research)
  - `max_betting_penetration: 0.85` (Hi-Lo degrades at 90%+)
  - `wong_out_threshold: -1.0` (exit signal when TC < -1)

### API Endpoints Available
| Endpoint | Method | Mode | Description |
|----------|--------|------|-------------|
| `/` | GET | - | API info |
| `/health` | GET | - | Health check |
| `/api/session/start` | POST | - | `{mode: "AUTO"\|"MANUAL", bankroll: float}` → `{session_id, mode, status}` |
| `/api/session/{id}` | GET | - | Session status |
| `/api/session/{id}` | DELETE | - | End session |
| `/api/session/{id}/shuffle` | POST | - | Reset shoe, count → 0 |
| `/api/session/{id}/deal` | POST | AUTO | Deal hand → `{player_cards, dealer_card, true_count, recommended_bet}` |
| `/api/session/{id}/action` | POST | AUTO | `{action: "HIT"\|"STAND"\|...}` → `{is_correct, correct_action, outcome}` |
| `/api/session/{id}/input` | POST | MANUAL | `{cards: ["Ah", "Kd"]}` → `{running_count, true_count, recommended_bet}` |
| `/api/session/{id}/decision` | POST | MANUAL | `{player_cards, dealer_card}` → `{recommended_action, should_exit, exit_reason}` |

### Key Feature: Exit Signal (Wong Out)
When `true_count < -1.0` AND `hands_played_this_shoe > 0`, the API returns:
```json
{
  "should_exit": true,
  "exit_reason": "True Count -1.6 < -1.0 (Wong Out)"
}
```
The frontend should display a **bold warning** when this triggers.

### Game Modes
1. **AUTO (Training)**: Engine deals from simulated shoe. User practices decisions, gets feedback on correctness.
2. **MANUAL (Shadowing)**: User inputs cards from real casino game. Engine provides real-time count and recommendations.

---

## Your Task

**Your Role:** Senior Frontend Engineer.
**Stack:** React (Vite), TypeScript, Tailwind CSS, Axios.
**Aesthetic:** "Rainbet Style" (Dark mode, Slate grays, Emerald greens, clean typography).

### Task 1: Initialize Project
1. Create a React + TypeScript project using Vite in `frontend/`.
2. Configure **Tailwind CSS** for styling.
3. Install `axios` for API requests and `lucide-react` for icons.

### Task 2: Implement API Client (`frontend/src/lib/api.ts`)
Create a strongly-typed wrapper for our FastAPI endpoints.

**Base URL:** `http://localhost:8000`

**Types to Define:**
```typescript
interface StartSessionRequest {
  mode: 'AUTO' | 'MANUAL';
  bankroll: number;
}

interface StartSessionResponse {
  session_id: string;
  mode: string;
  status: string;
  bankroll: number;
}

interface DealResponse {
  player_cards: string[];
  player_total: number;
  dealer_card: string;
  running_count: number;
  true_count: number;
  recommended_bet: number;
  is_blackjack: boolean;
}

interface ActionRequest {
  action: 'HIT' | 'STAND' | 'DOUBLE' | 'SPLIT' | 'SURRENDER';
}

interface ActionResponse {
  action_taken: string;
  correct_action: string;
  is_correct: boolean;
  player_total: number;
  new_card?: string;
  new_total?: number;
  is_bust?: boolean;
  outcome?: 'WIN' | 'LOSS' | 'PUSH' | 'BUST' | 'SURRENDER';
  dealer_total?: number;
  should_exit: boolean;
  exit_reason?: string;
}

interface InputCardsRequest {
  cards: string[];
}

interface InputCardsResponse {
  cards_observed: string[];
  running_count: number;
  true_count: number;
  decks_remaining: number;
  penetration: number;
  recommended_bet: number;
}

interface DecisionRequest {
  player_cards: string[];
  dealer_card: string;
}

interface DecisionResponse {
  player_cards: string[];
  player_total: number;
  dealer_card: string;
  recommended_action: string;
  running_count: number;
  true_count: number;
  should_exit: boolean;
  exit_reason?: string;
  recommended_bet: number;
}

interface SessionStatus {
  session_id: string;
  mode: string;
  hand_in_progress: boolean;
  running_count: number;
  true_count: number;
  recommended_bet: number;
}
```

**Functions:**
- `startSession(mode: 'AUTO' | 'MANUAL', bankroll: number): Promise<StartSessionResponse>`
- `getSessionStatus(sessionId: string): Promise<SessionStatus>`
- `deleteSession(sessionId: string): Promise<void>`
- `shuffleDeck(sessionId: string): Promise<{status: string, running_count: number, true_count: number}>`
- `dealHand(sessionId: string): Promise<DealResponse>` (AUTO mode)
- `sendAction(sessionId: string, action: string): Promise<ActionResponse>` (AUTO mode)
- `inputCards(sessionId: string, cards: string[]): Promise<InputCardsResponse>` (MANUAL mode)
- `getDecision(sessionId: string, playerCards: string[], dealerCard: string): Promise<DecisionResponse>` (MANUAL mode)

### Task 3: Global State (`frontend/src/context/GameContext.tsx`)
Create a React Context to manage the active session.

**State:**
```typescript
interface GameState {
  sessionId: string | null;
  gameMode: 'AUTO' | 'MANUAL' | null;
  bankroll: number;
  runningCount: number;
  trueCount: number;
  recommendedBet: number;
  handsPlayed: number;
  correctDecisions: number;
  shouldExit: boolean;
  exitReason: string | null;
}
```

**Actions:**
- `startGame(mode, bankroll)` - Creates session, stores ID
- `updateStats(rc, tc, bet)` - Updates count display
- `recordDecision(isCorrect)` - Tracks training accuracy
- `triggerExit(reason)` - Sets exit warning
- `resetGame()` - Clears session

**Hook:** `useGame()` to access state and actions from any component.

### Task 4: Design System Tokens
Create `frontend/src/styles/tokens.ts` with Rainbet-inspired colors:
```typescript
export const colors = {
  background: '#0f1419',      // Near black
  surface: '#1a1f26',         // Dark slate
  surfaceHover: '#242b35',    // Lighter slate
  border: '#2d3748',          // Subtle border
  text: '#e2e8f0',            // Light gray text
  textMuted: '#718096',       // Muted text
  primary: '#10b981',         // Emerald green (positive)
  primaryHover: '#059669',    // Darker emerald
  danger: '#ef4444',          // Red (negative/exit warning)
  warning: '#f59e0b',         // Amber (caution)
  accent: '#6366f1',          // Indigo (secondary actions)
};
```

---

## Constraints

1. **CORS**: Backend CORS is already configured to allow all origins (`allow_origins=["*"]`).

2. **Card Notation**: API responses use format like `"A♥"`, `"K♦"`, `"T♣"`, `"5♠"`. Handle display accordingly.

3. **Error Handling**: API client should handle network errors gracefully and display user-friendly messages.

---

## File Structure (Expected)

```
frontend/
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css              # Tailwind imports
│   ├── lib/
│   │   └── api.ts             # API client
│   ├── context/
│   │   └── GameContext.tsx    # Global state
│   ├── styles/
│   │   └── tokens.ts          # Design tokens
│   ├── components/
│   │   ├── Card.tsx           # Playing card display
│   │   ├── CountDisplay.tsx   # RC/TC display
│   │   ├── ActionButtons.tsx  # HIT/STAND/DOUBLE/etc
│   │   └── ExitWarning.tsx    # Wong out alert
│   └── pages/
│       ├── Home.tsx           # Mode selection
│       ├── Training.tsx       # AUTO mode UI
│       └── Shadowing.tsx      # MANUAL mode UI
```

---

## Success Criteria

- [ ] Vite + React + TypeScript project builds without errors
- [ ] Tailwind CSS is configured and working
- [ ] API client can connect to `http://localhost:8000`
- [ ] GameContext provides session state to components
- [ ] Design tokens match Rainbet aesthetic

**Go.**
