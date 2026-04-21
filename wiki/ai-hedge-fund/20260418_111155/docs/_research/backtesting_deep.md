
# AI Hedge Fund Project - Comprehensive Research Report

## Executive Summary

The **AI Hedge Fund** is a multi-agent AI trading system that simulates decision-making by famous investors (Warren Buffett, Michael Burry, Cathie Wood, etc.). It uses LangGraph for agent orchestration, multiple LLM providers for inference, and a modular backtesting engine for evaluating trading strategies. The project is educational and demonstrates how AI can synthesize diverse analytical approaches to generate trading signals.

---

## Module Analysis

### 1. **Backtesting Engine** (`src/backtesting/`)

#### Purpose and Role
The backtesting engine provides the simulation infrastructure for evaluating trading strategies over historical data. It:
- Executes the main simulation loop day-by-day
- Orchestrates agent decisions and trade execution
- Calculates portfolio metrics, exposures, and performance statistics
- Maintains historical portfolio state and generates results output

#### Key Classes and Functions

**Types & Data Models** (`types.py`):
- `Action` (Enum): `BUY`, `SELL`, `SHORT`, `COVER`, `HOLD`
- `PortfolioSnapshot`: Dict with `cash`, `margin_used`, `margin_requirement`, `positions`, `realized_gains`
- `PositionState`: Per-ticker tracking with `long`, `short`, cost bases and margin
- `PerformanceMetrics`: `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, exposures
- `PortfolioValuePoint`: Timestamped portfolio value with exposure metrics

**Portfolio** (`portfolio.py`):
```python
class Portfolio:
    def __init__(self, tickers: list[str], initial_cash: float, margin_requirement: float) -> None
    def get_snapshot(self) -> PortfolioSnapshot
    def apply_long_buy(self, ticker: str, quantity: int, price: float) -> int
    def apply_long_sell(self, ticker: str, quantity: int, price: float) -> int
    def apply_short_open(self, ticker: str, quantity: int, price: float) -> int
    def apply_short_cover(self, ticker: str, quantity: int, price: float) -> int
```

**Trade Executor** (`trader.py`):
```python
class TradeExecutor:
    def execute_trade(
        self, ticker: str, action: ActionLiteral, quantity: float,
        current_price: float, portfolio: Portfolio
    ) -> int
```

**Agent Controller** (`controller.py`):
```python
class AgentController:
    def run_agent(
        self, agent: Callable[..., AgentOutput],
        tickers: Sequence[str], start_date: str, end_date: str,
        portfolio: Portfolio | PortfolioSnapshot,
        model_name: str, model_provider: str,
        selected_analysts: Sequence[str] | None
    ) -> AgentOutput
```

**Performance Metrics Calculator** (`metrics.py`):
```python
class PerformanceMetricsCalculator:
    def __init__(self, annual_trading_days: int = 252, annual_rf_rate: float = 0.0434) -> None
    def compute_metrics(self, values: Sequence[PortfolioValuePoint]) -> PerformanceMetrics
```

**BacktestEngine** (`engine.py`):
```python
class BacktestEngine:
    def __init__(
        self, agent, tickers: list[str], start_date: str, end_date: str,
        initial_capital: float, model_name: str, model_provider: str,
        selected_analysts: list[str] | None, initial_margin_requirement: float
    ) -> None
    
    def run_backtest(self) -> PerformanceMetrics
    def get_portfolio_values(self) -> Sequence[PortfolioValuePoint]
```

**Valuation Functions** (`valuation.py`):
```python
def calculate_portfolio_value(portfolio: Portfolio, current_prices: Mapping[str, float]) -> float
def compute_exposures(portfolio: Portfolio, current_prices: Mapping[str, float]) -> Dict[str, float]
def compute_portfolio_summary(...) -> Dict[str, float | None]
```

#### Important Code Patterns

1. **Portfolio State Encapsulation**: Portfolio class manages internal state with read-only snapshots via `get_snapshot()` to preserve immutability for agent consumption.

2. **Trade Execution with Liquidity Constraints**:
   - Long buys: Limited by available cash
   - Short opens: Limited by margin requirement (typically 0.3-0.5x of proceeds)
   - Automatic downsizing to max executable quantity

3. **Cost Basis Tracking**: Average cost calculation for both long and short positions:
```python
# From Portfolio.apply_long_buy():
total_shares = old_shares + quantity
if total_shares > 0:
    total_old_cost = old_cost_basis * old_shares
    total_new_cost = cost
    position["long_cost_basis"] = (total_old_cost + total_new_cost) / total_shares
```

4. **Daily Loop with Prefetch**: The engine pre-fetches 1 year of historical data before the backtest starts to optimize API calls.

#### Representative Code Snippets

**Snippet 1: Portfolio Long Buy with Cash Constraint**
```python
def apply_long_buy(self, ticker: str, quantity: int, price: float) -> int:
    if quantity <= 0:
        return 0
    quantity = int(quantity)
    position = self._portfolio["positions"][ticker]
    cost = quantity * price
    if cost <= self._portfolio["cash"]:
        old_shares = position["long"]
        old_cost_basis = position["long_cost_basis"]
        total_shares = old_shares + quantity
        if total_shares > 0:
            total_old_cost = old_cost_basis * old_shares
            total_new_cost = cost
            position["long_cost_basis"] = (total_old_cost + total_new_cost) / total_shares
        position["long"] = old_shares + quantity
        self._portfolio["cash"] -= cost
        return quantity
    # Auto-scale to max affordable quantity
    max_quantity = int(self._portfolio["cash"] / price) if price > 0 else 0
    if max_quantity > 0:
        # ... same logic ...
    return 0
```

**Snippet 2: Sharpe Ratio Calculation**
```python
def compute_metrics(self, values: Sequence[PortfolioValuePoint]) -> PerformanceMetrics:
    df = pd.DataFrame(values).set_index("Date")
    df["Daily Return"] = df["Portfolio Value"].pct_change()
    clean_returns = df["Daily Return"].dropna()
    
    daily_rf = self.annual_rf_rate / self.annual_trading_days
    excess = clean_returns - daily_rf
    mean_excess = excess.mean()
    std_excess = excess.std()
    
    if std_excess > 1e-12:
        sharpe = float(np.sqrt(self.annual_trading_days) * (mean_excess / std_excess))
    else:
        sharpe = 0.0
    return {"sharpe_ratio": sharpe, ...}
