# Research & Validation Framework: Design Document

**Version:** 1.0  
**Date:** December 24, 2025  
**Author:** Research Director (AI)  
**Status:** SPECIFICATION

---

## Executive Summary

This document outlines the transformation of the Blackjack Decision Engine from an engineering artifact into a **high-precision experimental apparatus** capable of:

1. **Ablation Studies** - Isolating marginal gain of each component
2. **Composite Weight Tuning** - Confidence thresholding and counterfactual analysis
3. **Failure & Bias Analysis** - Detecting model breakdown conditions
4. **Research Instrumentation** - Flight Recorder for hand-level forensics

The goal is to answer: **Where does the edge actually come from?**

---

## Phase R1: Strategy Decomposition Tests (Ablation Studies)

### Problem Statement

The current simulator produces a composite EV (observed: +1.5%), but we cannot attribute this to specific modules:
- How much comes from **bet sizing** (Kelly criterion)?
- How much comes from **playing deviations** (Illustrious 18)?
- How much comes from **CDZ vs TDZ** lookup precision?

### Experimental Configurations

| Config ID | Betting | Strategy | Deviations | Description | Target EV |
|-----------|---------|----------|------------|-------------|-----------|
| `B0_S0` | Flat | TDZ (Basic) | None | **Control** - Pure basic strategy | -0.40% to -0.50% |
| `B0_S1` | Flat | CDZ (Exact) | None | CDZ precision gain | -0.35% to -0.45% |
| `B0_S2` | Flat | TDZ | I18 + Fab4 | Playing deviation gain | -0.30% to -0.40% |
| `B1_S0` | Hi-Lo Kelly | TDZ | None | Bet sizing gain (no play deviation) | +0.5% to +1.0% |
| `B1_S2` | Hi-Lo Kelly | TDZ | I18 + Fab4 | **Full Engine** | +1.0% to +1.5% |
| `B1_S1` | Hi-Lo Kelly | CDZ | I18 + Fab4 | Full + CDZ (theoretical max) | +1.2% to +1.8% |

### Kelly Fraction Variants (Risk of Ruin Analysis)

| Config ID | Kelly Fraction | Description | Expected RoR |
|-----------|----------------|-------------|--------------|
| `B_K100` | 1.00 | Full Kelly | ~13% RoR |
| `B_K50` | 0.50 | Half Kelly (current default) | ~1.8% RoR |
| `B_K25` | 0.25 | Quarter Kelly | ~0.1% RoR |

### Implementation: ExperimentConfig Dataclass

```python
@dataclass
class ExperimentConfig:
    """Configuration for ablation study experiments."""
    
    # Identification
    config_id: str                      # e.g., "B0_S0", "B1_S2"
    description: str
    
    # Betting Configuration
    use_counting: bool = False          # Whether to use Hi-Lo counting for bets
    kelly_fraction: float = 0.0         # 0 = flat betting, 0.5 = half-kelly
    flat_bet_units: float = 1.0         # Units for flat betting
    
    # Strategy Configuration  
    strategy_type: str = "TDZ"          # "TDZ" (Total-Dependent) or "CDZ" (Composition-Dependent)
    use_deviations: bool = False        # Whether to apply I18/Fab4 deviations
    deviation_set: str = "I18_FAB4"     # Which deviation set to use
    
    # Deviation Tuning (Phase R2)
    deviation_margin: float = 0.0       # Extra TC margin before deviating (confidence threshold)
    
    # Logging
    enable_counterfactual: bool = False # Log what basic strategy would have done
    enable_flight_recorder: bool = False # Full JSON hand traces
    
    @classmethod
    def control(cls) -> 'ExperimentConfig':
        """B0_S0: Flat bet + Basic Strategy (Control)."""
        return cls(
            config_id="B0_S0",
            description="Control: Flat Bet + Basic Strategy (TDZ)",
            use_counting=False,
            kelly_fraction=0.0,
            strategy_type="TDZ",
            use_deviations=False
        )
    
    @classmethod
    def full_engine(cls) -> 'ExperimentConfig':
        """B1_S2: Full counting + deviations."""
        return cls(
            config_id="B1_S2",
            description="Full Engine: Hi-Lo Kelly + I18/Fab4",
            use_counting=True,
            kelly_fraction=0.5,
            strategy_type="TDZ",
            use_deviations=True
        )
```

### Simulator Modifications

The `BlackjackSimulator` class will accept an `ExperimentConfig` and route decisions accordingly:

