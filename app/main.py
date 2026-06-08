from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from app.services.analysis_service import AnalysisService
from app.services.chat_agent import RepoChatAgent
from app.services.database import Database
from app.services.github_service import GitHubService, read_text
from app.services.translation_guard import TranslationGuard


load_dotenv()
db = Database("repopilot.db")
analysis_service = AnalysisService(db)
chat_agent = RepoChatAgent()
translation_guard = TranslationGuard()
github_service = GitHubService()

app = FastAPI(title="RepoPilot MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    user_profile: str = "beginner"
    goal: str = "first contribution"


class ChatRequest(BaseModel):
    analysis_id: int
    message: str
    history: list[dict[str, str]] = []
    lang: str = "zh"


@app.on_event("startup")
def on_startup() -> None:
    db.init()


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/api/repos/analyze")
def analyze_repo(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    repo_id = db.create_repository(str(payload.url), payload.user_profile, payload.goal)
    background_tasks.add_task(
        analysis_service.analyze,
        repo_id,
        str(payload.url),
        payload.user_profile,
        payload.goal,
    )
    return {"repo_id": repo_id, "status": "analyzing"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    repo_id = db.create_repository(str(payload.url), payload.user_profile, payload.goal)
    background_tasks.add_task(
        analysis_service.analyze,
        repo_id,
        str(payload.url),
        payload.user_profile,
        payload.goal,
    )
    return {"analysis_id": repo_id, "status": "analyzing"}


@app.get("/api/analysis/{analysis_id}")
def analysis_result(analysis_id: int, lang: str = "zh"):
    repo = db.get_repository(analysis_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return translation_guard.translate_result(db.get_analysis_result(analysis_id), lang)


@app.get("/api/analysis/{analysis_id}/file")
def analysis_file(analysis_id: int, path: str):
    repo_row = db.get_repository(analysis_id)
    if not repo_row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if not path or "\x00" in path:
        raise HTTPException(status_code=400, detail="Invalid file path")
    try:
        repo = github_service.parse_url(repo_row["url"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid repository URL") from exc
    root = github_service.local_repo_path(repo).resolve()
    target = (root / path).resolve()
    if root not in target.parents and target != root:
        raise HTTPException(status_code=400, detail="File path escapes repository")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found in local repository snapshot")
    max_bytes = 160_000
    content = read_text(target, max_bytes + 1)
    return {
        "analysis_id": analysis_id,
        "path": path,
        "language": target.suffix.lstrip(".") or "text",
        "size": target.stat().st_size,
        "truncated": target.stat().st_size > max_bytes,
        "content": content[:max_bytes],
    }


@app.get("/api/demo-analysis")
def demo_analysis(lang: str = "zh"):
    repo_id = db.get_latest_completed_repository_id()
    if repo_id is None:
        raise HTTPException(status_code=404, detail="No completed demo analysis found. Run Analyze Repository once first.")
    return translation_guard.translate_result(db.get_analysis_result(repo_id), lang)


@app.get("/api/graph/{analysis_id}")
def graph_result(analysis_id: int):
    return db.get_analysis_result(analysis_id).get("architecture_graph", {})


@app.get("/api/learning-path/{analysis_id}")
def learning_path_result(analysis_id: int):
    result = db.get_analysis_result(analysis_id)
    return {"learning_path": result.get("learning_path", []), "checkpoint_quiz": result.get("checkpoint_quiz", [])}


@app.get("/api/contributions/{analysis_id}")
def contributions_result(analysis_id: int):
    return {"contribution_tasks": db.get_analysis_result(analysis_id).get("contribution_tasks", [])}


@app.post("/api/chat")
def chat(payload: ChatRequest):
    repo = db.get_repository(payload.analysis_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    analysis = db.get_analysis_result(payload.analysis_id)
    return chat_agent.answer(analysis, payload.message, payload.history, payload.lang)


@app.get("/api/repos/{repo_id}/status")
def repo_status(repo_id: int):
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {
        "repo_id": repo_id,
        "status": repo["status"],
        "progress": repo["progress"],
        "current_step": repo["current_step"],
        "error": repo["error"],
    }


@app.get("/api/repos/{repo_id}/overview")
def repo_overview(repo_id: int):
    return db.get_overview(repo_id)


@app.get("/api/repos/{repo_id}/map")
def repo_map(repo_id: int):
    return db.get_code_map(repo_id)


@app.get("/api/repos/{repo_id}/learning-paths")
def learning_paths(repo_id: int):
    return {"paths": db.get_learning_paths(repo_id)}


@app.get("/api/repos/{repo_id}/issues")
def issues(repo_id: int):
    return {"issues": db.get_issues(repo_id)}


@app.post("/api/repos/{repo_id}/issues/{issue_id}/mission")
def mission(repo_id: int, issue_id: int):
    mission_id = analysis_service.create_mission(repo_id, issue_id)
    return db.get_mission(mission_id)


@app.get("/api/repos/{repo_id}/agent-traces")
def agent_traces(repo_id: int):
    return {"traces": db.get_agent_traces(repo_id)}
