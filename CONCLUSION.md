# Blackjack Decision Engine - Project Conclusion

## Executive Summary

This project implements a **production-ready real-time Blackjack Decision Engine** that provides mathematically optimal play recommendations using card counting (Hi-Lo system), count-based strategy deviations (Illustrious 18), and Kelly Criterion bet sizing.

**Final Status:** ✅ Complete with 105 passing tests

---

## Project Overview

### What It Does

The engine observes cards as they are dealt and provides:

1. **Optimal Play Decisions** - Stand, Hit, Double, Split, or Surrender based on:
   - Basic strategy lookup tables
   - Real-time true count adjustments (Illustrious 18 deviations)
   - Rule variations (S17/H17, DAS, surrender availability)

2. **Optimal Bet Sizing** - Using Half-Kelly Criterion:
   - Scales bets with player advantage
   - Protects bankroll with conservative fractional Kelly
   - Includes defensive cutoff at deep penetration

3. **Game State Tracking** - Hi-Lo card counting:
   - Running count maintenance
   - True count calculation (RC ÷ decks remaining)
   - Penetration tracking

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACES                                │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │   Simulator     │              │    Live API     │           │
│  │  (Monte Carlo)  │              │  (Real-time)    │           │
│  └────────┬────────┘              └────────┬────────┘           │
└───────────┼────────────────────────────────┼────────────────────┘
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN CORE (src/)                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │    State     │  │   Strategy   │  │   Betting    │           │
│  │   Manager    │──│    Engine    │──│    Engine    │           │
│  │  (Counting)  │  │ (Deviations) │  │   (Kelly)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Core Types & Config                  │           │
│  │     Card, Hand, Action, GameState, GameRules      │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

**Hexagonal Architecture** enforces strict module boundaries:
- `StateManager` only observes and counts (no strategy knowledge)
- `StrategyEngine` only decides actions (no counting logic)
- `BettingEngine` only sizes bets (no card awareness)

---

## Work Completed

### Phase 1: Core Engine Development

| Component | Description | Key Features |
|-----------|-------------|--------------|
| `src/core/` | Type definitions | Card, Hand, Action, Rank, Suit, GameState |
| `src/state/` | Hi-Lo counting | Running count, True count, Penetration tracking |
| `src/strategy/` | Decision engine | Basic strategy lookup, Illustrious 18 deviations |
| `src/betting/` | Bet sizing | Kelly criterion, EV estimation, Spread limits |
| `src/config/` | Rule loading | JSON-based rule configurations |

### Phase 2: Interface Layer

| Interface | Purpose | Features |
|-----------|---------|----------|
| `interfaces/simulator.py` | Monte Carlo testing | Configurable simulations, FlightRecorder logging |
| `interfaces/live_api.py` | Real-time decisions | Session management, Card observation, Recommendations |

### Phase 3: Critical Bug Fix

**Issue:** Rank enum aliasing caused JACK, QUEEN, KING to share values with lower cards.

**Impact:** -12% EV (catastrophic) → +1.5% EV (optimal)

**Solution:** Unique ordinal values for each rank with `blackjack_value` property.

### Phase R1-R4: Research & Validation

| Phase | Objective | Key Finding |
|-------|-----------|-------------|
| R1: Ablation Study | Quantify component contributions | Kelly +0.86% EV, Deviations +0.22% EV |
| R2: Confidence Study | Optimize deviation thresholds | Margin 0.0 is optimal |
| R3: Model Error Study | Identify model limits | Hi-Lo fails at >90% penetration (5.1× error) |
| R4: Defensive Cutoff | Implement risk mitigation | 85% pen limit reduces deep-shoe risk by 43% |

### Phase 5: Production Hardening

- Hardcoded optimal defaults
- Organized research scripts into `research/` directory
- Final verification: **105 tests passing**

---

## Optimal Configuration

The engine is configured optimally out-of-the-box:

