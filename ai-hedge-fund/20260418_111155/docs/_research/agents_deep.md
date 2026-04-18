
# AI Hedge Fund - Comprehensive Agent Architecture Research Report

## Executive Summary

The AI Hedge Fund is a sophisticated multi-agent investment decision system powered by LangGraph, featuring 22 AI agents representing legendary investors and analytical approaches. The system orchestrates signals from diverse investing philosophies through a graph-based workflow that combines fundamental analysis, technical analysis, sentiment analysis, and risk management into unified portfolio decisions.

---

## 1. System Architecture Overview

### 1.1 Graph Structure

**Location:** `/src/graph/__init__.py`, `/src/main.py`

The system implements a **Linear Ensemble Architecture** using LangGraph's StateGraph:

```
START_NODE 
    ↓
[All Selected Analyst Agents] (parallel execution capable)
    ↓
RISK_MANAGEMENT_AGENT (gates position sizing)
    ↓
PORTFOLIO_MANAGER (generates final trading decisions)
    ↓
END
```

**Key Graph Nodes:**
- **Entry**: `start_node` - Initializes with user inputs (tickers, dates, portfolio)
- **Analysis Layer**: 19 specialist agents (see agents catalog below)
- **Risk Layer**: `risk_management_agent` - Volatility/correlation-adjusted position limits
- **Execution Layer**: `portfolio_manager` - Converts signals to trading actions

### 1.2 Shared State (AgentState)

**Location:** `/src/graph/state.py`

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]  # Accumulating messages
    data: Annotated[dict[str, any], merge_dicts]             # Financial data & signals
    metadata: Annotated[dict[str, any], merge_dicts]         # Config (show_reasoning, model)
