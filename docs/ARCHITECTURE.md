# RepoPilot MVP Architecture

## Modules

- Frontend: static workbench in `static/`, served by FastAPI.
- Backend: FastAPI routes in `app/main.py`.
- Agent layer: rule-stable MVP agents in `app/services/agents.py`.
- Data layer: SQLite persistence in `app/services/database.py`.
- Code parsing layer: `TreeSitterCodeGraph` in `app/services/codegraph.py`.
- GitHub integration layer: REST API and codeload zip in `app/services/github_service.py`.

## CodeGraph Route

```text
GitHub repository URL
  -> GitHub metadata / codeload zip
  -> file scan
  -> Tree-sitter AST parse
  -> symbols / imports / calls
  -> networkx directed CodeGraph
  -> module importance scores
  -> learning paths and first-contribution missions
```

## Demo Reliability

When GitHub Issues are unavailable because of API rate limits, RepoPilot generates local first-contribution candidates from docs, tests, and high-centrality CodeGraph modules. The trace panel marks this as a fallback so the demo remains transparent.