```python
# These are the production defaults (no flags needed)

# Strategy: deviation_threshold_margin = 0.0
#   - Illustrious 18 indices fire at exact trigger points
#   - No additional confidence buffer (research showed 0.0 is optimal)

# Betting: kelly_fraction = 0.5
#   - Half-Kelly for bankroll protection
#   - Balances growth rate vs risk of ruin

# Betting: max_betting_penetration = 0.85
#   - Defensive cutoff at 85% penetration
#   - Forces minimum bet in deep shoes where Hi-Lo model is unreliable
```

---

## How to Use

### Installation

```bash
# Clone/navigate to project
cd BlackJack

# Install dependencies (standard library only - no external deps required)
python -m pytest tests/ -v  # Verify installation
```

### Basic Usage

```python
from src.core import Card, Hand, Rank, Suit
from src.state import StateManager
from src.strategy import StrategyEngine
from src.betting import BettingEngine

# Initialize engines
state = StateManager()
strategy = StrategyEngine()
betting = BettingEngine()

# Observe cards as they're dealt
state.observe_card(Card(Rank.FIVE, Suit.HEARTS))
state.observe_card(Card(Rank.TEN, Suit.SPADES))

# Get current metrics
metrics = state.get_metrics()
print(f"True Count: {metrics.true_count:.2f}")
print(f"Penetration: {metrics.penetration:.1%}")

# Get optimal play decision
player_hand = Hand.from_cards([
    Card(Rank.TEN, Suit.HEARTS),
    Card(Rank.SIX, Suit.DIAMONDS)
])
dealer_up = Card(Rank.SEVEN, Suit.CLUBS)

action = strategy.decide(player_hand, dealer_up, metrics)
print(f"Optimal Action: {action}")  # e.g., Action.HIT

# Get optimal bet size
bankroll = 5000.0
bet = betting.compute_bet(
    metrics.true_count, 
    bankroll, 
    penetration=metrics.penetration
)
print(f"Optimal Bet: ${bet:.2f}")
```

### Using the Live API

```python
from interfaces.live_api import LiveBlackjackAPI

# Start session
api = LiveBlackjackAPI(bankroll=10000.0)
api.start_session()

# New hand
api.new_hand()

# Observe cards
api.observe_player_card("TH")  # Ten of Hearts
api.observe_player_card("6D")  # Six of Diamonds
api.observe_dealer_card("7C")  # Seven of Clubs

# Get recommendation
rec = api.get_recommendation()
print(f"Action: {rec['action']}")
print(f"Bet: ${rec['recommended_bet']:.2f}")
print(f"True Count: {rec['true_count']:.2f}")

# End session
summary = api.end_session()
```

### Running Simulations

```python
from interfaces.simulator import BlackjackSimulator, SimulatorConfig

config = SimulatorConfig(
    num_hands=100000,
    num_decks=6,
    penetration=0.75,
    use_deviations=True,
    use_kelly_betting=True
)

simulator = BlackjackSimulator(config)
results = simulator.run()

print(f"EV: {results.ev_percent:.2f}%")
print(f"Total Wagered: ${results.total_wagered:,.0f}")
print(f"Net Profit: ${results.net_profit:,.2f}")
```

---

## Deployment Options

### Option 1: Command-Line Interface (CLI)

Create a simple CLI wrapper:

```python
# cli.py
import argparse
from interfaces.live_api import LiveBlackjackAPI

def main():
    api = LiveBlackjackAPI(bankroll=10000)
    api.start_session()
    
    while True:
        cmd = input("Command (new/card/rec/quit): ").strip().lower()
        
        if cmd == "new":
            api.new_hand()
            print("New hand started")
        elif cmd.startswith("card "):
            card = cmd.split()[1].upper()
            api.observe_card(card)
            print(f"Observed: {card}")
        elif cmd == "rec":
            rec = api.get_recommendation()
            print(f"Action: {rec['action']}, Bet: ${rec['recommended_bet']:.0f}")
        elif cmd == "quit":
            break
    
    api.end_session()

if __name__ == "__main__":
    main()
```

### Option 2: REST API (Flask/FastAPI)

