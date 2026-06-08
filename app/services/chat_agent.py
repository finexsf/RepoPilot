from __future__ import annotations

import json
from typing import Any

from app.services.deepseek_client import DeepSeekClient


class RepoChatAgent:
    """Conversational onboarding agent grounded in a stored AnalysisResult."""

    def __init__(self) -> None:
        self.deepseek = DeepSeekClient()

    def answer(
        self,
        analysis: dict[str, Any],
        message: str,
        history: list[dict[str, str]] | None = None,
        lang: str = "zh",
    ) -> dict[str, Any]:
        if self.is_architecture_question(message):
            return self.deepseek_architecture_answer(analysis, message, history or [], lang)

        intent = self.detect_intent(message)
        fallback = self.fallback_answer(analysis, message, lang)
        payload = self.compact_context(analysis)
        system = (
            "You are RepoPilot Chat Agent, an AI Software Onboarding Agent for first-time contributors. "
            "Answer only from the provided AnalysisResult context. If evidence is missing, say what is missing. "
            "Be concrete: cite files, modules, commands, functions, or tasks. Do not give generic advice. "
            "Use the current user question as the highest priority; history is only supporting context. "
            "When the question asks how to run/setup the repository, output executable commands only when they are "
            "supported by README/setup evidence or the authoritative fallback. Do not invent package-manager commands. "
            "When lang=zh, all user-facing text must be Simplified Chinese. Keep technical names/acronyms such as "
            "README, PR, API, LLM, DeepSeek, CodeGraph, Tree-sitter, Docker, file paths, commands, functions, "
            "and class names in English. Return JSON only."
        )
        user = json.dumps(
            {
                "lang": lang,
                "intent": intent,
                "question": message,
                "history": (history or [])[-6:],
                "analysis_context": payload,
                "authoritative_fallback_answer": fallback,
                "required_schema": {
                    "answer": "direct answer grounded in analysis context",
                    "citations": ["file path, tab name, or evidence source"],
                    "next_actions": ["one concrete next action"],
                    "confidence": 0.85,
                    "agent_trace": [
                        {"step": "understand_question", "detail": "what the user is asking"},
                        {"step": "retrieve_context", "detail": "which analysis sections were used"},
                        {"step": "llm_reasoning", "detail": "reason over the retrieved AnalysisResult evidence"},
                        {"step": "compose_answer", "detail": "how the answer helps onboarding"},
                    ],
                },
            },
            ensure_ascii=False,
        )
        result = self.deepseek.chat_json(system, user, fallback)
        if result.get("_llm_status") != "deepseek":
            return fallback | {
                "llm_status": result.get("_llm_status", "deterministic fallback"),
                "llm_stage": {
                    "provider": "deterministic fallback",
                    "model": "local rules",
                    "status": result.get("_llm_status", "fallback"),
                    "input_sections": self.context_sections(payload),
                },
            }
        answer = str(result.get("answer") or fallback["answer"])
        citations = [str(item) for item in result.get("citations", [])][:8]
        next_actions = [str(item) for item in result.get("next_actions", [])][:4]
        if intent == "run" and self.answer_needs_run_guard(answer, analysis):
            answer = fallback["answer"]
            citations = fallback.get("citations", [])
            next_actions = fallback.get("next_actions", [])
        return {
            "answer": answer,
            "citations": citations,
            "next_actions": next_actions,
            "confidence": self.clamp_float(result.get("confidence"), 0.05, 0.99, 0.86),
            "agent_trace": self.normalize_trace(result.get("agent_trace")),
            "llm_status": "deepseek",
            "llm_stage": {
                "provider": "DeepSeek",
                "model": self.deepseek.model,
                "status": "called",
                "input_sections": self.context_sections(payload),
            },
        }

    def is_architecture_question(self, message: str) -> bool:
        text = message.lower()
        keywords = [
            "architecture",
            "module",
            "call",
            "dependency",
            "flow",
            "\u67b6\u6784",
            "\u6a21\u5757",
            "\u8c03\u7528",
            "\u4f9d\u8d56",
            "\u6d41\u7a0b",
            "\u5173\u7cfb",
        ]
        return any(keyword in text for keyword in keywords)

    def detect_intent(self, message: str) -> str:
        text = message.lower()
        if self.matches(text, ["run", "install", "setup", "start", "local", "demo", "环境", "安装", "运行", "启动", "本地", "跑起来", "复现"]):
            return "run"
        if self.matches(text, ["first pr", "contribution", "contribute", "issue", "task", "pr", "贡献", "任务", "首次"]):
            return "contribution"
        if self.matches(text, ["read", "file", "learn", "path", "先读", "先看", "阅读", "文件", "学习"]):
            return "reading"
        return "general"

    def answer_needs_run_guard(self, answer: str, analysis: dict[str, Any]) -> bool:
        profile = analysis.get("repo_profile", {})
        repo_text = f"{profile.get('name', '')} {profile.get('url', '')}".lower()
        answer_text = answer.lower()
        if "px4" in repo_text and "npm install" in answer_text:
            return True
        if "see readme" in answer_text or "查看 readme" in answer_text:
            return True
        return False

    def deepseek_architecture_answer(
        self,
        analysis: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
        lang: str,
    ) -> dict[str, Any]:
        fallback = self.grounded_architecture_answer(analysis, lang, message, history)
        evidence = self.architecture_evidence_context(analysis)
        if not self.deepseek.enabled:
            return fallback | {
                "llm_status": "deterministic fallback",
                "llm_stage": {
                    "provider": "RepoPilot Evidence Engine",
                    "model": "AnalysisResult + CodeGraph",
                    "status": "deepseek disabled",
                    "input_sections": ["logical_graph", "call_hierarchy", "relation_details", "function_edges"],
                },
            }

        system = (
            "You are RepoPilot's architecture conversation agent. You must answer from the provided repository evidence, "
            "not from generic software-engineering advice. Use the user's current question and recent history to decide "
            "which modules, files, relations, and functions to discuss. If the user asks a follow-up, avoid repeating the "
            "same full overview; drill into the referenced module/relation/file. When lang=zh, write Simplified Chinese. "
            "Keep technical names, file paths, commands, functions/classes, CodeGraph, Tree-sitter, API, PR in English. "
            "Return JSON only."
        )
        user = json.dumps(
            {
                "lang": lang,
                "question": message,
                "recent_history": history[-8:],
                "repository_architecture_evidence": evidence,
                "required_behavior": [
                    "Give a concrete answer with module names, file paths, relation evidence, and function/class samples.",
                    "Do not answer with generic phrases like 'read files and CodeGraph'.",
                    "If this is a second or later turn, explicitly use the history to narrow or extend the prior answer.",
                    "Mention which evidence sections were inspected.",
                ],
                "required_schema": {
                    "answer": "grounded conversational answer",
                    "citations": ["specific file paths or evidence section names"],
                    "next_actions": ["concrete next action"],
                    "confidence": 0.9,
                    "agent_trace": [
                        {"step": "understand_question", "detail": "what the user is asking now"},
                        {"step": "retrieve_context", "detail": "which module/file/function evidence was retrieved"},
                        {"step": "llm_reasoning", "detail": "how DeepSeek reasons over repository evidence and history"},
                        {"step": "compose_answer", "detail": "how the answer differs from generic advice"},
                    ],
                },
            },
            ensure_ascii=False,
        )
        result = self.deepseek.chat_json(system, user, fallback)
        if result.get("_llm_status") != "deepseek":
            return fallback | {
                "llm_status": result.get("_llm_status", "deterministic fallback"),
                "llm_stage": {
                    "provider": "RepoPilot Evidence Engine",
                    "model": "AnalysisResult + CodeGraph",
                    "status": result.get("_llm_status", "fallback"),
                    "input_sections": ["logical_graph", "call_hierarchy", "relation_details", "function_edges"],
                },
            }
        return {
            "answer": str(result.get("answer") or fallback["answer"]),
            "citations": [str(item) for item in result.get("citations", [])][:10] or fallback.get("citations", []),
            "next_actions": [str(item) for item in result.get("next_actions", [])][:5] or fallback.get("next_actions", []),
            "confidence": self.clamp_float(result.get("confidence"), 0.05, 0.99, 0.9),
            "agent_trace": self.normalize_trace(result.get("agent_trace")),
            "llm_status": "deepseek",
            "llm_stage": {
                "provider": "DeepSeek",
                "model": self.deepseek.model,
                "status": "called with architecture evidence",
                "input_sections": ["logical_graph", "call_hierarchy", "relation_details", "function_edges", "chat_history"],
            },
        }

    def architecture_evidence_context(self, analysis: dict[str, Any]) -> dict[str, Any]:
        graph = analysis.get("architecture_graph", {})
        logical = graph.get("logical_graph", {})
        call_graph = graph.get("call_hierarchy", {})
        return {
            "logical_nodes": logical.get("nodes", [])[:40],
            "logical_edges": logical.get("edges", [])[:40],
            "core_chain": logical.get("core_chain", [])[:10],
            "relation_details": call_graph.get("relation_details", [])[:32],
            "module_cards": call_graph.get("modules", [])[:24],
            "file_edges": call_graph.get("file_edges", [])[:60],
            "function_edges": call_graph.get("function_edges", [])[:80],
            "core_flow": graph.get("core_flow", [])[:10],
            "detailed_modules": graph.get("detailed_modules", [])[:20],
        }

    def grounded_architecture_answer(
        self,
        analysis: dict[str, Any],
        lang: str,
        message: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        is_zh = lang == "zh"
        focus = self.extract_focus_terms(message, history or [])
        graph = analysis.get("architecture_graph", {})
        logical = graph.get("logical_graph", {})
        call_graph = graph.get("call_hierarchy", {})
        nodes = logical.get("nodes", [])
        edges = logical.get("edges", [])
        details = call_graph.get("relation_details", [])
        modules = call_graph.get("modules", [])
        function_edges = call_graph.get("function_edges", [])

        if not nodes and not modules:
            answer = "当前分析结果缺少架构图证据，需要重新分析仓库。" if is_zh else "No architecture evidence is available; rerun repository analysis."
            return self.pack(answer, ["Architecture"], ["重新点击 Analyze Repository。"] if is_zh else ["Run Analyze Repository again."], 0.35, "repo_inspection")

        filtered_nodes = self.filter_by_focus(nodes, focus, ["name", "files"]) or nodes
        filtered_details = self.filter_by_focus(details, focus, ["source_name", "target_name", "source_files", "target_files", "evidence", "reading_order"]) or details
        filtered_functions = self.filter_by_focus(function_edges, focus, ["source_file", "source_function", "target_file", "target_function"]) or function_edges
        top_modules = filtered_nodes[:12]
        top_details = filtered_details[:6]
        top_functions = filtered_functions[:10]

        if is_zh:
            lines = [
                "我已基于当前仓库的 CodeGraph 深入检查模块、文件和函数级证据。这个仓库的架构可以按下面方式读：",
                "",
                "一、核心模块块：",
            ]
            for item in top_modules:
                files = ", ".join((item.get("files") or [])[:3])
                lines.append(f"- {item.get('name')}：{item.get('file_count', 0)} 个文件；代表文件：{files}")
            if top_details:
                lines.extend(["", "二、关键模块调用关系："])
                for rel in top_details:
                    source = rel.get("source_name") or rel.get("source")
                    target = rel.get("target_name") or rel.get("target")
                    relation = rel.get("relation") or "calls"
                    purpose = rel.get("purpose") or ""
                    evidence = "; ".join(rel.get("evidence", [])[:2])
                    order = " -> ".join(rel.get("reading_order", [])[:4])
                    lines.append(f"- {source} --{relation}--> {target}：{purpose}")
                    if evidence:
                        lines.append(f"  证据：{evidence}")
                    if order:
                        lines.append(f"  阅读顺序：{order}")
            if top_functions:
                lines.extend(["", "三、函数/类调用样例："])
                for edge in top_functions:
                    source_file = edge.get("source_file") or "-"
                    source_fn = edge.get("source_function") or "-"
                    target_fn = edge.get("target_function") or "-"
                    target_file = edge.get("target_file") or "name-only"
                    lines.append(f"- {source_file}::{source_fn} -> {target_fn} ({target_file})")
            lines.extend([
                "",
                "结论：不要只看 README。先从入口/文档确认运行方式，再读 Core 子系统，最后沿着 Platform/Driver、Config、Tests 验证真实运行链路。",
            ])
            next_actions = [
                "打开 Architecture 页的“详细模块调用说明”，按第一条关系的阅读顺序逐个点开源码。",
                "从 Core / navigator 或 Core / ekf2 开始，记录它调用的平台/驱动或测试文件。",
            ]
        else:
            lines = [
                "I inspected the repository evidence from CodeGraph at module, file, and function levels. Read the architecture as:",
                "",
                "1. Core module blocks:",
            ]
            for item in top_modules:
                files = ", ".join((item.get("files") or [])[:3])
                lines.append(f"- {item.get('name')}: {item.get('file_count', 0)} files; representative files: {files}")
            if top_details:
                lines.extend(["", "2. Key module call relations:"])
                for rel in top_details:
                    source = rel.get("source_name") or rel.get("source")
                    target = rel.get("target_name") or rel.get("target")
                    relation = rel.get("relation") or "calls"
                    purpose = rel.get("purpose") or ""
                    evidence = "; ".join(rel.get("evidence", [])[:2])
                    order = " -> ".join(rel.get("reading_order", [])[:4])
                    lines.append(f"- {source} --{relation}--> {target}: {purpose}")
                    if evidence:
                        lines.append(f"  Evidence: {evidence}")
                    if order:
                        lines.append(f"  Reading order: {order}")
            if top_functions:
                lines.extend(["", "3. Function/class call samples:"])
                for edge in top_functions:
                    lines.append(f"- {edge.get('source_file') or '-'}::{edge.get('source_function') or '-'} -> {edge.get('target_function') or '-'} ({edge.get('target_file') or 'name-only'})")
            next_actions = [
                "Open the first relation in Architecture > Detailed Module Call Explanation and inspect its files.",
                "Start from a Core subsystem, then trace its Platform/Driver, Config, and Tests evidence.",
            ]

        citations = []
        for rel in top_details:
            citations.extend(rel.get("reading_order", [])[:2])
        if not citations:
            for item in top_modules:
                citations.extend((item.get("files") or [])[:1])
        return self.pack("\n".join(lines), list(dict.fromkeys(citations))[:8], next_actions, 0.9, "repo_inspection")

    def extract_focus_terms(self, message: str, history: list[dict[str, str]]) -> list[str]:
        text = " ".join([message] + [item.get("content", "") for item in history[-2:]])
        candidates = []
        for token in [
            "ekf2",
            "ekf",
            "navigator",
            "logger",
            "gimbal",
            "commander",
            "mavlink",
            "sensors",
            "platform",
            "driver",
            "posix",
            "nuttx",
            "pca9685",
            "mission",
            "rtl",
            "geofence",
        ]:
            if token.lower() in text.lower():
                candidates.append(token)
        for part in text.replace("\\", "/").split():
            if "/" in part and len(part) > 3:
                candidates.append(part.strip("`，。,.?？:：;；()（）"))
        return list(dict.fromkeys(candidates))[:8]

    def filter_by_focus(self, items: list[dict[str, Any]], focus: list[str], keys: list[str]) -> list[dict[str, Any]]:
        if not focus:
            return []
        matched = []
        for item in items:
            haystack_parts = []
            for key in keys:
                value = item.get(key)
                if isinstance(value, list):
                    haystack_parts.extend(str(part) for part in value)
                else:
                    haystack_parts.append(str(value or ""))
            haystack = " ".join(haystack_parts).lower()
            if any(term.lower() in haystack for term in focus):
                matched.append(item)
        return matched

    def compact_context(self, analysis: dict[str, Any]) -> dict[str, Any]:
        profile = analysis.get("repo_profile", {})
        graph = analysis.get("architecture_graph", {})
        call_graph = graph.get("call_hierarchy", {})
        logical = graph.get("logical_graph", {})
        return {
            "repo_profile": {
                "name": profile.get("name"),
                "url": profile.get("url"),
                "one_liner": profile.get("one_liner"),
                "zh_one_liner": profile.get("zh_one_liner"),
                "setup_guide": profile.get("setup_guide", [])[:6],
                "feature_runbook": profile.get("feature_runbook", [])[:6],
                "workflow_guide": profile.get("workflow_guide", {}),
            },
            "important_files": analysis.get("important_files", [])[:12],
            "architecture": {
                "logical_nodes": logical.get("nodes", [])[:24],
                "logical_edges": logical.get("edges", [])[:24],
                "relation_details": call_graph.get("relation_details", [])[:16],
                "function_edges": call_graph.get("function_edges", [])[:24],
                "core_flow": graph.get("core_flow", [])[:8],
            },
            "learning_path": analysis.get("learning_path", [])[:8],
            "checkpoint_quiz": analysis.get("checkpoint_quiz", [])[:6],
            "contribution_strategy": analysis.get("contribution_strategy", {}),
            "contribution_tasks": analysis.get("contribution_tasks", [])[:6],
            "reflection": analysis.get("reflection", {}),
        }

    def fallback_answer(self, analysis: dict[str, Any], message: str, lang: str) -> dict[str, Any]:
        text = message.lower()
        profile = analysis.get("repo_profile", {})
        is_zh = lang == "zh"
        repo_text = f"{profile.get('name', '')} {profile.get('url', '')}".lower()

        if self.matches(text, ["run", "install", "setup", "start", "local", "demo", "环境", "安装", "运行", "启动", "本地", "跑起来", "复现"]):
            if "px4" in repo_text:
                answer = (
                    "建议在 Ubuntu 或 WSL2 中按 PX4 官方开发路径运行，不要用 `npm install` 作为主安装方式。\n\n"
                    "```bash\n"
                    "git clone --recursive https://github.com/PX4/PX4-Autopilot.git\n"
                    "cd PX4-Autopilot\n"
                    "bash ./Tools/setup/ubuntu.sh\n"
                    "make px4_sitl gz_x500\n"
                    "```\n\n"
                    "如果仓库已经在本地，先进入仓库目录并补齐子模块：\n\n"
                    "```bash\n"
                    "cd PX4-Autopilot\n"
                    "git submodule update --init --recursive\n"
                    "bash ./Tools/setup/ubuntu.sh\n"
                    "make px4_sitl gz_x500\n"
                    "```\n\n"
                    "验证修改时，文档类 PR 可运行 `make -C docs html`；代码类改动优先运行相关模块测试或重新跑 SITL。"
                )
                return self.pack(
                    answer,
                    ["README.md", "Tools/setup/ubuntu.sh", "make px4_sitl gz_x500"],
                    ["先跑通 `make px4_sitl gz_x500`，再根据报错定位依赖、子模块或编译目标。"],
                    0.9,
                )
            return self.command_fallback_answer(profile, is_zh)

        if self.matches(text, ["contribution", "pr", "issue", "task", "贡献", "任务", "首次"]):
            tasks = analysis.get("contribution_tasks", [])
            if tasks:
                best = tasks[0]
                title = best.get("title") or "第一个 Beginner 任务"
                raw_reason = best.get("reason") or best.get("recommended_reason") or ""
                reason = self.zh_task_reason(raw_reason)
                files = ", ".join((best.get("files") or best.get("possible_files") or [])[:4])
                plan = [
                    "阅读推荐文件，先用一句话写清楚本次改动范围。",
                    "只做一个小的文档、测试、配置或源码改动，避免顺手重构。",
                    "运行对应验证命令，确认通过后提交聚焦的 PR。",
                ]
                answer = (
                    f"最适合作为首次 PR 的任务是：{title}。\n\n"
                    f"推荐理由：{reason}\n"
                    f"可能涉及文件：{files or 'README.md / docs'}\n\n"
                    "First PR Plan：\n"
                    + "\n".join(f"{idx}. {step}" for idx, step in enumerate(plan[:3], 1))
                )
            else:
                answer = "首次贡献建议选择低风险、可验证、涉及文件少的小任务，例如文档补充、示例补全或小测试。"
            return self.pack(answer, ["Contribution Radar"], ["选择一个 Beginner 任务，先写清楚 3 步 PR 计划。"], 0.82)

        if self.matches(text, ["read", "file", "learn", "path", "先读", "先看", "阅读", "文件", "学习"]):
            important = analysis.get("important_files", [])
            first = important[0] if important else {}
            path = first.get("path") or "README.md"
            reason = first.get("why_read") or first.get("reason") or "它是理解项目目标、安装方式和核心入口的最短路径。"
            next_files = [item.get("path") for item in important[1:5] if item.get("path")]
            answer = (
                f"建议先读 `{path}`。\n\n"
                f"原因：{reason}\n\n"
                "接着读：\n"
                + "\n".join(f"- `{item}`" for item in next_files)
            )
            return self.pack(answer, ["Important Files", "Learning Path"], ["先读第一个文件，再沿着推荐入口文件进入核心模块。"], 0.82)

        if self.matches(text, ["run", "install", "setup", "环境", "安装", "运行", "启动", "复现", "demo"]):
            steps = profile.get("setup_guide", [])
            features = profile.get("feature_runbook", [])
            lines = []
            for step in steps[:4]:
                commands = step.get("commands") or []
                if commands:
                    lines.append(f"- {step.get('title')}: {'; '.join(commands[:3])}")
            for feature in features[:4]:
                commands = feature.get("commands") or []
                if commands:
                    lines.append(f"- {feature.get('name')}: {'; '.join(commands[:3])}")
            answer = "\n".join(lines) or ("当前没有识别到可直接执行命令。" if is_zh else "No direct runnable commands were detected.")
            prefix = "建议按这些命令复现项目：\n" if is_zh else "Use these commands to reproduce the project:\n"
            return self.pack(prefix + answer, ["Overview / Environment Setup", "Overview / Functional Runbook"], ["先跑通第一个 demo，再把报错继续发给 Agent Chat。"] if is_zh else ["Run the first demo, then paste errors back into Agent Chat."], 0.76)

        if self.matches(text, ["contribution", "pr", "issue", "贡献", "任务", "首次"]):
            strategy = analysis.get("contribution_strategy", {})
            tasks = analysis.get("contribution_tasks", [])
            lines = [f"- {task.get('title')}: {task.get('reason')}" for task in tasks[:4]]
            summary = strategy.get("summary") or ("优先选择低风险、可验证、涉及文件少的小任务。" if is_zh else "Prefer low-risk, verifiable tasks with a small file scope.")
            answer = (f"首次贡献建议：{summary}\n\n推荐任务：\n" if is_zh else f"First contribution advice: {summary}\n\nRecommended tasks:\n") + "\n".join(lines)
            return self.pack(answer, ["Contribution Radar"], ["选第一个 Beginner 任务，先写 3 步 PR 计划。"] if is_zh else ["Pick the first Beginner task and write a three-step PR plan."], 0.77)

        if self.matches(text, ["learn", "学习", "路径", "怎么看", "先看", "阅读"]):
            steps = analysis.get("learning_path", [])
            lines = [f"{step.get('index')}. {step.get('title')}: {', '.join(step.get('files', [])[:3])}" for step in steps[:6]]
            answer = ("建议按这个学习路径推进：\n" if is_zh else "Follow this learning path:\n") + "\n".join(lines)
            return self.pack(answer, ["Learning Path"], ["完成每一步 checkpoint 后再进入下一步。"] if is_zh else ["Finish each checkpoint before moving on."], 0.77)

        name = profile.get("name") or ("这个仓库" if is_zh else "This repository")
        summary = profile.get("zh_cognitive_summary") if is_zh else None
        summary = summary or profile.get("cognitive_summary") or profile.get("zh_one_liner") or profile.get("one_liner")
        answer = (
            f"{name} 的核心定位是：{summary or '当前分析结果不足。'}\n\n你可以继续问：如何运行、先看哪些文件、架构调用关系、适合我的首次 PR 是什么。"
            if is_zh
            else f"{name} is about: {summary or 'insufficient evidence.'}\n\nAsk about setup, files, architecture, or first PR strategy."
        )
        return self.pack(answer, ["Overview / Project Cognitive Summary"], ["问一个更具体的问题，例如“我应该先读哪个文件？”"] if is_zh else ["Ask a more specific question, such as which file to read first."], 0.74)

    def command_fallback_answer(self, profile: dict[str, Any], is_zh: bool) -> dict[str, Any]:
        steps = profile.get("setup_guide", [])
        features = profile.get("feature_runbook", [])
        lines = []
        for step in steps[:5]:
            commands = [cmd for cmd in (step.get("commands") or []) if self.is_real_command(cmd)]
            if commands:
                lines.append(f"- {step.get('title')}: {'; '.join(commands[:3])}")
        for feature in features[:5]:
            commands = [cmd for cmd in (feature.get("commands") or []) if self.is_real_command(cmd)]
            if commands:
                lines.append(f"- {feature.get('name')}: {'; '.join(commands[:3])}")
        answer = "\n".join(lines) or ("当前没有识别到可直接执行的运行命令。" if is_zh else "No direct runnable commands were detected.")
        prefix = "建议按这些命令复现项目：\n" if is_zh else "Use these commands to reproduce the project:\n"
        next_action = "先跑通第一个 demo，再把报错继续发给 Agent Chat。" if is_zh else "Run the first demo, then paste errors back into Agent Chat."
        return self.pack(prefix + answer, ["Overview / Environment Setup", "Overview / Functional Runbook"], [next_action], 0.78)

    def is_real_command(self, command: str) -> bool:
        lowered = command.strip().lower()
        if not lowered:
            return False
        blocked = ["see readme", "read readme", "查看 readme", "pytest", "test:pytest"]
        if lowered in blocked:
            return False
        starters = ("git ", "python ", "python3 ", "pip ", "conda ", "uv ", "npm ", "yarn ", "pnpm ", "make ", "cmake ", "bash ", "sh ", "docker ")
        return lowered.startswith(starters) or lowered.startswith("./")

    def zh_task_reason(self, reason: str) -> str:
        text = reason.lower()
        parts = []
        if "newcomer-friendly" in text:
            parts.append("带有新手友好信号，适合第一次熟悉贡献流程。")
        if "focused change scope" in text:
            parts.append("改动范围比较集中，不需要一次理解整个仓库。")
        if "clear verification path" in text:
            parts.append("验证路径明确，改完后容易证明没有破坏现有功能。")
        if "documentation" in text or "readme" in text:
            parts.append("主要涉及 README 或文档，风险比核心飞控代码更低。")
        if not parts:
            parts.append("范围小、风险低、容易验证，适合作为首次 PR。")
        return "".join(parts)

    def pack(self, answer: str, citations: list[str], next_actions: list[str], confidence: float, status: str = "deterministic fallback") -> dict[str, Any]:
        return {
            "answer": answer,
            "citations": citations,
            "next_actions": next_actions,
            "confidence": confidence,
            "agent_trace": [
                {"step": "understand_question", "detail": "识别用户意图：运行复现、架构理解、学习路径或首次贡献。"},
                {"step": "retrieve_context", "detail": "从 AnalysisResult 检索相关证据片段。"},
                {"step": "repo_inspection", "detail": "读取 logical_graph、call_hierarchy、relation_details 和 function_edges。"},
                {"step": "compose_answer", "detail": "生成带文件证据和下一步行动的回答。"},
            ],
            "llm_stage": {
                "provider": "RepoPilot Evidence Engine",
                "model": "AnalysisResult + CodeGraph",
                "status": status,
                "input_sections": ["Overview", "Architecture", "Learning Path", "Contribution Radar"],
            },
            "llm_status": status,
        }

    def normalize_trace(self, trace: Any) -> list[dict[str, str]]:
        cleaned = []
        if isinstance(trace, list):
            for item in trace[:6]:
                if isinstance(item, dict) and item.get("step") and item.get("detail"):
                    cleaned.append({"step": str(item["step"]), "detail": str(item["detail"])})
        return cleaned or [
            {"step": "understand_question", "detail": "Parse the user's onboarding question."},
            {"step": "retrieve_context", "detail": "Retrieve relevant AnalysisResult sections."},
            {"step": "llm_reasoning", "detail": "Reason over repository evidence."},
            {"step": "compose_answer", "detail": "Return answer, citations, and next actions."},
        ]

    def context_sections(self, payload: dict[str, Any]) -> list[str]:
        sections = []
        if payload.get("repo_profile"):
            sections.append("Overview")
        if payload.get("important_files"):
            sections.append("Important Files")
        if payload.get("architecture"):
            sections.append("Architecture")
        if payload.get("learning_path"):
            sections.append("Learning Path")
        if payload.get("contribution_tasks"):
            sections.append("Contribution Radar")
        return sections

    def matches(self, text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def clamp_float(self, value: Any, low: float, high: float, default: float) -> float:
        try:
            return max(low, min(high, float(value)))
        except Exception:
            return default