```

**Snippet 3: Agent Controller Output Normalization**
```python
def run_agent(self, agent: Callable[..., AgentOutput], ...) -> AgentOutput:
    portfolio_payload = portfolio.get_snapshot() if isinstance(portfolio, Portfolio) else portfolio
    
    output = agent(
        tickers=list(tickers), start_date=start_date, end_date=end_date,
        portfolio=portfolio_payload, model_name=model_name,
        model_provider=model_provider, selected_analysts=list(selected_analysts) if selected_analysts else None
    )
    
    # Normalize outputs to handle None/missing keys
    normalized_decisions: AgentDecisions = {}
    for ticker in tickers:
        d = decisions_in.get(ticker, {})
        action = d.get("action", "hold")
        qty = d.get("quantity", 0)
        try:
            qty_val = float(qty)
        except:
            qty_val = 0.0
        try:
            action = Action(action).value
        except:
            action = Action.HOLD.value
        normalized_decisions[ticker] = {"action": action, "quantity": qty_val}
    
    return {"decisions": normalized_decisions, "analyst_signals": analyst_signals_in}
```

**Snippet 4: Main Backtest Loop (Day-by-Day)**
```python
for current_date in dates:
    lookback_start = (current_date - relativedelta(months=1)).strftime("%Y-%m-%d")
    current_date_str = current_date.strftime("%Y-%m-%d")
    
    # Fetch current prices for all tickers
    current_prices: Dict[str, float] = {}
    for ticker in self._tickers:
        price_data = get_price_data(ticker, previous_date_str, current_date_str)
        current_prices[ticker] = float(price_data.iloc[-1]["close"])
    
    # Run agent with 1-month lookback window
    agent_output = self._agent_controller.run_agent(
        self._agent, tickers=self._tickers, start_date=lookback_start,
        end_date=current_date_str, portfolio=self._portfolio,
        model_name=self._model_name, model_provider=self._model_provider,
        selected_analysts=self._selected_analysts
    )
    
    # Execute trades
    for ticker in self._tickers:
        d = agent_output["decisions"].get(ticker, {"action": "hold", "quantity": 0})
        executed_qty = self._executor.execute_trade(
            ticker, d["action"], d["quantity"], current_prices[ticker], self._portfolio
        )
    
    # Calculate exposures and metrics
    total_value = calculate_portfolio_value(self._portfolio, current_prices)
    exposures = compute_exposures(self._portfolio, current_prices)
    self._portfolio_values.append({
        "Date": current_date, "Portfolio Value": total_value,
        "Long Exposure": exposures["Long Exposure"], ...
    })
```

**Snippet 5: CLI Entry Point with Interactive Selection**
```python
def main() -> int:
    parser = argparse.ArgumentParser(description="Run backtesting engine")
    args = parser.parse_args()
    
    # Interactive analyst selection
    choices = questionary.checkbox(
        "Use Space bar to select/unselect analysts.",
        choices=[questionary.Choice(display, value=value) for display, value in ANALYST_ORDER],
        validate=lambda x: len(x) > 0 or "You must select at least one analyst."
    ).ask()
    selected_analysts = choices
    
    # Interactive model selection
    model_choice = questionary.select(
        "Select your LLM model:",
        choices=[questionary.Choice(display, value=(name, provider)) 
                 for display, name, provider in LLM_ORDER]
    ).ask()
    model_name, model_provider = model_choice
    
    # Run backtest
    engine = BacktestEngine(
        agent=run_hedge_fund, tickers=tickers, start_date=args.start_date,
        end_date=args.end_date, initial_capital=args.initial_capital,
        model_name=model_name, model_provider=model_provider,
        selected_analysts=selected_analysts,
        initial_margin_requirement=args.margin_requirement
    )
    
    metrics = engine.run_backtest()
    return 0
```

#### Connections to Other Modules
- **→ Data**: Calls `get_prices()`, `get_price_data()`, `get_financial_metrics()`, `get_insider_trades()`, `get_company_news()`
- **← Main System**: Called by `run_hedge_fund()` via BacktestEngine
- **← CLI**: Configured by `src/backtesting/cli.py` with interactive prompts
- **← Utils**: Uses `display` module for formatting output, `progress` for agent tracking

---

### 2. **Data Models & Caching** (`src/data/`)

#### Purpose and Role
The data module provides:
- Type-safe data models for all API responses (prices, financials, news, trades)
- In-memory caching layer to avoid redundant API calls
- Pydantic validation for robust response parsing
- Integration point between API tools and the trading agents

#### Key Classes and Functions

**Data Models** (`models.py`):

```python
class Price(BaseModel):
    open: float
    close: float
    high: float
    low: float
    volume: int
    time: str

class FinancialMetrics(BaseModel):
    ticker: str
    report_period: str
    market_cap: float | None
    price_to_earnings_ratio: float | None
    price_to_book_ratio: float | None
    debt_to_equity: float | None
    return_on_equity: float | None
    # ... 30+ fields for comprehensive fundamental analysis

class InsiderTrade(BaseModel):
    ticker: str
    name: str | None
    title: str | None
    transaction_date: str | None
    transaction_shares: float | None
    transaction_price_per_share: float | None
    shares_owned_after_transaction: float | None

class CompanyNews(BaseModel):
    ticker: str
    title: str
    author: str | None
    source: str
    date: str
    url: str
    sentiment: str | None

class Portfolio(BaseModel):
    positions: dict[str, Position]
    total_cash: float = 0.0

class AgentStateData(BaseModel):
    tickers: list[str]
    portfolio: Portfolio
    start_date: str
    end_date: str
    ticker_analyses: dict[str, TickerAnalysis]