```

**State Evolution:**
- Each agent adds a HumanMessage with its JSON analysis
- `data["analyst_signals"][agent_id]` stores: `{ticker: {signal, confidence, reasoning}}`
- `data["current_prices"]` updated by risk manager
- `data["portfolio"]` tracks positions, cash, margin usage

---

## 2. Agent Catalog

All agents follow the pattern:
1. **Fetch financial data** (metrics, line items, prices, news, insider trades)
2. **Run domain-specific analysis** (sub-analyses with scoring)
3. **Generate output signal** (bullish/bearish/neutral + confidence + reasoning)
4. **Return via HumanMessage** for graph persistence

### 2.1 Value Investing Agents

#### **Ben Graham Agent** (`ben_graham_agent`)
- **File:** `/src/agents/ben_graham.py`
- **Philosophy:** The Father of Value Investing - Margin of Safety, undervalued securities, strong balance sheets
- **Analysis Methods:**
  - `analyze_earnings_stability()`: 10-year EPS stability, positive earnings consistency
  - `analyze_financial_strength()`: Current ratio ≥2.0, debt ratio <0.5, dividend history
  - `analyze_valuation_graham()`: Net-Net Check (NCAV > Market Cap), Graham Number calculation
- **Financial Data Analyzed:**
  - Earnings per share, revenue, net income, book value
  - Total assets, liabilities, current assets/liabilities
  - Dividends, outstanding shares, market cap
- **Signals Produced:**
  - Bullish (score ≥ 70% of max 15 points)
  - Bearish (score ≤ 30%)
  - Neutral (otherwise)
- **State Interaction:**
  - Stores signals in `state["data"]["analyst_signals"]["ben_graham_agent"][ticker]`
  - Uses API key from state metadata

#### **Warren Buffett Agent** (`warren_buffett_agent`)
- **File:** `/src/agents/warren_buffett.py` (856 lines)
- **Philosophy:** Oracle of Omaha - Competitive advantages (moats), long-term ownership, quality businesses
- **Analysis Methods:** (from LLM-driven scoring)
  - Moat strength assessment
  - Free cash flow consistency
  - Management quality evaluation
  - Long-term growth potential
  - Valuation with margin of safety
- **Key Metrics:**
  - Revenue trends, FCF, operating margins
  - Return on equity, debt levels
  - Dividend and buyback history
- **System Prompt Focus:**
  - "Quality businesses with durable competitive advantages"
  - "Long-term value creation through reinvestment"
  - "Avoid overpaying even for quality"

#### **Charlie Munger Agent** (`charlie_munger_agent`)
- **File:** `/src/agents/charlie_munger.py` (856 lines - largest agent)
- **Philosophy:** The Rational Thinker - Rationality, value + quality, psychology, multidisciplinary thinking
- **Analysis Methods:** 
  - Business model clarity evaluation
  - Management quality assessment
  - Market position strength
  - Financial stability checks
  - Psychological/behavioral factors
- **Rationale:** Combines value investing discipline with insights into cognitive biases and business quality
- **Signals:** Bullish/bearish/neutral with 0-100 confidence

#### **Aswath Damodaran Agent** (`aswath_damodaran_agent`)
- **File:** `/src/agents/aswath_damodaran.py`
- **Philosophy:** Dean of Valuation - Rigorous DCF, intrinsic value, risk assessment, academic precision
- **Analysis Methods:**
  - `analyze_growth_and_reinvestment()`: 5-year revenue/FCFF trends, capex efficiency
  - `analyze_risk_profile()`: Cost of equity via CAPM (risk-free + β·ERP)
  - `calculate_intrinsic_value_dcf()`: FCFF-to-Firm DCF valuation
  - `analyze_relative_valuation()`: PE vs. sector median cross-check
- **Financial Data:**
  - FCF, EBIT, interest expense, capex, D&A
  - Outstanding shares, net income, total debt
  - Market cap, financial metrics (growth rates)
- **Decision Rules:**
  - Bullish if margin of safety ≥ 25%
  - Bearish if margin of safety ≤ -25%
  - Neutral otherwise
- **System Prompt:** Emphasizes academic rigor, sensitivity analysis, WACC calculations

---

### 2.2 Growth & Disruptive Technology Agents

#### **Cathie Wood Agent** (`cathie_wood_agent`)
- **File:** `/src/agents/cathie_wood.py`
- **Philosophy:** Queen of Growth - Disruptive innovation, TAM expansion, high-volatility tolerance
- **Analysis Methods:**
  - `analyze_disruptive_potential()`: Tech sector positioning, innovation metrics
  - `analyze_innovation_growth()`: R&D intensity, margin expansion potential
  - `analyze_cathie_wood_valuation()`: High-growth scenario DCF (accepts premium valuations)
- **Financial Data:**
  - Revenue, gross/operating margins, debt-to-equity
  - FCF, R&D spending, capex
  - Outstanding shares, market cap
- **Signals:** Bullish on high-growth, high-volatility names; accepts 2x+ revenue multiples for disruptors
- **Key Phrase:** "Willing to endure short-term volatility for long-term gains"

#### **Growth Analyst Agent** (`growth_analyst_agent`)
- **File:** `/src/agents/growth_agent.py`
- **Philosophy:** Growth Specialist - Historical growth trends, PEG ratio, margin expansion, insider conviction
- **Analysis Methods:**
  - `analyze_growth_trends()`: Revenue/EPS/FCF growth slopes
  - `analyze_valuation()`: PEG ratio <1.0 (good value), price-to-sales <2.0
  - `analyze_margin_trends()`: Gross/operating/net margin expansion
  - `analyze_insider_conviction()`: Net buy/sell flow ratio
  - `check_financial_health()`: Debt-to-equity, current ratio
- **Weights:** Growth 40%, Valuation 25%, Margins 15%, Insider 10%, Health 10%
- **Scoring:** 0.6+ weighted score = bullish, <0.4 = bearish

---

### 2.3 Contrarian & Deep-Value Agents

#### **Michael Burry Agent** (`michael_burry_agent`)
- **File:** `/src/agents/michael_burry.py`
- **Philosophy:** Big Short Contrarian - Deep value, short opportunities, market inefficiencies, tail hedges
- **Analysis Methods:**
  - `_analyze_value()`: Book-to-market, enterprise value metrics, margin of safety
  - `_analyze_balance_sheet()`: Debt/equity leverage, liquidity
  - `_analyze_insider_activity()`: Heavy insider buying (contrarian signal)
  - `_analyze_contrarian_sentiment()`: News sentiment (inverse correlation)
- **Data Sources:**
  - FCF, net income, total debt, cash
  - Total assets/liabilities, outstanding shares
  - Insider trades (1-year lookback)
  - Company news (1-year lookback, limit 250)
  - Market cap
- **Contrarian Twist:** Bullish on heavy insider buying despite negative sentiment

#### **Nassim Taleb Agent** (`nassim_taleb_agent`)
- **File:** `/src/agents/nassim_taleb.py` (761 lines)
- **Philosophy:** Black Swan Analyst - Tail risk, antifragility, convexity, barbell strategy
- **Analysis Methods (7 dimensions):**
  - `analyze_tail_risk()`: VaR, extreme drawdowns, left-tail exposure
  - `analyze_antifragility()`: Companies that improve in crises (stress-test metrics)
  - `analyze_convexity()`: Asymmetric payoff structures (limited downside, unlimited upside)
  - `analyze_fragility()`: Vulnerability to market shocks
  - `analyze_skin_in_the_game()`: Insider ownership % (alignment signal)
  - `analyze_volatility_regime()`: Vol clusters, GARCH effects
  - `analyze_black_swan_sentinel()`: News patterns suggesting systemic risk
- **Unique Signals:**
  - **Via Negativa:** Avoiding fragile businesses
  - **Barbell Strategy:** Small tail-hedge positions + core holdings
  - **Convexity Score:** Rewards high upside with limited downside
- **System Prompt:** "Tail risk, antifragility, asymmetric payoffs... seeks convex positions"

---

### 2.4 Tactical/Activist Agents

#### **Bill Ackman Agent** (`bill_ackman_agent`)
- **File:** `/src/agents/bill_ackman.py`
- **Philosophy:** Activist Investor - Quality + activism potential, operational leverage, value unlocking
- **Analysis Methods:**
  - `analyze_business_quality()`: Revenue growth, FCF, operating margins, ROE
  - `analyze_financial_discipline()`: Multi-period debt ratios, capital allocation
  - `analyze_activism_potential()`: Revenue growth + low margins → activism upside
  - `analyze_valuation()`: Basic DCF with margin of safety >30%
- **Financial Data:**
  - Revenue, operating margin, debt-to-equity, FCF
  - Total assets/liabilities, dividends, outstanding shares
  - Market cap
- **Activism Score:** Bullish on revenue growth + low margins → opportunity for operational improvements
- **Total Score Max:** 20 points (5 from each sub-analysis)

#### **Stanley Druckenmiller Agent** (`stanley_druckenmiller_agent`)
- **File:** `/src/agents/stanley_druckenmiller.py`
- **Philosophy:** Macro Investor - Macroeconomic trends, currencies, commodities, top-down calls
- **Approach:** Analyzes broad market conditions, interest rate trends, geopolitical factors
- **Data Focus:** Macro indicators (not company-specific fundamentals)

---

### 2.5 Classic Investors (Fundamental Growth & Quality)

#### **Peter Lynch Agent** (`peter_lynch_agent`)
- **File:** `/src/agents/peter_lynch.py`
- **Philosophy:** 10-Bagger Investor - "Buy what you know," GARP (Growth at Reasonable Price), understandable businesses
- **Analysis Methods:**
  - `analyze_lynch_growth()`: Revenue/EPS consistency, growth trajectory
  - `analyze_lynch_fundamentals()`: Margin stability, debt levels, cash flow quality
  - `analyze_lynch_valuation()`: **PEG ratio focus** (PE/Growth), P/B, P/E ratios
  - `analyze_sentiment()`: News sentiment signals
  - `analyze_insider_activity()`: Insider buying/selling
- **Key Metric:** PEG ratio < 1.5 = undervalued growth
- **Weighting:** Growth 30%, Valuation 25%, Fundamentals 20%, Sentiment 15%, Insider 10%
- **10-Bagger Signal:** Revenue growth + PEG <1.0 + insider buying

#### **Phil Fisher Agent** (`phil_fisher_agent`)
- **File:** `/src/agents/phil_fisher.py`
- **Philosophy:** Scuttlebutt Investor - Quality management, innovative products, long-term growth through proprietary research
- **Approach:** Qualitative research (scuttlebutt) + quantitative metrics
- **Metrics:** R&D spending, management tenure, product innovation pipeline

#### **Rakesh Jhunjhunwala Agent** (`rakesh_jhunjhunwala_agent`)
- **File:** `/src/agents/rakesh_jhunjhunwala.py` (707 lines)
- **Philosophy:** Big Bull of India - Macro insights, emerging markets, high-growth sectors
- **Focus:** Leverages macroeconomic trends, sector rotation, domestic opportunities

#### **Mohnish Pabrai Agent** (`mohnish_pabrai_agent`)
- **File:** `/src/agents/mohnish_pabrai.py`
- **Philosophy:** Dhandho Investor - Value investing, margin of safety, long-term growth
- **Approach:** Combines Ben Graham principles with focus on compounding

---

### 2.6 Technical & Market-Based Agents

#### **Technical Analyst Agent** (`technical_analyst_agent`)
- **File:** `/src/agents/technicals.py`
- **Philosophy:** Chart Pattern Specialist - Price action, technical indicators, trend following
- **Analysis Methods (5 strategies):**
  - `calculate_trend_signals()`: Moving average crossovers, trend strength
  - `calculate_mean_reversion_signals()`: Bollinger Bands, RSI extremes
  - `calculate_momentum_signals()`: MACD, Rate of Change
  - `calculate_volatility_signals()`: ATR, vol clusters
  - `calculate_statistical_arbitrage_signals()`: Z-scores, cointegration
- **Data:** Historical prices (start_date to end_date)
- **Output:** Structured signals per strategy with confidence scores
- **Key Classes:**
  - Price normalization, safe_float() for NaN handling
  - Pandas/NumPy for vectorized calculations

#### **Sentiment Analyst Agent** (`sentiment_analyst_agent`)
- **File:** `/src/agents/sentiment.py`
- **Philosophy:** Market Sentiment Specialist - Behavioral signals, crowd psychology
- **Analysis Methods:**
  - Insider trading patterns (weighting 0.3)
  - News sentiment (weighting 0.7)
  - Combined weighted signal aggregation
- **Output:** Bullish/bearish/neutral with confidence calculation
- **Metrics Tracked:**
  - Bullish/bearish/neutral trade counts
  - Article sentiment distribution
  - Weighted proportions per source

#### **News Sentiment Agent** (`news_sentiment_agent`)
- **File:** `/src/agents/news_sentiment.py`
- **Philosophy:** News Sentiment Specialist - Real-time news analysis, LLM classification
- **Analysis Methods:**
  - Fetches up to 100 company news articles
  - Uses LLM to classify sentiment of articles lacking explicit labels
  - Aggregates to overall bullish/bearish/neutral signal
- **LLM Integration:** Calls `call_llm()` for 5 most recent articles without sentiment
- **Confidence Calculation:**
  - 70% weight: Average LLM confidence scores
  - 30% weight: Signal proportion confidence
- **State Updates:** Stores per-article sentiment confidence tracking

---

### 2.7 Fundamental Analysis Agents

#### **Fundamentals Analyst Agent** (`fundamentals_analyst_agent`)
- **File:** `/src/agents/fundamentals.py`
- **Philosophy:** Financial Statement Specialist - Statement analysis, intrinsic value, financial health
- **Analysis Methods (4 sub-analyses):**
  1. **Profitability Signal:** ROE > 15%, net margin > 20%, op margin > 15%
  2. **Growth Signal:** Revenue/earnings/book value growth > 10%
  3. **Financial Health Signal:** Current ratio > 1.5, debt-to-equity < 0.5, FCF/EPS > 0.8
  4. **Valuation Signal:** P/E < 25, P/B < 3, P/S < 5
- **Scoring:** Count of bullish thresholds (3+ = bullish, 0 = bearish, else neutral)
- **Confidence:** (Max signals / Total signals) × 100

#### **Valuation Analyst Agent** (`valuation_analyst_agent`)
- **File:** `/src/agents/valuation.py`
- **Philosophy:** Company Valuation Specialist - Multiple valuation methodologies, margin of safety
- **4 Valuation Models:**
  1. **DCF (Discounted Cash Flow):**
     - Working capital changes
     - FCFF projections with terminal value
  2. **Relative Valuation:**
     - EV/EBITDA multiples vs. peers
     - P/E ratios vs. historical averages
  3. **Dividend Discount Model (DDM):**
     - Historical dividend trends
     - Payout ratio consistency
  4. **Asset-Based Valuation:**
     - Book value per share
     - Tangible asset coverage
- **Aggregation:** Weighted average of 4 methods
- **Signal:** Bullish if market price << weighted intrinsic value estimate

---

## 3. Infrastructure Components

### 3.1 Agent Configuration (`/src/utils/analysts.py`)

**ANALYST_CONFIG Dictionary** (19 analysts + 2 infrastructure agents):

| Key | Display Name | Type | Order | Agent Function |
|-----|--------------|------|-------|-----------------|
| aswath_damodaran | The Dean of Valuation | analyst | 0 | aswath_damodaran_agent |
| ben_graham | The Father of Value Investing | analyst | 1 | ben_graham_agent |
| bill_ackman | The Activist Investor | analyst | 2 | bill_ackman_agent |
| cathie_wood | The Queen of Growth Investing | analyst | 3 | cathie_wood_agent |
| charlie_munger | The Rational Thinker | analyst | 4 | charlie_munger_agent |
| michael_burry | The Big Short Contrarian | analyst | 5 | michael_burry_agent |
| mohnish_pabrai | The Dhandho Investor | analyst | 6 | mohnish_pabrai_agent |
| nassim_taleb | The Black Swan Risk Analyst | analyst | 7 | nassim_taleb_agent |
| peter_lynch | The 10-Bagger Investor | analyst | 8 | peter_lynch_agent |
| phil_fisher | The Scuttlebutt Investor | analyst | 9 | phil_fisher_agent |
| rakesh_jhunjhunwala | The Big Bull Of India | analyst | 10 | rakesh_jhunjhunwala_agent |
| stanley_druckenmiller | The Macro Investor | analyst | 11 | stanley_druckenmiller_agent |
| warren_buffett | The Oracle of Omaha | analyst | 12 | warren_buffett_agent |
| technical_analyst | Chart Pattern Specialist | analyst | 13 | technical_analyst_agent |
| fundamentals_analyst | Financial Statement Specialist | analyst | 14 | fundamentals_analyst_agent |
| growth_analyst | Growth Specialist | analyst | 15 | growth_analyst_agent |
| news_sentiment_analyst | News Sentiment Specialist | analyst | 16 | news_sentiment_agent |
| sentiment_analyst | Market Sentiment Specialist | analyst | 17 | sentiment_analyst_agent |
| valuation_analyst | Company Valuation Specialist | analyst | 18 | valuation_analyst_agent |

**Helper Functions:**
- `get_analyst_nodes()`: Returns dict mapping analyst_key → (node_name, agent_func)
- `get_agents_list()`: Returns list of agents for API responses with all metadata

### 3.2 State Management

**State Merging:**
- `messages`: Uses `operator.add` to concatenate messages (build message history)
- `data`: Uses custom `merge_dicts()` to accumulate financial data and signals
- `metadata`: Merges config flags (show_reasoning, model_name, model_provider)

**Data Schema:**
```python
state["data"] = {
    "tickers": ["AAPL", "MSFT"],  # Input
    "start_date": "2024-01-01",   # Input
    "end_date": "2024-03-31",     # Input
    "portfolio": {...},            # Input + updated by risk manager
    "analyst_signals": {           # Accumulated from all agents
        "ben_graham_agent": {
            "AAPL": {"signal": "bullish", "confidence": 85.5, "reasoning": "..."},
            "MSFT": {...}
        },
        "risk_management_agent": {
            "AAPL": {"remaining_position_limit": 50000, "current_price": 150, ...},
            ...
        }
    },
    "current_prices": {...}        # Set by risk manager
}
```

### 3.3 Entry Point (`/src/main.py`)

**Workflow Creation:**
```python
def create_workflow(selected_analysts=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)
    
    # Add selected analyst nodes (all connected from start_node)
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)
    
    # Add infrastructure nodes (sequential)
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_manager", portfolio_management_agent)
    
    # Connect analysts → risk → portfolio → end
    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "risk_management_agent")
    
    workflow.add_edge("risk_management_agent", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)
    workflow.set_entry_point("start_node")