```python
# api_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from interfaces.live_api import LiveBlackjackAPI

app = FastAPI()
sessions = {}

class CardInput(BaseModel):
    card: str  # e.g., "TH" for Ten of Hearts

@app.post("/session/start")
def start_session(bankroll: float = 10000):
    session_id = str(uuid.uuid4())
    sessions[session_id] = LiveBlackjackAPI(bankroll=bankroll)
    sessions[session_id].start_session()
    return {"session_id": session_id}

@app.post("/session/{session_id}/observe")
def observe_card(session_id: str, card: CardInput):
    api = sessions[session_id]
    api.observe_card(card.card)
    return {"status": "ok", "true_count": api.get_metrics().true_count}

@app.get("/session/{session_id}/recommendation")
def get_recommendation(session_id: str):
    api = sessions[session_id]
    return api.get_recommendation()
```

Run with: `uvicorn api_server:app --reload`

### Option 3: Graphical Interface (GUI)

For a desktop GUI, use **Tkinter** (built-in) or **PyQt**:

```python
# gui.py (Tkinter example structure)
import tkinter as tk
from tkinter import ttk
from interfaces.live_api import LiveBlackjackAPI

class BlackjackGUI:
    def __init__(self):
        self.api = LiveBlackjackAPI(bankroll=10000)
        self.api.start_session()
        
        self.root = tk.Tk()
        self.root.title("Blackjack Decision Engine")
        
        # Card input section
        self.card_frame = ttk.LabelFrame(self.root, text="Card Input")
        self.card_frame.pack(padx=10, pady=5)
        
        # Buttons for each card value
        for rank in ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]:
            btn = ttk.Button(
                self.card_frame, 
                text=rank,
                command=lambda r=rank: self.add_card(r)
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Display section
        self.display_frame = ttk.LabelFrame(self.root, text="Recommendation")
        self.display_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.action_label = ttk.Label(self.display_frame, text="Action: --", font=("Arial", 24))
        self.action_label.pack()
        
        self.count_label = ttk.Label(self.display_frame, text="TC: 0.00")
        self.count_label.pack()
        
        self.bet_label = ttk.Label(self.display_frame, text="Bet: $10")
        self.bet_label.pack()
        
    def add_card(self, rank):
        # Simplified: assume Hearts for demo
        self.api.observe_card(f"{rank}H")
        self.update_display()
    
    def update_display(self):
        rec = self.api.get_recommendation()
        self.action_label.config(text=f"Action: {rec['action']}")
        self.count_label.config(text=f"TC: {rec['true_count']:.2f}")
        self.bet_label.config(text=f"Bet: ${rec['recommended_bet']:.0f}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    gui = BlackjackGUI()
    gui.run()
```

### Option 4: Web Interface (HTML/JS Frontend)

Combine the FastAPI backend with a simple web frontend:

```
blackjack-web/
├── backend/
│   └── api_server.py    # FastAPI REST endpoints
├── frontend/
│   ├── index.html       # Card buttons, display area
│   ├── style.css        # Card visuals, layout
│   └── app.js           # Fetch API calls, UI updates
└── docker-compose.yml   # Container deployment
```

---

## Deployment Checklist

### Before Production Use

- [ ] **Run full test suite**: `python -m pytest tests/ -v`
- [ ] **Verify EV**: Run simulator with 100k+ hands, confirm positive EV
- [ ] **Test edge cases**: Deep penetration, extreme counts, bankroll limits
- [ ] **Configure for venue rules**: S17 vs H17, DAS, surrender, deck count

### Environment Setup

```bash
# Minimal requirements (standard library only)
Python 3.10+

# For API deployment
pip install fastapi uvicorn

# For GUI
pip install PyQt6  # or use built-in tkinter
```

### Configuration for Different Venues