```

**Cache Implementation** (`cache.py`):

```python
class Cache:
    def __init__(self):
        self._prices_cache: dict[str, list[dict[str, any]]] = {}
        self._financial_metrics_cache: dict[str, list[dict[str, any]]] = {}
        self._insider_trades_cache: dict[str, list[dict[str, any]]] = {}
        self._company_news_cache: dict[str, list[dict[str, any]]] = {}
    
    def _merge_data(self, existing: list[dict] | None, new_data: list[dict], key_field: str) -> list[dict]:
        """Merge avoiding duplicates based on key_field."""
        if not existing:
            return new_data
        existing_keys = {item[key_field] for item in existing}
        merged = existing.copy()
        merged.extend([item for item in new_data if item[key_field] not in existing_keys])
        return merged
    
    def get_prices(self, ticker: str) -> list[dict[str, any]] | None
    def set_prices(self, ticker: str, data: list[dict[str, any]])
    def get_financial_metrics(self, ticker: str) -> list[dict[str, any]]
    def set_financial_metrics(self, ticker: str, data: list[dict[str, any]])
    # ... similar for insider trades, news

# Global singleton
_cache = Cache()
def get_cache() -> Cache:
    return _cache
```

#### Important Code Patterns

1. **Composite Cache Keys**: Cache keys include date ranges to avoid false positives:
   ```python
   cache_key = f"{ticker}_{start_date}_{end_date}_{limit}"
   ```

2. **Smart Deduplication**: Uses a key field (e.g., "time" for prices, "filing_date" for trades) to merge new data without duplicates.

3. **Pydantic Validation**: All responses validated against models before caching, ensuring type safety downstream.

4. **Response Wrapper Pattern**: Each API call returns a `*Response` model containing a list (e.g., `PriceResponse` wraps `list[Price]`).

#### Representative Code Snippets

**Snippet 1: Cache Merge Logic**
```python
def _merge_data(self, existing: list[dict] | None, new_data: list[dict], key_field: str) -> list[dict]:
    """Merge existing and new data, avoiding duplicates based on a key field."""
    if not existing:
        return new_data
    
    # Create a set of existing keys for O(1) lookup
    existing_keys = {item[key_field] for item in existing}
    
    # Only add items that don't exist yet
    merged = existing.copy()
    merged.extend([item for item in new_data if item[key_field] not in existing_keys])
    return merged
```

**Snippet 2: Financial Metrics Model**
```python
class FinancialMetrics(BaseModel):
    ticker: str
    report_period: str
    period: str
    currency: str
    market_cap: float | None
    enterprise_value: float | None
    price_to_earnings_ratio: float | None
    price_to_book_ratio: float | None
    free_cash_flow_yield: float | None
    gross_margin: float | None
    operating_margin: float | None
    debt_to_equity: float | None
    interest_coverage: float | None
    revenue_growth: float | None
    earnings_growth: float | None
```

#### Connections to Other Modules
- **← Tools**: Consumed by API functions in `src/tools/api.py`
- **← LLM Agents**: Agents receive structured `TickerAnalysis` data
- **← Backtesting**: Metrics used for decision-making in agent prompts

---

### 3. **Financial Data API Tools** (`src/tools/`)

#### Purpose and Role
The tools module provides:
- Unified API wrappers for financial data (prices, fundamentals, insider trades, news)
- Rate limiting and retry logic for API stability
- Automatic caching integration
- Data transformation utilities (e.g., prices to DataFrame)

#### Key Functions

```python
def _make_api_request(url: str, headers: dict, method: str = "GET", 
                     json_data: dict = None, max_retries: int = 3) -> requests.Response
    # Linear backoff: 60s, 90s, 120s, 150s...

def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]
def get_financial_metrics(ticker: str, end_date: str, period: str = "ttm", 
                         limit: int = 10, api_key: str = None) -> list[FinancialMetrics]
def search_line_items(ticker: str, line_items: list[str], end_date: str, 
                     period: str = "ttm", limit: int = 10) -> list[LineItem]
def get_insider_trades(ticker: str, end_date: str, start_date: str | None = None, 
                      limit: int = 1000, api_key: str = None) -> list[InsiderTrade]
def get_company_news(ticker: str, end_date: str, start_date: str | None = None, 
                    limit: int = 1000, api_key: str = None) -> list[CompanyNews]
def get_market_cap(ticker: str, end_date: str, api_key: str = None) -> float | None
def prices_to_df(prices: list[Price]) -> pd.DataFrame
def get_price_data(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame
```

#### Important Code Patterns

1. **Rate Limit Handling with Exponential Backoff**:
   ```python
   for attempt in range(max_retries + 1):
       response = requests.get(url, headers=headers)
       if response.status_code == 429 and attempt < max_retries:
           delay = 60 + (30 * attempt)  # Linear: 60s, 90s, 120s...
           time.sleep(delay)
           continue
       return response
   ```

2. **Pagination for Large Datasets**: News and insider trades use pagination with date progression:
   ```python
   while True:
       url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={current_end_date}"
       response = _make_api_request(url, headers)
       # ... parse and accumulate ...
       if len(insider_trades) < limit:
           break
       current_end_date = min(trade.filing_date for trade in insider_trades).split("T")[0]
   ```

3. **API Key Environment Variable Fallback**:
   ```python
   headers = {}
   financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
   if financial_api_key:
       headers["X-API-KEY"] = financial_api_key
   ```

#### Representative Code Snippets

**Snippet 1: Request with Rate Limiting**
```python
def _make_api_request(url: str, headers: dict, method: str = "GET", 
                     json_data: dict = None, max_retries: int = 3) -> requests.Response:
    """Make an API request with rate limiting handling and moderate backoff."""
    for attempt in range(max_retries + 1):
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)
        
        if response.status_code == 429 and attempt < max_retries:
            delay = 60 + (30 * attempt)
            print(f"Rate limited (429). Attempt {attempt + 1}/{max_retries + 1}. Waiting {delay}s...")
            time.sleep(delay)
            continue
        
        return response
```

**Snippet 2: Get Prices with Cache**
```python
def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]:
    """Fetch price data from cache or API."""
    cache_key = f"{ticker}_{start_date}_{end_date}"
    
    if cached_data := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached_data]
    
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key
    
    url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&start_date={start_date}&end_date={end_date}"
    response = _make_api_request(url, headers)
    
    if response.status_code != 200:
        return []
    
    try:
        price_response = PriceResponse(**response.json())
        prices = price_response.prices
    except Exception as e:
        logger.warning("Failed to parse price response for %s: %s", ticker, e)
        return []
    
    _cache.set_prices(cache_key, [p.model_dump() for p in prices])
    return prices