```

**Execution:**
```python
final_state = agent.invoke({
    "messages": [HumanMessage(content="Make trading decisions...")],
    "data": {
        "tickers": [...],
        "portfolio": {...},
        "start_date": "...",
        "end_date": "...",
        "analyst_signals": {}
    },
    "metadata": {"show_reasoning": False, "model_name": "gpt-4", ...}
})
```

**Output Extraction:**
```python
{
    "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),  # Portfolio manager's JSON
    "analyst_signals": final_state["data"]["analyst_signals"]  # All agent signals
}
```

---

## 4. Infrastructure Agents

### 4.1 Risk Management Agent (`risk_management_agent`)

**Location:** `/src/agents/risk_manager.py`

**Philosophy:** Volatility and correlation-adjusted position sizing with portfolio-level risk controls

**Key Functions:**
- `calculate_volatility_metrics(prices_df)`: 
  - Daily volatility, annualized volatility (×√252)
  - Volatility percentile vs. historical rolling volatility
- `calculate_volatility_adjusted_limit(annualized_volatility)`:
  - Low vol (<15%): 25% allocation
  - Medium vol (15-30%): 20% → 12.5% scaling
  - High vol (30-50%): 15% → 5% scaling
  - Very high vol (>50%): 10% allocation
- `calculate_correlation_multiplier(avg_correlation)`:
  - Very high corr (≥0.8): 0.7x (reduce sharply)
  - High corr (0.6-0.8): 0.85x
  - Moderate (0.4-0.6): 1.0x (neutral)
  - Low (0.2-0.4): 1.05x (slight increase)
  - Very low (<0.2): 1.10x (increase)

**Analysis Scope:**
- Fetches price data for all tickers in portfolio
- Calculates price-based volatility metrics (60-day lookback)
- Builds correlation matrix across active positions
- Computes portfolio NLV (Net Liquidation Value) from current prices
- Applies volatility & correlation multipliers to base allocation limits

**Output per Ticker:**
```python
{
    "remaining_position_limit": float,  # $ available for new position
    "current_price": float,
    "volatility_metrics": {
        "daily_volatility": float,
        "annualized_volatility": float,
        "volatility_percentile": float,
        "data_points": int
    },
    "correlation_metrics": {
        "avg_correlation_with_active": float,
        "max_correlation_with_active": float,
        "top_correlated_tickers": [{"ticker": str, "correlation": float}, ...]
    },
    "reasoning": {
        "portfolio_value": float,
        "current_position_value": float,
        "base_position_limit_pct": float,
        "correlation_multiplier": float,
        "combined_position_limit_pct": float,
        "position_limit": float,
        "remaining_limit": float,
        "available_cash": float
    }
}
```

**State Updates:**
- `state["data"]["analyst_signals"]["risk_management_agent"][ticker]` ← risk metrics
- `state["data"]["current_prices"]` ← current market prices

### 4.2 Portfolio Manager Agent (`portfolio_management_agent`)

**Location:** `/src/agents/portfolio_manager.py`

**Philosophy:** Converts multi-agent signals into deterministic, risk-compliant trading decisions

**Key Functions:**
- `compute_allowed_actions()`: Determines permissible trades given liquidity/margin constraints
  - **Buy:** Limited by max_shares and available cash
  - **Sell:** Limited by existing long position
  - **Short:** Limited by max_shares and margin availability
  - **Cover:** Limited by existing short position
  - **Hold:** Always available
- `_compact_signals()`: Extracts {signal, confidence} from verbose analyst outputs
- `generate_trading_decision()`: LLM-based decision with deterministic constraints

**Decision Process:**
1. Extract analyst signals (compressed: {agent: {sig, conf}})
2. Compute allowed actions per ticker (deterministic)
3. Pre-fill pure holds (no trading available)
4. Send viable tickers to LLM with constraints
5. LLM picks action within allowed set + quantity ≤ max
6. Return PortfolioDecision objects

**Output Schema (per Ticker):**
```python
class PortfolioDecision(BaseModel):
    action: Literal["buy", "sell", "short", "cover", "hold"]
    quantity: int
    confidence: int  # 0-100
    reasoning: str   # Max 100 chars
