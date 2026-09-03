"""Repository Scanner & Intelligence Engine (Phase 5)."""

import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from app.context.base import DependencyManifest, FileMetric, RepositorySummary


DEFAULT_IGNORE_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".idea",
    ".vscode",
    ".next",
    ".cache",
    ".coverage",
    "htmlcov",
    "eggs",
    "*.egg-info",
}

DEFAULT_IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
    ".sqlite",
    ".db",
    ".lock",
}

EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".md": "Markdown",
    ".rst": "ReStructuredText",
    ".txt": "Text",
}


class RepositoryScanner:
    """Discovers repository structure, frameworks, manifests, entry points, and metrics."""

    def __init__(self, root_path: str, custom_ignore_dirs: Optional[Set[str]] = None) -> None:
        self.root_path = os.path.abspath(root_path)
        self.ignore_dirs = set(DEFAULT_IGNORE_DIRS)
        if custom_ignore_dirs:
            self.ignore_dirs.update(custom_ignore_dirs)

    def scan(self) -> RepositorySummary:
        """Executes full repository discovery and produces a RepositorySummary."""
        file_metrics: List[FileMetric] = []
        languages_count: Dict[str, int] = {}
        total_loc = 0
        key_directories: Set[str] = set()
        entry_points: List[str] = []
        test_frameworks: Set[str] = set()
        frameworks: Set[str] = set()
        manifests: List[DependencyManifest] = []

        if not os.path.exists(self.root_path):
            return RepositorySummary(
                root_path=self.root_path,
                languages=[],
                total_files=0,
                entry_points=[],
                test_frameworks=[],
                key_directories=[],
            )

        # Walk repository files
        for root, dirs, files in os.walk(self.root_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")]

            rel_root = os.path.relpath(root, self.root_path)
            if rel_root != ".":
                top_dir = rel_root.split(os.sep)[0]
                key_directories.add(top_dir)

            for file_name in files:
                ext = os.path.splitext(file_name)[1].lower()
                if ext in DEFAULT_IGNORE_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, self.root_path)

                # Skip root dotfiles except specific configs
                if file_name.startswith(".") and not file_name.startswith(".env"):
                    continue

                # Measure lines of code & detect traits
                loc, is_entry, is_test_file = self._analyze_file(full_path, rel_path)
                total_loc += loc

                language = EXTENSION_LANGUAGE_MAP.get(ext, "Other")
                if file_name in ("Dockerfile", "Containerfile"):
                    language = "Docker"
                elif file_name in ("Makefile", "GNUmakefile"):
                    language = "Makefile"

                languages_count[language] = languages_count.get(language, 0) + 1

                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0

                metric = FileMetric(
                    path=full_path,
                    relative_path=rel_path,
                    language=language,
                    size_bytes=size,
                    lines_of_code=loc,
                    is_test=is_test_file,
                    is_entry_point=is_entry,
                )
                file_metrics.append(metric)

                if is_entry:
                    entry_points.append(rel_path)

                if is_test_file:
                    if ext in (".py", ".pyi"):
                        test_frameworks.add("unittest/pytest")
                    elif ext in (".ts", ".tsx", ".js", ".jsx"):
                        test_frameworks.add("vitest/jest")

        # Scan and parse dependency manifests
        manifests = self._scan_manifests()
        for manifest in manifests:
            detected = self._infer_frameworks_from_manifest(manifest)
            frameworks.update(detected)

        # Detect additional frameworks from files and structure
        frameworks.update(self._detect_frameworks_from_files(file_metrics))

        sorted_languages = sorted(
            [lang for lang in languages_count.keys() if lang != "Other"],
            key=lambda l: languages_count.get(l, 0),
            reverse=True,
        )

        return RepositorySummary(
            root_path=self.root_path,
            languages=sorted_languages,
            total_files=len(file_metrics),
            total_lines_of_code=total_loc,
            entry_points=sorted(entry_points),
            test_frameworks=sorted(list(test_frameworks)),
            key_directories=sorted(list(key_directories)),
            language_breakdown=languages_count,
            frameworks=sorted(list(frameworks)),
            manifests=manifests,
            files=file_metrics,
        )

    def _analyze_file(self, full_path: str, rel_path: str) -> Tuple[int, bool, bool]:
        """Analyzes lines of code, entry point status, and test classification."""
        loc = 0
        is_entry = False
        is_test = False

        norm_rel = rel_path.replace("\\", "/")
        file_name = os.path.basename(norm_rel)

        # Test detection heuristics
        if (
            file_name.startswith("test_")
            or file_name.endswith("_test.py")
            or file_name.endswith(".test.ts")
            or file_name.endswith(".test.tsx")
            or file_name.endswith(".test.js")
            or file_name.endswith(".spec.ts")
            or file_name.endswith(".spec.js")
            or "/tests/" in f"/{norm_rel}"
            or "/__tests__/" in f"/{norm_rel}"
            or "/test/" in f"/{norm_rel}"
        ):
            is_test = True

        # Common known entry points
        known_entry_patterns = {
            "main.py",
            "app/main.py",
            "server.ts",
            "server.js",
            "app.py",
            "wsgi.py",
            "asgi.py",
            "manage.py",
            "cli.py",
            "src/main.tsx",
            "src/App.tsx",
            "src/index.ts",
            "src/index.js",
            "index.html",
        }
        if norm_rel in known_entry_patterns or file_name in ("main.py", "server.ts", "app.py", "cli.py"):
            is_entry = True

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                loc = len(lines)

                # Inspect content for entry points if not yet marked
                if not is_entry and len(lines) < 2000:
                    content = "".join(lines[:100])
                    if 'if __name__ == "__main__":' in content or 'app.listen(' in content:
                        is_entry = True
        except Exception:
            loc = 0

        return loc, is_entry, is_test

    def _scan_manifests(self) -> List[DependencyManifest]:
        """Finds and parses package manifests across the repository."""
        manifests: List[DependencyManifest] = []

        # 1. requirements.txt / requirements-dev.txt
        for req_name in ("requirements.txt", "requirements-dev.txt", "dev-requirements.txt"):
            req_path = os.path.join(self.root_path, req_name)
            if os.path.exists(req_path):
                pkgs = self._parse_requirements_txt(req_path)
                manifests.append(
                    DependencyManifest(
                        manifest_file=req_name,
                        manifest_type="requirements.txt",
                        packages=pkgs,
                    )
                )

        # 2. package.json
        pkg_json_path = os.path.join(self.root_path, "package.json")
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    manifests.append(
                        DependencyManifest(
                            manifest_file="package.json",
                            manifest_type="package.json",
                            packages=deps if isinstance(deps, dict) else {},
                            dev_packages=dev_deps if isinstance(dev_deps, dict) else {},
                        )
                    )
            except Exception:
                pass

        # 3. pyproject.toml
        pyproject_path = os.path.join(self.root_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            pkgs = self._parse_pyproject_toml(pyproject_path)
            manifests.append(
                DependencyManifest(
                    manifest_file="pyproject.toml",
                    manifest_type="pyproject.toml",
                    packages=pkgs,
                )
            )

        return manifests

    def _parse_requirements_txt(self, file_path: str) -> Dict[str, str]:
        """Parses a requirements.txt file into a map of package -> version constraint."""
        packages: Dict[str, str] = {}
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Match name and version
                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([=><~!~].*)?$", line)
                    if match:
                        name = match.group(1)
                        version = match.group(2).strip() if match.group(2) else "*"
                        packages[name] = version
        except Exception:
            pass
        return packages

    def _parse_pyproject_toml(self, file_path: str) -> Dict[str, str]:
        """Basic extraction of dependencies from pyproject.toml without heavy external parser."""
        packages: Dict[str, str] = {}
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                in_deps_section = False
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("[") and ("dependencies" in stripped or "tool.poetry.dependencies" in stripped):
                        in_deps_section = True
                        continue
                    elif stripped.startswith("["):
                        in_deps_section = False

                    if in_deps_section and "=" in stripped and not stripped.startswith("#"):
                        parts = stripped.split("=", 1)
                        name = parts[0].strip().strip('"').strip("'")
                        ver = parts[1].strip().strip('"').strip("'")
                        if name and name.lower() != "python":
                            packages[name] = ver
        except Exception:
            pass
        return packages

    def _infer_frameworks_from_manifest(self, manifest: DependencyManifest) -> Set[str]:
        """Infers major technology frameworks from dependency names."""
        frameworks: Set[str] = set()
        all_pkgs = {**manifest.packages, **manifest.dev_packages}
        pkg_lower = {k.lower(): v for k, v in all_pkgs.items()}

        mapping = {
            "fastapi": "FastAPI",
            "flask": "Flask",
            "django": "Django",
            "pytest": "Pytest",
            "pydantic": "Pydantic",
            "sqlalchemy": "SQLAlchemy",
            "celery": "Celery",
            "torch": "PyTorch",
            "tensorflow": "TensorFlow",
            "transformers": "Hugging Face Transformers",
            "google-genai": "Google GenAI SDK",
            "@google/genai": "Google GenAI SDK",
            "react": "React",
            "next": "Next.js",
            "express": "Express",
            "vite": "Vite",
            "tailwindcss": "Tailwind CSS",
            "lucide-react": "Lucide Icons",
            "drizzle-orm": "Drizzle ORM",
            "sqlite3": "SQLite",
            "pg": "PostgreSQL",
            "jest": "Jest",
            "vitest": "Vitest",
        }

        for pkg_key, framework_name in mapping.items():
            if pkg_key in pkg_lower:
                frameworks.add(framework_name)

        return frameworks

    def _detect_frameworks_from_files(self, files: List[FileMetric]) -> Set[str]:
        """Detects frameworks based on specific configuration files or code signals."""
        frameworks: Set[str] = set()
        for f in files:
            rel = f.relative_path.replace("\\", "/")
            if "sqlite" in rel.lower() or "sqlite_store.py" in rel:
                frameworks.add("SQLite Persistence")
            if rel.endswith("vite.config.ts") or rel.endswith("vite.config.js"):
                frameworks.add("Vite")
            if rel.endswith("tailwind.config.js") or "tailwindcss" in rel:
                frameworks.add("Tailwind CSS")
            if "unittest" in rel or "test_" in rel:
                frameworks.add("Python unittest")

        return frameworks
