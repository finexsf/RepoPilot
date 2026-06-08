from __future__ import annotations

from pathlib import Path

from app.services.agents import ContributionPlannerAgent, IssueMinerAgent, LearningAgent, RepoScannerAgent
from app.services.codegraph import TreeSitterCodeGraph, classify_file
from app.services.database import Database
from app.services.deepseek_client import DeepSeekClient
from app.services.github_service import GitHubService, collect_files, relpath


class AnalysisService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.github = GitHubService()
        self.repo_scanner = RepoScannerAgent()
        self.learning_agent = LearningAgent()
        self.issue_miner = IssueMinerAgent()
        self.contribution_planner = ContributionPlannerAgent()
        self.deepseek = DeepSeekClient()

    def analyze(self, repo_id: int, url: str, user_profile: str, goal: str) -> None:
        try:
            self.db.update_repo(repo_id, status="analyzing", progress=5, current_step="Parsing GitHub URL")
            repo = self.github.parse_url(url)
            self.db.add_trace(repo_id, "Orchestrator Agent", "start", "Created repository onboarding workflow.", {"url": url, "goal": goal})

            self.db.update_repo(repo_id, progress=12, current_step="Fetching GitHub metadata")
            meta = self.github.get_repo_meta(repo)
            languages = self.github.get_languages(repo)
            self.db.update_repo(repo_id, **meta)
            self.db.add_trace(repo_id, "GitHub Integration Layer", "fetch", "Fetched repository metadata and language statistics.", {"languages": languages})

            using_local_repo = self.github.has_local_repo(repo)
            self.db.update_repo(
                repo_id,
                progress=22,
                current_step="Using local repository snapshot" if using_local_repo else "Downloading repository snapshot",
            )
            root = self.github.download_repo(repo, meta["default_branch"])
            files = collect_files(root)
            rel_files = [relpath(root, path) for path in files[:80]]
            self.db.add_trace(
                repo_id,
                "Repo Scanner Agent",
                "scan",
                f"Collected {len(files)} files from {'local repository cache' if using_local_repo else 'downloaded repository snapshot'}.",
                rel_files[:18],
            )

            self.db.update_repo(repo_id, progress=36, current_step="Building repository profile")
            profile = self.repo_scanner.run(meta, root, files, languages)
            profile["snapshot_source"] = "local cache" if using_local_repo else "downloaded snapshot"
            self.db.replace_profile(repo_id, profile)
            self.db.add_trace(repo_id, "Repo Scanner Agent", "profile", "Generated runnable repository profile.", profile)

            self.db.update_repo(repo_id, progress=52, current_step="Parsing code with Tree-sitter and building CodeGraph")
            codegraph = TreeSitterCodeGraph(root, files)
            modules, edges = codegraph.build()
            modules = self.merge_non_source_modules(root, files, modules)

            self.db.update_repo(repo_id, progress=60, current_step="Enhancing onboarding analysis with DeepSeek")
            llm_result = self.deepseek.enhance_onboarding(profile, modules, user_profile, goal)
            if llm_result.get("project_summary"):
                profile["project_summary"] = llm_result["project_summary"]
            profile["ai_summary"] = llm_result.get("three_minute_summary") or ""
            profile["architecture_insight"] = llm_result.get("architecture_insight") or ""
            profile["learning_advice"] = llm_result.get("learning_advice") or ""
            profile["contribution_advice"] = llm_result.get("contribution_advice") or ""
            profile["llm_provider"] = self.deepseek.model if llm_result.get("_llm_status") == "deepseek" else "deterministic fallback"
            profile["llm_status"] = llm_result.get("_llm_status", "disabled")
            self.db.replace_profile(repo_id, profile)
            self.db.add_trace(
                repo_id,
                "DeepSeek Reasoning Agent",
                "llm_enhance",
                "Enhanced repository summary, onboarding advice, and contribution guidance with DeepSeek when available.",
                {"provider": profile["llm_provider"], "status": profile["llm_status"]},
            )
            self.db.replace_modules(repo_id, modules, edges)
            self.db.add_trace(
                repo_id,
                "Architecture Agent",
                "codegraph",
                "Built Tree-sitter AST powered CodeGraph with source modules and import edges.",
                {"module_count": len(modules), "edge_count": len(edges), "top_modules": [m["path"] for m in modules[:8]]},
            )

            self.db.update_repo(repo_id, progress=68, current_step="Generating learning paths")
            paths = self.learning_agent.run(modules, profile, user_profile)
            self.db.replace_learning_paths(repo_id, paths)
            self.db.add_trace(repo_id, "Learning Coach Agent", "plan", "Generated 30-minute, 2-hour, and 1-day learning paths.", [path["title"] for path in paths])

            self.db.update_repo(repo_id, progress=82, current_step="Mining newcomer-friendly issues")
            raw_issues = self.github.get_issues(repo)
            if not raw_issues:
                raw_issues = self.local_contribution_candidates(modules)
                self.db.add_trace(
                    repo_id,
                    "Issue Miner Agent",
                    "fallback",
                    "GitHub Issues were unavailable, so generated local first-contribution candidates from docs, tests, and CodeGraph modules.",
                    [issue["title"] for issue in raw_issues[:5]],
                )
            issues = self.issue_miner.run(raw_issues, modules)
            self.db.replace_issues(repo_id, issues)
            self.db.add_trace(repo_id, "Issue Miner Agent", "score", "Scored open issues by first-contribution suitability.", [{"title": i["title"], "score": i["beginner_score"]} for i in issues[:5]])

            self.db.update_repo(repo_id, progress=92, current_step="Running full-process DeepSeek reasoning")
            full_llm = self.deepseek.analyze_full_process(profile, modules, edges, issues, user_profile, goal)
            profile["llm_analysis"] = full_llm
            profile["llm_provider"] = self.deepseek.model if full_llm.get("_llm_status") == "deepseek" else profile.get("llm_provider", "deterministic fallback")
            profile["llm_status"] = full_llm.get("_llm_status", profile.get("llm_status", "disabled"))
            llm_profile = full_llm.get("repo_profile") if isinstance(full_llm.get("repo_profile"), dict) else {}
            if llm_profile.get("one_liner"):
                profile["project_summary"] = llm_profile["one_liner"]
            if llm_profile.get("cognitive_summary"):
                profile["ai_summary"] = llm_profile["cognitive_summary"]
            if isinstance(full_llm.get("architecture_graph"), dict) and full_llm["architecture_graph"].get("insight"):
                profile["architecture_insight"] = full_llm["architecture_graph"]["insight"]
            self.db.replace_profile(repo_id, profile)
            self.db.add_trace(
                repo_id,
                "DeepSeek Reasoning Agent",
                "full_process",
                "Analyzed README, setup commands, Tree-sitter CodeGraph, learning plan, issues, contribution tasks, and reflection as one onboarding workflow.",
                {
                    "provider": profile.get("llm_provider"),
                    "status": profile.get("llm_status"),
                    "learning_steps": len(full_llm.get("learning_path") or []),
                    "contribution_tasks": len(full_llm.get("contribution_tasks") or []),
                },
            )

            self.db.update_repo(repo_id, status="completed", progress=100, current_step="Analysis completed")
            self.db.add_trace(repo_id, "Orchestrator Agent", "done", "Repository onboarding workspace is ready.", {})
        except Exception as exc:
            self.db.update_repo(repo_id, status="failed", error=str(exc), current_step="Analysis failed")
            self.db.add_trace(repo_id, "Orchestrator Agent", "error", f"Analysis failed: {exc}", {})

    def merge_non_source_modules(self, root: Path, files: list[Path], modules: list[dict]) -> list[dict]:
        existing = {module["path"] for module in modules}
        extra = []
        candidates = []
        for path in files:
            rel = relpath(root, path)
            kind = classify_file(rel)
            if kind in {"docs", "config", "ci", "test"} and rel not in existing:
                candidates.append((rel, kind))
        priority = {"docs": 5, "config": 20, "ci": 30, "test": 35}
        for rel, kind in candidates[:40]:
            score = {"docs": 62, "config": 70, "ci": 66, "test": 68}.get(kind, 50)
            extra.append(
                {
                    "path": rel,
                    "name": Path(rel).name,
                    "type": kind,
                    "importance_score": score,
                    "summary": f"{kind.title()} file that helps newcomers understand project operation and contribution workflow.",
                    "read_priority": priority.get(kind, 80),
                    "symbols": [],
                }
            )
        return sorted(modules + extra, key=lambda item: (item.get("read_priority", 99), -item.get("importance_score", 0)))[:120]

    def create_mission(self, repo_id: int, issue_id: int) -> int:
        issue = self.db.get_issue(repo_id, issue_id)
        if not issue:
            raise ValueError("Issue not found")
        profile = self.db.get_overview(repo_id)
        modules = self.db.get_code_map(repo_id)["nodes"]
        mission = self.contribution_planner.run(issue, modules, profile)
        mission_id = self.db.create_mission(repo_id, issue_id, mission)
        self.db.add_trace(repo_id, "Contribution Planner Agent", "mission", "Generated first-contribution mission sandbox.", {"issue": issue.get("title"), "mission_id": mission_id})
        return mission_id

    def local_contribution_candidates(self, modules: list[dict]) -> list[dict]:
        docs = [module for module in modules if module.get("type") == "docs"]
        tests = [module for module in modules if module.get("type") == "test"]
        source = [module for module in modules if module.get("type") == "source"]
        candidates = []
        now = "2026-06-05T00:00:00Z"
        if docs:
            target = docs[0]["path"]
            candidates.append(
                {
                    "number": 9001,
                    "title": f"Improve newcomer explanation in {target}",
                    "body": f"Local candidate generated by RepoPilot because GitHub Issues were unavailable. Review {target} and add a short clarification, example, or setup note for new contributors.",
                    "url": "",
                    "labels": ["local-candidate", "documentation", "good first issue"],
                    "state": "open",
                    "comments_count": 0,
                    "created_at": now,
                    "updated_at": now,
                    "related_files": [target],
                }
            )
        if tests:
            target = tests[0]["path"]
            candidates.append(
                {
                    "number": 9002,
                    "title": f"Add or refine a small test near {target}",
                    "body": f"Local candidate generated from the test map. Inspect {target}, find a nearby behavior with clear expectations, and add a focused regression or edge-case test.",
                    "url": "",
                    "labels": ["local-candidate", "test", "help wanted"],
                    "state": "open",
                    "comments_count": 0,
                    "created_at": now,
                    "updated_at": now,
                    "related_files": [target],
                }
            )
        for index, module in enumerate(source[:3], start=3):
            candidates.append(
                {
                    "number": 9000 + index,
                    "title": f"Create a first-contribution reading note for {module['path']}",
                    "body": f"Local candidate generated from CodeGraph centrality. Read {module['path']}, summarize its public symbols, and improve nearby docs or comments only if a small clarification is obvious.",
                    "url": "",
                    "labels": ["local-candidate", "docs", "beginner"],
                    "state": "open",
                    "comments_count": 0,
                    "created_at": now,
                    "updated_at": now,
                    "related_files": [module["path"]],
                }
            )
        return candidates
