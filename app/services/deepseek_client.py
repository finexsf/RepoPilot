from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat_json(self, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            result = dict(fallback)
            result["_llm_status"] = "disabled"
            return result
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": 0.35,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=45,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                parsed["_llm_status"] = "deepseek"
                return parsed
            except Exception as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1.2)
                    continue
                break
        result = dict(fallback)
        result["_llm_status"] = f"fallback: {last_exc.__class__.__name__ if last_exc else 'UnknownError'}"
        return result

    def enhance_onboarding(
        self,
        profile: dict[str, Any],
        modules: list[dict[str, Any]],
        user_profile: str,
        goal: str,
    ) -> dict[str, Any]:
        top_modules = [
            {
                "path": module.get("path"),
                "type": module.get("type"),
                "score": module.get("importance_score"),
                "summary": module.get("summary"),
                "symbols": module.get("symbols", [])[:6],
            }
            for module in modules[:12]
        ]
        fallback = {
            "project_summary": profile.get("project_summary", ""),
            "three_minute_summary": "",
            "architecture_insight": "",
            "learning_advice": "",
            "contribution_advice": "",
        }
        system = (
            "You are RepoPilot, an AI Software Onboarding Agent. "
            "Return concise JSON only. Help a first-time open-source contributor understand and contribute to a repository. "
            "Base the repository overview primarily on README content. "
            "All user-facing text must be Simplified Chinese. Keep technical names/acronyms such as README, PR, API, RAG, LLM, DeepSeek, CodeGraph, Tree-sitter, Docker, file paths, commands, functions, and class names in English."
        )
        user = json.dumps(
            {
                "repo_profile": profile,
                "readme_language": profile.get("readme_language", "en"),
                "readme_overview_source": profile.get("readme_overview_source", ""),
                "top_modules": top_modules,
                "user_profile": user_profile,
                "goal": goal,
                "required_schema": {
                    "project_summary": "one-sentence repository positioning based on README, Simplified Chinese, keep technical names/acronyms in English",
                    "three_minute_summary": "3-minute explanation for newcomer based on README and code graph, Simplified Chinese, keep technical names/acronyms in English",
                    "architecture_insight": "how to read the architecture, Simplified Chinese, keep technical names/acronyms in English",
                    "learning_advice": "role-aware learning advice, Simplified Chinese, keep technical names/acronyms in English",
                    "contribution_advice": "first PR advice, Simplified Chinese, keep technical names/acronyms in English",
                },
            },
            ensure_ascii=False,
        )
        return self.chat_json(system, user, fallback)

    def analyze_full_process(
        self,
        profile: dict[str, Any],
        modules: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        issues: list[dict[str, Any]],
        user_profile: str,
        goal: str,
    ) -> dict[str, Any]:
        important_modules = [
            {
                "path": module.get("path"),
                "type": module.get("type"),
                "category": module.get("category"),
                "score": module.get("importance_score"),
                "summary": module.get("summary"),
                "symbols": module.get("symbols", [])[:8],
                "imports": module.get("imports", [])[:10],
                "calls": module.get("calls", [])[:12],
            }
            for module in modules[:18]
        ]
        graph_edges = [
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation_type": edge.get("relation_type"),
                "weight": edge.get("weight", 1),
            }
            for edge in edges[:40]
        ]
        candidate_issues = [
            {
                "title": issue.get("title"),
                "labels": issue.get("labels", []),
                "score": issue.get("beginner_score"),
                "reason": issue.get("recommended_reason"),
                "risk": issue.get("risk_summary"),
                "url": issue.get("url"),
            }
            for issue in issues[:8]
        ]
        fallback = {
            "repo_profile": {},
            "overview_cards": [],
            "setup_guide": [],
            "feature_runbook": [],
            "workflow_guide": {},
            "requirement_coverage": [],
            "architecture_graph": {},
            "learning_path": [],
            "checkpoint_quiz": [],
            "contribution_tasks": [],
            "agent_trace": [],
            "reflection": {},
        }
        system = (
            "You are RepoPilot, an AI Software Onboarding Agent for first-time contributors. "
            "Return JSON only. Analyze the whole repository onboarding process, not only a Q&A answer. "
            "Use README as the primary source for project positioning, use Tree-sitter/CodeGraph evidence for architecture, "
            "and write all user-facing text in Simplified Chinese. Do not invent files that are not present in the provided module list. "
            "Every recommendation must be grounded in README, commands, modules, edges, or issues. "
            "Keep technical names/acronyms such as README, PR, API, RAG, LLM, DeepSeek, CodeGraph, Tree-sitter, Docker, file paths, commands, functions, and class names in English. "
            "For architecture, be concrete: identify subsystem layers, key source modules, important functions/classes, "
            "and dependency/call relationships. Prefer explaining startup flow, UI/API boundary, event bus, domain task flow, "
            "plugin/runtime integration, and test/docs surfaces when evidence exists."
        )
        user = json.dumps(
            {
                "repo_profile": profile,
                "readme_language": profile.get("readme_language", "en"),
                "readme_overview_source": profile.get("readme_overview_source", ""),
                "command_hints": profile.get("command_hints", {}),
                "demo_media": profile.get("demo_media", [])[:6],
                "tree_sitter_codegraph": {
                    "important_modules": important_modules,
                    "edges": graph_edges,
                    "node_count": len(modules),
                    "edge_count": len(edges),
                },
                "issues_or_static_candidates": candidate_issues,
                "user_profile": user_profile,
                "goal": goal,
                "required_schema": {
                    "repo_profile": {
                        "one_liner": "README-grounded one sentence positioning, Simplified Chinese, keep technical names/acronyms in English",
                        "cognitive_summary": "3-minute newcomer explanation, Simplified Chinese, keep technical names/acronyms in English",
                        "risks": ["Simplified Chinese newcomer risk 1", "Simplified Chinese newcomer risk 2"],
                    },
                    "overview_cards": [
                        {
                            "label": "short metric/context label",
                            "value": "human-readable value",
                            "explanation": "why this matters for onboarding",
                        }
                    ],
                    "setup_guide": [
                        {
                            "title": "environment/setup step title",
                            "commands": ["real command or concrete manual step grounded in README"],
                            "reason": "why newcomer should do this step",
                        }
                    ],
                    "feature_runbook": [
                        {
                            "name": "feature or capability name",
                            "purpose": "what this feature demonstrates",
                            "commands": ["command/manual action grounded in README or code"],
                            "files": ["existing file path only"],
                            "media_features": ["media feature labels if relevant"],
                        }
                    ],
                    "workflow_guide": {
                        "title": "development workflow title",
                        "evidence_files": ["existing file path only"],
                        "commands": ["validation/build/check command or manual check"],
                        "checklist": ["PR workflow checklist item"],
                        "standards": ["code/review convention inferred from repo evidence"],
                    },
                    "requirement_coverage": [
                        {
                            "requirement": "coding-test requirement",
                            "implementation": "how RepoPilot satisfies it for this repo",
                        }
                    ],
                    "architecture_graph": {
                        "layers": [
                            {
                                "name": "architecture layer name, Simplified Chinese unless it is a technical name",
                                "type": "entry|ui|service|domain|integration|runtime|test|docs",
                                "description": "what this layer does for the system",
                                "files": ["existing file path only"],
                                "why_newcomers_read_it": "why a first-time contributor should inspect this layer",
                            }
                        ],
                        "core_flow": [
                            {
                                "step": 1,
                                "file": "existing file path only",
                                "role": "entry|module|utility|test|config|docs",
                                "summary": "why this file belongs to the core flow",
                            }
                        ],
                        "flow_story": "plain-language architecture walkthrough from user action to core behavior",
                        "relationships": [
                            {
                                "source": "existing file path only",
                                "target": "existing file path only",
                                "type": "imports|calls|initializes|dispatches|uses|documents",
                                "explanation": "semantic reason this relationship matters to the architecture",
                            }
                        ],
                        "module_notes": [
                            {
                                "file": "existing file path only",
                                "responsibility": "module responsibility",
                                "key_symbols": ["symbol names from provided modules only"],
                                "key_calls": ["important calls from provided evidence when available"],
                                "read_after": ["existing file path only"],
                                "read_before": ["existing file path only"],
                            }
                        ],
                        "insight": "how to read the architecture from entry to core modules",
                    },
                    "architecture_quality_requirements": {
                        "min_layers_when_possible": 6,
                        "min_relationships_when_possible": 10,
                        "min_module_notes_when_possible": 8,
                        "relationship_style": "source -> target with an architectural verb and concrete explanation",
                    },
                    "learning_path": [
                        {
                            "index": 1,
                            "title": "step title",
                            "objective": "learning goal",
                            "files": ["existing file path only"],
                            "reason": "why these files now",
                            "estimated_time": "10 min",
                            "checkpoint": "self-check question",
                        }
                    ],
                    "checkpoint_quiz": [{"question": "question", "answer": "answer grounded in files"}],
                    "contribution_tasks": [
                        {
                            "title": "first PR task",
                            "difficulty": "Beginner|Intermediate|Advanced",
                            "difficulty_score": 20,
                            "impact_score": 70,
                            "reason": "why suitable",
                            "files": ["existing file path only"],
                            "knowledge": ["knowledge point"],
                            "first_pr_plan": ["step 1", "step 2", "step 3"],
                            "risk": "risk",
                            "evidence": ["README/CodeGraph/Issue evidence"],
                            "verification": ["command or manual check before PR"],
                            "pr_title": "suggested pull request title",
                            "maintainer_pitch": "short PR description that would convince maintainers",
                        }
                    ],
                    "contribution_strategy": {
                        "summary": "overall first-contribution strategy, Simplified Chinese, keep technical names/acronyms in English",
                        "best_first_task": "title of best task",
                        "selection_reason": "why DeepSeek ranks it first",
                        "avoid_for_first_pr": ["large risky areas to avoid"],
                    },
                    "agent_trace": [
                        {
                            "agent": "Orchestrator Agent|Repo Scanner Agent|CodeGraph Agent|Onboarding Planner Agent|Contribution Advisor Agent|Reflection Agent|DeepSeek Reasoning Agent",
                            "input": "input evidence",
                            "action": "reasoning action",
                            "output": "output artifact",
                            "confidence": 0.85,
                            "next_step": "next user action",
                        }
                    ],
                    "reflection": {
                        "limitations": ["analysis limitation"],
                        "possibly_missing": ["missing evidence"],
                        "recommended_next_input": ["what user should provide or run next"],
                    },
                    "ui_translations": {
                        "zh": {
                            "repo_profile": {
                                "one_liner": "Simplified Chinese translation of one_liner, keeping technical names/acronyms in English",
                                "cognitive_summary": "Simplified Chinese translation of cognitive_summary, keeping technical names/acronyms in English",
                                "risks": ["Simplified Chinese risk item"],
                            },
                            "overview_cards": [
                                {
                                    "label": "Simplified Chinese label",
                                    "value": "Simplified Chinese value where appropriate",
                                    "explanation": "Simplified Chinese explanation",
                                }
                            ],
                        }
                    },
                },
            },
            ensure_ascii=False,
        )
        return self.chat_json(system, user, fallback)