```

**System Prompt:**
```
You are a portfolio manager.
Inputs per ticker: analyst signals and allowed actions with max qty (already validated).
Pick one allowed action per ticker and a quantity ≤ the max. 
Keep reasoning very concise (max 100 chars). No cash or margin math. Return JSON only.
```

**Minimal Prompt Approach:**
- Inputs: Compacted signals + allowed actions only
- No redundant portfolio math (already validated by risk manager)
- LLM focuses on synthesis of signals → action selection

**State Updates:**
- Returns updated `messages` with portfolio decisions
- Data unchanged (all constraints pre-computed by risk manager)

---

## 5. Data Flow & Execution Patterns

### 5.1 Single Ticker Analysis Flow

For each ticker across all selected agents:

```
Agent Input: state (shared AgentState)
    ↓
Fetch Financial Data (metrics, line items, prices, news, insiders)
    ↓
Run Domain-Specific Sub-Analyses (scoring, calculations)
    ↓
Aggregate Score → Signal (bullish/bearish/neutral)
    ↓
LLM Call (optional, for many agents):
    - System prompt: Agent's philosophy
    - Prompt: Analysis data + requested output format
    - Output: Pydantic model (Signal + confidence + reasoning)
    ↓
Generate HumanMessage with JSON output
    ↓