```

**Snippet 3: Pagination with Date-Based Continuation**
```python
def get_insider_trades(ticker: str, end_date: str, start_date: str | None = None,
                      limit: int = 1000, api_key: str = None) -> list[InsiderTrade]:
    all_trades = []
    current_end_date = end_date
    
    while True:
        url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={current_end_date}"
        if start_date:
            url += f"&filing_date_gte={start_date}"
        url += f"&limit={limit}"
        
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            break
        
        insider_trades = response_model.insider_trades
        if not insider_trades:
            break
        
        all_trades.extend(insider_trades)
        
        if not start_date or len(insider_trades) < limit:
            break
        
        # Update end_date to oldest filing date for next iteration
        current_end_date = min(trade.filing_date for trade in insider_trades).split("T")[0]
        if current_end_date <= start_date:
            break
    
    _cache.set_insider_trades(cache_key, [trade.model_dump() for trade in all_trades])
    return all_trades
```

**Snippet 4: Market Cap with Conditional API Endpoint**
```python
def get_market_cap(ticker: str, end_date: str, api_key: str = None) -> float | None:
    """Fetch market cap from the API."""
    if end_date == datetime.datetime.now().strftime("%Y-%m-%d"):
        # Use company facts API for today
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key
        
        url = f"https://api.financialdatasets.ai/company/facts/?ticker={ticker}"
        response = _make_api_request(url, headers)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        response_model = CompanyFactsResponse(**data)
        return response_model.company_facts.market_cap
    
    # Otherwise use historical financial metrics
    financial_metrics = get_financial_metrics(ticker, end_date, api_key=api_key)
    return financial_metrics[0].market_cap if financial_metrics else None
```

#### Connections to Other Modules
- **→ Data Models**: Uses Pydantic models from `src/data/models.py`
- **→ Cache**: Integrates with `src/data/cache.py` for deduplication
- **← Backtesting**: Called by `BacktestEngine._prefetch_data()` and daily loops
- **← Agents**: Accessed by all agents for fundamental/technical analysis

---

### 4. **LLM Model Configuration** (`src/llm/`)

#### Purpose and Role
The LLM module:
- Manages LLM provider integrations (OpenAI, Anthropic, Groq, DeepSeek, Ollama, etc.)
- Loads model configurations from JSON files
- Provides factory function to instantiate LLM clients with appropriate API keys
- Supports model-specific features (JSON mode, custom endpoints)

#### Key Components

```python
class ModelProvider(str, Enum):
    ANTHROPIC = "Anthropic"
    DEEPSEEK = "DeepSeek"
    GOOGLE = "Google"
    GROQ = "Groq"
    OPENAI = "OpenAI"
    OLLAMA = "Ollama"
    OPENROUTER = "OpenRouter"
    GIGACHAT = "GigaChat"
    AZURE_OPENAI = "Azure OpenAI"
    XAI = "xAI"

class LLMModel(BaseModel):
    display_name: str
    model_name: str
    provider: ModelProvider
    
    def to_choice_tuple(self) -> Tuple[str, str, str]
    def is_custom(self) -> bool
    def has_json_mode(self) -> bool
    def is_deepseek(self) -> bool
    def is_gemini(self) -> bool
    def is_ollama(self) -> bool

def get_model(model_name: str, model_provider: ModelProvider, api_keys: dict = None) 
    -> ChatOpenAI | ChatGroq | ChatOllama | GigaChat | None

def load_models_from_json(json_path: str) -> List[LLMModel]
```

#### Important Code Patterns

1. **Provider-Specific Configuration**: Each provider has unique authentication:
   ```python
   if model_provider == ModelProvider.GROQ:
       return ChatGroq(model=model_name, api_key=api_key)
   elif model_provider == ModelProvider.OPENAI:
       return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)
   elif model_provider == ModelProvider.OLLAMA:
       ollama_host = os.getenv("OLLAMA_HOST", "localhost")
       base_url = os.getenv("OLLAMA_BASE_URL", f"http://{ollama_host}:11434")
       return ChatOllama(model=model_name, base_url=base_url)
   ```

2. **JSON Mode Detection**: DeepSeek and Gemini don't support JSON mode:
   ```python
   def has_json_mode(self) -> bool:
       if self.is_deepseek() or self.is_gemini():
           return False
       if self.is_ollama():
           return "llama3" in self.model_name or "neural-chat" in self.model_name
       return True
   ```

3. **OpenRouter with Custom Headers**: Passes referer for analytics:
   ```python
   return ChatOpenAI(
       model=model_name, openai_api_key=api_key,
       openai_api_base="https://openrouter.ai/api/v1",
       model_kwargs={"extra_headers": {
           "HTTP-Referer": site_url,
           "X-Title": site_name
       }}
   )
   ```

#### Representative Code Snippets

**Snippet 1: Model Configuration Loading**
```python
def load_models_from_json(json_path: str) -> List[LLMModel]:
    """Load models from a JSON file"""
    with open(json_path, 'r') as f:
        models_data = json.load(f)
    
    models = []
    for model_data in models_data:
        provider_enum = ModelProvider(model_data["provider"])
        models.append(
            LLMModel(
                display_name=model_data["display_name"],
                model_name=model_data["model_name"],
                provider=provider_enum
            )
        )
    return models

# Get the path to the JSON files
current_dir = Path(__file__).parent
models_json_path = current_dir / "api_models.json"
AVAILABLE_MODELS = load_models_from_json(str(models_json_path))
LLM_ORDER = [model.to_choice_tuple() for model in AVAILABLE_MODELS]
```

**Snippet 2: Provider-Specific LLM Instantiation**
```python
def get_model(model_name: str, model_provider: ModelProvider, api_keys: dict = None):
    if model_provider == ModelProvider.GROQ:
        api_key = (api_keys or {}).get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key not found...")
        return ChatGroq(model=model_name, api_key=api_key)
    
    elif model_provider == ModelProvider.OPENAI:
        api_key = (api_keys or {}).get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE")
        if not api_key:
            raise ValueError("OpenAI API key not found...")
        return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)
    
    elif model_provider == ModelProvider.ANTHROPIC:
        api_key = (api_keys or {}).get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key not found...")
        return ChatAnthropic(model=model_name, api_key=api_key)
    
    # ... more providers ...
    
    elif model_provider == ModelProvider.OLLAMA:
        ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        base_url = os.getenv("OLLAMA_BASE_URL", f"http://{ollama_host}:11434")
        return ChatOllama(model=model_name, base_url=base_url)
