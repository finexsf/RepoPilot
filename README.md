# RepoPilot

RepoPilot is an AI Software Onboarding Agent for first-time open-source contributors.

The demo focuses on a concrete loop:

1. Input a GitHub repository URL.
2. Fetch repository metadata, README, issues, and source files.
3. Parse code with Tree-sitter.
4. Build a lightweight CodeGraph from AST symbols, imports, calls, and file/module relations.
5. Generate an Overview, Architecture Map, Learning Path, Contribution Radar, Agent Trace, and Agent Chat.
6. Show how an agent helps a newcomer move from "unknown repository" to "first PR plan".

## Demo

<video src="D:\campus\夏令营\中科院软件所中文信息处理实验室\coding\repopilot演示讲解视频.mp4"></video>

## Run

```powershell
.\start.ps1
```

**I have deployed the complete system on a server. You can access it directly through your web browser without any additional installation or environment configuration. System URL: **

```
http://8.163.30.99:23133
```

The server listens on `0.0.0.0:8000`, so other devices on the same network can access it through your machine IP. Local access still works at `http://127.0.0.1:8000`.

Optional:

```powershell
$env:GITHUB_TOKEN="ghp_xxx"
```

DeepSeek full-process reasoning:

```powershell
Copy-Item .env.example .env
# Edit .env and set DEEPSEEK_API_KEY
```

**The system is currently integrated with the `DeepSeek-V4-Pro` model.**

RepoPilot uses DeepSeek across the whole analysis pipeline:

- README-grounded project overview in the same language as README.
- Tree-sitter + CodeGraph architecture reasoning and core-flow explanation.
- Personalized learning path and checkpoint quiz.
- First-contribution task planning from GitHub Issues or static fallback candidates.
- Multi-agent trace and reflection.
- Grounded Agent Chat over the current AnalysisResult for follow-up questions about setup, architecture, learning, and first PR strategy.

If the key is missing or the API call fails, RepoPilot automatically falls back to deterministic Tree-sitter + CodeGraph analysis, so the demo remains runnable offline.

## Demo Script

Use the default repository in the input box:

```text
https://github.com/pallets/flask
```

If a local copy of the target repository is already available, the system will, by default, bypass GitHub snapshot retrieval.

Recommended narration:

1. "RepoPilot is not a repository Q&A bot. It is an onboarding agent for first-time contributors."
2. Click **Analyze Repository** and point to the status strip: the system runs a multi-agent workflow.
3. Open **Overview**: show Files / Modules / Relations / Onboarding Score, then explain the 3-minute project summary and newcomer risks.
4. Open **Architecture**: explain that Tree-sitter extracts AST symbols/imports, CodeGraph ranks entry/module/utility nodes, and DeepSeek reasons over that evidence to produce the core flow. Click a node to show the inspector.
5. Open **Learning Path**: show how DeepSeek turns README + CodeGraph + user role into a route with Checkpoint Quiz, proving it is a tutor, not a static document.
6. Open **Contribution Radar**: show difficulty-impact matrix and the First PR Plan. If GitHub Issues are rate-limited, RepoPilot transparently generates simulated opportunities from docs/tests/CodeGraph, then DeepSeek rewrites them into contributor-facing tasks.
7. Open **Agent Trace**: explain Orchestrator, Repo Scanner, CodeGraph Agent, DeepSeek Reasoning Agent, Onboarding Planner, Contribution Advisor, and Reflection Agent.
8. Open **Agent Chat**: ask "Which file should I read first?" or "What is the core call chain?" to show a conversational agent grounded in the generated AnalysisResult rather than generic repository Q&A.

## MVP Scope

- Python and JavaScript/TypeScript parsing via Tree-sitter language pack.
- GitHub public repository analysis via REST API and codeload zip.
- SQLite persistence.
- Static frontend served by FastAPI.
- DeepSeek reasoning layer with deterministic fallback for demo stability.