Update state["data"]["analyst_signals"][agent_id][ticker]
    ↓
Return {"messages": [message], "data": state["data"]}
```

### 5.2 Graph Execution Model

```
Input Invocation:
- tickers: ["AAPL", "MSFT", "GOOGL"]
- start_date, end_date, portfolio, analysts to run
    ↓
compile() creates executable graph
    ↓
invoke() with initial state
    ↓
[Parallel potential] Start node passes to all analyst nodes
    ↓
Each agent:
    - Fetches data (may be cached)
    - Runs analysis
    - Adds message to state
    - Updates analyst_signals in state
    ↓
[Sequential] Risk manager runs:
    - Consumes all analyst signals
    - Calculates volatility/correlation adjustments
    - Sets position limits per ticker
    - Adds risk metrics to analyst_signals
    ↓
[Sequential] Portfolio manager runs:
    - Consumes risk limits + analyst signals
    - Generates final buy/sell/short/cover decisions
    - Returns portfolio decisions
    ↓
final_state["messages"]: [all agent messages]
final_state["data"]["analyst_signals"]: {all signals}
```

### 5.3 Message Passing via TypedDict

**Accumulation Pattern:**
- `messages` uses `operator.add` → each agent appends HumanMessage
- Final state has all messages in order: [user_init, ben_graham, warren_buffett, ..., risk, portfolio]
- Portfolio manager extracts its own output from `final_state["messages"][-1].content`

**Data Merging Pattern:**
- `data` uses `merge_dicts()` → each agent updates analyst_signals dict
- Risk manager adds its own signals
- Portfolio manager reads all accumulated signals before generating decisions

---

## 6. Agent Signal Synthesis & Interpretation

### 6.1 Signal Format

**Standard Output (Most Agents):**
```json
{
  "AAPL": {
    "signal": "bullish" | "bearish" | "neutral",
    "confidence": 75.5,  // 0-100 float
    "reasoning": "string explaining the decision"
  },
  "MSFT": { ... }
}
```

**Reasoning Styles:**

| Agent Type | Reasoning Detail |
|------------|-----------------|
| LLM-Based Agents (Graham, Buffett, Ackman) | Natural language narrative with specific metrics |
| Quantitative Agents (Technicals, Sentiment) | Structured JSON with component signals & calculations |
| Hybrid Agents (Damodaran, Taleb) | Technical metrics + interpretive text |

### 6.2 Scoring & Aggregation

**Two Primary Patterns:**

**Pattern A: Sub-Analysis Scoring** (Ben Graham, Ackman, etc.)
- Each sub-analysis returns `{score: float, details: str}`
- Max possible score determined by combination
- Signal mapping: score ≥ 70% of max = bullish, ≤ 30% = bearish, else neutral
- Confidence: Often derived from score proportion

**Pattern B: Signal Voting** (Fundamentals, Sentiment)
- Each metric generates a bullish/bearish/neutral signal
- Count: bullish_count > bearish_count = bullish overall
- Confidence: max(bullish, bearish) / total × 100

### 6.3 LLM Integration

**For LLM-Driven Agents:**
1. Prepare comprehensive analysis data in structured format
2. Create ChatPromptTemplate with:
   - System message: Agent's philosophy, decision rules, tone
   - Human message: Analysis data + requested output schema (Pydantic)
3. Call `call_llm()` utility:
   ```python
   call_llm(
       prompt=prompt,
       pydantic_model=BenGrahamSignal,  # Return type
       agent_name=agent_id,
       state=state,
       default_factory=create_default_signal  # Fallback on error
   )
   ```
4. Pydantic validation ensures structured output

**Models Returned:**
- `BenGrahamSignal`, `WarrenBuffettSignal`, `BillAckmanSignal`, etc.
- All follow: `signal: Literal["bullish", "bearish", "neutral"]`, `confidence: float`, `reasoning: str`

---

## 7. Key Design Patterns

### 7.1 State-Based Coordination

- **No agent-to-agent messaging**: All communication via shared AgentState
- **Append-only signal storage**: Each agent adds signals, none overwrites others
- **Price caching**: Risk manager fetches once, stores in state for portfolio manager

### 7.2 Deterministic Constraints → LLM Synthesis

- Risk manager pre-computes all position limits (deterministic, no LLM)
- Portfolio manager receives validated constraints
- LLM respects constraints, focuses on signal interpretation

### 7.3 Financial Data Abstraction

- All agents use `/src/tools/api.py` for data fetching:
  - `get_financial_metrics()`: TTM or annual periods, configurable limit
  - `search_line_items()`: Flexible line item queries
  - `get_market_cap()`, `get_prices()`, `get_insider_trades()`, `get_company_news()`
- Data models in `/src/data/models.py` provide type safety

### 7.4 Progress Tracking

- `progress.update_status(agent_id, ticker, status_msg)` provides real-time feedback
- Enables long-running operations to show progress without blocking

---

## 8. Extensibility & Configuration

### 8.1 Adding New Agents

1. **Create agent file** in `/src/agents/` with function:
   ```python
   def new_agent(state: AgentState, agent_id: str = "new_agent"):
       # Analyze and return signal
       message = HumanMessage(content=json.dumps(signals), name=agent_id)
       state["data"]["analyst_signals"][agent_id] = signals
       return {"messages": [message], "data": state["data"]}
   ```

2. **Register in ANALYST_CONFIG** (`/src/utils/analysts.py`):
   ```python
   "new_agent": {
       "display_name": "New Analyst Name",
       "description": "...",
       "investing_style": "...",
       "agent_func": new_agent,
       "type": "analyst",
       "order": 19,  # Next order number
   }
   ```

3. **Graph automatically includes** via `get_analyst_nodes()` lookup

### 8.2 Selecting Subset of Agents

```python
selected_analysts = ["ben_graham", "warren_buffett", "technical_analyst"]
workflow = create_workflow(selected_analysts)
```
- Omitted agents are skipped (no edge from start_node)
- Risk & portfolio managers always run

### 8.3 Model & Provider Configuration

```python
result = run_hedge_fund(
    tickers=tickers,
    start_date=start_date,
    end_date=end_date,
    portfolio=portfolio,
    model_name="gpt-4-turbo",
    model_provider="OpenAI"  # or "Ollama", etc.
)
```
- Metadata propagated to all agents
- LLM calls use configured model

---

## 9. Financial Analysis Techniques Summary

### 9.1 Valuation Methods Used

| Agent | DCF | Relative Multiples | Graham Number | PEG Ratio | Asset-Based |
|-------|-----|-------------------|--------------|-----------|-------------|
| Ben Graham | ✗ | ✗ | ✓ | ✗ | ✓ (NCAV) |
| Warren Buffett | ✓ | ✓ | ✗ | ✗ | ✗ |
| Aswath Damodaran | ✓ | ✓ | ✗ | ✗ | ✗ |
| Cathie Wood | ✓ | ✓ | ✗ | ✗ | ✗ |
| Peter Lynch | ✗ | ✓ | ✗ | ✓ | ✗ |
| Valuation Analyst | ✓ | ✓ | ✗ | ✗ | ✓ |

### 9.2 Risk Metrics Analyzed

| Category | Methods |
|----------|---------|
| **Volatility** | Daily vol, annualized vol, vol percentile, GARCH (Taleb) |
| **Leverage** | Debt-to-equity, debt-to-assets, interest coverage |
| **Liquidity** | Current ratio, quick ratio, cash/liabilities |
| **Tail Risk** | VaR, extreme drawdowns, left-tail analysis |
| **Correlation** | Inter-ticker correlation, portfolio-level diversification |
| **Fragility** | Leverage stress-tests, covenant proximity (Taleb) |

### 9.3 Growth Metrics Analyzed

| Metric | Used By |
|--------|---------|
| Revenue growth (YoY, trend) | Most agents |
| Earnings growth (EPS trend) | Graham, Lynch, Growth Agent |
| Free cash flow growth | Buffett, Damodaran, Ackman |
| Margin expansion trends | Growth Agent, Cathie Wood |
| Return on equity (ROE) | Ackman, Fundamentals |
| Return on invested capital (ROIC) | Damodaran |

---

## 10. Signal Aggregation at Portfolio Level

### 10.1 Risk Manager Gatekeeping

- **Before:** Analyst signals flow directly to portfolio manager
- **After (with risk manager):** Signals + volatility/correlation adjustments
- **Effect:** High-vol stocks get smaller position limits; correlated stocks reduce allocation

### 10.2 Portfolio Manager Synthesis

LLM receives:
```
Signals: {
  "ben_graham_agent": {"sig": "bullish", "conf": 85},
  "technical_analyst_agent": {"sig": "bearish", "conf": 60},
  ...
}