```

**Snippet 3: JSON Mode Feature Detection**
```python
def has_json_mode(self) -> bool:
    """Check if the model supports JSON mode"""
    if self.is_deepseek() or self.is_gemini():
        return False
    # Only certain Ollama models support JSON mode
    if self.is_ollama():
        return "llama3" in self.model_name or "neural-chat" in self.model_name
    # OpenRouter models generally support JSON mode
    if self.provider == ModelProvider.OPENROUTER:
        return True
    return True
```

#### Connections to Other Modules
- **← Utils/LLM**: Used by `call_llm()` in `src/utils/llm.py`
- **← CLI**: Called by `select_model()` in `src/cli/input.py`
- **← Agents**: Every agent calls `get_model()` to instantiate LLM

---

### 5. **CLI Interface** (`src/cli/`)

#### Purpose and Role
The CLI module provides:
- Argument parsing utilities for consistent command-line interfaces
- Interactive prompts for analyst, model, and date selection
- Input validation and normalization
- Dataclass for structured CLI inputs across different commands

#### Key Functions and Classes

```python
def add_common_args(parser, require_tickers=False, include_analyst_flags=True, include_ollama=True) -> argparse.ArgumentParser

def add_date_args(parser, default_months_back: int | None = None) -> argparse.ArgumentParser

def parse_tickers(tickers_arg: str | None) -> list[str]

def select_analysts(flags: dict | None = None) -> list[str]

def select_model(use_ollama: bool, model_flag: str | None = None) -> tuple[str, str]

def resolve_dates(start_date: str | None, end_date: str | None, 
                 default_months_back: int | None = None) -> tuple[str, str]

@dataclass
class CLIInputs:
    tickers: list[str]
    selected_analysts: list[str]
    model_name: str
    model_provider: str
    start_date: str
    end_date: str
    initial_cash: float
    margin_requirement: float
    show_reasoning: bool = False
    show_agent_graph: bool = False
    raw_args: Optional[argparse.Namespace] = None

def parse_cli_inputs(description: str, require_tickers: bool, default_months_back: int | None,
                    include_graph_flag: bool = False, 
                    include_reasoning_flag: bool = False) -> CLIInputs
```

#### Important Code Patterns

1. **Composable Argument Builders**: Separate functions for common groups:
   ```python
   parser = argparse.ArgumentParser(description=description)
   add_common_args(parser, require_tickers=require_tickers)
   add_date_args(parser, default_months_back=default_months_back)
   ```

2. **Interactive Questionary Integration**: Rich checkbox/select UIs:
   ```python
   choices = questionary.checkbox(
       "Select your AI analysts.",
       choices=[questionary.Choice(display, value=value) for display, value in ANALYST_ORDER],
       style=questionary.Style([("checkbox-selected", "fg:green"), ...])
   ).ask()
   ```

3. **Default Date Calculation**: Uses `dateutil.relativedelta` for natural date arithmetic:
   ```python
   if start_date:
       final_start = start_date
   else:
       months = default_months_back if default_months_back else 3
       end_date_obj = datetime.strptime(final_end, "%Y-%m-%d")
       final_start = (end_date_obj - relativedelta(months=months)).strftime("%Y-%m-%d")
   ```

#### Representative Code Snippets

**Snippet 1: Analyst Selection with Questionary**
```python
def select_analysts(flags: dict | None = None) -> list[str]:
    if flags and flags.get("analysts_all"):
        return [a[1] for a in ANALYST_ORDER]
    
    if flags and flags.get("analysts"):
        return [a.strip() for a in flags["analysts"].split(",") if a.strip()]
    
    choices = questionary.checkbox(
        "Select your AI analysts.",
        choices=[questionary.Choice(display, value=value) for display, value in ANALYST_ORDER],
        instruction="\n\nInstructions: \n1. Press Space to select/unselect analysts.\n2. Press 'a' to select/unselect all.\n3. Press Enter when done.",
        validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
        style=questionary.Style([
            ("checkbox-selected", "fg:green"),
            ("selected", "fg:green noinherit"),
        ])
    ).ask()
    
    if not choices:
        print("\n\nInterrupt received. Exiting...")
        sys.exit(0)
    
    print(f"\nSelected analysts: {', '.join(Fore.GREEN + c.title().replace('_', ' ') + Style.RESET_ALL for c in choices)}\n")
    return choices
```

**Snippet 2: Model Selection with Fallback Logic**
```python
def select_model(use_ollama: bool, model_flag: str | None = None) -> tuple[str, str]:
    if model_flag:
        model = find_model_by_name(model_flag)
        if model:
            print(f"\nUsing specified model: {Fore.CYAN}{model.provider.value}{Style.RESET_ALL} - {Fore.GREEN}{model.model_name}{Style.RESET_ALL}\n")
            return model.model_name, model.provider.value
        else:
            print(f"{Fore.RED}Model '{model_flag}' not found. Please select a model.{Style.RESET_ALL}")
    
    if use_ollama:
        print(f"{Fore.CYAN}Using Ollama for local LLM inference.{Style.RESET_ALL}")
        model_name = questionary.select(
            "Select your Ollama model:",
            choices=[questionary.Choice(display, value=value) for display, value, _ in OLLAMA_LLM_ORDER],
            style=questionary.Style([
                ("selected", "fg:green bold"),
                ("pointer", "fg:green bold"),
            ])
        ).ask()
        
        if not model_name:
            print("\n\nInterrupt received. Exiting...")
            sys.exit(0)
        
        if model_name == "-":
            model_name = questionary.text("Enter the custom model name:").ask()
            if not model_name:
                sys.exit(0)
        
        if not ensure_ollama_and_model(model_name):
            print(f"{Fore.RED}Cannot proceed without Ollama and the selected model.{Style.RESET_ALL}")
            sys.exit(1)
        
        return model_name, ModelProvider.OLLAMA.value
    
    # Default cloud LLM selection...
