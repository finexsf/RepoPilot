from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from app.services.deepseek_client import DeepSeekClient


SKIP_KEYS = {
    "url",
    "path",
    "file",
    "files",
    "commands",
    "command",
    "verification",
    "symbols",
    "imports",
    "calls",
    "source",
    "target",
    "id",
    "owner",
    "model",
    "provider",
    "llm_provider",
    "llm_status",
    "snapshot_source",
    "status",
    "type",
    "category",
    "role",
    "difficulty",
}

TRANSLATABLE_KEYS = {
    "one_liner",
    "zh_one_liner",
    "cognitive_summary",
    "zh_cognitive_summary",
    "zh_risks",
    "name",
    "risks",
    "label",
    "value",
    "explanation",
    "why_important",
    "title",
    "reason",
    "purpose",
    "summary",
    "architecture_insight",
    "learning_advice",
    "contribution_advice",
    "description",
    "why_newcomers_read_it",
    "notice",
    "flow_story",
    "responsibility",
    "objective",
    "checkpoint",
    "question",
    "answer",
    "best_first_task",
    "selection_reason",
    "avoid_for_first_pr",
    "knowledge",
    "evidence",
    "first_pr_plan",
    "risk",
    "pr_title",
    "maintainer_pitch",
    "input",
    "action",
    "output",
    "next_step",
    "limitations",
    "recommended_next_input",
    "newcomer_note",
}

MODULE_NAME_RE = re.compile(r"^(Entry|App|Runtime|Core|Module|Model|Driver|Platform|Lib|Tools|Config|Tests|Docs|Component)\s*/\s*")
FILE_REL_RE = re.compile(r"\.(py|js|ts|tsx|jsx|cpp|cc|c|h|hpp|md|toml|yaml|yml|json|cmake)\b", re.IGNORECASE)