```python
class BlackjackSimulator:
    def __init__(
        self,
        rules: GameRules,
        experiment: ExperimentConfig,  # NEW: Experiment configuration
        seed: Optional[int] = None
    ):
        self.experiment = experiment
        
        # Configure betting engine based on experiment
        if experiment.use_counting:
            self.betting_engine = BettingEngine(
                kelly_fraction=experiment.kelly_fraction
            )
        else:
            self.betting_engine = FlatBettingEngine(
                bet_units=experiment.flat_bet_units
            )
        
        # Configure strategy engine based on experiment
        self.strategy_engine = StrategyEngine(
            rule_config=...,
            use_deviations=experiment.use_deviations,
            deviation_margin=experiment.deviation_margin
        )
```

---

## Phase R2: Composite Weight Tuning

### 2.1 Confidence Thresholding

**Problem:** Deviations fire at exact index values (e.g., STAND 16v10 at TC ≥ 0), but index values have uncertainty. A TC of +0.1 is not meaningfully different from -0.1.

**Solution:** Add a **deviation margin** parameter that requires extra TC confidence:

```python
# Current behavior (deviation_margin = 0)
if true_count >= index_threshold:
    apply_deviation()

# With margin (deviation_margin = 1.0)
if true_count >= index_threshold + deviation_margin:
    apply_deviation()
```

**Experiment:** Run simulations with margin = {0.0, 0.5, 1.0, 2.0} to find optimal threshold.

### 2.2 Counterfactual Logging

**Problem:** We can't measure if a deviation *helped* without knowing what would have happened otherwise.

**Solution:** For every hand where a deviation fires, log:
1. What basic strategy would have recommended
2. What the deviation recommended
3. The actual outcome
4. The counterfactual outcome (simulated)

```python
@dataclass
class CounterfactualRecord:
    """Records what-if analysis for deviation decisions."""
    hand_id: int
    true_count: float
    
    # Situation
    player_hand: str          # e.g., "16 Hard"
    dealer_up: int
    
    # Decisions
    basic_strategy_action: Action
    deviation_action: Action
    action_taken: Action
    
    # Outcomes
    actual_outcome: float     # What happened
    deviation_fired: bool     # Did we deviate?
    
    # Attribution
    ev_delta: float           # Estimated EV difference
```

**Analysis Output:**
```
DEVIATION PERFORMANCE REPORT
============================
I18_16v10 (STAND at TC>=0):
  Times Fired: 1,234
  Actual Avg Outcome: +$2.34/hand
  Basic Strategy Counterfactual: -$1.56/hand
  Deviation Value: +$3.90/decision

I18_15v10 (STAND at TC>=+4):
  Times Fired: 342
  Actual Avg Outcome: +$0.89/hand
  Basic Strategy Counterfactual: +$0.45/hand
  Deviation Value: +$0.44/decision
```

---

## Phase R3: Failure & Bias Analysis

### 3.1 Deep Shoe Nonlinearity

**Hypothesis:** The linear EoR model (Edge = TC × 0.5% - baseline) breaks down at deep penetration (>85%) because:
1. Card removal effects become nonlinear
2. True Count becomes unstable (small denominator)
3. Extreme compositions have different EoR slopes

**Experiment Design:**
```python
@dataclass  
class PenetrationBucket:
    """Track performance by penetration depth."""
    penetration_range: Tuple[float, float]  # e.g., (0.75, 0.85)
    hands_played: int
    total_wagered: float
    net_result: float
    predicted_ev: float  # Based on linear model
    actual_ev: float     # Observed
    model_error: float   # predicted - actual
```

**Expected Findings:**
| Penetration | Model Prediction | Actual EV | Error |
|-------------|------------------|-----------|-------|
| 0.00-0.25 | +0.5% | +0.4% | -0.1% |
| 0.25-0.50 | +0.8% | +0.7% | -0.1% |
| 0.50-0.75 | +1.2% | +1.1% | -0.1% |
| 0.75-0.85 | +1.8% | +1.4% | **-0.4%** |
| 0.85+ | +2.5% | +1.2% | **-1.3%** |

### 3.2 Phantom Edge Detection

**Problem:** The engine may predict +EV in situations where true combinatorial probability is negative (model overconfidence).

**Detection Method:**
1. At high TC (>+5), log exact shoe composition
2. Calculate **exact** player advantage using combinatorial analysis
3. Compare to linear model prediction
4. Flag "phantom edge" when:
   - Linear model predicts +EV
   - Combinatorial analysis shows -EV