```

**Snippet 3: Comprehensive CLI Input Parsing**
```python
def parse_cli_inputs(description: str, require_tickers: bool, default_months_back: int | None,
                    include_graph_flag: bool = False, include_reasoning_flag: bool = False) -> CLIInputs:
    parser = argparse.ArgumentParser(description=description)
    
    add_common_args(parser, require_tickers=require_tickers)
    add_date_args(parser, default_months_back=default_months_back)
    
    parser.add_argument("--initial-cash", "--initial-capital", dest="initial_cash", 
                       type=float, default=100000.0)
    parser.add_argument("--margin-requirement", dest="margin_requirement", 
                       type=float, default=0.0)
    
    if include_reasoning_flag:
        parser.add_argument("--show-reasoning", action="store_true")
    if include_graph_flag:
        parser.add_argument("--show-agent-graph", action="store_true")
    
    args = parser.parse_args()
    
    # Normalize parsed values
    tickers = parse_tickers(getattr(args, "tickers", None))
    selected_analysts = select_analysts({
        "analysts_all": getattr(args, "analysts_all", False),
        "analysts": getattr(args, "analysts", None),
    })
    model_name, model_provider = select_model(getattr(args, "ollama", False), getattr(args, "model", None))
    start_date, end_date = resolve_dates(getattr(args, "start_date", None), 
                                        getattr(args, "end_date", None), 
                                        default_months_back=default_months_back)
    
    return CLIInputs(
        tickers=tickers,
        selected_analysts=selected_analysts,
        model_name=model_name,
        model_provider=model_provider,
        start_date=start_date,
        end_date=end_date,
        initial_cash=getattr(args, "initial_cash", 100000.0),
        margin_requirement=getattr(args, "margin_requirement", 0.0),
        show_reasoning=getattr(args, "show_reasoning", False),
        show_agent_graph=getattr(args, "show_agent_graph", False),
        raw_args=args,
    )
```

#### Connections to Other Modules
- **← Backtesting CLI**: Calls `select_analysts()`, `select_model()`
- **← Main System**: Calls `parse_cli_inputs()` at startup
- **→ LLM**: Uses `find_model_by_name()`, `get_model_info()`
- **→ Utils**: Uses `ANALYST_ORDER` from `analysts.py`

---

### 6. **Utility Functions** (`src/utils/`)

#### Purpose and Role
The utils module provides:
- Display formatting for trading output (tables, colors)
- LLM invocation helpers with retry logic
- API key management
- Progress tracking for multi-agent execution
- Analyst configuration registry
- Docker and Ollama integration helpers
- Visualization utilities

#### Key Components

**Analysts Configuration** (`analysts.py`):
```python
ANALYST_CONFIG = {
    "aswath_damodaran": {
        "display_name": "Aswath Damodaran",
        "description": "The Dean of Valuation",
        "investing_style": "...",
        "agent_func": aswath_damodaran_agent,
        "type": "analyst",
        "order": 0,
    },
    # ... 18 more analyst configs ...
}

ANALYST_ORDER = [(config["display_name"], key) for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])]
```

**Display Utilities** (`display.py`):
```python
def print_trading_output(result: dict) -> None
def print_backtest_results(table_rows: list) -> None
def format_backtest_row(date, ticker, action, quantity, price, ..., is_summary=False) -> list
```

**LLM Utilities** (`llm.py`):
```python
def call_llm(prompt, pydantic_model, agent_name: str | None = None, 
            state: AgentState | None = None, max_retries: int = 3) -> BaseModel

def create_default_response(model_class: type[BaseModel]) -> BaseModel

def extract_json_from_response(content: str) -> dict | None

def get_agent_model_config(state, agent_name) -> tuple[str, str]
```

**Progress Tracking** (`progress.py`):
```python
class AgentProgress:
    def __init__(self)
    def register_handler(self, handler: Callable) 
    def start(self)
    def stop(self)
    def update_status(self, agent_name: str, ticker: Optional[str] = None, status: str = "")
    def get_all_status(self) -> dict
    def _refresh_display(self)

progress = AgentProgress()  # Global singleton
```

**API Key Management** (`api_key.py`):
```python
def get_api_key_from_state(state: dict, api_key_name: str) -> str
```

#### Important Code Patterns

1. **Colored Output with Colorama**:
   ```python
   print(f"{Fore.GREEN}Bullish{Style.RESET_ALL}")
   print(f"{Fore.RED}Bearish{Style.RESET_ALL}")
   print(f"{Fore.YELLOW}Neutral{Style.RESET_ALL}")
   ```

2. **JSON Parsing with Markdown Extraction**:
   ```python
   def extract_json_from_response(content: str) -> dict | None:
       try:
           json_start = content.find("```json")
           if json_start != -1:
               json_text = content[json_start + 7:]
               json_end = json_text.find("```")
               if json_end != -1:
                   json_text = json_text[:json_end].strip()
                   return json.loads(json_text)
       except Exception:
           pass
       return None
   ```

3. **Default Response Factory**:
   ```python
   def create_default_response(model_class: type[BaseModel]) -> BaseModel:
       default_values = {}
       for field_name, field in model_class.model_fields.items():
           if field.annotation == str:
               default_values[field_name] = "Error in analysis, using default"
           elif field.annotation == float:
               default_values[field_name] = 0.0
           # ... more type handling ...
       return model_class(**default_values)
   ```

4. **Real-Time Progress Updates with Rich**:
   ```python
   class AgentProgress:
       def __init__(self):
           self.table = Table(show_header=False, box=None, padding=(0, 1))
           self.live = Live(self.table, console=console, refresh_per_second=4)
       
       def update_status(self, agent_name: str, ticker: Optional[str] = None, status: str = ""):
           # ... update internal state ...
           self._refresh_display()  # Updates live terminal display
   ```

#### Representative Code Snippets

**Snippet 1: Trading Output Display**
```python
def print_trading_output(result: dict) -> None:
    """Print formatted trading results with colored tables for multiple tickers."""
    decisions = result.get("decisions")
    
    for ticker, decision in decisions.items():
        print(f"\n{Fore.WHITE}{Style.BRIGHT}Analysis for {Fore.CYAN}{ticker}{Style.RESET_ALL}")
        
        # Prepare analyst signals table
        table_data = []
        for agent, signals in result.get("analyst_signals", {}).items():
            if ticker not in signals:
                continue
            
            signal = signals[ticker]
            agent_name = agent.replace("_agent", "").replace("_", " ").title()
            signal_type = signal.get("signal", "").upper()
            confidence = signal.get("confidence", 0)
            
            signal_color = {
                "BULLISH": Fore.GREEN,
                "BEARISH": Fore.RED,
                "NEUTRAL": Fore.YELLOW,
            }.get(signal_type, Fore.WHITE)
            
            table_data.append([
                f"{Fore.CYAN}{agent_name}{Style.RESET_ALL}",
                f"{signal_color}{signal_type}{Style.RESET_ALL}",
                f"{Fore.WHITE}{confidence}%{Style.RESET_ALL}",
                f"{Fore.WHITE}{reasoning_str}{Style.RESET_ALL}",
            ])
        
        print(tabulate(table_data, headers=["Agent", "Signal", "Confidence", "Reasoning"]))
