"""
ATHU Module - Filesystem Agent
Provides file search, content search, open, and document summarisation tools.
Read-only by default. Write access requires explicit config flag.
"""

import glob
import os
import subprocess
from pathlib import Path
from typing import Callable

from modules.base_module import BaseModule


class FilesystemAgent(BaseModule):
    MODULE_NAME = "filesystem"

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "find_files",
                {
                    "name": "find_files",
                    "description": "Find files by name using glob patterns or fuzzy matching.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Filename pattern or search term"},
                            "path": {"type": "string", "description": "Root directory to search (default: user home)"},
                            "extensions": {"type": "array", "items": {"type": "string"}, "description": "File extensions to filter (e.g. ['.py', '.txt'])"},
                        },
                        "required": ["query"],
                    },
                },
                self.find_files,
            ),
            (
                "search_file_content",
                {
                    "name": "search_file_content",
                    "description": "Search for text content inside files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text to search for"},
                            "path": {"type": "string", "description": "Directory to search in"},
                            "extensions": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["query"],
                    },
                },
                self.search_file_content,
            ),
            (
                "open_file",
                {
                    "name": "open_file",
                    "description": "Open a file with the default system application.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Full path to the file"},
                        },
                        "required": ["path"],
                    },
                },
                self.open_file,
            ),
            (
                "summarize_document",
                {
                    "name": "summarize_document",
                    "description": "Read and summarise the contents of a document.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Full path to the document"},
                        },
                        "required": ["path"],
                    },
                },
                self.summarize_document,
            ),
        ]

    def find_files(self, query: str, path: str = None, extensions: list[str] = None) -> str:
        root = Path(path or Path.home())
        if not root.exists():
            return f"Directory not found: {root}"

        results = []
        pattern = f"**/*{query}*"
        try:
            for match in root.glob(pattern):
                if extensions and match.suffix.lower() not in [e.lower() for e in extensions]:
                    continue
                results.append(str(match))
                if len(results) >= 20:
                    break
        except PermissionError:
            pass

        if not results:
            return f"No files matching '{query}' found in {root}"
        return "Found files:\n" + "\n".join(results[:20])

    def search_file_content(self, query: str, path: str = None, extensions: list[str] = None) -> str:
        root = str(path or Path.home())
        ext_args = []
        if extensions:
            for ext in extensions:
                ext_args += ["-e", f"*.{ext.lstrip('.')}"]

        try:
            # Try ripgrep first (fast)
            cmd = ["rg", "--no-heading", "-n", "-l", query, root] + (["--glob", ",".join(extensions)] if extensions else [])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                files = result.stdout.strip().split("\n")[:10]
                return "Files containing '{}' :\n{}".format(query, "\n".join(files))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Python fallback
        matches = []
        for root_dir, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                if extensions and not any(fname.endswith(e) for e in extensions):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        if query.lower() in f.read().lower():
                            matches.append(fpath)
                            if len(matches) >= 10:
                                break
                except Exception:
                    pass
            if len(matches) >= 10:
                break

        if not matches:
            return f"No files containing '{query}' found."
        return "Files containing '{}':\n{}".format(query, "\n".join(matches))

    def open_file(self, path: str) -> str:
        fpath = Path(path)
        if not fpath.exists():
            return f"File not found: {path}"
        try:
            os.startfile(str(fpath))  # Windows
            return f"Opened: {path}"
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", str(fpath)])
            return f"Opened: {path}"

    def summarize_document(self, path: str) -> str:
        fpath = Path(path)
        if not fpath.exists():
            return f"File not found: {path}"
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if len(text) > 8000:
                text = text[:8000] + "\n...[truncated]"
            return f"Document content ({fpath.name}):\n{text}"
        except Exception as e:
            return f"Could not read file: {e}"