```python
@dataclass
class PhantomEdgeRecord:
    """Records potential model overconfidence."""
    hand_id: int
    true_count: float
    
    # Shoe composition
    cards_remaining: int
    tens_remaining: int
    aces_remaining: int
    low_cards_remaining: int
    
    # Model predictions
    linear_model_edge: float
    
    # Flags
    is_phantom: bool  # True if combinatorial < 0 but linear > 0
    confidence_interval: Tuple[float, float]
```

---

## Phase R4: Research Instrumentation (Flight Recorder)

### Design Goals

The current CSV logging captures aggregate statistics but lacks **hand-level forensics**. We need a "Flight Recorder" that captures:

1. **Shoe State** - Exact card composition at decision time
2. **Decision Context** - Why we made each decision (baseline, deviation, TC)
3. **Outcome Attribution** - Which decisions contributed to P&L

### JSON Hand Trace Format

```json
{
  "session_id": "sim_20251224_123456",
  "experiment_config": "B1_S2",
  "game_rules": {
    "num_decks": 6,
    "dealer_stands_soft_17": true,
    "double_after_split": true,
    "surrender_allowed": true
  },
  "hands": [
    {
      "hand_id": 1,
      "timestamp_ms": 1703419200000,
      
      "shoe_state": {
        "cards_dealt": 47,
        "cards_remaining": 265,
        "penetration": 0.151,
        "running_count": 3,
        "true_count": 0.59,
        "composition": {
          "2": 22, "3": 21, "4": 20, "5": 19, "6": 23,
          "7": 24, "8": 23, "9": 24, "T": 89, "A": 20
        }
      },
      
      "deal": {
        "player_cards": ["8♠", "8♥"],
        "dealer_up": "T♦",
        "player_total": 16,
        "player_hand_type": "PAIR"
      },
      
      "decision_trace": [
        {
          "step": 1,
          "hand_state": "8,8 vs T",
          "true_count_at_decision": 0.59,
          "baseline_action": "SPLIT",
          "deviation_check": {
            "applicable_deviations": [],
            "deviation_fired": false
          },
          "action_taken": "SPLIT",
          "decision_reason": "BASELINE"
        }
      ],
      
      "betting": {
        "true_count_at_bet": 0.59,
        "kelly_optimal_bet": 15.50,
        "actual_bet": 15.50,
        "bet_reason": "KELLY_HALF"
      },
      
      "outcome": {
        "final_player_total": 20,
        "final_dealer_total": 17,
        "result": "WIN",
        "payout": 31.00,
        "net_profit": 15.50
      },
      
      "counterfactual": {
        "basic_strategy_action": "SPLIT",
        "would_have_differed": false,
        "estimated_basic_outcome": null
      },
      
      "attribution": {
        "ev_from_bet_sizing": 0.08,
        "ev_from_play_deviation": 0.00,
        "ev_from_cdz_precision": 0.00
      }
    }
  ],
  
  "session_summary": {
    "total_hands": 50000,
    "total_wagered": 1137881.58,
    "net_profit": 17110.16,
    "ev_percent": 1.5037,
    "deviations_fired": {
      "I18_16v10": 1234,
      "I18_15v10": 342,
      "FAB4_15v10": 567
    }
  }
}
```

### Implementation: FlightRecorder Class