```python
from src.config import GameRules

# Vegas Strip rules
vegas_rules = GameRules(
    num_decks=6,
    penetration=0.75,
    dealer_stands_soft_17=True,  # S17
    double_after_split=True,
    surrender_allowed=True,
    blackjack_pays=1.5  # 3:2
)

# Downtown Vegas (tighter rules)
downtown_rules = GameRules(
    num_decks=6,
    penetration=0.70,
    dealer_stands_soft_17=False,  # H17 - worse for player
    double_after_split=True,
    surrender_allowed=False,
    blackjack_pays=1.5
)

# Avoid 6:5 tables!
bad_rules = GameRules(
    blackjack_pays=1.2  # 6:5 - house edge too high
)
```

---

## Research Artifacts

All research data is preserved in `test_results/`:

| File Pattern | Phase | Contents |
|--------------|-------|----------|
| `ablation_*.csv` | R1 | EV by configuration (6 configs) |
| `confidence_study_*.csv` | R2 | Deviation margin analysis |
| `model_error_study_*.csv` | R3 | Hi-Lo vs Exact EoR by penetration |
| `defense_validation_*.csv` | R4 | Safe vs Unsafe betting comparison |
| `FINAL_RESEARCH_REPORT_*.md` | All | Synthesis report |

Research scripts in `research/`:
- `ablation_runner.py` - Component contribution study
- `study_confidence.py` - Deviation threshold optimization
- `study_model_error.py` - Deep shoe drift analysis
- `validate_defense.py` - Defensive cutoff validation
- `verify_theory.py` - Literature benchmark verification
- `final_report.py` - Report generator

---

## Key Technical Decisions

### Why Hi-Lo Counting?

- **Simplicity**: Only three values (+1, 0, -1)
- **Effectiveness**: 0.97 betting correlation with optimal
- **Practicality**: Easier to maintain accuracy in real-time

### Why Half-Kelly?

- **Full Kelly** maximizes growth but has high variance
- **Half-Kelly** sacrifices ~25% growth for ~50% less variance
- **Real-world**: Accounts for model uncertainty and EV estimation error

### Why 85% Penetration Cutoff?

Research (Phase R3) showed:
- At <50% penetration: 0.56% MAE (Hi-Lo tracks well)
- At >90% penetration: 2.87% MAE (5.1× worse)
- Maximum divergence: 14.65% at deep penetration

The linear Hi-Lo model becomes unreliable in deep shoes, creating "phantom edge" that leads to overbetting.

### Why Illustrious 18 Deviations?

The Illustrious 18 capture 80%+ of deviation value with minimal indices to memorize:
- 16 vs 10 (Stand at TC ≥ 0)
- 15 vs 10 (Stand at TC ≥ 4)
- 12 vs 2/3 (Stand at TC ≥ 3/2)
- Insurance (Take at TC ≥ 3)
- And 14 more...

---

## Future Enhancements

### Potential Additions

1. **Side Bet Analysis** - Lucky Ladies, 21+3 EV calculation
2. **Multi-Hand Support** - Optimal play across multiple spots
3. **Shuffle Tracking** - Advanced ace sequencing
4. **Zen/Omega II Counts** - Higher betting correlation systems
5. **Neural Network Integration** - ML-based play refinements

### Performance Optimizations

1. **Numba JIT** - Compile hot paths for simulation speed
2. **Cython** - C-extension for core counting loops
3. **Multiprocessing** - Parallel simulation runs

---

## Conclusion

This Blackjack Decision Engine represents a complete, mathematically rigorous implementation of advantage play techniques. Through systematic research and validation:

- **Quantified EV sources**: Kelly betting (+0.86%) and deviations (+0.22%)
- **Optimized configuration**: Margin 0.0, Half-Kelly, 85% pen limit
- **Documented limitations**: Model fails at >90% penetration
- **Implemented safeguards**: Defensive cutoff reduces deep-shoe risk by 43%

The engine is ready for integration into any interface - CLI, REST API, desktop GUI, or web application. All components are thoroughly tested (105 tests) and configured with research-validated optimal defaults.

**Use responsibly. Gambling involves risk. This tool is for educational and research purposes.**

---

*Generated: December 24, 2025*
*Tests: 105 passing*
*Research Phases: R1-R4 complete*
