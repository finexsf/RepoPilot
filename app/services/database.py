from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class Database:
    def __init__(self, path: str):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  owner TEXT,
                  name TEXT,
                  url TEXT NOT NULL,
                  user_profile TEXT,
                  goal TEXT,
                  description TEXT,
                  default_branch TEXT,
                  primary_language TEXT,
                  stars INTEGER DEFAULT 0,
                  forks INTEGER DEFAULT 0,
                  status TEXT NOT NULL,
                  progress INTEGER DEFAULT 0,
                  current_step TEXT DEFAULT '',
                  error TEXT,
                  created_at TEXT,
                  updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS repo_profiles (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  project_summary TEXT,
                  tech_stack_json TEXT,
                  demo_media_json TEXT,
                  demo_runbook_json TEXT,
                  command_hints_json TEXT,
                  readme_language TEXT,
                  readme_overview_source TEXT,
                  ai_summary TEXT,
                  architecture_insight TEXT,
                  learning_advice TEXT,
                  contribution_advice TEXT,
                  llm_provider TEXT,
                  llm_status TEXT,
                  snapshot_source TEXT,
                  llm_analysis_json TEXT,
                  install_command TEXT,
                  run_command TEXT,
                  test_command TEXT,
                  contribution_guide_summary TEXT,
                  newcomer_score INTEGER,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS modules (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  path TEXT NOT NULL,
                  name TEXT,
                  type TEXT,
                  importance_score INTEGER,
                  summary TEXT,
                  read_priority INTEGER,
                  symbols_json TEXT,
                  imports_json TEXT,
                  calls_json TEXT,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS module_edges (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  source TEXT NOT NULL,
                  target TEXT NOT NULL,
                  relation_type TEXT,
                  weight INTEGER DEFAULT 1,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS issues (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  github_issue_number INTEGER,
                  title TEXT,
                  body TEXT,
                  url TEXT,
                  labels_json TEXT,
                  state TEXT,
                  comments_count INTEGER,
                  created_at TEXT,
                  updated_at TEXT,
                  clarity_score INTEGER,
                  scope_score INTEGER,
                  testability_score INTEGER,
                  activity_score INTEGER,
                  beginner_score INTEGER,
                  recommended_reason TEXT,
                  risk_summary TEXT,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS learning_paths (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  user_profile TEXT,
                  duration_type TEXT,
                  title TEXT,
                  steps_json TEXT,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS contribution_missions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  issue_id INTEGER NOT NULL,
                  goal TEXT,
                  background TEXT,
                  files_to_read_json TEXT,
                  files_to_modify_json TEXT,
                  implementation_plan_json TEXT,
                  test_plan_json TEXT,
                  pr_checklist_json TEXT,
                  risk_points_json TEXT,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id),
                  FOREIGN KEY(issue_id) REFERENCES issues(id)
                );

                CREATE TABLE IF NOT EXISTS agent_traces (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repo_id INTEGER NOT NULL,
                  agent_name TEXT,
                  step_type TEXT,
                  message TEXT,
                  evidence_json TEXT,
                  created_at TEXT,
                  FOREIGN KEY(repo_id) REFERENCES repositories(id)
                );
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(repo_profiles)").fetchall()}
            if "demo_media_json" not in columns:
                conn.execute("ALTER TABLE repo_profiles ADD COLUMN demo_media_json TEXT")
            if "demo_runbook_json" not in columns:
                conn.execute("ALTER TABLE repo_profiles ADD COLUMN demo_runbook_json TEXT")
            if "command_hints_json" not in columns:
                conn.execute("ALTER TABLE repo_profiles ADD COLUMN command_hints_json TEXT")
            for column in ["ai_summary", "architecture_insight", "learning_advice", "contribution_advice", "llm_provider", "llm_status"]:
                if column not in columns:
                    conn.execute(f"ALTER TABLE repo_profiles ADD COLUMN {column} TEXT")
            if "snapshot_source" not in columns:
                conn.execute("ALTER TABLE repo_profiles ADD COLUMN snapshot_source TEXT")
            if "llm_analysis_json" not in columns:
                conn.execute("ALTER TABLE repo_profiles ADD COLUMN llm_analysis_json TEXT")
            for column in ["readme_language", "readme_overview_source"]:
                if column not in columns:
                    conn.execute(f"ALTER TABLE repo_profiles ADD COLUMN {column} TEXT")
            module_columns = {row["name"] for row in conn.execute("PRAGMA table_info(modules)").fetchall()}
            if "imports_json" not in module_columns:
                conn.execute("ALTER TABLE modules ADD COLUMN imports_json TEXT")
            if "calls_json" not in module_columns:
                conn.execute("ALTER TABLE modules ADD COLUMN calls_json TEXT")

    def create_repository(self, url: str, user_profile: str, goal: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO repositories
                (url, user_profile, goal, status, progress, current_step, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', 0, 'Queued', ?, ?)
                """,
                (url, user_profile, goal, now(), now()),
            )
            return int(cur.lastrowid)

    def update_repo(self, repo_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = now()
        names = ", ".join(f"{key}=?" for key in fields)
        values = list(fields.values()) + [repo_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE repositories SET {names} WHERE id=?", values)

    def get_repository(self, repo_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone()
            return dict(row) if row else None

    def get_latest_completed_repository_id(self) -> int | None:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM repositories WHERE status='completed' ORDER BY id DESC LIMIT 1").fetchone()
            return int(row["id"]) if row else None

    def add_trace(self, repo_id: int, agent: str, step_type: str, message: str, evidence: Any = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_traces
                (repo_id, agent_name, step_type, message, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (repo_id, agent, step_type, message, json.dumps(evidence or [], ensure_ascii=False), now()),
            )

    def replace_profile(self, repo_id: int, profile: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM repo_profiles WHERE repo_id=?", (repo_id,))
            conn.execute(
                """
                INSERT INTO repo_profiles
                (repo_id, project_summary, tech_stack_json, demo_media_json, demo_runbook_json, command_hints_json,
                 readme_language, readme_overview_source,
                 ai_summary, architecture_insight, learning_advice, contribution_advice, llm_provider, llm_status, snapshot_source, llm_analysis_json,
                 install_command, run_command, test_command, contribution_guide_summary, newcomer_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_id,
                    profile.get("project_summary"),
                    json.dumps(profile.get("tech_stack", []), ensure_ascii=False),
                    json.dumps(profile.get("demo_media", []), ensure_ascii=False),
                    json.dumps(profile.get("demo_runbook", []), ensure_ascii=False),
                    json.dumps(profile.get("command_hints", {}), ensure_ascii=False),
                    profile.get("readme_language"),
                    profile.get("readme_overview_source"),
                    profile.get("ai_summary"),
                    profile.get("architecture_insight"),
                    profile.get("learning_advice"),
                    profile.get("contribution_advice"),
                    profile.get("llm_provider"),
                    profile.get("llm_status"),
                    profile.get("snapshot_source"),
                    json.dumps(profile.get("llm_analysis", {}), ensure_ascii=False),
                    profile.get("install_command"),
                    profile.get("run_command"),
                    profile.get("test_command"),
                    profile.get("contribution_guide_summary"),
                    profile.get("newcomer_score", 60),
                ),
            )

    def replace_modules(self, repo_id: int, modules: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM modules WHERE repo_id=?", (repo_id,))
            conn.execute("DELETE FROM module_edges WHERE repo_id=?", (repo_id,))
            for module in modules:
                conn.execute(
                    """
                    INSERT INTO modules
                    (repo_id, path, name, type, importance_score, summary, read_priority, symbols_json, imports_json, calls_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        repo_id,
                        module["path"],
                        module.get("name"),
                        module.get("type"),
                        module.get("importance_score", 0),
                        module.get("summary"),
                        module.get("read_priority", 99),
                        json.dumps(module.get("symbols", []), ensure_ascii=False),
                        json.dumps(module.get("imports", []), ensure_ascii=False),
                        json.dumps(module.get("calls", []), ensure_ascii=False),
                    ),
                )
            for edge in edges:
                conn.execute(
                    """
                    INSERT INTO module_edges
                    (repo_id, source, target, relation_type, weight)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (repo_id, edge["source"], edge["target"], edge.get("relation_type"), edge.get("weight", 1)),
                )

    def replace_issues(self, repo_id: int, issues: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM issues WHERE repo_id=?", (repo_id,))
            for issue in issues:
                conn.execute(
                    """
                    INSERT INTO issues
                    (repo_id, github_issue_number, title, body, url, labels_json, state, comments_count,
                     created_at, updated_at, clarity_score, scope_score, testability_score, activity_score,
                     beginner_score, recommended_reason, risk_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        repo_id,
                        issue.get("number"),
                        issue.get("title"),
                        issue.get("body"),
                        issue.get("url"),
                        json.dumps(issue.get("labels", []), ensure_ascii=False),
                        issue.get("state"),
                        issue.get("comments_count", 0),
                        issue.get("created_at"),
                        issue.get("updated_at"),
                        issue.get("clarity_score"),
                        issue.get("scope_score"),
                        issue.get("testability_score"),
                        issue.get("activity_score"),
                        issue.get("beginner_score"),
                        issue.get("recommended_reason"),
                        issue.get("risk_summary"),
                    ),
                )

    def replace_learning_paths(self, repo_id: int, paths: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM learning_paths WHERE repo_id=?", (repo_id,))
            for path in paths:
                conn.execute(
                    """
                    INSERT INTO learning_paths
                    (repo_id, user_profile, duration_type, title, steps_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        repo_id,
                        path.get("user_profile"),
                        path.get("duration_type"),
                        path.get("title"),
                        json.dumps(path.get("steps", []), ensure_ascii=False),
                    ),
                )

    def create_mission(self, repo_id: int, issue_id: int, mission: dict[str, Any]) -> int:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM contribution_missions WHERE repo_id=? AND issue_id=?",
                (repo_id, issue_id),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM contribution_missions WHERE id=?", (existing["id"],))
            cur = conn.execute(
                """
                INSERT INTO contribution_missions
                (repo_id, issue_id, goal, background, files_to_read_json, files_to_modify_json,
                 implementation_plan_json, test_plan_json, pr_checklist_json, risk_points_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_id,
                    issue_id,
                    mission.get("goal"),
                    mission.get("background"),
                    json.dumps(mission.get("files_to_read", []), ensure_ascii=False),
                    json.dumps(mission.get("files_to_modify", []), ensure_ascii=False),
                    json.dumps(mission.get("implementation_plan", []), ensure_ascii=False),
                    json.dumps(mission.get("test_plan", []), ensure_ascii=False),
                    json.dumps(mission.get("pr_checklist", []), ensure_ascii=False),
                    json.dumps(mission.get("risk_points", []), ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def get_overview(self, repo_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            repo = conn.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone()
            profile = conn.execute("SELECT * FROM repo_profiles WHERE repo_id=?", (repo_id,)).fetchone()
            if not repo:
                return {}
            result = dict(repo)
            if profile:
                result.update(dict(profile))
                result["tech_stack"] = json.loads(result.pop("tech_stack_json") or "[]")
                result["demo_media"] = json.loads(result.pop("demo_media_json", None) or "[]")
                result["demo_runbook"] = json.loads(result.pop("demo_runbook_json", None) or "[]")
                result["command_hints"] = json.loads(result.pop("command_hints_json", None) or "{}")
                result["llm_analysis"] = json.loads(result.pop("llm_analysis_json", None) or "{}")
            return result

    def get_code_map(self, repo_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            nodes = [dict(row) for row in conn.execute("SELECT * FROM modules WHERE repo_id=? ORDER BY read_priority, importance_score DESC", (repo_id,))]
            edges = [dict(row) for row in conn.execute("SELECT * FROM module_edges WHERE repo_id=?", (repo_id,))]
        for node in nodes:
            node["symbols"] = json.loads(node.pop("symbols_json") or "[]")
            node["imports"] = json.loads(node.pop("imports_json", None) or "[]")
            node["calls"] = json.loads(node.pop("calls_json", None) or "[]")
            node["id"] = node["path"]
        return {"nodes": nodes, "edges": edges}

    def get_learning_paths(self, repo_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM learning_paths WHERE repo_id=?", (repo_id,))]
        for row in rows:
            row["steps"] = json.loads(row.pop("steps_json") or "[]")
        return rows

    def get_issues(self, repo_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM issues WHERE repo_id=? ORDER BY beginner_score DESC", (repo_id,))]
        for row in rows:
            row["labels"] = json.loads(row.pop("labels_json") or "[]")
        return rows

    def get_issue(self, repo_id: int, issue_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM issues WHERE repo_id=? AND id=?", (repo_id, issue_id)).fetchone()
            if not row:
                return None
            result = dict(row)
            result["labels"] = json.loads(result.pop("labels_json") or "[]")
            return result

    def get_mission(self, mission_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM contribution_missions WHERE id=?", (mission_id,)).fetchone()
            if not row:
                return {}
            result = dict(row)
        for key in ["files_to_read", "files_to_modify", "implementation_plan", "test_plan", "pr_checklist", "risk_points"]:
            result[key] = json.loads(result.pop(f"{key}_json") or "[]")
        return result

    def get_agent_traces(self, repo_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM agent_traces WHERE repo_id=? ORDER BY id", (repo_id,))]
        for row in rows:
            row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
        return rows

    def get_analysis_result(self, repo_id: int) -> dict[str, Any]:
        repo = self.get_repository(repo_id) or {}
        overview = self.get_overview(repo_id)
        graph = self.get_code_map(repo_id)
        paths = self.get_learning_paths(repo_id)
        issues = self.get_issues(repo_id)
        traces = self.get_agent_traces(repo_id)

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        files_count = self.extract_file_count(traces) or len(nodes)
        modules_count = len([node for node in nodes if node.get("type") == "source"])
        score = int(overview.get("newcomer_score") or 0)
        important_files = self.important_files(nodes, edges)
        known_paths = {node.get("path") for node in nodes if node.get("path")}
        known_paths.update(item["path"] for item in important_files if item.get("path"))
        risks = self.risks(overview, nodes, edges, issues)
        summary = self.three_minute_summary(overview, important_files, risks)
        architecture_graph = self.architecture_graph(nodes, edges)
        learning_path, quiz = self.learning_path(paths, important_files, repo.get("user_profile"), repo.get("goal"))
        tasks = self.contribution_tasks(issues, important_files, nodes)
        agent_trace = self.agent_trace(traces, repo, nodes, edges, tasks)
        reflection = self.reflection(overview, nodes, edges, issues)
        setup_guide = self.setup_guide(overview, important_files)
        feature_runbook = self.clean_llm_feature_runbook(overview.get("demo_runbook"), known_paths, overview.get("demo_media", [])) or self.feature_runbook(overview, important_files, overview.get("demo_media", []))
        workflow_guide = self.workflow_guide(overview, important_files)
        requirement_coverage = self.requirement_coverage(architecture_graph, learning_path, tasks, workflow_guide)
        llm_analysis = overview.get("llm_analysis") or {}
        llm_profile = llm_analysis.get("repo_profile") if isinstance(llm_analysis.get("repo_profile"), dict) else {}
        ui_zh = self.clean_llm_ui_zh(llm_analysis.get("ui_translations"))
        zh_profile = ui_zh.get("repo_profile", {})
        if llm_profile.get("risks"):
            risks = [str(item) for item in llm_profile.get("risks", []) if str(item).strip()][:4] or risks
        llm_setup = self.clean_llm_setup_guide(llm_analysis.get("setup_guide"))
        if llm_setup:
            setup_guide = llm_setup
        llm_feature_runbook = self.clean_llm_feature_runbook(llm_analysis.get("feature_runbook"), known_paths, overview.get("demo_media", []))
        if llm_feature_runbook and not overview.get("demo_runbook"):
            feature_runbook = llm_feature_runbook
        llm_workflow = self.clean_llm_workflow_guide(llm_analysis.get("workflow_guide"), known_paths)
        if llm_workflow:
            workflow_guide = llm_workflow
        llm_requirement_coverage = self.clean_llm_requirement_coverage(llm_analysis.get("requirement_coverage"))
        if llm_requirement_coverage:
            requirement_coverage = llm_requirement_coverage
        if isinstance(llm_analysis.get("architecture_graph"), dict):
            llm_graph = llm_analysis["architecture_graph"]
            layers = self.clean_llm_architecture_layers(llm_graph.get("layers"), known_paths)
            if layers:
                architecture_graph["layers"] = layers
            core_flow = self.clean_llm_core_flow(llm_graph.get("core_flow"), known_paths)
            if core_flow:
                architecture_graph["core_flow"] = core_flow
                architecture_graph["notice"] = (
                    "Static analysis based on Tree-sitter AST and imports, with DeepSeek reasoning over the CodeGraph."
                )
            if llm_graph.get("insight"):
                architecture_graph["insight"] = str(llm_graph["insight"])
            if llm_graph.get("flow_story"):
                architecture_graph["flow_story"] = str(llm_graph["flow_story"])
            relationships = self.clean_llm_relationships(llm_graph.get("relationships"), known_paths)
            if relationships:
                architecture_graph["relationships"] = relationships
            module_notes = self.clean_llm_module_notes(llm_graph.get("module_notes"), known_paths)
            if module_notes:
                architecture_graph["module_notes"] = module_notes
        llm_learning = self.clean_llm_learning_path(llm_analysis.get("learning_path"), known_paths)
        if llm_learning:
            learning_path = llm_learning
        llm_quiz = self.clean_llm_quiz(llm_analysis.get("checkpoint_quiz"))
        if llm_quiz:
            quiz = llm_quiz
        llm_tasks = self.clean_llm_tasks(llm_analysis.get("contribution_tasks"), known_paths)
        if llm_tasks:
            tasks = llm_tasks
        contribution_strategy = self.clean_llm_contribution_strategy(llm_analysis.get("contribution_strategy"))
        llm_trace = self.clean_llm_trace(llm_analysis.get("agent_trace"))
        if llm_trace:
            agent_trace = llm_trace
        if isinstance(llm_analysis.get("reflection"), dict) and llm_analysis["reflection"]:
            reflection = self.merge_reflection(reflection, llm_analysis["reflection"])
        overview_cards = self.clean_llm_overview_cards(llm_analysis.get("overview_cards"))
        if not overview_cards:
            overview_cards = self.derived_deepseek_overview_cards(llm_profile, architecture_graph, learning_path, tasks, contribution_strategy)

        return {
            "id": repo_id,
            "status": repo.get("status"),
            "progress": repo.get("progress"),
            "current_step": repo.get("current_step"),
            "error": repo.get("error"),
            "repo_profile": {
                "owner": overview.get("owner"),
                "name": overview.get("name"),
                "url": overview.get("url"),
                "description": overview.get("description"),
                "one_liner": llm_profile.get("one_liner") or overview.get("project_summary") or overview.get("description") or "Repository analyzed by RepoPilot.",
                "zh_one_liner": zh_profile.get("one_liner"),
                "readme_language": overview.get("readme_language") or "en",
                "ai_summary": overview.get("ai_summary"),
                "architecture_insight": overview.get("architecture_insight"),
                "learning_advice": overview.get("learning_advice"),
                "contribution_advice": overview.get("contribution_advice"),
                "llm_provider": overview.get("llm_provider") or "deterministic fallback",
                "llm_status": overview.get("llm_status") or "disabled",
                "snapshot_source": overview.get("snapshot_source") or "unknown",
                "primary_language": overview.get("primary_language") or "-",
                "install_command": self.display_command(overview.get("install_command")),
                "run_command": self.display_command(overview.get("run_command")),
                "test_command": self.display_command(overview.get("test_command")),
                "onboarding_score": score,
                "cognitive_summary": llm_profile.get("cognitive_summary") or overview.get("ai_summary") or summary,
                "zh_cognitive_summary": zh_profile.get("cognitive_summary"),
                "zh_risks": zh_profile.get("risks", []),
                "risks": risks,
                "demo_media": overview.get("demo_media", []),
                "setup_guide": setup_guide,
                "feature_runbook": feature_runbook,
                "workflow_guide": workflow_guide,
                "requirement_coverage": requirement_coverage,
                "overview_cards": ui_zh.get("overview_cards") or overview_cards,
            },
            "metrics": {
                "files": files_count,
                "modules": modules_count,
                "relations": len(edges),
                "onboarding_score": score,
            },
            "tech_stack": overview.get("tech_stack", []),
            "important_files": important_files,
            "architecture_graph": architecture_graph,
            "learning_path": learning_path,
            "checkpoint_quiz": quiz,
            "contribution_tasks": tasks,
            "contribution_strategy": contribution_strategy,
            "agent_trace": agent_trace,
            "reflection": reflection,
        }

    def clean_llm_overview_cards(self, cards: Any) -> list[dict[str, str]]:
        if not isinstance(cards, list):
            return []
        cleaned = []
        for item in cards[:6]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            value = str(item.get("value") or "").strip()
            if label and value:
                cleaned.append(
                    {
                        "label": label[:60],
                        "value": value[:120],
                        "explanation": str(item.get("explanation") or "")[:260],
                    }
                )
        return cleaned

    def clean_llm_ui_zh(self, translations: Any) -> dict[str, Any]:
        if not isinstance(translations, dict):
            return {}
        zh = translations.get("zh")
        if not isinstance(zh, dict):
            return {}
        profile = zh.get("repo_profile") if isinstance(zh.get("repo_profile"), dict) else {}
        result = {
            "repo_profile": {
                "one_liner": str(profile.get("one_liner") or "")[:500],
                "cognitive_summary": str(profile.get("cognitive_summary") or "")[:1600],
                "risks": [str(item)[:260] for item in profile.get("risks", []) if str(item).strip()][:5],
            },
            "overview_cards": self.clean_llm_overview_cards(zh.get("overview_cards")),
        }
        return result

    def derived_deepseek_overview_cards(
        self,
        llm_profile: dict[str, Any],
        architecture_graph: dict[str, Any],
        learning_path: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        contribution_strategy: dict[str, Any],
    ) -> list[dict[str, str]]:
        cards = []
        if llm_profile.get("one_liner"):
            cards.append(
                {
                    "label": "Project Position",
                    "value": str(llm_profile["one_liner"])[:120],
                    "explanation": "Derived from DeepSeek's README-grounded repository positioning.",
                }
            )
        if architecture_graph.get("layers"):
            cards.append(
                {
                    "label": "Architecture Reading",
                    "value": f"{len(architecture_graph.get('layers', []))} semantic layers",
                    "explanation": str(architecture_graph.get("insight") or architecture_graph.get("flow_story") or "DeepSeek reconstructed the architecture from CodeGraph evidence.")[:260],
                }
            )
        if learning_path:
            cards.append(
                {
                    "label": "Learning Route",
                    "value": f"{len(learning_path)} guided steps",
                    "explanation": "DeepSeek generated a role-aware route with files, reasons, and checkpoints.",
                }
            )
        if tasks:
            cards.append(
                {
                    "label": "First PR Focus",
                    "value": contribution_strategy.get("best_first_task") or tasks[0].get("title") or "First contribution task",
                    "explanation": contribution_strategy.get("selection_reason") or "DeepSeek ranked contribution tasks by newcomer fit, impact, and risk.",
                }
            )
        return cards[:4]

    def clean_llm_setup_guide(self, steps: Any) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []
        cleaned = []
        for item in steps[:7]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            commands = [str(value)[:900] for value in item.get("commands", []) if self.is_useful_command(value)][:6]
            if title and commands:
                cleaned.append(
                    {
                        "title": title[:90],
                        "commands": commands,
                        "reason": str(item.get("reason") or "")[:320],
                    }
                )
        return cleaned

    def clean_llm_feature_runbook(self, runbook: Any, known_paths: set[str], media: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(runbook, list):
            return []
        media_by_feature: dict[str, list[dict[str, Any]]] = {}
        for item in media:
            media_by_feature.setdefault(str(item.get("feature") or ""), []).append(item)
        cleaned = []
        for item in runbook[:6]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            files = [str(path) for path in item.get("files", []) if str(path) in known_paths][:6]
            commands = [str(value)[:900] for value in item.get("commands", []) if self.is_useful_command(value)][:6]
            if not name or not (files or commands):
                continue
            media_features = [str(value) for value in item.get("media_features", []) if str(value).strip()]
            selected_media = []
            for feature in media_features:
                selected_media.extend(media_by_feature.get(feature, []))
            if not selected_media:
                selected_media = media_by_feature.get(name, [])[:2]
            cleaned.append(
                {
                    "name": name[:90],
                    "purpose": str(item.get("purpose") or "")[:360],
                    "commands": commands,
                    "files": files,
                    "media": selected_media[:3],
                }
            )
        return cleaned

    def clean_llm_workflow_guide(self, workflow: Any, known_paths: set[str]) -> dict[str, Any]:
        if not isinstance(workflow, dict):
            return {}
        title = str(workflow.get("title") or "").strip()
        evidence_files = [str(path) for path in workflow.get("evidence_files", []) if str(path) in known_paths][:8]
        commands = [str(value)[:900] for value in workflow.get("commands", []) if self.is_useful_command(value)][:6]
        checklist = [str(value)[:180] for value in workflow.get("checklist", []) if str(value).strip()][:8]
        standards = [str(value)[:180] for value in workflow.get("standards", []) if str(value).strip()][:8]
        if not any([title, evidence_files, commands, checklist, standards]):
            return {}
        return {
            "title": title[:100] or "Development Workflow",
            "evidence_files": evidence_files,
            "commands": commands,
            "checklist": checklist,
            "standards": standards,
        }

    def clean_llm_requirement_coverage(self, coverage: Any) -> list[dict[str, str]]:
        if not isinstance(coverage, list):
            return []
        cleaned = []
        for item in coverage[:7]:
            if not isinstance(item, dict):
                continue
            requirement = str(item.get("requirement") or "").strip()
            implementation = str(item.get("implementation") or "").strip()
            if requirement and implementation:
                cleaned.append({"requirement": requirement[:180], "implementation": implementation[:360]})
        return cleaned

    def clean_llm_architecture_layers(self, layers: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(layers, list):
            return []
        cleaned = []
        for index, item in enumerate(layers[:8], start=1):
            if not isinstance(item, dict):
                continue
            files = [str(path) for path in item.get("files", []) if str(path) in known_paths][:6]
            if not files:
                continue
            layer_type = str(item.get("type") or "domain").strip().lower()
            if layer_type not in {"entry", "ui", "service", "domain", "integration", "runtime", "test", "docs"}:
                layer_type = "domain"
            cleaned.append(
                {
                    "index": index,
                    "name": str(item.get("name") or f"Layer {index}")[:80],
                    "type": layer_type,
                    "description": str(item.get("description") or "Architecture layer inferred by DeepSeek from CodeGraph evidence.")[:420],
                    "files": files,
                    "why_newcomers_read_it": str(item.get("why_newcomers_read_it") or "This layer helps newcomers connect the project goal to concrete code.")[:320],
                }
            )
        return cleaned

    def clean_llm_core_flow(self, flow: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(flow, list):
            return []
        cleaned = []
        for index, item in enumerate(flow[:7], start=1):
            if not isinstance(item, dict):
                continue
            path = str(item.get("file") or "").strip()
            if path not in known_paths:
                continue
            cleaned.append(
                {
                    "step": int(item.get("step") or index),
                    "file": path,
                    "role": str(item.get("role") or "module")[:24],
                    "summary": str(item.get("summary") or "Selected by DeepSeek from Tree-sitter CodeGraph evidence.")[:320],
                }
            )
        return cleaned

    def clean_llm_learning_path(self, steps: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []
        cleaned = []
        for index, item in enumerate(steps[:7], start=1):
            if not isinstance(item, dict):
                continue
            files = [str(path) for path in item.get("files", []) if str(path) in known_paths][:5]
            cleaned.append(
                {
                    "index": int(item.get("index") or index),
                    "title": str(item.get("title") or f"Learning step {index}")[:120],
                    "objective": str(item.get("objective") or "Understand repository behavior.")[:360],
                    "files": files,
                    "reason": str(item.get("reason") or "Generated by DeepSeek from README and CodeGraph evidence.")[:360],
                    "estimated_time": str(item.get("estimated_time") or "15 min")[:40],
                    "checkpoint": str(item.get("checkpoint") or "Can you explain this step in your own words?")[:220],
                }
            )
        return cleaned

    def clean_llm_quiz(self, quiz: Any) -> list[dict[str, str]]:
        if not isinstance(quiz, list):
            return []
        cleaned = []
        for item in quiz[:5]:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if question and answer:
                cleaned.append({"question": question[:220], "answer": answer[:260]})
        return cleaned

    def clean_llm_relationships(self, relationships: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(relationships, list):
            return []
        cleaned = []
        for item in relationships[:28]:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or "").strip()
            target = str(item.get("target") or "").strip()
            if source not in known_paths or target not in known_paths:
                continue
            cleaned.append(
                {
                    "source": source,
                    "target": target,
                    "type": str(item.get("type") or "uses")[:40],
                    "weight": self.clamp_int(item.get("weight"), 1, 10, 2),
                    "explanation": str(item.get("explanation") or "DeepSeek inferred this architectural relationship from CodeGraph evidence.")[:420],
                }
            )
        return cleaned

    def clean_llm_module_notes(self, notes: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(notes, list):
            return []
        cleaned = []
        for item in notes[:14]:
            if not isinstance(item, dict):
                continue
            file = str(item.get("file") or "").strip()
            if file not in known_paths:
                continue
            cleaned.append(
                {
                    "file": file,
                    "responsibility": str(item.get("responsibility") or "")[:360],
                    "key_symbols": [str(value)[:80] for value in item.get("key_symbols", []) if str(value).strip()][:8],
                    "key_calls": [str(value)[:80] for value in item.get("key_calls", []) if str(value).strip()][:8],
                    "read_after": [str(value) for value in item.get("read_after", []) if str(value) in known_paths][:5],
                    "read_before": [str(value) for value in item.get("read_before", []) if str(value) in known_paths][:5],
                }
            )
        return cleaned

    def clean_llm_tasks(self, tasks: Any, known_paths: set[str]) -> list[dict[str, Any]]:
        if not isinstance(tasks, list):
            return []
        cleaned = []
        for index, item in enumerate(tasks[:6], start=1):
            if not isinstance(item, dict):
                continue
            files = [str(path) for path in item.get("files", []) if str(path) in known_paths][:4]
            plan = [str(step)[:220] for step in item.get("first_pr_plan", []) if str(step).strip()][:5]
            if not files or not plan:
                continue
            difficulty = str(item.get("difficulty") or "Beginner")
            if difficulty not in {"Beginner", "Intermediate", "Advanced"}:
                difficulty = "Beginner"
            cleaned.append(
                {
                    "id": f"deepseek-{index}",
                    "title": str(item.get("title") or f"DeepSeek first contribution task {index}")[:180],
                    "source": "DeepSeek reasoning over GitHub Issues and static CodeGraph",
                    "difficulty": difficulty,
                    "difficulty_score": self.clamp_int(item.get("difficulty_score"), 10, 95, 35),
                    "impact_score": self.clamp_int(item.get("impact_score"), 20, 95, 70),
                    "reason": str(item.get("reason") or "Selected by DeepSeek as a bounded first PR opportunity.")[:420],
                    "files": files,
                    "knowledge": [str(point)[:80] for point in item.get("knowledge", []) if str(point).strip()][:5],
                    "first_pr_plan": plan,
                    "risk": str(item.get("risk") or "Confirm scope before editing.")[:260],
                    "evidence": [str(value)[:180] for value in item.get("evidence", []) if str(value).strip()][:5],
                    "verification": [str(value)[:160] for value in item.get("verification", []) if str(value).strip()][:5],
                    "pr_title": str(item.get("pr_title") or "")[:140],
                    "maintainer_pitch": str(item.get("maintainer_pitch") or "")[:360],
                    "url": str(item.get("url") or ""),
                }
            )
        return cleaned

    def clean_llm_contribution_strategy(self, strategy: Any) -> dict[str, Any]:
        if not isinstance(strategy, dict):
            return {}
        return {
            "summary": str(strategy.get("summary") or "")[:520],
            "best_first_task": str(strategy.get("best_first_task") or "")[:180],
            "selection_reason": str(strategy.get("selection_reason") or "")[:420],
            "avoid_for_first_pr": [str(value)[:160] for value in strategy.get("avoid_for_first_pr", []) if str(value).strip()][:5],
        }

    def clean_llm_trace(self, trace: Any) -> list[dict[str, Any]]:
        if not isinstance(trace, list):
            return []
        cleaned = []
        for item in trace[:8]:
            if not isinstance(item, dict):
                continue
            agent = str(item.get("agent") or "").strip()
            if not agent:
                continue
            cleaned.append(
                {
                    "agent": agent[:80],
                    "input": str(item.get("input") or "")[:260],
                    "action": str(item.get("action") or "")[:260],
                    "output": str(item.get("output") or "")[:260],
                    "confidence": self.clamp_float(item.get("confidence"), 0.05, 0.99, 0.82),
                    "next_step": str(item.get("next_step") or "")[:180],
                }
            )
        return cleaned

    def merge_reflection(self, fallback: dict[str, Any], llm_reflection: dict[str, Any]) -> dict[str, Any]:
        return {
            "limitations": [str(item) for item in llm_reflection.get("limitations", []) if str(item).strip()][:5]
            or fallback.get("limitations", []),
            "possibly_missing": [str(item) for item in llm_reflection.get("possibly_missing", []) if str(item).strip()][:5]
            or fallback.get("possibly_missing", []),
            "recommended_next_input": [str(item) for item in llm_reflection.get("recommended_next_input", []) if str(item).strip()][:5]
            or fallback.get("recommended_next_input", []),
        }

    def clamp_int(self, value: Any, low: int, high: int, default: int) -> int:
        try:
            return max(low, min(high, int(value)))
        except Exception:
            return default

    def clamp_float(self, value: Any, low: float, high: float, default: float) -> float:
        try:
            return max(low, min(high, float(value)))
        except Exception:
            return default

    def workflow_guide(self, overview: dict[str, Any], important: list[dict[str, Any]]) -> dict[str, Any]:
        hints = overview.get("command_hints") or {}
        ci_files = [item["path"] for item in important if item["type"] == "ci"]
        config_files = [item["path"] for item in important if item["type"] == "config"]
        docs = [item["path"] for item in important if item["type"] == "docs"]
        style_commands = []
        for key in ["test", "docs"]:
            style_commands.extend(hints.get(key) or [])
        if not style_commands:
            style_commands = [overview.get("test_command") or "See README"]
        return {
            "title": "Development Workflow & Code Standards",
            "evidence_files": (ci_files + config_files + docs)[:8],
            "commands": self.commands_or_default(style_commands, [overview.get("test_command") or "See README"]),
            "checklist": [
                "Read README and contribution documents before editing.",
                "Keep the first PR focused on one small behavior, test, example, or documentation change.",
                "Run the detected validation command before submitting.",
                "Reference the related issue or explain the static-analysis opportunity.",
                "Include changed files, test result, and before/after behavior in the PR description.",
            ],
            "standards": [
                "Prefer nearby code style over broad refactors.",
                "Add or update tests when behavior changes.",
                "Avoid touching unrelated modules in a first contribution.",
                "Use CI/config files as the source of truth for project validation.",
            ],
        }

    def requirement_coverage(self, architecture_graph: dict[str, Any], learning_path: list[dict[str, Any]], tasks: list[dict[str, Any]], workflow: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "requirement": "快速理解项目目标与整体架构",
                "implementation": f"Overview summary + Architecture graph with {len(architecture_graph.get('nodes', []))} nodes and {len(architecture_graph.get('edges', []))} relations.",
            },
            {
                "requirement": "学习关键模块与核心代码",
                "implementation": "Tree-sitter extracts symbols/imports and ranks entry/module/utility files with node inspector.",
            },
            {
                "requirement": "理解开发流程与代码规范",
                "implementation": f"Workflow guide uses {len(workflow.get('evidence_files', []))} evidence files plus validation commands and PR checklist.",
            },
            {
                "requirement": "找到适合入门贡献的任务",
                "implementation": f"Contribution Radar recommends {len(tasks)} first-PR tasks with difficulty, impact, files, and command-line plan.",
            },
            {
                "requirement": "降低新贡献者学习成本",
                "implementation": f"Role-aware learning timeline with {len(learning_path)} steps, checkpoint quiz, setup commands, and runnable feature commands.",
            },
        ]

    def setup_guide(self, overview: dict[str, Any], important: list[dict[str, Any]]) -> list[dict[str, str]]:
        config_files = [item["path"] for item in important if item["type"] in {"config", "ci"}]
        test_files = [item["path"] for item in important if item["type"] == "test"]
        hints = overview.get("command_hints") or {}
        clone_commands = [f"git clone {overview.get('url') or 'https://github.com/owner/repo'}", f"cd {overview.get('name') or 'repo'}"]
        setup_commands = self.commands_or_default(hints.get("setup"), ["conda create -n <env_name> python=3.10 -y", "conda activate <env_name>"])
        install_commands = self.commands_or_default(hints.get("install"), [overview.get("install_command") or "See README"])
        run_commands = self.commands_or_default(hints.get("web") or hints.get("run"), [overview.get("run_command") or "See README"])
        test_commands = self.commands_or_default(hints.get("test"), [overview.get("test_command") or "See README"])
        steps = [
            {
                "title": "Clone repository",
                "commands": clone_commands,
                "reason": "Get a local copy before reading or modifying code.",
            },
            {
                "title": "Create environment",
                "commands": setup_commands,
                "reason": "Create or enter the runtime environment described by README.",
            },
            {
                "title": "Install dependencies",
                "commands": install_commands,
                "reason": f"Detected from setup files: {', '.join(config_files[:3]) or 'README / dependency files'}",
            },
            {
                "title": "Run project or demo",
                "commands": run_commands,
                "reason": "Use this to verify the runtime path before changing source code.",
            },
            {
                "title": "Validate before PR",
                "commands": test_commands,
                "reason": f"Detected test evidence: {', '.join(test_files[:3]) or 'test files / CI config'}",
            },
        ]
        return [step for step in steps if step.get("commands")]

    def feature_runbook(self, overview: dict[str, Any], important: list[dict[str, Any]], media: list[dict[str, Any]]) -> list[dict[str, Any]]:
        paths = [item["path"] for item in important]
        hints = overview.get("command_hints") or {}
        def pick(keyword: str, fallback_type: str = "source") -> list[str]:
            matched = [path for path in paths if keyword in path.lower()]
            if matched:
                return matched[:3]
            return [item["path"] for item in important if item["type"] == fallback_type][:3]

        features = [
            {
                "name": "Web / Interactive Demo",
                "purpose": "Run the repository's user-facing demo or web interface.",
                "commands": self.commands_or_default(hints.get("web") or hints.get("run"), [self.command_from_paths(pick("web_demo"), overview.get("run_command") or "See README")]),
                "files": pick("web_demo"),
            },
            {
                "name": "Core Model / API",
                "purpose": "Read the central model or API modules before attempting source changes.",
                "commands": self.commands_or_default([overview.get("test_command")], []),
                "files": [item["path"] for item in important if item["type"] == "source"][:4],
            },
            {
                "name": "Tests / Evaluation",
                "purpose": "Validate a first PR with tests or evaluation scripts.",
                "commands": self.commands_or_default(hints.get("eval") or hints.get("test"), [overview.get("test_command") or "See README"]),
                "files": [item["path"] for item in important if item["type"] == "test"][:4] or pick("test"),
            },
            {
                "name": "Documentation / Examples",
                "purpose": "Find the safest documentation or example contribution surface.",
                "commands": self.commands_or_default(hints.get("docs"), ["make -C docs html", overview.get("test_command") or "See README"]),
                "files": [item["path"] for item in important if item["type"] == "docs"][:4],
            },
        ]
        for feature in features:
            feature["media"] = [item for item in media if item.get("feature") == feature["name"]]
        leftovers = [item for item in media if not any(item in feature["media"] for feature in features)]
        if leftovers:
            features[0]["media"].extend(leftovers[:3])
        if media and max(len(feature["media"]) for feature in features) == len(media):
            for feature in features:
                feature["media"] = []
            for index, item in enumerate(media):
                features[index % len(features)]["media"].append(item)
        return [feature for feature in features if feature.get("commands")]

    def commands_or_default(self, commands: Any, fallback: list[str]) -> list[str]:
        result = [command for command in (commands or []) if self.is_useful_command(command)]
        if result:
            return result[:6]
        return [command for command in fallback if self.is_useful_command(command)][:6]

    def display_command(self, command: Any) -> str:
        return str(command).strip() if self.is_useful_command(command) else ""

    def is_useful_command(self, command: Any) -> bool:
        text = str(command or "").strip()
        lower = text.lower()
        if not text:
            return False
        if lower in {"see readme", "read readme", "pytest", "npm test"}:
            return False
        if "<changed_module_or_package>" in lower:
            return False
        return True

    def command_from_paths(self, paths: list[str], fallback: str) -> str:
        for path in paths:
            name = Path(path).name
            if name in {"server.py", "app.py", "demo.py"}:
                return f"python {path}"
        return fallback

    def extract_file_count(self, traces: list[dict[str, Any]]) -> int | None:
        for trace in traces:
            match = re.search(r"Collected\s+(\d+)\s+files", trace.get("message", ""))
            if match:
                return int(match.group(1))
        return None

    def important_files(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        incoming = {}
        outgoing = {}
        imports_by_source = {}
        for edge in edges:
            outgoing[edge["source"]] = outgoing.get(edge["source"], 0) + 1
            incoming[edge["target"]] = incoming.get(edge["target"], 0) + 1
            imports_by_source.setdefault(edge["source"], []).append(edge["target"])
        enriched = []
        for node in nodes:
            path = node.get("path") or node.get("id")
            symbols = node.get("symbols", [])
            category = self.node_category(node, incoming.get(path, 0), outgoing.get(path, 0))
            reason = self.entry_reason(node, category, incoming.get(path, 0), outgoing.get(path, 0))
            enriched.append(
                {
                    "path": path,
                    "name": node.get("name"),
                    "type": node.get("type"),
                    "category": category,
                    "importance_score": self.display_score(node, category, incoming.get(path, 0), outgoing.get(path, 0)),
                    "summary": node.get("summary"),
                    "symbols": symbols,
                    "imports": imports_by_source.get(path, [])[:8],
                    "why_important": reason,
                    "newcomer_reason": reason,
                }
            )
        groups = {
            "entry": [item for item in enriched if item["category"] == "entry"],
            "module": [item for item in enriched if item["category"] == "module"],
            "utility": [item for item in enriched if item["category"] == "utility"],
            "test": [item for item in enriched if item["type"] == "test"],
            "config": [item for item in enriched if item["type"] in {"config", "ci"}],
            "docs": [item for item in enriched if item["type"] == "docs"],
        }
        for key in groups:
            groups[key] = sorted(groups[key], key=lambda item: item["importance_score"], reverse=True)
        selected = []
        selected.extend(groups["entry"][:2])
        selected.extend(groups["module"][:7])
        selected.extend(groups["test"][:2])
        selected.extend(groups["config"][:2])
        selected.extend(groups["docs"][:2])
        selected.extend(groups["utility"][:3])
        deduped = []
        seen = set()
        for item in selected:
            if item["path"] not in seen:
                deduped.append(item)
                seen.add(item["path"])
        if len(deduped) < 12:
            for item in sorted(enriched, key=lambda item: item["importance_score"], reverse=True):
                if item["path"] not in seen:
                    deduped.append(item)
                    seen.add(item["path"])
                if len(deduped) >= 12:
                    break
        return deduped[:14]

    def display_score(self, node: dict[str, Any], category: str, incoming: int, outgoing: int) -> int:
        base = int(node.get("importance_score") or 0)
        path = (node.get("path") or "").lower()
        if category == "entry":
            base += 10
        if category == "module":
            base += 8
        if node.get("type") == "source":
            base += 6
        if node.get("type") == "docs" and path != "readme.md":
            base -= 18
        if node.get("type") == "test":
            base += 4
        if path in {"readme.md", "pyproject.toml", "package.json"}:
            base += 8
        return max(1, min(100, base))

    def node_category(self, node: dict[str, Any], incoming: int, outgoing: int) -> str:
        path = (node.get("path") or "").lower()
        name = (node.get("name") or "").lower()
        if name in {"main.py", "app.py", "server.py", "cli.py", "demo.py", "train.py", "infer.py", "index.ts", "index.js"}:
            return "entry"
        if path == "readme.md" or node.get("type") in {"config", "ci"}:
            return "entry"
        if "utils" in path or "helper" in path or "common" in path:
            return "utility"
        if incoming + outgoing >= 2 or (node.get("importance_score") or 0) >= 70:
            return "module"
        return "utility"

    def entry_reason(self, node: dict[str, Any], category: str, incoming: int, outgoing: int) -> str:
        if category == "entry":
            return "It is likely to be an onboarding entry because it is documentation, configuration, or a runtime entry file."
        if category == "module":
            return f"It connects to {incoming + outgoing} CodeGraph relations and gives newcomers a high-leverage view of project behavior."
        return "It is a bounded utility surface; useful after reading the main flow."

    def architecture_graph(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
        important = self.important_files(nodes, edges)[:28]
        source_nodes = [item for item in important if item["type"] == "source"]
        if len(source_nodes) < 6:
            source_nodes.extend([item for item in self.important_files(nodes, edges) if item["type"] == "source" and item not in source_nodes])
        graph_nodes = []
        graph_nodes.extend([item for item in important if item["category"] == "entry"][:4])
        graph_nodes.extend(source_nodes[:16])
        graph_nodes.extend([item for item in important if item["type"] in {"test", "config", "ci"}][:5])
        graph_nodes.extend([item for item in important if item["type"] == "docs"][:4])
        seen = set()
        graph_nodes = [item for item in graph_nodes if not (item["path"] in seen or seen.add(item["path"]))][:26]
        keep = {item["path"] for item in graph_nodes}
        graph_edges = [edge for edge in edges if edge["source"] in keep and edge["target"] in keep][:60]
        if len(graph_edges) < min(12, len(graph_nodes) - 1):
            existing = {(edge["source"], edge["target"]) for edge in graph_edges}
            for index in range(min(len(graph_nodes) - 1, 16)):
                source = graph_nodes[index]["path"]
                target = graph_nodes[index + 1]["path"]
                if (source, target) not in existing:
                    graph_edges.append({"source": source, "target": target, "relation_type": "reading-flow", "weight": 1})
                    existing.add((source, target))
        flow_seed = [item for item in graph_nodes if item["category"] == "entry"][:1] + [item for item in graph_nodes if item["category"] == "module"][:4] + [item for item in graph_nodes if item["type"] == "test"][:1]
        flow = [{"step": index + 1, "file": item["path"], "role": item["category"], "summary": item["summary"]} for index, item in enumerate(flow_seed[:6])]
        logical_graph = self.logical_architecture_graph(graph_nodes, graph_edges, nodes, edges)
        return {
            "notice": "Static analysis based on Tree-sitter AST, imports, and deterministic CodeGraph heuristics.",
            "nodes": graph_nodes,
            "edges": graph_edges,
            "logical_graph": logical_graph,
            "call_hierarchy": self.call_hierarchy(nodes, edges, logical_graph),
            "core_flow": flow,
            "detailed_modules": self.architecture_modules(graph_nodes, edges),
            "relationships": self.architecture_relationships(graph_nodes, graph_edges),
        }

    def logical_architecture_graph(
        self,
        graph_nodes: list[dict[str, Any]],
        graph_edges: list[dict[str, Any]],
        all_nodes: list[dict[str, Any]],
        all_edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        source_by_path = {node.get("path"): node for node in all_nodes if node.get("path")}
        candidates = graph_nodes[:]
        candidate_paths = {item.get("path") for item in candidates}
        for node in sorted(all_nodes, key=lambda item: item.get("importance_score") or 0, reverse=True):
            if len(candidates) >= 220:
                break
            if node.get("path") not in candidate_paths:
                candidates.append(node)
                candidate_paths.add(node.get("path"))

        representatives: dict[str, int] = {}
        for node in all_nodes:
            group = self.logical_module_for_path(node)
            current = representatives.get(group["id"], 0)
            if current >= 6:
                continue
            path = node.get("path")
            if path and path not in candidate_paths:
                candidates.append(node)
                candidate_paths.add(path)
                representatives[group["id"]] = current + 1

        groups: dict[str, dict[str, Any]] = {}
        for node in candidates:
            group = self.logical_module_for_path(node)
            bucket = groups.setdefault(
                group["id"],
                {
                    **group,
                    "files": [],
                    "symbols": [],
                    "score": 0,
                    "file_count": 0,
                },
            )
            path = node.get("path")
            if path:
                bucket["files"].append(path)
            bucket["symbols"].extend((node.get("symbols") or [])[:4])
            bucket["score"] += int(node.get("importance_score") or 0)
            bucket["file_count"] += 1

        logical_nodes = []
        for bucket in groups.values():
            bucket["files"] = bucket["files"][:12]
            bucket["symbols"] = list(dict.fromkeys([self.symbol_label(item) for item in bucket["symbols"] if item]))[:14]
            bucket["importance"] = round(bucket["score"] / max(1, bucket["file_count"]))
            bucket["description"] = self.logical_module_description(bucket)
            logical_nodes.append(bucket)

        priority = {
            "entry": 1,
            "app": 2,
            "core": 3,
            "runtime": 4,
            "platform": 5,
            "library": 6,
            "config": 7,
            "test": 8,
            "docs": 9,
        }
        logical_nodes.sort(key=lambda item: (priority.get(item.get("kind"), 99), -item.get("importance", 0), item.get("id", "")))
        logical_nodes = self.balanced_logical_nodes(logical_nodes, limit=40)
        keep_ids = {node["id"] for node in logical_nodes}

        edge_counts: dict[tuple[str, str], dict[str, Any]] = {}
        for edge in (all_edges or []) + (graph_edges or []):
            source = source_by_path.get(edge.get("source"))
            target = source_by_path.get(edge.get("target"))
            if not source or not target:
                continue
            src_group = self.logical_module_for_path(source)
            tgt_group = self.logical_module_for_path(target)
            if src_group["id"] == tgt_group["id"] or src_group["id"] not in keep_ids or tgt_group["id"] not in keep_ids:
                continue
            key = (src_group["id"], tgt_group["id"])
            item = edge_counts.setdefault(
                key,
                {
                    "source": src_group["id"],
                    "target": tgt_group["id"],
                    "relation": edge.get("relation_type") or "imports",
                    "weight": 0,
                    "evidence": [],
                },
            )
            item["weight"] += int(edge.get("weight") or 1)
            if len(item["evidence"]) < 10:
                item["evidence"].append(f"{edge.get('source')} -> {edge.get('target')}")

        logical_edges = sorted(edge_counts.values(), key=lambda item: item["weight"], reverse=True)[:80]
        if len(logical_edges) < max(2, min(5, len(logical_nodes) - 1)):
            existing = {(edge["source"], edge["target"]) for edge in logical_edges}
            for source, target, relation in self.default_logical_flow(logical_nodes):
                if (source, target) not in existing:
                    logical_edges.append(
                        {
                            "source": source,
                            "target": target,
                            "relation": relation,
                            "weight": 1,
                            "evidence": ["Synthesized reading flow from repository structure and entry files."],
                        }
                    )
                    existing.add((source, target))
            if len(logical_edges) < max(8, min(24, len(logical_nodes) - 1)):
                for index in range(min(len(logical_nodes) - 1, 30)):
                    source = logical_nodes[index]["id"]
                    target = logical_nodes[index + 1]["id"]
                    if source == target or (source, target) in existing:
                        continue
                    logical_edges.append(
                        {
                            "source": source,
                            "target": target,
                            "relation": "reading-flow",
                            "weight": 1,
                            "evidence": [
                                f"{(logical_nodes[index].get('files') or [''])[0]} -> {(logical_nodes[index + 1].get('files') or [''])[0]}"
                            ],
                        }
                    )
                    existing.add((source, target))

        core_chain = self.logical_core_chain(logical_nodes, logical_edges)
        return {
            "title": "Logical Architecture & Module Calls",
            "subtitle": "Module-level graph aggregated from Tree-sitter symbols, imports, file roles, and CodeGraph edges.",
            "nodes": logical_nodes,
            "edges": logical_edges,
            "core_chain": core_chain,
        }

    def balanced_logical_nodes(self, nodes: list[dict[str, Any]], limit: int = 40) -> list[dict[str, Any]]:
        quotas = {
            "entry": 2,
            "app": 3,
            "runtime": 3,
            "core": 26,
            "platform": 7,
            "library": 5,
            "config": 4,
            "test": 4,
            "docs": 3,
        }
        selected = []
        seen = set()
        for kind, quota in quotas.items():
            for node in [item for item in nodes if item.get("kind") == kind][:quota]:
                if node.get("id") not in seen and len(selected) < limit:
                    selected.append(node)
                    seen.add(node.get("id"))
        for node in nodes:
            if len(selected) >= limit:
                break
            if node.get("id") not in seen:
                selected.append(node)
                seen.add(node.get("id"))
        priority = {
            "entry": 1,
            "app": 2,
            "runtime": 3,
            "core": 4,
            "platform": 5,
            "library": 6,
            "config": 7,
            "test": 8,
            "docs": 9,
        }
        return sorted(selected, key=lambda item: (priority.get(item.get("kind"), 99), -item.get("importance", 0), item.get("id", "")))

    def logical_module_for_path(self, node: dict[str, Any]) -> dict[str, str]:
        path = (node.get("path") or "").replace("\\", "/")
        lower = path.lower()
        name = Path(path).name.lower()
        if node.get("category") == "entry" or name in {"main.py", "app.py", "server.py", "cli.py", "demo.py", "train.py", "infer.py"}:
            entry_name = self.module_segment(path, 0) or "Entry"
            return {"id": f"entry:{entry_name.lower()}", "kind": "entry", "name": f"Entry / {entry_name}"}
        if lower == "readme.md" or lower.startswith("docs/") or "/docs/" in lower or name.endswith(".md"):
            segment = self.module_segment(path, 1) if lower.startswith("docs/") else "README"
            return {"id": f"docs:{segment.lower()}", "kind": "docs", "name": f"Docs / {segment}"}
        if node.get("type") in {"config", "ci"} or lower.startswith((".github/", "cmake", "boards/", "romfs/")) or name in {"pyproject.toml", "package.json", "cmakelists.txt"}:
            segment = self.config_segment(path)
            return {"id": f"config:{segment.lower()}", "kind": "config", "name": f"Config / {segment}"}
        if node.get("type") == "test" or "test" in lower or "pytest" in lower or "gtest" in lower:
            segment = self.test_segment(path)
            return {"id": f"test:{segment.lower()}", "kind": "test", "name": f"Tests / {segment}"}
        if lower.startswith(("web/", "frontend/", "src/pages/", "src/app/", "web_demo/", "examples/", "demo/")) or "/web/" in lower:
            segment = self.module_segment(path, 1) or self.module_segment(path, 0) or "Demo"
            return {"id": f"app:{segment.lower()}", "kind": "app", "name": f"App / {segment}"}
        if lower.startswith("src/modules/"):
            segment = self.subsystem_segment(path, 2)
            return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Core / {segment}"}
        if lower.startswith("modules/"):
            segment = self.module_segment(path, 1) or "modules"
            return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Core / {segment}"}
        if lower.startswith("homeassistant/components/"):
            segment = self.module_segment(path, 2) or "component"
            return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Component / {segment}"}
        if "/model/" in lower or "/models/" in lower:
            segment = self.model_segment(path)
            return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Model / {segment}"}
        if "core" in lower:
            segment = self.module_segment(path, 1) or "core"
            return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Core / {segment}"}
        if lower.startswith("src/drivers/") or lower.startswith("drivers/") or "/drivers/" in lower:
            segment = self.driver_segment(path)
            return {"id": f"platform:driver:{segment.lower()}", "kind": "platform", "name": f"Driver / {segment}"}
        if lower.startswith(("platforms/", "platform/", "arch/", "hal/")):
            segment = self.module_segment(path, 1) or self.module_segment(path, 0) or "platform"
            return {"id": f"platform:{segment.lower()}", "kind": "platform", "name": f"Platform / {segment}"}
        if lower.startswith("src/lib/"):
            segment = self.module_segment(path, 2) or "lib"
            return {"id": f"library:{segment.lower()}", "kind": "library", "name": f"Lib / {segment}"}
        if lower.startswith(("lib/", "libs/")):
            segment = self.module_segment(path, 1) or "lib"
            return {"id": f"library:{segment.lower()}", "kind": "library", "name": f"Lib / {segment}"}
        if lower.startswith(("tools/", "scripts/")) or any(part in lower for part in ["/utils/", "/common/", "/tools/"]):
            segment = self.module_segment(path, 1) or self.module_segment(path, 0) or "tools"
            return {"id": f"library:{segment.lower()}", "kind": "library", "name": f"Tools / {segment}"}
        if lower.startswith(("src/", "app/", "server/", "backend/")):
            segment = self.module_segment(path, 1) or self.module_segment(path, 0) or "runtime"
            return {"id": f"runtime:{segment.lower()}", "kind": "runtime", "name": f"Runtime / {segment}"}
        segment = self.module_segment(path, 0) or "misc"
        return {"id": f"core:{segment.lower()}", "kind": "core", "name": f"Module / {segment}"}

    def module_segment(self, path: str, index: int) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if 0 <= index < len(parts):
            return parts[index]
        return ""

    def subsystem_segment(self, path: str, base_index: int) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if base_index >= len(parts):
            return "module"
        module = parts[base_index]
        if base_index + 1 >= len(parts):
            return module
        child = parts[base_index + 1]
        if "." in child:
            stem = Path(child).stem
            return f"{module} / {stem}" if stem and stem != module else module
        if base_index + 2 < len(parts):
            return f"{module} / {child}"
        return module

    def config_segment(self, path: str) -> str:
        lower = path.lower()
        if lower.startswith(".github/"):
            return ".github"
        if lower.startswith("cmake/"):
            return "cmake"
        if lower.startswith("boards/"):
            return "boards"
        if lower.startswith("romfs/"):
            return "ROMFS"
        return Path(path).name or "build"

    def test_segment(self, path: str) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        for part in parts:
            if "test" in part.lower() or "gtest" in part.lower():
                return part
        return parts[1] if len(parts) > 1 else "validation"

    def driver_segment(self, path: str) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if "drivers" in [part.lower() for part in parts]:
            index = [part.lower() for part in parts].index("drivers")
            if index + 1 < len(parts):
                return parts[index + 1]
        return parts[1] if len(parts) > 1 else "drivers"

    def model_segment(self, path: str) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        for token in ("model", "models"):
            if token in [part.lower() for part in parts]:
                index = [part.lower() for part in parts].index(token)
                if index + 1 < len(parts):
                    return parts[index + 1]
        return parts[1] if len(parts) > 1 else "model"

    def logical_module_description(self, node: dict[str, Any]) -> str:
        descriptions = {
            "entry": "入口层承接 README Quick Start、CLI/server/Demo 启动脚本或 main 函数，是复现工程时最先确认的执行入口。",
            "app": "应用/Demo 层负责把项目能力包装成用户可运行的示例、Web 界面、推理流程或交互式入口，是演示效果和调试起点。",
            "core": "核心领域模块承载项目主要业务/算法/控制逻辑，是理解架构和做代码修改前必须读懂的高价值源码区域。",
            "runtime": "运行时服务负责生命周期、事件/请求处理、任务调度和模块胶水代码，连接入口层与核心模块。",
            "platform": "平台/驱动层把核心逻辑适配到硬件、OS、设备、仿真或部署目标，解释项目为什么能在真实环境运行。",
            "library": "共享库/工具层提供通用算法、脚本、IO、模型工具或复用 API，被上层模块反复调用。",
            "config": "配置/构建层定义依赖、编译、CI、运行参数和可复现约束，决定工程如何被安装、构建和启动。",
            "test": "测试/验证层提供最小可验证路径，帮助新贡献者在提交 PR 前证明改动有效且影响范围可控。",
            "docs": "文档/示例层解释项目目标、使用方式、贡献规范和 Demo 资源，是建立心智模型和演示讲解的入口。",
        }
        return descriptions.get(node.get("kind"), "该逻辑模块由文件布局、Tree-sitter 符号和 CodeGraph 静态关系推断得到。")

    def default_logical_flow(self, nodes: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
        ids = {node["id"] for node in nodes}
        preferred = [
            ("docs", "entry", "guides"),
            ("entry", "app", "starts"),
            ("entry", "runtime", "initializes"),
            ("app", "core", "calls"),
            ("runtime", "core", "dispatches"),
            ("core", "library", "uses"),
            ("core", "platform", "adapts-to"),
            ("config", "runtime", "configures"),
            ("test", "core", "validates"),
        ]
        return [(source, target, relation) for source, target, relation in preferred if source in ids and target in ids]

    def logical_core_chain(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id = {node["id"]: node for node in nodes}
        chain_ids = []
        for source, target, _relation in self.default_logical_flow(nodes):
            if source not in chain_ids:
                chain_ids.append(source)
            if target not in chain_ids:
                chain_ids.append(target)
        if not chain_ids:
            chain_ids = [node["id"] for node in nodes[:5]]
        return [
            {
                "step": index + 1,
                "module": by_id[module_id]["name"],
                "kind": by_id[module_id]["kind"],
                "files": by_id[module_id].get("files", [])[:4],
                "summary": by_id[module_id].get("description", ""),
            }
            for index, module_id in enumerate(chain_ids[:7])
            if module_id in by_id
        ]

    def symbol_label(self, symbol: Any) -> str:
        if isinstance(symbol, dict):
            return str(symbol.get("name") or symbol.get("label") or symbol)
        return str(symbol)

    def call_hierarchy(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], logical_graph: dict[str, Any]) -> dict[str, Any]:
        source_nodes = [node for node in nodes if node.get("type") == "source"]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for node in sorted(source_nodes, key=lambda item: item.get("importance_score") or 0, reverse=True):
            group = self.logical_module_for_path(node)
            grouped.setdefault(group["id"], []).append(node)

        selected: list[dict[str, Any]] = []
        seen = set()
        for logical_node in logical_graph.get("nodes", []):
            for node in grouped.get(logical_node.get("id"), [])[:4]:
                if node.get("path") not in seen:
                    selected.append(node)
                    seen.add(node.get("path"))
        for node in sorted(source_nodes, key=lambda item: item.get("importance_score") or 0, reverse=True):
            if len(selected) >= 96:
                break
            if node.get("path") not in seen:
                selected.append(node)
                seen.add(node.get("path"))

        selected_paths = {node.get("path") for node in selected}
        node_by_path = {node.get("path"): node for node in selected}
        logical_by_id = {node.get("id"): node for node in logical_graph.get("nodes", [])}
        file_to_module = {}
        for node in selected:
            group = self.logical_module_for_path(node)
            file_to_module[node.get("path")] = group["id"]

        file_edges = [
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation": edge.get("relation_type") or "imports",
                "source_module": file_to_module.get(edge.get("source")),
                "target_module": file_to_module.get(edge.get("target")),
                "weight": edge.get("weight", 1),
            }
            for edge in edges
            if edge.get("source") in selected_paths and edge.get("target") in selected_paths
        ][:120]

        symbol_index: dict[str, tuple[str, str]] = {}
        for node in selected:
            for symbol in (node.get("symbols") or [])[:12]:
                name = self.symbol_label(symbol)
                symbol_index.setdefault(name.split("::")[-1], (node.get("path"), name))

        file_cards = []
        function_edges = []
        for node in selected:
            path = node.get("path")
            module_id = file_to_module.get(path)
            symbols = [self.symbol_label(symbol) for symbol in (node.get("symbols") or [])[:10]]
            calls = [str(call) for call in (node.get("calls") or [])[:14]]
            caller = symbols[0] if symbols else Path(path or "").stem
            resolved_calls = []
            for call in calls[:8]:
                clean_call = call.split(".")[-1].split("::")[-1]
                target = symbol_index.get(clean_call)
                if target:
                    target_file, target_symbol = target
                    resolved_calls.append({"name": call, "target_file": target_file, "target_symbol": target_symbol, "resolved": True})
                    function_edges.append(
                        {
                            "source_file": path,
                            "source_function": caller,
                            "target_file": target_file,
                            "target_function": target_symbol,
                            "relation": "calls",
                            "confidence": "medium",
                        }
                    )
                else:
                    resolved_calls.append({"name": call, "target_file": "", "target_symbol": "", "resolved": False})
                    if len(function_edges) < 160:
                        function_edges.append(
                            {
                                "source_file": path,
                                "source_function": caller,
                                "target_file": "",
                                "target_function": call,
                                "relation": "calls",
                                "confidence": "name-only",
                            }
                        )
            file_cards.append(
                {
                    "path": path,
                    "module_id": module_id,
                    "module_name": (logical_by_id.get(module_id) or {}).get("name") or self.logical_module_for_path(node)["name"],
                    "importance_score": node.get("importance_score") or 0,
                    "summary": node.get("summary") or "",
                    "symbols": symbols,
                    "calls": resolved_calls,
                    "imports": (node.get("imports") or [])[:10],
                    "incoming_files": [edge["source"] for edge in file_edges if edge.get("target") == path][:8],
                    "outgoing_files": [edge["target"] for edge in file_edges if edge.get("source") == path][:8],
                }
            )

        module_cards = []
        for logical_node in logical_graph.get("nodes", []):
            module_files = [card for card in file_cards if card.get("module_id") == logical_node.get("id")]
            if not module_files:
                continue
            module_cards.append(
                {
                    "id": logical_node.get("id"),
                    "name": logical_node.get("name"),
                    "kind": logical_node.get("kind"),
                    "description": logical_node.get("description"),
                    "files": module_files[:5],
                    "incoming_modules": [
                        edge.get("source")
                        for edge in logical_graph.get("edges", [])
                        if edge.get("target") == logical_node.get("id")
                    ][:6],
                    "outgoing_modules": [
                        edge.get("target")
                        for edge in logical_graph.get("edges", [])
                        if edge.get("source") == logical_node.get("id")
                    ][:6],
                }
            )

        relation_details = self.module_relation_details(logical_graph, module_cards, file_edges, function_edges)

        return {
            "notice": "Three-level static call view: module -> file -> function/class. Function calls are extracted from Tree-sitter call expressions; unresolved dynamic calls are shown as name-only.",
            "modules": module_cards[:36],
            "file_edges": file_edges,
            "function_edges": function_edges[:160],
            "relation_details": relation_details,
        }

    def module_relation_details(
        self,
        logical_graph: dict[str, Any],
        module_cards: list[dict[str, Any]],
        file_edges: list[dict[str, Any]],
        function_edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        modules = {module.get("id"): module for module in module_cards}
        details = []
        for edge in logical_graph.get("edges", [])[:32]:
            source_id = edge.get("source")
            target_id = edge.get("target")
            source = modules.get(source_id)
            target = modules.get(target_id)
            if not source or not target:
                continue
            source_files = [file.get("path") for file in source.get("files", []) if file.get("path")]
            target_files = [file.get("path") for file in target.get("files", []) if file.get("path")]
            direct_file_edges = [
                item for item in file_edges
                if item.get("source_module") == source_id and item.get("target_module") == target_id
            ][:8]
            direct_function_edges = [
                item for item in function_edges
                if item.get("source_file") in source_files and (item.get("target_file") in target_files or not item.get("target_file"))
            ][:10]
            details.append(
                {
                    "source": source_id,
                    "source_name": source.get("name"),
                    "target": target_id,
                    "target_name": target.get("name"),
                    "relation": edge.get("relation") or "calls",
                    "weight": edge.get("weight") or 1,
                    "purpose": self.module_relation_purpose(source, target, edge),
                    "source_files": source_files[:6],
                    "target_files": target_files[:6],
                    "file_edges": direct_file_edges,
                    "function_edges": direct_function_edges,
                    "evidence": (edge.get("evidence") or [])[:8],
                    "reading_order": self.relation_reading_order(source, target, direct_file_edges),
                    "newcomer_note": self.module_relation_newcomer_note(source, target, edge),
                }
            )
        return details

    def module_relation_purpose(self, source: dict[str, Any], target: dict[str, Any], edge: dict[str, Any]) -> str:
        source_kind = source.get("kind")
        target_kind = target.get("kind")
        relation = edge.get("relation") or "uses"
        if source_kind == "docs":
            return "文档模块负责把新贡献者引导到可复现路径：先说明项目目标、安装命令、Demo 入口，再指向真正需要阅读的源码文件。"
        if source_kind == "entry":
            return "入口模块负责接收用户命令、Demo 启动或 main/CLI 调用，然后把控制权交给运行时、应用层或核心模块。"
        if source_kind == "app" and target_kind == "core":
            return "应用/Demo 层通过调用核心模块把项目能力暴露给用户；复现 Demo 时应先看应用入口，再顺着调用进入核心实现。"
        if source_kind == "runtime" and target_kind == "core":
            return "运行时服务负责生命周期、事件/请求分发和调度，把外部输入转交给核心领域模块处理。"
        if source_kind == "core" and target_kind == "platform":
            return "核心模块通过平台/驱动抽象访问硬件、OS、设备或部署环境；理解真实运行行为时需要沿着这条边看适配层。"
        if source_kind == "core" and target_kind == "library":
            return "核心模块复用共享库/工具来完成通用算法、解析、IO、模型工具或工程脚本能力；修改核心逻辑前要确认这些依赖。"
        if source_kind == "test":
            return "测试/验证模块会导入或驱动项目模块，用来证明修改没有破坏行为；首次 PR 应优先找到这里的最小验证路径。"
        if target_kind == "config":
            return "目标模块提供构建、依赖或运行配置，会影响源模块如何被编译、装配或启动。"
        return f"这条关系被静态分析识别为 `{relation}`，依据来自 import/include、Tree-sitter 符号和 CodeGraph 边；阅读时应先看源文件如何发起依赖，再看目标文件提供了什么抽象。"

    def relation_reading_order(self, source: dict[str, Any], target: dict[str, Any], file_edges: list[dict[str, Any]]) -> list[str]:
        order = []
        if file_edges:
            for edge in file_edges[:3]:
                if edge.get("source") and edge.get("source") not in order:
                    order.append(edge["source"])
                if edge.get("target") and edge.get("target") not in order:
                    order.append(edge["target"])
        if not order:
            for file in (source.get("files") or [])[:2] + (target.get("files") or [])[:2]:
                path = file.get("path") if isinstance(file, dict) else file
                if path and path not in order:
                    order.append(path)
        return order[:6]

    def module_relation_newcomer_note(self, source: dict[str, Any], target: dict[str, Any], edge: dict[str, Any]) -> str:
        return (
            f"可以把它理解为从 {source.get('name')} 到 {target.get('name')} 的桥："
            "先打开源模块关键文件，找到 import/include 或调用表达式；再打开目标模块文件，确认被复用的类、函数或配置。"
            "按下方阅读顺序逐个打开文件，并用函数调用样例定位具体实现。"
        )

    def architecture_modules(self, graph_nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        incoming = {}
        outgoing = {}
        for edge in edges:
            outgoing.setdefault(edge["source"], []).append(edge)
            incoming.setdefault(edge["target"], []).append(edge)
        modules = []
        for node in graph_nodes[:14]:
            modules.append(
                {
                    "path": node.get("path"),
                    "category": node.get("category"),
                    "type": node.get("type"),
                    "summary": node.get("summary"),
                    "symbols": node.get("symbols", [])[:8],
                    "imports": node.get("imports", [])[:10],
                    "calls": node.get("calls", [])[:12],
                    "incoming": [edge["source"] for edge in incoming.get(node.get("path"), [])[:6]],
                    "outgoing": [edge["target"] for edge in outgoing.get(node.get("path"), [])[:6]],
                    "why_newcomers_read_it": node.get("newcomer_reason") or node.get("why_important") or self.entry_reason(node, node.get("category", "module"), len(incoming.get(node.get("path"), [])), len(outgoing.get(node.get("path"), []))),
                }
            )
        return modules

    def architecture_relationships(self, graph_nodes: list[dict[str, Any]], graph_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        paths = {node.get("path") for node in graph_nodes}
        relationships = []
        for edge in graph_edges[:24]:
            if edge.get("source") not in paths or edge.get("target") not in paths:
                continue
            relationships.append(
                {
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "type": edge.get("relation_type") or "imports",
                    "weight": edge.get("weight", 1),
                    "explanation": f"{Path(edge.get('source', '')).name} depends on {Path(edge.get('target', '')).name} through static {edge.get('relation_type') or 'import'} analysis.",
                }
            )
        return relationships

    def risks(self, overview: dict[str, Any], nodes: list[dict[str, Any]], edges: list[dict[str, Any]], issues: list[dict[str, Any]]) -> list[str]:
        risks = []
        if not self.is_useful_command(overview.get("install_command")):
            risks.append("Dependency installation command is not explicit; confirm package manager and Python/Node version before reproducing.")
        if not self.is_useful_command(overview.get("run_command")):
            risks.append("No direct demo/service command was detected; reproduction may require locating the runtime entry or release artifact first.")
        if not self.is_useful_command(overview.get("test_command")):
            risks.append("Validation command is not explicit; run a small smoke test before changing source code.")
        if len(edges) < max(3, len(nodes) // 20):
            risks.append("Static import graph is sparse; runtime wiring may be hidden in configuration, plugin registration, or dynamic imports.")
        if not issues:
            risks.append("GitHub issues were unavailable; first-contribution opportunities are inferred from static analysis rather than maintainer labels.")
        if not risks:
            risks.append("Reproduce the project before editing: install dependencies, run one demo/service command, then validate with the detected test command.")
        return risks[:4]

    def three_minute_summary(self, overview: dict[str, Any], important: list[dict[str, Any]], risks: list[str]) -> str:
        top = ", ".join(item["path"] for item in important[:3]) or "README and core source files"
        stack = ", ".join(overview.get("tech_stack", [])[:4]) or overview.get("primary_language") or "detected source files"
        if (overview.get("readme_language") or "en") == "zh":
            return (
                f"这个仓库可以先作为一个 {stack} 项目来理解。先阅读 README 中的项目目标，再重点查看 {top}。"
                f"环境搭建可从 `{overview.get('install_command') or '查看 README'}` 开始，提交前用 `{overview.get('test_command') or '查看 README'}` 验证。"
                f"当前主要上手风险是：{risks[0] if risks else '未发现明显风险'}"
            )
        return (
            f"This repository is best learned as a {stack} project. Start by reading the project goal, then inspect {top}. "
            f"Use `{overview.get('install_command') or 'See README'}` to set up and `{overview.get('test_command') or 'See README'}` to validate changes. "
            f"The main onboarding risk is: {risks[0] if risks else 'none detected'}"
        )

    def learning_path(self, paths: list[dict[str, Any]], important: list[dict[str, Any]], role: str | None, goal: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        role = role or "beginner"
        goal = goal or "first contribution"
        readme = ["README.md"] if any(item["path"].lower() == "readme.md" for item in important) else [important[0]["path"]] if important else ["README.md"]
        source_files = [item["path"] for item in important if item["type"] == "source"]
        entry_files = [item["path"] for item in important if item["category"] == "entry"]
        test_files = [item["path"] for item in important if item["type"] == "test"]
        config_files = [item["path"] for item in important if item["type"] in {"config", "ci"}]
        doc_files = [item["path"] for item in important if item["type"] == "docs" and item["path"].lower() != "readme.md"]
        setup_files = readme + config_files[:2] + doc_files[:1]
        top_files = source_files[:6] or [item["path"] for item in important[:6]]
        role_templates = {
            "beginner": [
                ("Orient with README", "Understand what the project does and how people use it.", readme, "Why should this project exist?", "8 min"),
                ("Run the project locally", "Find install, quickstart, demo, and validation commands before deep reading.", setup_files, "What command proves the project can run?", "12 min"),
                ("Trace the data/control entry", "Follow the first realistic flow from entry to core module.", entry_files[:2] + top_files[:2], "Where does user input or execution enter the system?", "20 min"),
                ("Inspect the core module", "Read the most connected source file and its public symbols.", top_files[:3], "Which class or function would you debug first?", "25 min"),
            ],
            "intermediate": [
                ("Map architecture layers", "Separate entry, module, and utility surfaces.", entry_files[:2] + top_files[:4], "Which files form the backbone?", "15 min"),
                ("Read configuration and runtime wiring", "Connect setup/config files with source modules.", config_files[:3] + top_files[:2], "Which config affects runtime behavior?", "20 min"),
                ("Understand test strategy", "Find smallest validation path for a change.", test_files[:3] + top_files[:1], "Which test should run before a PR?", "20 min"),
                ("Pick a bounded contribution", "Choose a task with clear files and verification.", top_files[:3], "What is the smallest reviewable diff?", "25 min"),
            ],
            "advanced": [
                ("Deep-read CodeGraph hubs", "Inspect high-centrality modules and coupling.", top_files[:5], "Where is architectural coupling highest?", "20 min"),
                ("Find extension/performance surfaces", "Look for utilities, hot paths, and configuration gates.", top_files[2:6], "Which function is likely a bottleneck or extension point?", "30 min"),
                ("Connect Issue to PR strategy", "Translate code knowledge into a reviewable contribution.", top_files[:4], "What evidence will convince maintainers?", "25 min"),
            ],
        }
        selected = role_templates.get(role, role_templates["beginner"])
        if goal == "run":
            selected.insert(1, ("Environment checkpoint", "Prioritize install, run, and test commands before architecture.", setup_files, "Can you reproduce the documented happy path?", "10 min"))
        if goal == "understand":
            selected.append(("Explain back the architecture", "Summarize entry, core module, utility, and test surfaces.", top_files[:5], "Can you explain the project in 3 minutes?", "15 min"))
        steps = [
            {
                "index": index + 1,
                "title": title,
                "objective": objective,
                "files": files,
                "reason": "Selected from README, entry-file heuristics, and CodeGraph importance.",
                "estimated_time": time,
                "checkpoint": checkpoint,
            }
            for index, (title, objective, files, checkpoint, time) in enumerate(selected)
        ]
        quiz = [
            {"question": "Where is the most suitable debugging entry point?", "answer": (entry_files + top_files)[0] if (entry_files + top_files) else "README.md"},
            {"question": "Which source file should a newcomer inspect after README?", "answer": top_files[0] if top_files else "Top CodeGraph module"},
            {"question": "What is the safest validation command before a first PR?", "answer": "Use the detected test command or the closest documented test workflow."},
        ]
        return steps, quiz

    def contribution_tasks(self, issues: list[dict[str, Any]], important: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tasks = []
        all_files = self.files_for_matching(important, nodes)
        for index, issue in enumerate(issues[:6]):
            score = issue.get("beginner_score") or 60
            difficulty = "Beginner" if score >= 78 else "Intermediate" if score >= 58 else "Advanced"
            files = self.task_files(issue, all_files, important)
            tasks.append(
                {
                    "id": issue.get("id"),
                    "title": issue.get("title"),
                    "source": "GitHub Issue" if issue.get("url") else "Simulated static-analysis opportunity",
                    "difficulty": difficulty,
                    "difficulty_score": max(10, 100 - score),
                    "impact_score": min(95, 45 + score // 2 + index * 4),
                    "reason": issue.get("recommended_reason"),
                    "files": files,
                    "knowledge": self.knowledge_points(issue, files),
                    "first_pr_plan": [
                        "Read the recommended files and restate the change scope.",
                        "Make one small documentation/test/config/source change.",
                        "Run the detected validation command and open a focused PR.",
                    ],
                    "risk": issue.get("risk_summary"),
                    "url": issue.get("url"),
                }
            )
        return tasks

    def files_for_matching(self, important: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_path = {}
        for item in nodes:
            path = item.get("path") or item.get("id")
            if path:
                by_path[path] = {
                    "path": path,
                    "type": item.get("type"),
                    "importance_score": item.get("importance_score") or 0,
                }
        for item in important:
            by_path[item["path"]] = item
        return list(by_path.values())

    def task_files(self, issue: dict[str, Any], all_files: list[dict[str, Any]], important: list[dict[str, Any]]) -> list[str]:
        text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
        exact = []
        for item in all_files:
            path = item["path"]
            name = Path(path).name.lower()
            if path.lower() in text or name in text:
                exact.append(item)
        if exact:
            return [item["path"] for item in sorted(exact, key=lambda item: item.get("importance_score", 0), reverse=True)[:3]]
        labels = [label.lower() for label in issue.get("labels", [])]
        if any(label in {"documentation", "docs"} for label in labels) or any(word in text for word in ["doc", "readme", "documentation"]):
            candidates = [item for item in all_files if item.get("type") == "docs"]
        elif any(label in {"test", "testing"} for label in labels) or "test" in text:
            candidates = [item for item in all_files if item.get("type") == "test"]
        elif any(word in text for word in ["config", "setting", "validation"]):
            candidates = [item for item in all_files if item.get("type") in {"config", "ci"}]
        else:
            candidates = [item for item in all_files if item.get("type") == "source"]
        if not candidates:
            candidates = important
        return [item["path"] for item in sorted(candidates, key=lambda item: item.get("importance_score", 0), reverse=True)[:3]]

    def knowledge_points(self, issue: dict[str, Any], files: list[str]) -> list[str]:
        text = f"{issue.get('title', '')} {issue.get('body', '')}".lower()
        points = []
        if "doc" in text or "readme" in text:
            points.append("documentation convention")
        if "test" in text:
            points.append("test layout")
        if any(file.endswith((".py", ".ts", ".js", ".tsx")) for file in files):
            points.append("core module API")
        if not points:
            points = ["project structure", "minimal PR workflow"]
        return points

    def agent_trace(self, traces: list[dict[str, Any]], repo: dict[str, Any], nodes: list[dict[str, Any]], edges: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        roles = [
            ("Orchestrator Agent", "GitHub URL, user role, goal", "Coordinate scanner, CodeGraph, planner, advisor", f"Analysis state: {repo.get('status')}", 0.93, "Show dashboard"),
            ("Repo Scanner Agent", "Repository snapshot and metadata", "Detect files, docs, setup, tests, tech stack", f"Scanned {self.extract_file_count(traces) or len(nodes)} files", 0.88, "Build repository profile"),
            ("CodeGraph Agent", "Source files and Tree-sitter AST", "Extract symbols, imports, approximate module relations", f"{len(nodes)} nodes, {len(edges)} relations", 0.84, "Rank entry files"),
            ("Onboarding Planner Agent", "Role, goal, important files", "Generate timeline and checkpoint quiz", "Personalized learning route ready", 0.86, "Guide user reading"),
            ("Contribution Advisor Agent", "Issues or simulated opportunities", "Score difficulty, impact, and first PR plan", f"{len(tasks)} candidate tasks", 0.82, "Choose a first contribution"),
            ("Reflection Agent", "All analysis artifacts", "Identify uncertainty and missing evidence", "Reflection generated", 0.79, "Ask user to run/test locally"),
        ]
        return [
            {
                "agent": agent,
                "input": input_text,
                "action": action,
                "output": output,
                "confidence": confidence,
                "next_step": next_step,
            }
            for agent, input_text, action, output, confidence, next_step in roles
        ]

    def reflection(self, overview: dict[str, Any], nodes: list[dict[str, Any]], edges: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
        limitations = [
            "Static analysis approximates runtime flow; dynamic plugin registration may be missed.",
            "Tree-sitter extracts symbols/imports but does not execute the project.",
        ]
        if not issues or any("local-candidate" in issue.get("labels", []) for issue in issues):
            limitations.append("GitHub Issue API was unavailable or incomplete; some contribution tasks are simulated.")
        missing = []
        if overview.get("install_command") == "See README":
            missing.append("Explicit install command")
        if overview.get("test_command") == "See README":
            missing.append("Explicit test command")
        if len(edges) < 5:
            missing.append("Rich import/call graph evidence")
        return {
            "limitations": limitations,
            "possibly_missing": missing or ["Runtime behavior, maintainer preferences, and environment-specific setup details"],
            "recommended_next_input": [
                "Run the install/test command locally and paste failures back into RepoPilot.",
                "Choose one contribution task and inspect the recommended files.",
                "If available, provide a GitHub token to improve Issue and PR analysis.",
            ],
        }
