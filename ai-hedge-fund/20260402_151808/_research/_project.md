# AI Hedge Fund — Project Research

## Detected Depth: 2-level
The project has 8 sub-directories under src/, each with Python source files. No sub-sub-directories with source. This is a 2-level wiki.

## Module Classifications
- agents (L1+L2): 22 files, 9,384 lines — AI analyst agents modeled after famous investors
- backtesting (L1+L2): 10 files, 1,115 lines — Backtesting engine and portfolio management
- tools (L1+L2): 2 files, 371 lines — Financial data API wrappers
- data (L1+L2): 3 files, 245 lines — Pydantic data models and in-memory cache
- llm (L1+L2): 3 files, 242 lines — Multi-provider LLM model registry
- graph (L1+L2): 2 files, 51 lines — LangGraph workflow state
- utils (L1+L2): 8 files, 1,207 lines — Display, progress, LLM helpers, analyst config
- cli (L1+L2): 2 files, 288 lines — CLI input parsing and interactive prompts

## Cross-Module Dependencies
- main.py → agents, graph, utils, cli
- agents/* → graph.state, tools.api, utils.llm, utils.progress, data models
- backtesting → tools.api, main.run_hedge_fund, llm.models, utils.analysts
- tools.api → data.cache, data.models
- utils.llm → llm.models, graph.state
- cli.input → utils.analysts, llm.models, utils.ollama

## Language: Python (100% .py files)
## Total: 56 Python files, ~13,705 lines
