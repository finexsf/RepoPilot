from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
from tree_sitter_language_pack import get_language, get_parser

from app.services.github_service import SOURCE_SUFFIXES, read_text, relpath


@dataclass
class Symbol:
    name: str
    kind: str
    line: int


@dataclass
class ParsedFile:
    path: str
    language: str
    imports: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)


class TreeSitterCodeGraph:
    def __init__(self, root: Path, files: list[Path]) -> None:
        self.root = root
        self.files = self.prioritize_source_files([path for path in files if path.suffix.lower() in SOURCE_SUFFIXES])
        self.graph = nx.DiGraph()

    def build(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        parsed = [self.parse_file(path) for path in self.files[:260]]
        file_by_name = {item.path: item for item in parsed}

        for item in parsed:
            self.graph.add_node(
                item.path,
                type="source",
                symbols=[symbol.__dict__ for symbol in item.symbols],
                language=item.language,
            )

        for item in parsed:
            for imported in item.imports:
                target = self.resolve_import(item.path, imported, file_by_name)
                if target:
                    self.graph.add_edge(item.path, target, relation_type="imports", weight=2)
            for symbol in item.symbols[:8]:
                symbol_id = f"{item.path}::{symbol.name}"
                self.graph.add_node(symbol_id, type="symbol", symbols=[], language=item.language)
                self.graph.add_edge(item.path, symbol_id, relation_type="defines", weight=1)

        centrality = {}
        if self.graph.nodes:
            node_count = max(1, len(self.graph.nodes) - 1)
            for node in self.graph.nodes:
                centrality[node] = (self.graph.in_degree(node) + self.graph.out_degree(node)) / node_count
        modules = []
        for index, item in enumerate(parsed[:240], start=1):
            score = int(min(100, 25 + centrality.get(item.path, 0) * 180 + min(len(item.symbols) * 4, 25) + min(len(item.imports) * 2, 20) + self.entry_bonus(item.path)))
            modules.append(
                {
                    "path": item.path,
                    "name": Path(item.path).name,
                    "type": "source",
                    "importance_score": score,
                    "summary": self.summarize_file(item),
                    "read_priority": index,
                    "symbols": [symbol.__dict__ for symbol in item.symbols[:12]],
                    "imports": item.imports[:20],
                    "calls": item.calls[:24],
                }
            )

        edges = [
            {
                "source": source,
                "target": target,
                "relation_type": data.get("relation_type", "related"),
                "weight": data.get("weight", 1),
            }
            for source, target, data in self.graph.edges(data=True)
            if "::" not in source and "::" not in target
        ][:300]
        return modules, edges

    def prioritize_source_files(self, files: list[Path]) -> list[Path]:
        def priority(path: Path) -> tuple[int, int, str]:
            rel = relpath(self.root, path).lower()
            name = path.name.lower()
            if name in {"main.py", "app.py", "server.py", "cli.py", "demo.py", "train.py", "infer.py", "main.cpp", "main.c"}:
                return (0, len(rel), rel)
            if rel.startswith(("src/modules/", "modules/", "homeassistant/components/")):
                return (1, len(rel), rel)
            if rel.startswith(("src/drivers/", "drivers/", "platforms/", "platform/", "src/lib/")):
                return (2, len(rel), rel)
            if rel.startswith(("src/", "app/", "server/", "backend/", "web_demo/", "web/", "examples/")):
                return (3, len(rel), rel)
            if rel.startswith(("test/", "tests/")) or "/test" in rel:
                return (4, len(rel), rel)
            if rel.startswith(("tools/", "scripts/")):
                return (5, len(rel), rel)
            return (6, len(rel), rel)

        return sorted(files, key=priority)

    def entry_bonus(self, path: str) -> int:
        name = Path(path).name.lower()
        if name in {"app.py", "main.py", "server.py", "cli.py", "demo.py", "train.py", "infer.py", "index.ts", "index.js"}:
            return 28
        if any(part in path.lower() for part in ["/app.", "/cli.", "/routing.", "/blueprints.", "/ctx."]):
            return 14
        return 0

    def parse_file(self, path: Path) -> ParsedFile:
        rel = relpath(self.root, path)
        suffix = path.suffix
        language = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".c": "c",
            ".h": "cpp",
            ".hh": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
            ".cc": "cpp",
            ".cpp": "cpp",
            ".cxx": "cpp",
        }.get(suffix.lower(), "unknown")
        text = read_text(path, 120_000)
        result = ParsedFile(path=rel, language=language)
        if not text.strip():
            return result

        try:
            parser = get_parser(language)
            tree = parser.parse(text.encode("utf-8", errors="replace"))
            root = tree.root_node
            if language == "python":
                self.extract_python(root, text, result)
            elif language in {"c", "cpp"}:
                self.extract_c_like(root, text, result)
            else:
                self.extract_js_like(root, text, result)
        except Exception:
            self.fallback_parse(text, result)
        return result

    def extract_python(self, root: Any, text: str, result: ParsedFile) -> None:
        source = text.encode("utf-8", errors="replace")

        def walk(node: Any) -> None:
            node_type = node.type
            if node_type in {"function_definition", "class_definition"}:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    result.symbols.append(Symbol(name=name, kind="class" if node_type == "class_definition" else "function", line=node.start_point[0] + 1))
            elif node_type in {"import_statement", "import_from_statement"}:
                snippet = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                result.imports.extend(self.extract_import_words(snippet))
            elif node_type == "call":
                snippet = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                match = re.match(r"([A-Za-z_][A-Za-z0-9_\.]*)\s*\(", snippet)
                if match:
                    result.calls.append(match.group(1))
            for child in node.children:
                walk(child)

        walk(root)

    def extract_c_like(self, root: Any, text: str, result: ParsedFile) -> None:
        source = text.encode("utf-8", errors="replace")

        def node_text(node: Any) -> str:
            return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        def walk(node: Any) -> None:
            node_type = node.type
            if node_type in {"function_definition", "declaration"}:
                snippet = node_text(node)[:500]
                match = re.search(r"(?:^|[\s:*&>])([A-Za-z_][A-Za-z0-9_:~]*)\s*\([^;{}]*\)", snippet)
                if match and len(result.symbols) < 80:
                    name = match.group(1).split("::")[-1]
                    if name not in {"if", "for", "while", "switch", "return"}:
                        result.symbols.append(Symbol(name=name, kind="function", line=node.start_point[0] + 1))
            elif node_type in {"class_specifier", "struct_specifier"}:
                name_node = node.child_by_field_name("name")
                if name_node and len(result.symbols) < 80:
                    result.symbols.append(Symbol(name=node_text(name_node), kind="class", line=node.start_point[0] + 1))
            elif node_type == "preproc_include":
                snippet = node_text(node)
                match = re.search(r"[<\"]([^>\"]+)[>\"]", snippet)
                if match:
                    result.imports.append(match.group(1))
            elif node_type == "call_expression":
                snippet = node_text(node)[:160]
                match = re.match(r"([A-Za-z_][A-Za-z0-9_:~\.]*)\s*\(", snippet)
                if match:
                    result.calls.append(match.group(1))
            for child in node.children:
                walk(child)

        walk(root)

    def extract_js_like(self, root: Any, text: str, result: ParsedFile) -> None:
        source = text.encode("utf-8", errors="replace")

        def walk(node: Any) -> None:
            node_type = node.type
            if node_type in {"function_declaration", "class_declaration", "method_definition"}:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    kind = "class" if node_type == "class_declaration" else "function"
                    result.symbols.append(Symbol(name=name, kind=kind, line=node.start_point[0] + 1))
            elif node_type in {"import_statement", "export_statement"}:
                snippet = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                for match in re.findall(r"from\s+['\"]([^'\"]+)['\"]|import\s*\(\s*['\"]([^'\"]+)['\"]", snippet):
                    result.imports.append(match[0] or match[1])
            elif node_type == "call_expression":
                snippet = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                match = re.match(r"([A-Za-z_$][A-Za-z0-9_$\.]*)\s*\(", snippet)
                if match:
                    result.calls.append(match.group(1))
            for child in node.children:
                walk(child)

        walk(root)

    def fallback_parse(self, text: str, result: ParsedFile) -> None:
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result.symbols.append(Symbol(node.name, "function", node.lineno))
                elif isinstance(node, ast.ClassDef):
                    result.symbols.append(Symbol(node.name, "class", node.lineno))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    result.imports.extend(alias.name for alias in getattr(node, "names", []))
        except Exception:
            pass

    def extract_import_words(self, snippet: str) -> list[str]:
        if snippet.startswith("from "):
            match = re.match(r"from\s+([A-Za-z0-9_\.]+)\s+import", snippet)
            return [match.group(1)] if match else []
        if snippet.startswith("import "):
            return [part.strip().split(" as ")[0] for part in snippet.replace("import ", "").split(",")]
        return []

    def resolve_import(self, source_path: str, imported: str, file_by_name: dict[str, ParsedFile]) -> str | None:
        imported = imported.strip()
        if imported in file_by_name:
            return imported
        source_dir = Path(source_path).parent
        relative_candidate = (source_dir / imported).as_posix()
        if relative_candidate in file_by_name:
            return relative_candidate
        suffixes = [".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx"]
        if Path(imported).suffix.lower() in suffixes:
            basename_matches = [path for path in file_by_name if path.endswith("/" + imported) or path.endswith(imported)]
            if basename_matches:
                return sorted(basename_matches, key=len)[0]
        if imported.startswith("."):
            base = Path(source_path).parent
            candidate = (base / imported.replace(".", "/")).as_posix()
        else:
            candidate = imported.replace(".", "/")
        for suffix in [".py", ".ts", ".tsx", ".js", ".jsx", ".h", ".hpp", ".c", ".cpp", "/index.ts", "/index.tsx", "/index.js"]:
            full = candidate + suffix
            if full in file_by_name:
                return full
        matches = [
            path for path in file_by_name
            if path.endswith(candidate + ".py")
            or path.endswith(candidate + ".ts")
            or path.endswith(candidate + ".js")
            or path.endswith(candidate + ".h")
            or path.endswith(candidate + ".hpp")
            or path.endswith(candidate + ".cpp")
        ]
        return matches[0] if matches else None

    def summarize_file(self, item: ParsedFile) -> str:
        symbol_names = ", ".join(symbol.name for symbol in item.symbols[:4]) or "no top-level symbols detected"
        imports = ", ".join(item.imports[:3]) or "few explicit imports"
        return f"Tree-sitter parsed {item.language} file. Key symbols: {symbol_names}. Imports: {imports}."


def classify_file(path: str) -> str:
    lower = path.lower()
    name = Path(path).name.lower()
    if "test" in lower or "__tests__" in lower or name.startswith("test_"):
        return "test"
    if lower.startswith("docs/") or name in {"readme.md", "contributing.md"}:
        return "docs"
    if lower.startswith(".github/workflows") or name.endswith(".yml") or name.endswith(".yaml"):
        return "ci" if ".github/workflows" in lower else "config"
    if name in {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "cargo.toml"}:
        return "config"
    if Path(path).suffix in SOURCE_SUFFIXES:
        return "source"
    return "unknown"