Allowed: {
  "buy": 1000,   // max 1000 shares
  "short": 500,  // max 500 shares
  "hold": 0
}
```

LLM reconciles conflicting signals (bullish vs bearish) within portfolio constraints:
- High conviction bullish + low confidence bearish → buy
- Multiple bullish signals → increase buy quantity
- Mixed signals → hold or smaller position

---

## 11. Execution Examples

### Example 1: Single Ticker, All Agents

**Input:**
```python
run_hedge_fund(
    tickers=["AAPL"],
    start_date="2024-01-01",
    end_date="2024-03-31",
    portfolio={"cash": 100000, "positions": {"AAPL": {"long": 0, "short": 0}}},
    selected_analysts=None  # All 19 agents
)
```

**Execution Path:**
1. Start node
2. 19 analyst agents (parallel-capable):
   - Ben Graham: Fetches earnings, current ratio, calculates Graham Number
   - Warren Buffett: Analyzes moat, FCF, management
   - Technical Analyst: Calculates trend, momentum, vol signals
   - ... (16 more)
3. Risk manager: Calculates AAPL volatility, position limit
4. Portfolio manager: Aggregates 19 signals + 1 risk constraint → decision

**Output:**
```python
{
    "decisions": {
        "AAPL": {
            "action": "buy",
            "quantity": 150,
            "confidence": 92,
            "reasoning": "Strong bullish consensus across value and growth agents"
        }
    },
    "analyst_signals": {
        "ben_graham_agent": {"AAPL": {"signal": "bullish", ...}},
        "warren_buffett_agent": {"AAPL": {"signal": "bullish", ...}},
        "technical_analyst_agent": {"AAPL": {"signal": "neutral", ...}},
        ...
        "risk_management_agent": {"AAPL": {"remaining_position_limit": 50000, ...}}
    }
}
```

### Example 2: Multi-Ticker, Subset of Agents

**Input:**
```python
run_hedge_fund(
    tickers=["TSLA", "NVDA", "AMD"],
    selected_analysts=["cathie_wood", "nassim_taleb", "technical_analyst"]
)
```

**Graph Execution:**
- Start → Cathie Wood, Nassim Taleb, Technical Analyst (all 3 in parallel)
  - Cathie Wood: Disruptive tech, R&D, growth scenarios
  - Nassim Taleb: Tail risk, volatility regimes, antifragility
  - Technical: Trend + momentum signals
- Risk Manager: Volatility limits for TSLA/NVDA/AMD, correlation adjustments
- Portfolio Manager: 3 signals × 3 tickers + risk constraints → 3 decisions

---

## 12. Summary Table: Agent Characteristics

| Agent | LLM-Driven | Quantitative | Philosophy | Key Metric |
|-------|-----------|-------------|-----------|-----------|
| Ben Graham | Yes | Yes | Value, Safety | Graham Number, NCAV |
| Warren Buffett | Yes | Yes | Quality, Moats | ROE, Moat Strength |
| Charlie Munger | Yes | Yes | Quality, Psychology | Business Model, Mgmt |
| Aswath Damodaran | Yes | Yes | Academic DCF | Intrinsic Value, WACC |
| Cathie Wood | Yes | No | Growth, Disruption | Revenue Growth, TAM |
| Peter Lynch | Yes | Yes | GARP | PEG Ratio, Growth |
| Phil Fisher | Yes | Yes | Scuttlebutt, Quality | Management, Products |
| Rakesh Jhunjhunwala | Yes | No | Macro, Emerging | Sector Growth, Macro |
| Mohnish Pabrai | Yes | Yes | Value, Compounding | Margin of Safety |
| Michael Burry | Yes | Yes | Deep Value, Shorts | Book/Market, Contrarian |
| Nassim Taleb | Yes | Yes | Tail Risk, Antifragility | Convexity, Tail VaR |
| Stanley Druckenmiller | Yes | No | Macro Trends | Macro Indicators |
| Bill Ackman | Yes | Yes | Activism, Moats | Brand, Activism Upside |
| Technical Analyst | No | Yes | Chart Patterns | Moving Averages, RSI |
| Fundamentals Analyst | No | Yes | Financial Statements | ROE, Growth, Ratios |
| Valuation Analyst | No | Yes | Multi-Method Valuation | DCF, Multiples, DDM |
| Sentiment Analyst | No | Yes | Crowd Psychology | News/Insider Sentiment |
| News Sentiment Analyst | Yes | Yes | News Classification | Article Sentiment |
| Growth Analyst | No | Yes | Growth + Quality | Growth Rate, PEG |

---

## 13. Conclusion

The **AI Hedge Fund** represents a sophisticated **multi-agent ensemble system** that:

1. **Orchestrates diverse investment philosophies** through 19 specialized agents
2. **Combines LLM reasoning** with quantitative analysis for nuanced decision-making
3. **Enforces risk constraints** through a dedicated risk management layer
4. **Generates deterministic, rule-based trades** via portfolio management
5. **Scales flexibly** - users can select agent subsets or use all
6. **Maintains auditability** - all signals and reasoning are stored and displayable

**Key Strengths:**
- Heterogeneous viewpoints reduce single-perspective bias
- Risk layer prevents over-leveraged positions
- Modular design enables adding new agents easily
- State-based architecture ensures consistency across parallel execution
- Deterministic constraints ensure trades respect portfolio risk limits

**Data Flow:**
```
Input (tickers, dates, portfolio)
    ↓
19 Analyst Agents (parallel execution)
    ↓
Risk Manager (volatility & correlation adjustment)
    ↓
Portfolio Manager (LLM synthesis → actions)
    ↓
Output (trading decisions + all signals)
```

This design balances **interpretability** (understand each agent's logic) with **sophistication** (multi-factor optimization), enabling both research and production deployment.