```

**Snippet 2: LLM Call with Retry Logic**
```python
def call_llm(prompt, pydantic_model, agent_name: str | None = None,
            state: AgentState | None = None, max_retries: int = 3) -> BaseModel:
    """Makes an LLM call with retry logic, handling both JSON and non-JSON models."""
    
    # Extract model configuration
    if state and agent_name:
        model_name, model_provider = get_agent_model_config(state, agent_name)
    else:
        model_name = "gpt-4.1"
        model_provider = "OPENAI"
    
    model_info = get_model_info(model_name, model_provider)
    llm = get_model(model_name, model_provider, api_keys)
    
    # Use JSON mode if supported
    if not (model_info and not model_info.has_json_mode()):
        llm = llm.with_structured_output(pydantic_model, method="json_mode")
    
    # Call with retries
    for attempt in range(max_retries):
        try:
            result = llm.invoke(prompt)
            
            # For non-JSON models, parse manually
            if model_info and not model_info.has_json_mode():
                parsed_result = extract_json_from_response(result.content)
                if parsed_result:
                    return pydantic_model(**parsed_result)
            else:
                return result
        
        except Exception as e:
            if agent_name:
                progress.update_status(agent_name, None, f"Error - retry {attempt + 1}/{max_retries}")
            
            if attempt == max_retries - 1:
                if default_factory:
                    return default_factory()
                return create_default_response(pydantic_model)
    
    return create_default_response(pydantic_model)
```

**Snippet 3: Live Progress Tracking**
```python
class AgentProgress:
    def update_status(self, agent_name: str, ticker: Optional[str] = None, status: str = "", 
                     analysis: Optional[str] = None):
        """Update the status of an agent."""
        if agent_name not in self.agent_status:
            self.agent_status[agent_name] = {"status": "", "ticker": None}
        
        if ticker:
            self.agent_status[agent_name]["ticker"] = ticker
        if status:
            self.agent_status[agent_name]["status"] = status
        
        # Notify all registered handlers
        for handler in self.update_handlers:
            handler(agent_name, ticker, status, analysis, timestamp)
        
        self._refresh_display()

    def _refresh_display(self):
        """Refresh the progress display."""
        self.table.columns.clear()
        self.table.add_column(width=100)
        
        for agent_name, info in sorted(self.agent_status.items(), key=sort_key):
            status = info["status"]
            ticker = info["ticker"]
            
            if status.lower() == "done":
                style = Style(color="green", bold=True)
                symbol = "✓"
            elif status.lower() == "error":
                style = Style(color="red", bold=True)
                symbol = "✗"
            else:
                style = Style(color="yellow")
                symbol = "⋯"
            
            agent_display = self._get_display_name(agent_name)
            status_text = Text()
            status_text.append(f"{symbol} ", style=style)
            status_text.append(f"{agent_display:<20}", style=Style(bold=True))
            
            if ticker:
                status_text.append(f"[{ticker}] ", style=Style(color="cyan"))
            status_text.append(status, style=style)
            
            self.table.add_row(status_text)
```

**Snippet 4: Analyst Configuration Registry**
```python
ANALYST_CONFIG = {
    "aswath_damodaran": {
        "display_name": "Aswath Damodaran",
        "description": "The Dean of Valuation",
        "investing_style": "Focuses on intrinsic value and financial metrics...",
        "agent_func": aswath_damodaran_agent,
        "type": "analyst",
        "order": 0,
    },
    "ben_graham": {
        "display_name": "Ben Graham",
        "description": "The Father of Value Investing",
        "investing_style": "Emphasizes margin of safety...",
        "agent_func": ben_graham_agent,
        "type": "analyst",
        "order": 1,
    },
    # ... more analysts ...
}

# Create display tuple list sorted by order
ANALYST_ORDER = [(config["display_name"], key) for key, config in sorted(
    ANALYST_CONFIG.items(), key=lambda x: x[1]["order"]
)]
```

#### Connections to Other Modules
- **← Backtesting**: Calls `format_backtest_row()`, `print_backtest_results()`
- **← Main System**: Uses `call_llm()` throughout agent execution
- **← Agents**: Uses `progress.update_status()` for real-time feedback
- **← CLI**: Uses `ANALYST_ORDER` for analyst selection

---

## System Architecture & Integration

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI/Entry Point (src/main.py)                │
│  parse_cli_inputs → user selections → run_hedge_fund()          │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         v                               v
    ┌────────────┐              ┌──────────────────┐
    │  BacktestEngine (src/backtesting/engine.py) │
    │  - Prefetch data                            │
    │  - Daily loop                               │
    │  - Execute trades                           │
    │  - Calculate metrics                        │
    └────────────┬──────────────────────┘
         │       │
         │       ├─→ get_prices() ──┐
         │       ├─→ get_financial_metrics() ─────────┐
         │       ├─→ get_insider_trades() ────────────┼─→ [Cache] → Pydantic Models
         │       └─→ get_company_news() ─────────────┐│             (src/data/models.py)
         │                                           ││
         │       ┌────────────────────────────────────┘│
         │       v                                     │
         │   ┌──────────────────────────────┐          │
         │   │ API Tools (src/tools/api.py) │          │
         │   │ - HTTP requests              │          │
         │   │ - Rate limiting              │          │
         │   │ - Pagination                 │          │
         │   └──────────────────────────────┘          │
         │                                              │
         │   ┌──────────────────────────────────────────┘
         │   v
         │   ┌──────────────────────────────┐
         │   │ Financial API endpoints      │
         │   │ (financialdatasets.ai)       │
         │   └──────────────────────────────┘
         │
         v
    ┌────────────────────────┐
    │ Agent Controller       │
    │ run_agent() →          │
    │ Agent(Langgraph) →     │
    │ LLM (get_model())      │
    └────┬───────────────────┘
         │
         ├─→ Model Selection (src/llm/models.py)
         │   - Provider: OpenAI, Anthropic, Groq, etc.
         │   - JSON mode detection
         │
         ├─→ Agent Outputs
         │   (decisions, analyst_signals)
         │
         v
    ┌────────────────────────┐
    │ Trade Executor         │
    │ - Long buy/sell        │
    │ - Short open/cover     │
    │ - Margin enforcement   │
    └────┬───────────────────┘
         │
         v
    ┌────────────────────────┐
    │ Portfolio              │
    │ - Position tracking    │
    │ - Cash/margin          │
    │ - Realized gains       │
    └─────────────────────────┘
         │
         v
    ┌────────────────────────┐
    │ Valuation              │
    │ - Portfolio value      │
    │ - Exposures            │
    │ - Performance metrics  │
    └────┬───────────────────┘
         │
         v
    ┌────────────────────────┐
    │ Output Display         │
    │ (src/utils/display.py) │
    │ - Colored tables       │
    │ - Backtest results     │
    └────────────────────────┘
```