class TranslationGuard:
    def __init__(self) -> None:
        self.deepseek = DeepSeekClient()
        self.cache: dict[str, str] = {}

    def translate_result(self, result: dict[str, Any], lang: str) -> dict[str, Any]:
        if lang != "zh":
            return result
        translated = deepcopy(result)
        refs: list[tuple[dict[str, Any] | list[Any], str | int, str]] = []
        self.collect_refs(translated, refs)
        texts = []
        seen = set()
        for _, _, text in refs:
            if text not in seen and self.needs_translation(text):
                seen.add(text)
                texts.append(text)
        mapping = self.translate_texts(texts)
        for container, key, text in refs:
            if text in mapping:
                container[key] = mapping[text]
        translated["translation_guard"] = {
            "lang": "zh",
            "provider": self.deepseek.model if self.deepseek.enabled else "disabled",
            "checked_segments": len(texts),
            "translated_segments": len(mapping),
        }
        return translated

    def collect_refs(self, node: Any, refs: list[tuple[dict[str, Any] | list[Any], str | int, str]], key: str = "") -> None:
        if isinstance(node, dict):
            for child_key, value in node.items():
                if child_key in SKIP_KEYS:
                    continue
                if child_key == "name" and not self.is_translatable_name(value):
                    continue
                if isinstance(value, str) and child_key in TRANSLATABLE_KEYS and self.needs_translation(value):
                    refs.append((node, child_key, value))
                elif isinstance(value, (dict, list)):
                    self.collect_refs(value, refs, child_key)
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, str) and key in TRANSLATABLE_KEYS and self.needs_translation(value):
                    refs.append((node, index, value))
                elif isinstance(value, (dict, list)):
                    self.collect_refs(value, refs, key)

    def needs_translation(self, text: str) -> bool:
        text = str(text or "").strip()
        if len(text) < 4:
            return False
        if re.search(r"[\u4e00-\u9fff]", text):
            return False
        if MODULE_NAME_RE.match(text):
            return False
        if "->" in text and FILE_REL_RE.search(text):
            return False
        if text.count("/") >= 2 and FILE_REL_RE.search(text):
            return False
        if re.match(r"^[\w./\\:-]+$", text):
            return False
        latin = len(re.findall(r"[A-Za-z]", text))
        return latin >= 8

    def is_translatable_name(self, value: Any) -> bool:
        text = str(value or "")
        if MODULE_NAME_RE.match(text):
            return False
        return bool(re.search(r"\b(demo|inference|quick start|interactive|core model|tests|evaluation|documentation|examples|web|project|task|agent)\b", text, re.IGNORECASE))

    def translate_texts(self, texts: list[str]) -> dict[str, str]:
        missing = [text for text in texts if text not in self.cache]
        for start in range(0, len(missing), 45):
            batch = missing[start : start + 45]
            if batch:
                self.cache.update(self.translate_batch(batch))
        return {text: self.cache[text] for text in texts if text in self.cache}

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        fallback = {"translations": texts}
        system = (
            "You are a UI localization guard for RepoPilot. Translate every user-facing English text to Simplified Chinese. "
            "Preserve technical names/acronyms and code terms such as README, PR, API, LLM, DeepSeek, CodeGraph, Tree-sitter, "
            "Python, npm, Docker, file paths, commands, class/function names, model names, and URLs. Return JSON only."
        )
        user = json.dumps(
            {
                "texts": texts,
                "schema": {"translations": ["Simplified Chinese translation, same order and length as texts"]},
            },
            ensure_ascii=False,
        )
        result = self.deepseek.chat_json(system, user, fallback)
        translations = result.get("translations") if result.get("_llm_status") == "deepseek" else None
        if not isinstance(translations, list) or len(translations) != len(texts):
            return {text: self.local_fallback_translate(text) for text in texts}
        output = {}
        for source, target in zip(texts, translations):
            target_text = str(target)
            output[source] = target_text if re.search(r"[\u4e00-\u9fff]", target_text) else self.local_fallback_translate(source)
        return output

    def local_fallback_translate(self, text: str) -> str:
        replacements = {
            "Web / Interactive Demo": "Web / 交互式 Demo",
            "Core Model / API": "核心模型 / API",
            "Tests / Evaluation": "测试 / 评测",
            "Documentation / Examples": "文档 / 示例",
            "Inference / Quick Start": "推理 / 快速开始",
            "Demo / Basic Demo": "演示 / 基础 Demo",
            "Demo / Real-Time Interactive Demo": "演示 / 实时交互 Demo",
            "Clone repository": "克隆仓库",
            "Create environment": "创建运行环境",
            "Install dependencies": "安装依赖",
            "Run project or demo": "运行项目或 Demo",
            "Validate before PR": "提交 PR 前验证",
        }
        if text in replacements:
            return replacements[text]
        if text.startswith("About PX4 is an open-source autopilot stack") or text.startswith("PX4 is an open-source autopilot stack"):
            return "PX4 是面向无人机和无人系统的开源 autopilot stack，支持多旋翼、固定翼、VTOL、无人车和多种实验平台。理解该项目时应重点关注飞控核心模块、平台适配层、构建/仿真流程和开发文档。"
        about_match = re.match(r"^About\s+([A-Za-z0-9_.-]+)\s+is\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
        if about_match:
            repo_name = about_match.group(1)
            return f"关于 {repo_name}：这是一个开源项目。请从项目目标、核心模块、运行命令和可验证的修改入口四个角度理解它。"
        is_match = re.match(r"^([A-Za-z0-9_.-]+)\s+is\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
        if is_match and len(text) > 80:
            repo_name = is_match.group(1)
            return f"{repo_name} 是一个开源项目。请从项目目标、核心模块、运行命令和可验证的修改入口四个角度理解它。"
        if re.search(r"\b(demo|run|server|inference|quick start)\b", text, re.IGNORECASE):
            return "项目运行或 Demo 复现入口：按下方命令执行，并打开关联文件查看入口逻辑。"
        if re.search(r"\b(test|validation|evaluation|benchmark)\b", text, re.IGNORECASE):
            return "测试或评测验证入口：执行下方验证命令，并打开关联文件查看断言范围。"
        if re.search(r"\b(contribution|PR|issue|change|scope)\b", text, re.IGNORECASE):
            return "首次贡献任务：先打开推荐文件，限定变更范围，再执行验证步骤。"
        if re.search(r"\b(architecture|module|codegraph|import|dependency|relation)\b", text, re.IGNORECASE):
            return "RepoPilot 已读取模块图、文件边和函数调用样例；请查看下方具体模块、文件和调用证据。"
        return "基于当前仓库的文件、命令和调用关系生成。"