```python
@dataclass
class ShoeState:
    """Snapshot of shoe composition at a point in time."""
    cards_dealt: int
    cards_remaining: int
    penetration: float
    running_count: int
    true_count: float
    composition: Dict[str, int]  # rank -> count remaining
    
    @classmethod
    def capture(cls, state_manager: StateManager) -> 'ShoeState':
        """Capture current shoe state from StateManager."""
        # Implementation: Query observed cards and compute remaining
        ...


@dataclass
class DecisionStep:
    """Single decision point in a hand."""
    step: int
    hand_state: str
    true_count_at_decision: float
    baseline_action: Action
    deviation_check: Dict[str, Any]
    action_taken: Action
    decision_reason: str  # "BASELINE", "DEVIATION_I18_16v10", etc.


@dataclass
class HandTrace:
    """Complete trace of a single hand."""
    hand_id: int
    shoe_state: ShoeState
    deal: Dict[str, Any]
    decision_trace: List[DecisionStep]
    betting: Dict[str, Any]
    outcome: Dict[str, Any]
    counterfactual: Optional[Dict[str, Any]]
    attribution: Dict[str, float]


class FlightRecorder:
    """
    High-fidelity hand trace recorder for research analysis.
    
    Captures every decision point with full context for
    post-hoc analysis and ablation attribution.
    """
    
    def __init__(self, session_id: str, experiment_config: ExperimentConfig):
        self.session_id = session_id
        self.experiment_config = experiment_config
        self.traces: List[HandTrace] = []
        self._current_hand: Optional[HandTrace] = None
    
    def start_hand(self, hand_id: int, shoe_state: ShoeState):
        """Begin recording a new hand."""
        self._current_hand = HandTrace(
            hand_id=hand_id,
            shoe_state=shoe_state,
            deal={},
            decision_trace=[],
            betting={},
            outcome={},
            counterfactual=None,
            attribution={}
        )
    
    def record_deal(self, player_cards: List[Card], dealer_up: Card):
        """Record the initial deal."""
        ...
    
    def record_decision(
        self,
        hand_state: str,
        true_count: float,
        baseline_action: Action,
        action_taken: Action,
        deviation_info: Optional[Dict] = None
    ):
        """Record a decision point."""
        ...
    
    def record_outcome(self, result: str, payout: float, net: float):
        """Record hand outcome."""
        ...
    
    def finalize_hand(self):
        """Finalize and store the current hand trace."""
        if self._current_hand:
            self.traces.append(self._current_hand)
            self._current_hand = None
    
    def export_json(self, filepath: str):
        """Export all traces to JSON file."""
        ...
    
    def export_parquet(self, filepath: str):
        """Export to Parquet for large-scale analysis."""
        ...
```

---

## Simulator Modification Summary

### Files to Modify

| File | Changes |
|------|---------|
| `interfaces/simulator.py` | Add `ExperimentConfig` support, integrate `FlightRecorder` |
| `src/strategy/engine.py` | Add `deviation_margin` parameter, counterfactual tracking |
| `src/betting/engine.py` | Add `FlatBettingEngine` for control experiments |

### Files to Create

| File | Purpose |
|------|---------|
| `research/config.py` | `ExperimentConfig` dataclass and presets |
| `research/flight_recorder.py` | `FlightRecorder`, `HandTrace`, `ShoeState` classes |
| `research/analysis.py` | Post-hoc analysis tools for JSON traces |
| `research/ablation_runner.py` | Batch runner for ablation experiments |
| `scripts/run_ablation.py` | CLI for running ablation studies |

### New CLI Interface

```bash
# Run single experiment
python -m research.ablation_runner --config B0_S0 --hands 100000 --seed 42

# Run full ablation battery
python -m research.ablation_runner --all --hands 100000 --seeds 42,43,44,45,46

# Analyze results
python -m research.analysis --input results/ablation_*.json --output report.md
```

---

## Implementation Priority

### Phase 1: Core Infrastructure (Week 1)
1. Create `research/config.py` with `ExperimentConfig`
2. Create `research/flight_recorder.py` with JSON trace format
3. Modify `BlackjackSimulator` to accept experiment configs

### Phase 2: Ablation Support (Week 2)
1. Implement `FlatBettingEngine` for control experiments
2. Add `use_deviations` flag to `StrategyEngine`
3. Create `ablation_runner.py` batch executor

### Phase 3: Advanced Analysis (Week 3)
1. Implement counterfactual logging
2. Add penetration bucket tracking
3. Create analysis/reporting tools

### Phase 4: Validation (Week 4)
1. Run full ablation battery
2. Generate attribution report
3. Identify phantom edge scenarios

---

## Success Criteria

| Metric | Target |
|--------|--------|
| B0_S0 (Control) EV | -0.40% to -0.50% |
| Deviation Attribution | Quantified ±0.05% |
| Bet Sizing Attribution | Quantified ±0.10% |
| Phantom Edge Detection | <1% false positive rate |
| Flight Recorder Overhead | <5% runtime increase |

---

## Appendix: Theoretical EV Attribution

Based on published research and simulation studies:

| Component | Expected EV Contribution |
|-----------|-------------------------|
| Basic Strategy (6D S17 DAS) | -0.40% |
| Hi-Lo Bet Spread (1-12) | +0.80% to +1.20% |
| Illustrious 18 | +0.05% to +0.10% |
| Fab 4 Surrenders | +0.02% to +0.05% |
| CDZ vs TDZ | +0.01% to +0.03% |
| **Total (Full Engine)** | **+0.48% to +0.98%** |

Note: Our observed +1.5% EV is higher than theoretical, suggesting either:
1. Favorable variance (50k hands is still noisy)
2. Aggressive bet sizing (Half-Kelly with high spread)
3. Model needs recalibration

The ablation studies will resolve this discrepancy.
