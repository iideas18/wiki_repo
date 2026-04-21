# v2 Pipeline — Deep Analysis

## Existence Rationale
The v2 module represents the next-generation quantitative pipeline, designed for production use. While the v1 system (src/) relies entirely on LLM-based analysis, v2 introduces traditional quantitative finance methods: signal generation from raw data (no LLM), portfolio optimization (mean-variance, Black-Litterman), systematic risk management, and optimal execution modeling. It exists as a separate module to evolve independently without breaking the working v1 system.

## Design Decisions
| Decision | Choice Made | Alternatives | Rationale |
|----------|------------|-------------|-----------|
| Architecture | Pipeline stages (signals → portfolio → risk → execution) | Monolithic, event-driven | Clear separation of concerns, each stage testable independently |
| Signal model | Pure numerical [-1, +1] range | LLM-based, categorical | Deterministic, faster, backtestable without API costs |
| Portfolio optimization | Mean-variance + Black-Litterman + Risk Parity | Simple equal-weight, momentum | Industry-standard approaches for portfolio construction |
| Execution | Almgren-Chriss optimal execution | Simple market orders | Models market impact for realistic simulation |

## Current State
Mostly placeholder/interface code (~870 LOC). Defines data models (SignalResult, QuantSignals, PortfolioTarget, TradeOrder) and pipeline structure, but implementation is minimal. Ready for contributors to fill in.

## Key Data Models
- SignalResult: Individual signal with confidence [-1, +1]
- QuantSignals: Aggregated signals for a date
- PortfolioTarget: Optimization output (target weights per ticker)
- TradeOrder: Individual trade with direction, quantity, price
- ExecutionResult: Batch execution results with P&L
