# Real-Time Blackjack Decision Engine# Real-Time Blackjack Decision Engine



[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)A professional-grade blackjack decision engine implementing perfect basic strategy with count-based deviations (Illustrious 18 and Fab 4).

[![Tests](https://img.shields.io/badge/tests-105%20passed-brightgreen.svg)](#testing)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)## Architecture



A professional-grade blackjack decision engine with Hi-Lo card counting, Illustrious 18/Fab 4 deviations, Kelly Criterion betting, and Monte Carlo simulation. Built with **Hexagonal Architecture** for clean separation of concerns.This project follows **Hexagonal Architecture** (Ports and Adapters) to isolate core domain logic from external interfaces.



## 🎯 Features```

blackjack-engine/

- **Perfect Basic Strategy** - Optimal play for every hand combination├── data/                       # JSON/Binary strategy tables

- **Hi-Lo Card Counting** - Real-time running count and true count calculation│   ├── strategies/             # Baseline CDZ/TDZ tables

- **Illustrious 18 + Fab 4** - Count-based playing deviations│   ├── deviations/             # Illustrious 18 / Fab 4 indices

- **Kelly Criterion Betting** - Optimal bet sizing with configurable risk│   └── rules/                  # Casino rule configurations

- **Exit Signal (Wonging)** - Know when to leave the table (TC < -1)├── src/

- **Live CLI Interface** - Real-time decision support for casino play│   ├── core/                   # Domain Primitives (Zero dependencies)

- **Monte Carlo Simulator** - Validate strategy with millions of hands│   ├── state/                  # Module A: State Manager

- **Research Framework** - Ablation studies and EV analysis│   ├── strategy/               # Module C: Decision Core

│   ├── betting/                # Module B: EV Engine

## 📦 Installation│   └── config/                 # Module D: Rule Adapter

├── interfaces/                 # Adapters for external systems

```bash├── tests/                      # Validation

# Clone the repository└── scripts/                    # Offline tools

git clone https://github.com/yourusername/blackjack-engine.git```

cd blackjack-engine

## Module Responsibilities

# Install dependencies

pip install -r requirements.txt### Core (`src/core/`)

- Immutable primitives: `Card`, `Hand`

# Or install as a package- Type definitions: `Rank`, `Suit`, `Action`, `HandType`

pip install -e .- Zero external dependencies



# Verify installation### State Manager (`src/state/`)

python -m pytest tests/ -q- Maintains Running Count using Hi-Lo system

```- Calculates True Count

- Tracks cards remaining in shoe

## 🎮 Quick Start: Live CLI- **FORBIDDEN**: Strategy logic



For real-time decision support at the casino:### Strategy Engine (`src/strategy/`)

- Deterministic decision function: `f(State) → Action`

```bash- Baseline strategy lookup (O(1) hash-based)

python -m interfaces.live_api- Count-based deviations (Illustrious 18, Fab 4)

```- **FORBIDDEN**: EV calculation, random numbers, bankroll access



### CLI Commands### Betting Engine (`src/betting/`)

- Maps True Count to bet size

| Command | Example | Description |- Kelly Criterion implementation

|---------|---------|-------------|- Linear EV approximation

| `new` | `new` | Start a new shoe (shuffle) |- **FORBIDDEN**: Knowledge of specific cards

| `c <cards>` | `c Ah Kd 5s` | Observe cards dealt |

| `hand <player> <dealer>` | `hand Ah,Kd 10s` | Start hand, get decision |### Config Loader (`src/config/`)

| `hit <card>` | `hit 5d` | Add card after hitting |- Loads game rules from JSON

| `bet` | `bet` | Get recommended bet size |- Dependency injection for rule-dependent components

| `status` | `status` | Show count and session stats |

| `win/lose/push <amt>` | `win 25` | Record hand result |## Quick Start

| `quit` | `quit` | Exit session |

```python

### Example Sessionfrom src.core import Card, Hand, Rank, Suit

from src.state import StateManager

```from src.strategy import StrategyEngine, RuleConfig

🃏 Blackjack Decision Engine - Live Sessionfrom src.betting import BettingEngine

============================================

# Initialize engines

> newstate = StateManager()

🔄 New shoe started. Rules: S17, 6 decksstrategy = StrategyEngine(RuleConfig())

betting = BettingEngine()

> hand Ah,7d 6s

🃏 Player: Ah,7d = 18# Observe cards dealt

   Dealer: 6sstate.observe_card(Card(Rank.FIVE, Suit.SPADES))

state.observe_card(Card(Rank.TEN, Suit.HEARTS))

   ➡️  DOUBLE

# Get current metrics

> c Kh Qd Jc 10s Kc Qh Jd 10h Kd Qsmetrics = state.get_metrics()

✓ Observed: K♥, Q♦, J♣, 10♠, K♣, Q♥, J♦, 10♥, K♦, Q♠print(f"True Count: {metrics.true_count:.2f}")

  RC: -10, TC: -1.72

# Make a decision

> hand 9h,6d 5shand = Hand.from_cards([

    Card(Rank.TEN, Suit.SPADES),

   ➡️  STAND    Card(Rank.SIX, Suit.HEARTS)

])

   ⚠️  STRATEGY ALERT: LEAVE TABLEdealer_up = Card(Rank.TEN, Suit.DIAMONDS)

       True Count -1.7 < -1.0 (Wong Out)

```action = strategy.decide(hand, dealer_up, metrics)

print(f"Recommended action: {action}")

## 📊 Research: Reproduce the Graphs

# Get bet recommendation

### 1. Ablation Study (Component Value Analysis)bet = betting.compute_bet(metrics.true_count, bankroll=1000)

print(f"Recommended bet: ${bet:.2f}")

Measures the EV contribution of each system component:```



```bash## Data Format

python research/ablation_runner.py

```### Strategy Tables (`data/strategies/`)

```json

**Expected Results:**{

| Configuration | EV % | Description |  "tables": {

|---------------|------|-------------|    "H_16:10": "HIT",     // Hard 16 vs dealer 10

| B0_S0 (Control) | -0.50% | Flat bet + Basic Strategy |    "S_18:09": "HIT",     // Soft 18 vs dealer 9

| B0_S2 | -0.28% | Flat bet + Deviations |    "P_08:10": "SPLIT"    // Pair of 8s vs dealer 10

| B1_S0 | +1.28% | Kelly betting, no deviations |  }

| B1_S2 (Full) | +1.50% | Full system |}

```

### 2. Deviation Threshold Study

### Deviations (`data/deviations/`)

Finds optimal confidence margin for deviation triggers:```json

[

```bash  {

python research/study_deviation_confidence.py    "id": "ILL_16v10",

```    "trigger": { "type": "HARD", "value": 16, "dealer": 10 },

    "rule": {

**Key Finding:** Margin 0.0 is optimal (+1.39% EV)      "threshold": 0,

      "direction": "ABOVE_OR_EQUAL",

### 3. Model Error Study (Hi-Lo Breakdown)      "action": "STAND"

    }

Tests when linear TC approximation fails:  }

]

```bash```

python research/study_model_error.py

```## Key Deviations



**Key Finding:** Hi-Lo accuracy degrades above 90% penetration (5.1× error multiplier)### Illustrious 18 (Playing Deviations)

| Hand | vs Dealer | Index | Action |

### 4. Wonging Realism Study|------|-----------|-------|--------|

| 16 | 10 | ≥ 0 | STAND |

Compares ideal vs realistic table-hopping conditions:| 15 | 10 | ≥ +4 | STAND |

| 12 | 3 | ≥ +2 | STAND |

```bash| 12 | 2 | ≥ +3 | STAND |

python research/study_wonging_realism.py| 11 | A | ≥ +1 | DOUBLE |

```| 10 | 10 | ≥ +4 | DOUBLE |

| 10 | A | ≥ +4 | DOUBLE |

**Expected Results:**| 9 | 2 | ≥ +1 | DOUBLE |

| Configuration | EV % | Description || 9 | 7 | ≥ +3 | DOUBLE |

|---------------|------|-------------|

| IDEAL | +1.00% | Perfect wonging |### Fab 4 (Surrender Deviations)

| COVERED | +0.75% | 10-hand minimum cover || Hand | vs Dealer | Index | Action |

| LATE_ENTRY | -0.03% | Mid-shoe entry penalty ||------|-----------|-------|--------|

| REALISTIC_PRO | +0.50% | Combined realistic constraints || 15 | 10 | ≥ 0 | SURRENDER |

| 15 | A | ≥ +1 | SURRENDER |

## 🏗️ Architecture| 15 | 9 | ≥ +2 | SURRENDER |

| 14 | 10 | ≥ +3 | SURRENDER |

```

blackjack-engine/## Testing

├── src/                        # Core domain logic (no I/O)

│   ├── core/                   # Primitives: Card, Hand, Action```bash

│   ├── state/                  # Hi-Lo counting state machine# Run all tests

│   ├── strategy/               # Decision engine with deviationspytest tests/

│   ├── betting/                # Kelly Criterion bet sizing

│   └── config/                 # Rule configurations# Run unit tests only

├── interfaces/                 # External adapterspytest tests/unit/

│   ├── live_api.py             # CLI for live play

│   └── simulator.py            # Monte Carlo engine# Run integration tests

├── research/                   # Analysis scriptspytest tests/integration/

│   ├── ablation_runner.py      # Component value study

│   ├── study_deviation_confidence.py# Run with coverage

│   ├── study_model_error.pypytest --cov=src tests/

│   └── study_wonging_realism.py```

├── data/                       # Strategy tables (JSON)

│   ├── strategies/             # Basic strategy lookup## Mathematical Foundation

│   └── deviations/             # Illustrious 18 / Fab 4

├── tests/                      # 105 unit + integration tests### True Count Calculation

└── scripts/                    # Utility scripts$$TC = \frac{RC}{D_r}$$

```

Where:

### Design Principles- $TC$ = True Count

- $RC$ = Running Count

- **Hexagonal Architecture** - Core logic isolated from I/O- $D_r$ = Decks Remaining (clamped to minimum 0.5)

- **Dependency Injection** - Easy testing and configuration

- **Immutable Primitives** - `Card`, `Hand` are value objects### Advantage Estimation

- **Single Responsibility** - Each module has one job$$A = (TC \times 0.005) - E_{base}$$



## 🧪 TestingWhere:

- $A$ = Player advantage (decimal)

```bash- $TC$ = True Count

# Run all tests (105 tests)- $E_{base}$ = Rule-adjusted baseline house edge

python -m pytest tests/ -v

**Critical Rule Adjustments to $E_{base}$:**

# Run with coverage| Rule Variation | Impact |

python -m pytest tests/ --cov=src --cov-report=term-missing|----------------|--------|

| Base S17 DAS | ~0.40% |

# Run specific test categories| H17 (dealer hits soft 17) | +0.22% |

python -m pytest tests/unit/           # Unit tests| 6:5 blackjack payout | +1.39% |

python -m pytest tests/integration/    # Integration tests| No DAS | +0.14% |

python -m pytest tests/validation/     # Truth table validation| No surrender | +0.08% |

```

⚠️ **WARNING**: Using hardcoded 0.5% on an H17 table will overestimate your edge!

## 📐 Mathematical Foundation

### Kelly Criterion (Half-Kelly Safety)

### True Count Calculation$$f^* = k \times \frac{A}{V}$$

$$TC = \frac{RC}{D_r}$$

Where:

Where:- $f^*$ = Fraction of bankroll to bet

- $RC$ = Running Count (Hi-Lo: +1 for 2-6, -1 for 10-A)- $k$ = Kelly fraction (default 0.5 = Half-Kelly)

- $D_r$ = Decks Remaining (clamped to minimum 0.5)- $A$ = Player advantage

- $V$ = Variance (≈ 1.26 for blackjack)

### Player Advantage

$$A = (TC \times 0.005) - E_{base}$$⚠️ **Safety Note**: Full Kelly ($k=1$) assumes perfect knowledge. With linear approximation systems, this leads to high risk of ruin. Half-Kelly ($k=0.5$) is the safe default.



Where:## License

- $A$ = Player advantage (decimal)

- $E_{base}$ = Rule-adjusted house edge (~0.40% for S17 DAS)MIT License


### Kelly Criterion Betting
$$f^* = k \times \frac{A}{V}$$

Where:
- $f^*$ = Fraction of bankroll to bet
- $k$ = Kelly fraction (0.5 = Half-Kelly for safety)
- $V$ = Variance (≈1.26 for blackjack)

### Key Thresholds

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| `kelly_fraction` | 0.5 | Half-Kelly reduces risk of ruin |
| `deviation_threshold_margin` | 0.0 | Optimal per research |
| `max_betting_penetration` | 0.85 | Hi-Lo degrades at 90%+ |
| `wong_out_threshold` | -1.0 | Exit when house edge exceeds 1% |

## 🎰 Key Deviations

### Illustrious 18 (Playing Deviations)
| Hand | vs Dealer | Index | Deviation |
|------|-----------|-------|-----------|
| 16 | 10 | ≥ 0 | STAND (normally hit) |
| 15 | 10 | ≥ +4 | STAND |
| 12 | 3 | ≥ +2 | STAND |
| 12 | 2 | ≥ +3 | STAND |
| 11 | A | ≥ +1 | DOUBLE |
| 10 | 10 | ≥ +4 | DOUBLE |
| 10 | A | ≥ +4 | DOUBLE |
| 9 | 2 | ≥ +1 | DOUBLE |
| 9 | 7 | ≥ +3 | DOUBLE |

### Fab 4 (Surrender Deviations)
| Hand | vs Dealer | Index | Deviation |
|------|-----------|-------|-----------|
| 15 | 10 | ≥ 0 | SURRENDER |
| 15 | A | ≥ +1 | SURRENDER |
| 15 | 9 | ≥ +2 | SURRENDER |
| 14 | 10 | ≥ +3 | SURRENDER |

## 📁 Configuration

### Game Rules (`src/config/`)

```python
from src.config import GameRules

rules = GameRules(
    num_decks=6,
    dealer_stands_soft_17=True,   # S17 (favorable)
    double_after_split=True,       # DAS allowed
    surrender_allowed=True,        # Late surrender
    blackjack_payout=1.5,          # 3:2 payout
    penetration=0.75               # 75% dealt before shuffle
)
```

### Betting Configuration

```python
from src.betting import BettingConfig

config = BettingConfig(
    table_min=15.0,
    table_max=500.0,
    kelly_fraction=0.5,            # Half-Kelly
    max_betting_penetration=0.85   # Stop spreading at 85%
)
```

## 🔬 Simulator Usage

```python
from interfaces.simulator import BlackjackSimulator, SimulatorConfig

# Full system simulation
config = SimulatorConfig.full_engine()
sim = BlackjackSimulator(config=config)
result = sim.run(num_hands=100_000)

print(f"EV: {result.ev_percent:+.2f}%")
print(f"Hands: {result.hands_played:,}")
print(f"Win Rate: {result.win_rate:.1%}")
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Donald Schlesinger's *Blackjack Attack* for the Illustrious 18
- Stanford Wong's work on wonging strategy
- Griffin's *Theory of Blackjack* for mathematical foundations

---

**Disclaimer:** This software is for educational purposes only. Card counting is legal but casinos may ask you to leave. Always gamble responsibly.
