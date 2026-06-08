from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.codegraph import classify_file
from app.services.github_service import read_text, relpath


class RepoScannerAgent:
    def run(self, meta: dict[str, Any], root: Path, files: list[Path], languages: list[str]) -> dict[str, Any]:
        rel_files = [relpath(root, path) for path in files]
        names = {Path(path).name.lower(): path for path in rel_files if "/" not in path}
        package = self.read_first(root, ["package.json"])
        pyproject = self.read_first(root, ["pyproject.toml"])
        requirements = self.read_first(root, ["requirements.txt"])
        readme = self.read_first(root, ["README.md", "readme.md"])
        contributing = self.read_first(root, ["CONTRIBUTING.md", "contributing.md", ".github/CONTRIBUTING.md", "docs/contributing.rst", "docs/contributing.md"])
        command_hints = self.extract_shell_commands(readme)
        inferred_hints = self.infer_command_hints(rel_files, package, pyproject, requirements)
        for key, values in inferred_hints.items():
            command_hints[key] = list(dict.fromkeys(command_hints.get(key, []) + values))[:8]
        readme_language = self.detect_readme_language(readme)
        release_usage = self.detect_release_usage(readme, rel_files)

        tech_stack = list(dict.fromkeys(languages + self.detect_stack(package, pyproject, requirements)))
        install = (command_hints.get("install") or [""])[0]
        if not install:
            install = "npm install" if "package.json" in names else "pip install -r requirements.txt" if "requirements.txt" in names else "pip install -e ." if "pyproject.toml" in names else ""
        run = (command_hints.get("web") or command_hints.get("run") or [""])[0]
        if not run:
            run = self.detect_script(package, "dev") or self.detect_script(package, "start") or ("python main.py" if "main.py" in names else "flask --app app run" if "flask" in (meta.get("name") or "").lower() else "")
        test = (command_hints.get("test") or [""])[0]
        if not test:
            test = self.detect_script(package, "test") or ("python -m pytest" if any("test" in path.lower() for path in rel_files) else "")
        if release_usage.get("install"):
            install = release_usage["install"]
            command_hints["install"] = list(dict.fromkeys(release_usage.get("install_steps", []) + command_hints.get("install", [])))[:8]
        if release_usage.get("run"):
            run = release_usage["run"]
            command_hints["run"] = list(dict.fromkeys(release_usage.get("run_steps", []) + command_hints.get("run", [])))[:8]
            command_hints["web"] = list(dict.fromkeys(release_usage.get("run_steps", []) + command_hints.get("web", [])))[:8]
        if not test and any(path.endswith(".py") for path in rel_files):
            test = "python -m compileall <changed_module_or_package>"

        docs_score = 20 if readme else 0
        contrib_score = 15 if contributing else 0
        tests_score = 15 if any(classify_file(path) == "test" for path in rel_files) else 0
        issue_score = 20
        newcomer_score = min(100, 35 + docs_score + contrib_score + tests_score + issue_score)

        return {
            "project_summary": self.summarize(meta, readme),
            "readme_language": readme_language,
            "readme_overview_source": self.readme_overview_source(readme),
            "tech_stack": tech_stack[:8],
            "demo_media": self.extract_demo_media(readme, meta),
            "demo_runbook": self.extract_demo_runbook(readme, rel_files),
            "command_hints": command_hints,
            "install_command": install,
            "run_command": run,
            "test_command": test,
            "contribution_guide_summary": "Contribution guide detected." if contributing else "No dedicated CONTRIBUTING file detected; use README and recent PR conventions.",
            "newcomer_score": newcomer_score,
        }

    def read_first(self, root: Path, candidates: list[str]) -> str:
        for candidate in candidates:
            path = root / candidate
            if path.exists():
                return read_text(path, 80_000)
        return ""

    def detect_stack(self, package: str, pyproject: str, requirements: str) -> list[str]:
        stack = []
        text = "\n".join([package, pyproject, requirements]).lower()
        for key, label in [
            ("next", "Next.js"),
            ("react", "React"),
            ("vue", "Vue"),
            ("fastapi", "FastAPI"),
            ("django", "Django"),
            ("pytest", "pytest"),
            ("typescript", "TypeScript"),
            ("tailwind", "Tailwind CSS"),
        ]:
            if key in text:
                stack.append(label)
        return stack

    def detect_script(self, package: str, script: str) -> str | None:
        if not package:
            return None
        try:
            data = json.loads(package)
            if script in data.get("scripts", {}):
                return f"npm run {script}"
        except Exception:
            return None
        return None

    def infer_command_hints(self, rel_files: list[str], package: str, pyproject: str, requirements: str) -> dict[str, list[str]]:
        files = set(rel_files)
        names = {Path(path).name.lower(): path for path in rel_files}
        hints = {"setup": [], "install": [], "run": [], "test": [], "web": [], "eval": [], "docs": []}
        if "package.json" in names:
            hints["install"].append("npm install")
            for script in ["dev", "start", "serve"]:
                command = self.detect_script(package, script)
                if command:
                    hints["web"].append(command)
            for script in ["test", "lint", "typecheck"]:
                command = self.detect_script(package, script)
                if command:
                    hints["test"].append(command)
        if "pyproject.toml" in names:
            hints["install"].append("pip install -e .")
        req_files = [path for path in rel_files if Path(path).name.lower().startswith("requirements") and path.lower().endswith(".txt")]
        for path in sorted(req_files)[:3]:
            hints["install"].append(f"pip install -r {path}")
        if "environment.yml" in names:
            hints["setup"].append("conda env create -f environment.yml")
            hints["setup"].append("conda activate <env_name>")
        if "environment.yaml" in names:
            hints["setup"].append("conda env create -f environment.yaml")
            hints["setup"].append("conda activate <env_name>")
        if "docker-compose.yml" in names:
            hints["web"].append("docker compose up")
        if "compose.yaml" in names or "compose.yml" in names:
            hints["web"].append("docker compose up")
        if "makefile" in names:
            hints["install"].append("make install")
            hints["test"].append("make test")
            hints["docs"].append("make docs")
        for candidate in ["manage.py", "app.py", "server.py", "main.py", "demo.py", "gradio_app.py", "streamlit_app.py"]:
            path = names.get(candidate)
            if not path:
                continue
            if candidate == "manage.py":
                hints["web"].append("python manage.py runserver")
            elif candidate.startswith("streamlit"):
                hints["web"].append(f"streamlit run {path}")
            else:
                hints["web"].append(f"python {path}")
        main_modules = [path for path in rel_files if path.endswith("/__main__.py") and len(Path(path).parts) == 2]
        for path in main_modules[:3]:
            package_name = Path(path).parts[0]
            if package_name == "homeassistant":
                hints["web"].append("python -m homeassistant --config config")
            else:
                hints["run"].append(f"python -m {package_name}")
        demo_paths = [
            path for path in rel_files
            if any(token in path.lower() for token in ["demo", "example", "examples", "web_demo"])
            and path.lower().endswith((".py", ".js", ".ts"))
        ]
        for path in demo_paths[:5]:
            if path.endswith(".py"):
                hints["run"].append(f"python {path}")
            elif path.endswith((".js", ".ts")):
                hints["run"].append(f"node {path}")
        test_dirs = any(path.startswith(("tests/", "test/")) or "/tests/" in path for path in rel_files)
        has_test_requirements = any(Path(path).name.lower().startswith("requirements_test") for path in rel_files)
        if test_dirs:
            hints["test"].append("python -m pytest")
        elif has_test_requirements:
            hints["test"].append("python -m pytest tests")
        if any(path.startswith("docs/") for path in rel_files):
            hints["docs"].append("make -C docs html")
        for key, values in hints.items():
            hints[key] = list(dict.fromkeys(value for value in values if value))[:8]
        return hints

    def detect_release_usage(self, readme: str, rel_files: list[str]) -> dict[str, Any]:
        text = readme or ""
        lower = text.lower()
        exe_names = re.findall(r"`([^`]*\.exe)`", text, flags=re.IGNORECASE)
        exe_names.extend(re.findall(r"([\w.-]+\.exe)", text, flags=re.IGNORECASE))
        exe = next((name for name in exe_names if name.lower().endswith(".exe") and not name.lower().endswith((".7z.exe", ".zip.exe"))), "")
        has_archive_release = any(token in lower for token in [".7z", ".zip", "release", "自解压", "压缩包", "解压"])
        no_install = any(token in text for token in ["无需安装", "免安装", "解压即用"])
        if not exe and any(Path(path).name.lower().endswith(".exe") for path in rel_files):
            exe = Path(next(path for path in rel_files if Path(path).name.lower().endswith(".exe"))).name
        if not (exe and (has_archive_release or no_install)):
            return {}
        install_steps = [
            "从 GitHub Releases 下载 .7z 或 .7z.exe 发布包",
            "解压发布包到本地目录",
        ]
        run_steps = [f".\\{exe}"]
        source_entry = next((path for path in rel_files if path.lower().endswith("/main.py")), "")
        if source_entry:
            run_steps.append(f"python {source_entry}")
        return {
            "install": "下载 Release 发布包并解压",
            "run": f".\\{exe}",
            "install_steps": install_steps,
            "run_steps": run_steps,
        }

    def summarize(self, meta: dict[str, Any], readme: str) -> str:
        readme_summary = self.readme_summary(readme, meta.get("name") or "")
        if readme_summary:
            return readme_summary
        if meta.get("description") and "unavailable" not in meta["description"].lower():
            return meta["description"]
        if (meta.get("name") or "").lower() == "flask":
            return "Flask is a lightweight Python web framework for building web applications and APIs."
        return f"{meta.get('name', 'This repository')} is a software project analyzed from its source tree, documentation, and static code graph."

    def detect_readme_language(self, readme: str) -> str:
        if not readme:
            return "en"
        sample = readme[:6000]
        cjk = len(re.findall(r"[\u4e00-\u9fff]", sample))
        latin_words = len(re.findall(r"[A-Za-z]{3,}", sample))
        if cjk >= 30 and cjk > latin_words * 0.25:
            return "zh"
        return "en"

    def readme_overview_source(self, readme: str) -> str:
        if not readme:
            return ""
        lines = []
        in_code = False
        for line in readme.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code or not stripped:
                continue
            if stripped.startswith(("<", "!", "[!", "|", "---")):
                continue
            lines.append(stripped.strip("# "))
            if len("\n".join(lines)) > 2600:
                break
        return "\n".join(lines)[:2600]

    def readme_summary(self, readme: str, repo_name: str = "") -> str:
        if not readme:
            return ""
        lines = []
        for line in readme.splitlines():
            clean = line.strip(" #\t").replace("[WSGI]", "WSGI")
            if not clean or clean.startswith(("[!", "<", "---", ":")):
                continue
            if repo_name and clean.lower() == repo_name.lower():
                continue
            if clean.lower() in {"project links", "license", "install", "installation"}:
                continue
            lines.append(clean)
            if len(" ".join(lines)) > 120:
                break
        summary = " ".join(lines).strip()
        if len(summary) > 220:
            summary = summary[:217].rsplit(" ", 1)[0] + "..."
        elif summary and summary[-1] not in ".!?。！？":
            summary += "..."
        return summary

    def extract_demo_media(self, readme: str, meta: dict[str, Any]) -> list[dict[str, str]]:
        if not readme:
            return []
        owner = meta.get("owner") or ""
        name = meta.get("name") or ""
        branch = meta.get("default_branch") or "main"
        media = []
        markdown_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", readme, flags=re.IGNORECASE)
        seen = set()
        for alt, url in markdown_images:
            media_item = self.media_item(url, alt or "Repository demo media", owner, name, branch)
            if media_item and media_item["url"] not in seen:
                seen.add(media_item["url"])
                media.append(media_item)
                if len(media) >= 6:
                    return media
        patterns = [
            r"<(?:video|img)[^>]+src=[\"']([^\"']+)[\"']",
            r"(https?://[^\s)]+(?:\.mp4|\.webm|\.mov|\.gif|\.png|\.jpg|\.jpeg))",
            r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s)]+)",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, readme, flags=re.IGNORECASE):
                media_item = self.media_item(match, "Repository demo media", owner, name, branch)
                if not media_item or media_item["url"] in seen:
                    continue
                seen.add(media_item["url"])
                media.append(media_item)
                if len(media) >= 6:
                    return media
        return media

    def extract_demo_runbook(self, readme: str, rel_files: list[str]) -> list[dict[str, Any]]:
        if not readme:
            return []
        lower = readme.lower()
        if not all(token in lower for token in ["quick start", "basic demo", "real-time interactive demo"]):
            return []
        demo_setup = self.extract_section_commands(readme, "Demo", stop_level=4)
        demo_setup = [self.normalize_demo_command(command) for command in demo_setup]
        quick_commands = [self.normalize_demo_command(command) for command in self.extract_section_commands(readme, "Quick Start", stop_level=3)]
        basic_commands = [self.normalize_demo_command(command) for command in self.extract_section_commands(readme, "Basic Demo", stop_level=4)]
        realtime_commands = [self.normalize_demo_command(command) for command in self.extract_section_commands(readme, "Real-Time Interactive Demo", stop_level=4)]
        cards = []
        if quick_commands:
            cards.append(
                {
                    "name": "Inference / Quick Start",
                    "purpose": "Run single-turn VITA inference for text, image, and audio examples from README.",
                    "commands": quick_commands[:4],
                    "files": self.keep_existing_files(["video_audio_demo.py", "vita/config/dataset_config.py"], rel_files),
                    "media_features": ["Project Showcase"],
                }
            )
        if basic_commands:
            cards.append(
                {
                    "name": "Demo / Basic Demo",
                    "purpose": "Launch the basic VITA web ability demo after preparing the vLLM-adapted demo checkpoint.",
                    "commands": (demo_setup + basic_commands)[:10],
                    "files": self.keep_existing_files(["web_demo/web_ability_demo.py", "web_demo/web_demo_requirements.txt", "web_demo/vllm_tools/qwen2p5_model_weight_file/processor_whale.py"], rel_files),
                    "media_features": ["Web / Interactive Demo", "Project Showcase"],
                }
            )
        if realtime_commands:
            cards.append(
                {
                    "name": "Demo / Real-Time Interactive Demo",
                    "purpose": "Start the real-time interactive VITA server with VAD resources and the demo checkpoint.",
                    "commands": (demo_setup + realtime_commands)[:10],
                    "files": self.keep_existing_files(["web_demo/server.py", "web_demo/vita_html/web/resources/demo.html", "web_demo/wakeup_and_vad/resource"], rel_files),
                    "media_features": ["Web / Interactive Demo", "Multimodal Capability"],
                }
            )
        return cards

    def extract_section_commands(self, readme: str, heading: str, stop_level: int) -> list[str]:
        section = self.markdown_section(readme, heading, stop_level)
        commands = []
        for block in re.findall(r"```(?:bash|shell|sh|powershell|console|text)?\s*([\s\S]*?)```", section, flags=re.IGNORECASE):
            command = self.normalize_code_block(block)
            if command:
                commands.append(command)
        return commands

    def markdown_section(self, readme: str, heading: str, stop_level: int) -> str:
        pattern = re.compile(rf"^(?P<hashes>#{{1,6}})\s*(?:[^\w\s]+)?\s*{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(readme)
        if not match:
            return ""
        start = match.end()
        in_code = False
        offset = start
        for line in readme[start:].splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
            if not in_code:
                header = re.match(r"^(#{1,6})\s+\S", line)
                if header and len(header.group(1)) <= stop_level:
                    return readme[start:offset]
            offset += len(line)
        return readme[start:]

    def normalize_code_block(self, block: str) -> str:
        lines = []
        for raw in block.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            line = re.sub(r"^(?:\$|>|PS>)\s*", "", line)
            lines.append(line)
        if not lines:
            return ""
        joined = "\n".join(lines)
        joined = re.sub(r"\\\s*\n\s*", " \\\n    ", joined)
        return joined.strip()

    def normalize_demo_command(self, command: str) -> str:
        command = command.replace("[vita/path]", "<VITA_CHECKPOINT_DIR>")
        command = command.replace("your_anaconda/envs/vita_demo", "$CONDA_PREFIX")
        command = command.replace("cp -rf vllm_file/*  $CONDA_PREFIX/lib/python3.10/site-packages/vllm/model_executor/models/", "cp -rf vllm_file/* $CONDA_PREFIX/lib/python3.10/site-packages/vllm/model_executor/models/")
        command = command.replace("cp -rL  VITA_ckpt/ demo_VITA_ckpt/", "cp -rL VITA_ckpt/ demo_VITA_ckpt/")
        return command

    def keep_existing_files(self, candidates: list[str], rel_files: list[str]) -> list[str]:
        file_set = set(rel_files)
        kept = []
        for candidate in candidates:
            if candidate in file_set:
                kept.append(candidate)
                continue
            prefix_matches = [path for path in rel_files if path.startswith(candidate.rstrip("/") + "/")]
            kept.extend(prefix_matches[:1])
        return kept[:6]

    def media_item(self, url: str, label: str, owner: str, name: str, branch: str) -> dict[str, str] | None:
        url = url.strip().strip("'\"")
        if not url or url.startswith("#"):
            return None
        media_url = self.resolve_media_url(url, owner, name, branch)
        lower = media_url.lower()
        kind = "video" if any(lower.endswith(ext) for ext in [".mp4", ".webm", ".mov"]) else "youtube" if "youtu" in lower else "image"
        text = f"{label} {url}".lower()
        if any(word in text for word in ["web", "demo", "gui", "interface"]):
            feature = "Web / Interactive Demo"
        elif any(word in text for word in ["speech", "audio", "asr", "voice"]):
            feature = "Speech / Audio Evaluation"
        elif any(word in text for word in ["benchmark", "score", "comparison", "performance", "chart"]):
            feature = "Benchmark / Evaluation"
        elif any(word in text for word in ["video", "vision", "image", "mllm"]):
            feature = "Multimodal Capability"
        else:
            feature = "Project Showcase"
        return {"type": kind, "url": media_url, "label": label or feature, "feature": feature}

    def extract_shell_commands(self, readme: str) -> dict[str, list[str]]:
        buckets = {"setup": [], "install": [], "run": [], "test": [], "web": [], "eval": [], "docs": []}
        if not readme:
            return buckets
        candidates: list[str] = []
        for block in re.findall(r"```(?:bash|shell|sh|powershell|python|console|text)?\s*([\s\S]*?)```", readme, flags=re.IGNORECASE):
            for line in block.splitlines():
                candidates.extend(self.clean_command_line(line))
        for line in readme.splitlines():
            candidates.extend(self.clean_command_line(line))
        seen = set()
        for command in candidates:
            if command in seen:
                continue
            seen.add(command)
            lower = command.lower()
            is_install = any(token in lower for token in ["pip install", "conda install", "npm install", "yarn install", "poetry install", "uv sync"])
            is_executable = command.startswith(("python ", "python3 ", "bash ", "sh ", "npm run ", "flask ", "streamlit ", "gradio ", "make "))
            if any(token in lower for token in ["conda create", "conda activate", "virtualenv", "python -m venv"]):
                buckets["setup"].append(command)
            if is_install:
                buckets["install"].append(command)
            if any(token in lower for token in ["pytest", "npm test", "unittest", "tox", "coverage"]):
                buckets["test"].append(command)
            if any(token in lower for token in ["sphinx", "mkdocs", "docs", "readthedocs"]):
                buckets["docs"].append(command)
            if is_executable and any(token in lower for token in ["web_demo", "gradio", "streamlit", "server.py", "app.py", "npm run dev", "npm start"]):
                buckets["web"].append(command)
            if is_executable and any(token in lower for token in ["eval", "evaluate", "benchmark", "vlmeval", "test.py", "inference", "infer", "parse_answer"]):
                buckets["eval"].append(command)
            if is_executable:
                buckets["run"].append(command)
        for key in buckets:
            buckets[key] = buckets[key][:8]
        return buckets

    def clean_command_line(self, line: str) -> list[str]:
        clean = line.strip()
        clean = re.sub(r"^(?:\$|>|PS>)\s*", "", clean)
        if not clean or clean.startswith(("#", "//", "<", "|", "!", "[")):
            return []
        if clean.endswith("\\"):
            clean = clean[:-1].strip()
        prefixes = (
            "git ",
            "cd ",
            "conda ",
            "pip ",
            "python ",
            "python3 ",
            "bash ",
            "sh ",
            "npm ",
            "yarn ",
            "pnpm ",
            "poetry ",
            "uv ",
            "pytest",
            "tox",
            "flask ",
            "streamlit ",
            "gradio ",
            "make ",
        )
        if clean.startswith(prefixes):
            return [clean]
        return []

    def resolve_media_url(self, url: str, owner: str, name: str, branch: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("./"):
            url = url[2:]
        if owner and name:
            return f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{url.lstrip('/')}"
        return url


class LearningAgent:
    def run(self, modules: list[dict[str, Any]], profile: dict[str, Any], user_profile: str) -> list[dict[str, Any]]:
        top = modules[:8]
        readme_step = {"title": "建立项目目标心智模型", "files": ["README.md"], "objective": "用一句话解释项目解决的问题", "checkpoint": "能说清项目输入、输出和典型用户"}
        module_steps = [
            {
                "title": f"理解核心模块 {module['name']}",
                "files": [module["path"]],
                "objective": module["summary"],
                "checkpoint": "能解释这个文件和项目主流程的关系",
            }
            for module in top[:5]
        ]
        return [
            {
                "user_profile": user_profile,
                "duration_type": "30min",
                "title": "30 分钟项目速览",
                "steps": [readme_step] + module_steps[:2],
            },
            {
                "user_profile": user_profile,
                "duration_type": "2hour",
                "title": "2 小时首贡准备路径",
                "steps": [readme_step] + module_steps[:5] + [
                    {"title": "理解测试入口", "files": [], "objective": f"确认最小验证命令：{profile.get('test_command')}", "checkpoint": "能运行或解释项目测试方式"}
                ],
            },
            {
                "user_profile": user_profile,
                "duration_type": "1day",
                "title": "1 天深入理解路径",
                "steps": [readme_step] + module_steps + [
                    {"title": "阅读贡献规范", "files": ["CONTRIBUTING.md", ".github/workflows"], "objective": "理解提交、测试、CI 与 Review 预期", "checkpoint": "能写出一份符合项目风格的 PR Checklist"}
                ],
            },
        ]


class IssueMinerAgent:
    FRIENDLY_LABELS = {"good first issue", "good-first-issue", "beginner", "easy", "docs", "documentation", "help wanted", "bug"}

    def run(self, issues: list[dict[str, Any]], modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        module_paths = [module["path"] for module in modules[:20]]
        scored = []
        for issue in issues:
            labels = [label.lower() for label in issue.get("labels", [])]
            body = issue.get("body") or ""
            title = issue.get("title") or ""
            text = f"{title}\n{body}".lower()
            label_score = 95 if any(label in self.FRIENDLY_LABELS for label in labels) else 55
            clarity_score = min(95, 35 + len(body) // 12 + (20 if "expected" in text or "steps" in text else 0))
            scope_score = 90 if any(word in text for word in ["typo", "doc", "readme", "test"]) else 65
            testability_score = 85 if any(word in text for word in ["test", "docs", "readme", "bug", "reproduce"]) else 60
            activity_score = self.activity_score(issue.get("updated_at"))
            beginner = round(label_score * 0.25 + clarity_score * 0.25 + scope_score * 0.2 + testability_score * 0.15 + activity_score * 0.15)
            related = [path for path in module_paths if Path(path).name.lower().split(".")[0] in text][:3]
            issue.update(
                {
                    "clarity_score": clarity_score,
                    "scope_score": scope_score,
                    "testability_score": testability_score,
                    "activity_score": activity_score,
                    "beginner_score": beginner,
                    "recommended_reason": self.reason(labels, related, scope_score, testability_score),
                    "risk_summary": "Scope may be larger than it looks; verify behavior with tests." if scope_score < 75 else "Low blast radius; suitable for a first contribution sandbox.",
                }
            )
            scored.append(issue)
        return sorted(scored, key=lambda item: item["beginner_score"], reverse=True)[:20]

    def activity_score(self, updated_at: str | None) -> int:
        if not updated_at:
            return 55
        try:
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - updated).days
            return max(40, min(95, 95 - days))
        except Exception:
            return 55

    def reason(self, labels: list[str], related: list[str], scope: int, testability: int) -> str:
        parts = []
        if any(label in self.FRIENDLY_LABELS for label in labels):
            parts.append("has newcomer-friendly labels")
        if related:
            parts.append(f"mentions likely related modules: {', '.join(related)}")
        if scope >= 80:
            parts.append("appears to have a focused change scope")
        if testability >= 80:
            parts.append("has a clear verification path")
        return "; ".join(parts) or "ranked by clarity, limited scope, activity, and testability"


class ContributionPlannerAgent:
    def run(self, issue: dict[str, Any], modules: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
        text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
        chosen = []
        for module in modules[:20]:
            stem = Path(module["path"]).name.lower().split(".")[0]
            if stem and stem in text:
                chosen.append(module)
        if not chosen:
            if "doc" in text or "readme" in text:
                chosen = [{"path": "README.md", "summary": "Project-facing documentation"}]
            else:
                chosen = modules[:3]
        files_to_read = [{"path": module["path"], "reason": module.get("summary", "Relevant project context")} for module in chosen[:4]]
        files_to_modify = [{"path": module["path"], "reason": "Likely small, reviewable change target"} for module in chosen[:2]]
        return {
            "goal": issue.get("title"),
            "background": f"This mission translates issue #{issue.get('github_issue_number')} into a first-contribution plan with bounded reading, modification, and verification steps.",
            "files_to_read": files_to_read,
            "files_to_modify": files_to_modify,
            "implementation_plan": [
                "Reproduce or restate the issue in your own words.",
                "Read the selected files and identify the smallest behavior or documentation change.",
                "Make one focused change; avoid broad refactors.",
                "Add or update a test/documentation example if the project has a nearby pattern.",
                "Run the smallest verification command before opening the PR.",
            ],
            "test_plan": [profile.get("test_command") or "Run the repository's documented test command"],
            "pr_checklist": [
                f"Reference the issue with closes #{issue.get('github_issue_number')}.",
                "Explain the before/after behavior.",
                "List the verification command and result.",
                "Keep the PR focused on one contribution goal.",
            ],
            "risk_points": [
                issue.get("risk_summary") or "Confirm maintainers agree with the intended scope.",
                "Do not change public behavior unless the issue explicitly asks for it.",
            ],
        }
