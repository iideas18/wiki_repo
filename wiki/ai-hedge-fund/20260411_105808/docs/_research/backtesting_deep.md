# Phase 1B — Backtesting Module Deep Analysis

## Existence Rationale
The backtesting module exists to validate the AI hedge fund's trading decisions against historical data. It takes the same `run_hedge_fund()` function used for live analysis and replays it over a date range, executing trades on a simulated portfolio. Without this module, users would have no way to evaluate whether the agent ensemble actually generates alpha. It's separate from the main trading logic because backtesting introduces time-series iteration, portfolio tracking, and performance metrics that don't belong in the single-shot analysis pipeline.

## Design Decisions Analysis

| Decision | Choice Made | Plausible Alternatives | Inferred Rationale |
|----------|------------|----------------------|-------------------|
| Reuse run_hedge_fund() | Backtest calls the same agent function as live mode | Separate simplified backtesting agents | Ensures backtest results match live behavior exactly |
| Daily iteration | Loop over business days (pd.date_range freq="B") | Event-driven, tick-based | Daily granularity matches the investment horizon of the agents |
| Component decomposition | Engine, Controller, Trader, Portfolio, Metrics, Output | Monolithic Backtester class | Testability — each component has focused unit tests |
| In-memory portfolio | Portfolio class tracks positions in dicts | Database-backed portfolio | Speed — no I/O during backtest loop |
| Prefetch all data | _prefetch_data() loads 1 year of data before loop | Fetch on demand per date | Avoids repeated API calls; leverages cache layer |
| SPY benchmark | Always fetches SPY for comparison | User-configurable benchmark | SPY is the most universal equity benchmark |
| Long/short support | Portfolio tracks long AND short positions separately | Long-only | Matches the agent system which can recommend short/cover |

## Algorithm Deep-Dives

### 1. Backtest Loop (BacktestEngine.run_backtest)
- **Problem**: Simulate daily trading decisions over a historical period
- **Steps**: (1) Prefetch data (2) Iterate business days (3) Get current prices (4) Run agent ensemble (5) Execute trades (6) Calculate portfolio value (7) Update metrics
- **Lookback**: Each day uses 1-month lookback for agent analysis
- **Skip conditions**: Missing price data → skip that day entirely
- **Complexity**: O(D × T × A) where D=days, T=tickers, A=agents

### 2. Trade Execution (TradeExecutor)
- **Buy**: Deduct cash, add long shares, update cost basis
- **Sell**: Remove long shares, add cash, compute realized gains
- **Short**: Increase short shares, reserve margin
- **Cover**: Remove short shares, release margin, compute P&L
- **Validation**: Cannot sell more than owned, cannot cover more than shorted

### 3. Performance Metrics (PerformanceMetricsCalculator)
- **Sharpe Ratio**: (mean_return - risk_free) / std_return × sqrt(252)
- **Sortino Ratio**: (mean_return - risk_free) / downside_std × sqrt(252)
- **Max Drawdown**: max((peak - trough) / peak) over all time
- **Requires**: At least 3 portfolio value points

### 4. Portfolio Valuation
- **Total Value**: cash + Σ(long_shares × price) - Σ(short_shares × price)
- **Exposures**: Long exposure, short exposure, gross, net, L/S ratio
- **Why separate**: Valuation is pure math; decoupled from trade logic

## Error Philosophy
- Fail-safe: Missing price data → skip day (don't crash)
- Graceful SIGINT handling in backtester.py → prints partial results
- Default to "hold" if agent returns invalid decisions

## Performance Characteristics
- **Bottleneck**: Agent LLM calls (1 call per agent per ticker per day)
- **Optimization**: Data prefetching eliminates repeated API calls
- **Memory**: O(D × T) for portfolio value history
- **Output**: Real-time table display using colorama + tabulate