### Module Dependencies

```
backtesting/
├─ types.py (no deps except typing)
├─ portfolio.py → types.py
├─ trader.py → portfolio.py, types.py
├─ controller.py → portfolio.py, types.py
├─ metrics.py → types.py (pandas, numpy)
├─ valuation.py → portfolio.py
├─ output.py → portfolio.py, types.py, utils/display.py
├─ benchmarks.py → tools/api.py
├─ engine.py → ALL above + tools/api.py, utils
└─ cli.py → engine.py, llm/models.py, utils

data/
├─ models.py (pydantic only)
└─ cache.py (no deps)

tools/
├─ api.py → data/models.py, data/cache.py

llm/
└─ models.py → langchain providers

cli/
└─ input.py → llm/models.py, utils/analysts.py, utils/ollama.py

utils/
├─ analysts.py (agents module)
├─ display.py → utils/analysts.py, colorama, tabulate
├─ llm.py → llm/models.py, utils/progress.py
├─ api_key.py (minimal)
├─ progress.py → rich
├─ visualize.py → langgraph
└─ docker.py, ollama.py (external integrations)
```

---

## Key Design Decisions

### 1. **Portfolio Encapsulation with Snapshots**
- Portfolio maintains internal mutable state but exposes immutable `get_snapshot()` for agent consumption
- Prevents agents from accidentally modifying portfolio state
- Cost basis tracking ensures realistic P&L calculations

### 2. **TypedDict-Based Type System**
- Uses `TypedDict` instead of full Pydantic models for portfolio data
- Provides type hints while maintaining backward compatibility with dict-based code
- Enables drop-in refactoring of existing `src/backtester.py`

### 3. **Agent Decision Normalization**
- AgentController normalizes/validates agent outputs before execution
- Coerces string actions to enums, validates quantities, handles missing keys
- Decouples agent output format from execution requirements

### 4. **Rate Limiting with Linear Backoff**
- Uses linear (not exponential) backoff: 60s, 90s, 120s, 150s...
- Balances between avoiding request storms and quick recovery
- Respects API rate limits while preventing infinite loops

### 5. **Multi-Provider LLM Factory**
- Single `get_model()` function handles 12+ providers with provider-specific config
- Detects JSON mode support per model to enable/disable structured output
- Falls back to manual JSON parsing for non-JSON-supporting models

### 6. **Analyst Registry Pattern**
- Single `ANALYST_CONFIG` dict serves as SSOT for all analyst metadata
- Preserves order for UI display, enables dynamic agent graph construction
- Decouples analyst code organization from system integration

### 7. **CLI Input Normalization**
- `parse_cli_inputs()` returns structured `CLIInputs` dataclass
- Handles both interactive prompts and command-line arguments
- Supports feature flags for optional functionality (reasoning, graphs)

### 8. **Composite Cache Keys**
- Cache keys include all parameters (ticker, dates, limit) to avoid collisions
- Smart merging with key-field deduplication for incremental data
- Enables cross-day price data accumulation

---

## Configuration & Dependencies

### Python Version
- **Required**: Python 3.11+

### Core Dependencies
```toml
langchain = "^0.3.7"
langchain-anthropic = "0.3.5"
langchain-groq = "0.2.3"
langchain-openai = "^0.3.5"
langchain-deepseek = "^0.1.2"
langchain-ollama = "0.3.6"
langgraph = "0.2.56"
pandas = "^2.1.0"
numpy = "^1.24.0"
pydantic = "^2.4.2"
python-dotenv = "1.0.0"
matplotlib = "^3.9.2"
tabulate = "^0.9.0"
colorama = "^0.4.6"
questionary = "^2.1.0"
rich = "^13.9.4"
scipy = "^1.11.0"
```

### API Keys Required
```env
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=claude-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
GOOGLE_API_KEY=...
MOONSHOT_API_KEY=...  # Kimi
XAI_API_KEY=...

# Financial Data
FINANCIAL_DATASETS_API_KEY=...

# Optional: Ollama
OLLAMA_HOST=localhost
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Summary

The **AI Hedge Fund** is a sophisticated yet modular system that demonstrates:

1. **Clean Separation of Concerns**: Each module (backtesting, data, tools, LLM, CLI, utils) has a single, well-defined purpose
2. **Type Safety with Gradual Adoption**: Mix of TypedDict and Pydantic models enables flexible refactoring
3. **Robust External Integration**: Rate limiting, pagination, multi-provider support for resilience
4. **Interactive CLI with Structured Inputs**: Intuitive user experience with validation and normalization
5. **Real-Time Progress Tracking**: Live display of multi-agent execution
6. **Comprehensive Portfolio Accounting**: Proper handling of long/short positions, margin, and cost basis

The architecture supports educational exploration of AI-driven trading while maintaining production-grade practices for API resilience, error handling, and user experience.