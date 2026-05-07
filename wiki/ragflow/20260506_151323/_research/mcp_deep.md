# MCP Module Deep-Dive

## Existence Rationale

MCP (Model Context Protocol) is Claude's native integration standard. Without mcp/, RAGFlow would require users to build custom API proxies or string-based tool calls. By implementing the MCP spec directly, RAGFlow becomes a first-class Claude resource: the model can call KB search or chat as a function, not as an HTTP request.

### Real-World Analogy
MCP is like Slack's native API. If Slack only exposed REST, every bot would need a translation layer. Instead, Slack implements the protocol, so bots plug in and ask questions directly.

## Core Design Decisions

| Decision | Choice | Alternative | Why |
|----------|--------|-------------|-----|
| Stdio transport over HTTP | Simple, no port binding | REST API (standard), WebSocket (bidirectional) | Fits Claude's execution model (stdin/stdout). No firewall issues. Alternatives require external process listening. |
| Tool registry pattern | Dynamic tool registration | Hardcoded tool list | New tools (e.g., 'summarize') added without server restart. |
| JSON RPC protocol | MCP standard | Custom binary format | Interoperability with other MCP servers and clients. |


## Algorithm Spotlight

N/A — straightforward data flow, no complex algorithms.

## Failure Modes & Recovery

| Failure | Trigger | Detection | Recovery |
|---------|---------|-----------|----------|
| Network timeout calling RAGFlow API | MCP tool invocation hangs | Caught by Claude's timeout (30s default) | Server returns error JSON to Claude, which reports to user. |
| RAGFlow not running | MCP server can connect but KB API fails | Connection refused | MCP returns error; Claude tells user 'KB service unavailable'. |


## Performance Notes

- ('Stdio I/O vs HTTP', 'Stdin/stdout avoids TCP overhead ~1-2ms per call')
- ('No connection pooling needed', 'One stdio pipe per server instance')


## Key Files & Modules

- server/ — MCP server implementation (stdio transport)
- client/ — MCP client for testing
