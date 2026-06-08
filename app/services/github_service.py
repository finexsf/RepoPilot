from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests


SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
}


@dataclass
class GitHubRepo:
    owner: str
    name: str
    url: str


class GitHubService:
    def __init__(self) -> None:
        self.session = requests.Session()
        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.headers.update({"Accept": "application/vnd.github+json"})

    def parse_url(self, url: str) -> GitHubRepo:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if parsed.netloc not in {"github.com", "www.github.com"} or len(parts) < 2:
            raise ValueError("Only GitHub repository URLs are supported")
        return GitHubRepo(owner=parts[0], name=parts[1].replace(".git", ""), url=f"https://github.com/{parts[0]}/{parts[1].replace('.git', '')}")

    def get_repo_meta(self, repo: GitHubRepo) -> dict:
        try:
            resp = self.session.get(f"https://api.github.com/repos/{repo.owner}/{repo.name}", timeout=20)
        except requests.RequestException:
            return {
                "owner": repo.owner,
                "name": repo.name,
                "description": "GitHub API metadata unavailable; RepoPilot will analyze the repository snapshot directly.",
                "default_branch": "main",
                "primary_language": "",
                "stars": 0,
                "forks": 0,
            }
        if not resp.ok:
            return {
                "owner": repo.owner,
                "name": repo.name,
                "description": "GitHub API metadata unavailable; RepoPilot will analyze the repository snapshot directly.",
                "default_branch": "main",
                "primary_language": "",
                "stars": 0,
                "forks": 0,
            }
        data = resp.json()
        return {
            "owner": repo.owner,
            "name": repo.name,
            "description": data.get("description") or "",
            "default_branch": data.get("default_branch") or "main",
            "primary_language": data.get("language") or "",
            "stars": data.get("stargazers_count") or 0,
            "forks": data.get("forks_count") or 0,
        }

    def get_languages(self, repo: GitHubRepo) -> list[str]:
        try:
            resp = self.session.get(f"https://api.github.com/repos/{repo.owner}/{repo.name}/languages", timeout=20)
        except requests.RequestException:
            return []
        if not resp.ok:
            return []
        return list(resp.json().keys())

    def get_issues(self, repo: GitHubRepo, limit: int = 30) -> list[dict]:
        resp = self.session.get(
            f"https://api.github.com/repos/{repo.owner}/{repo.name}/issues",
            params={"state": "open", "per_page": limit, "sort": "updated", "direction": "desc"},
            timeout=20,
        )
        if not resp.ok:
            return []
        issues = []
        for item in resp.json():
            if "pull_request" in item:
                continue
            issues.append(
                {
                    "number": item.get("number"),
                    "title": item.get("title") or "",
                    "body": item.get("body") or "",
                    "url": item.get("html_url") or "",
                    "labels": [label.get("name", "") for label in item.get("labels", [])],
                    "state": item.get("state"),
                    "comments_count": item.get("comments") or 0,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
            )
        return issues

    def local_repo_path(self, repo: GitHubRepo) -> Path:
        return Path("storage/repos") / f"{repo.owner}__{repo.name}"

    def has_local_repo(self, repo: GitHubRepo) -> bool:
        target = self.local_repo_path(repo)
        if not target.exists() or not target.is_dir():
            return False
        return any(target.iterdir())

    def download_repo(self, repo: GitHubRepo, default_branch: str) -> Path:
        storage = Path("storage/repos")
        storage.mkdir(parents=True, exist_ok=True)
        target = self.local_repo_path(repo)
        if self.has_local_repo(repo):
            return target
        extract_root = storage / f"__download_{repo.owner}_{repo.name}_{uuid.uuid4().hex[:8]}"
        extract_root.mkdir(parents=True, exist_ok=True)
        branches = list(dict.fromkeys([default_branch, "main", "master"]))
        resp = None
        used_branch = None
        for branch in branches:
            zip_url = f"https://codeload.github.com/{repo.owner}/{repo.name}/zip/refs/heads/{branch}"
            candidate = self.session.get(zip_url, timeout=60)
            if candidate.ok:
                resp = candidate
                used_branch = branch
                break
        if resp is None:
            raise RuntimeError(f"Unable to download repository snapshot for {repo.owner}/{repo.name}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(resp.content)
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(tmp_path) as zf:
                zf.extractall(extract_root)
            extracted = next(extract_root.glob(f"{repo.name}-{used_branch}*"), None)
            if not extracted:
                extracted = next((path for path in extract_root.iterdir() if path.is_dir()), None)
            if not extracted:
                raise RuntimeError("Downloaded repository zip did not contain an extractable directory")
            replacement = storage / f"__ready_{repo.owner}_{repo.name}_{uuid.uuid4().hex[:8]}"
            shutil.move(str(extracted), str(replacement))
            if target.exists():
                shutil.rmtree(target)
            replacement.replace(target)
            return target
        finally:
            tmp_path.unlink(missing_ok=True)
            if extract_root.exists():
                shutil.rmtree(extract_root, ignore_errors=True)


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def should_skip_dir(path: Path) -> bool:
    return bool(re.search(r"(^|[\\/])(\.git|node_modules|dist|build|target|vendor|\.next|coverage|__pycache__)([\\/]|$)", str(path)))


def collect_files(root: Path, max_files: int = 1200) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if should_skip_dir(path):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda path: file_priority(root, path))[:max_files]


def file_priority(root: Path, path: Path) -> tuple[int, int, str]:
    rel = relpath(root, path).lower()
    name = path.name.lower()
    if name in {"readme.md", "contributing.md", "pyproject.toml", "package.json", "cmakelists.txt"}:
        return (0, len(rel), rel)
    if name in {"main.py", "app.py", "server.py", "cli.py", "demo.py", "train.py", "infer.py", "main.cpp", "main.c"}:
        return (1, len(rel), rel)
    if rel.startswith(("src/modules/", "modules/", "homeassistant/components/")):
        return (2, len(rel), rel)
    if rel.startswith(("src/drivers/", "drivers/", "platforms/", "platform/", "boards/", "src/lib/")):
        return (3, len(rel), rel)
    if rel.startswith(("src/", "app/", "server/", "backend/", "web_demo/", "web/", "examples/")):
        return (4, len(rel), rel)
    if rel.startswith(("test/", "tests/", "integrationtests/")) or "/test" in rel:
        return (5, len(rel), rel)
    if rel.startswith(("docs/", ".github/", "cmake/", "tools/", "scripts/")):
        return (6, len(rel), rel)
    if path.suffix.lower() in SOURCE_SUFFIXES:
        return (7, len(rel), rel)
    return (8, len(rel), rel)


def relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
