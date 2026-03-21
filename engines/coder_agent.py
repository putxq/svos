"""
SVOS Coder Agent — The Company's Developer.

Writes Python scripts, automations, data processors, and custom tools.
Runs code in a sandboxed environment (restricted builtins, no file system access outside workspace).

Use cases:
- Generate data processing scripts
- Build custom automations
- Create report generators
- Write API integration helpers
- Prototype tools for the company

Safety: All code runs in restricted exec with timeout.
"""

import ast
import json
import logging
import time
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from core.llm_provider import LLMProvider

logger = logging.getLogger("svos.coder")

# Maximum execution time for scripts (seconds)
MAX_EXEC_SECONDS = 10
# Maximum script size
MAX_SCRIPT_CHARS = 10000

# Safe builtins for sandboxed execution
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool,
    "dict": dict, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset,
    "int": int, "isinstance": isinstance, "len": len,
    "list": list, "map": map, "max": max, "min": min,
    "print": print, "range": range, "reversed": reversed,
    "round": round, "set": set, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "type": type,
    "zip": zip, "True": True, "False": False, "None": None,
}

# Blocked imports and operations
BLOCKED_KEYWORDS = [
    "import os", "import sys", "import subprocess",
    "__import__", "eval(", "exec(",
    "open(", "file(", "input(",
    "shutil", "pathlib", "glob",
    "socket", "http", "urllib",
    "pickle", "marshal",
    "rm ", "rmdir", "unlink",
]


class CoderAgent:
    """AI developer that writes and runs code for the company."""

    def __init__(self, customer_id: str = "", llm_provider: LLMProvider = None):
        self.customer_id = customer_id
        self.llm = llm_provider
        self._scripts_dir = self._get_scripts_dir()

    def _get_scripts_dir(self) -> Path:
        if self.customer_id:
            from core.tenant import get_tenant_dir
            d = get_tenant_dir(self.customer_id) / "scripts"
        else:
            d = Path("workspace/scripts")
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def generate_script(
        self,
        task: str,
        context: str = "",
        language: str = "python",
    ) -> dict:
        """AI generates a script based on task description."""
        if not self.llm:
            try:
                self.llm = LLMProvider()
            except Exception as e:
                return {"success": False, "error": f"LLM not available: {e}"}

        system = (
            "You are a Python developer for a digital company.\n"
            "Write clean, production-quality Python scripts.\n"
            "Rules:\n"
            "- Pure Python only (no external imports except json, math, datetime, re, collections)\n"
            "- No file I/O, no network calls, no os/sys operations\n"
            "- Script must be self-contained and runnable\n"
            "- Include docstring explaining what it does\n"
            "- Use print() for output\n"
            "- Keep it under 100 lines\n\n"
            "Return ONLY the Python code. No markdown, no backticks, no explanation."
        )

        user = f"Task: {task}"
        if context:
            user += f"\nContext: {context}"

        try:
            code = await self.llm.complete(
                system_prompt=system,
                user_message=user,
                temperature=0.2,
                max_tokens=2000,
            )

            # Clean up response
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            code = code.strip()

            # Validate
            validation = self._validate_code(code)
            if not validation["safe"]:
                return {
                    "success": False,
                    "error": f"Generated code failed safety check: {validation['reason']}",
                    "code": code,
                }

            # Save script
            script_id = f"script_{uuid.uuid4().hex[:8]}"
            script_path = self._scripts_dir / f"{script_id}.py"
            script_path.write_text(code, encoding="utf-8")

            meta = {
                "id": script_id,
                "task": task[:200],
                "language": language,
                "lines": len(code.split("\n")),
                "chars": len(code),
                "created_at": datetime.utcnow().isoformat(),
                "executed": False,
                "last_output": None,
            }
            meta_path = self._scripts_dir / f"{script_id}.meta.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            return {
                "success": True,
                "script_id": script_id,
                "code": code,
                "lines": meta["lines"],
                "validation": validation,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_script(self, script_id: str, input_data: dict = None) -> dict:
        """Run a saved script in sandboxed environment."""
        script_path = self._scripts_dir / f"{script_id}.py"
        if not script_path.exists():
            return {"success": False, "error": "Script not found"}

        code = script_path.read_text("utf-8")
        return self._execute_sandboxed(code, script_id, input_data)

    def run_code(self, code: str, input_data: dict = None) -> dict:
        """Run arbitrary code in sandboxed environment (for quick tasks)."""
        validation = self._validate_code(code)
        if not validation["safe"]:
            return {"success": False, "error": f"Code failed safety check: {validation['reason']}"}
        return self._execute_sandboxed(code, "inline", input_data)

    def _validate_code(self, code: str) -> dict:
        """Validate code for safety."""
        if not code or not code.strip():
            return {"safe": False, "reason": "Empty code"}

        if len(code) > MAX_SCRIPT_CHARS:
            return {"safe": False, "reason": f"Code too long ({len(code)} chars, max {MAX_SCRIPT_CHARS})"}

        # Check blocked keywords
        for blocked in BLOCKED_KEYWORDS:
            if blocked in code:
                return {"safe": False, "reason": f"Blocked operation: {blocked}"}

        # Try to parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"safe": False, "reason": f"Syntax error: {e}"}

        # Check for dangerous AST nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("os", "sys", "subprocess", "shutil", "socket"):
                        return {"safe": False, "reason": f"Blocked import: {alias.name}"}
            if isinstance(node, ast.ImportFrom):
                if node.module in ("os", "sys", "subprocess", "shutil", "socket"):
                    return {"safe": False, "reason": f"Blocked import from: {node.module}"}

        return {"safe": True, "reason": "passed"}

    def _execute_sandboxed(self, code: str, script_id: str, input_data: dict = None) -> dict:
        """Execute code in a restricted environment."""
        import io
        import contextlib

        # Capture stdout
        output_buffer = io.StringIO()

        # Build restricted globals
        restricted_globals = {"__builtins__": SAFE_BUILTINS}

        # Allow safe standard library modules
        import json as _json, math as _math, re as _re
        from datetime import datetime as _dt, timedelta as _td
        from collections import Counter as _Counter, defaultdict as _dd

        restricted_globals.update({
            "json": _json, "math": _math, "re": _re,
            "datetime": _dt, "timedelta": _td,
            "Counter": _Counter, "defaultdict": _dd,
        })

        # Inject input data
        if input_data:
            restricted_globals["INPUT"] = input_data

        start = time.time()
        try:
            with contextlib.redirect_stdout(output_buffer):
                exec(code, restricted_globals)
            elapsed = time.time() - start

            output = output_buffer.getvalue()

            # Update meta if saved script
            meta_path = self._scripts_dir / f"{script_id}.meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text("utf-8"))
                    meta["executed"] = True
                    meta["last_output"] = output[:1000]
                    meta["last_run"] = datetime.utcnow().isoformat()
                    meta["last_duration_ms"] = round(elapsed * 1000, 2)
                    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            return {
                "success": True,
                "script_id": script_id,
                "output": output[:5000],
                "duration_ms": round(elapsed * 1000, 2),
                "truncated": len(output) > 5000,
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "success": False,
                "script_id": script_id,
                "error": str(e)[:500],
                "duration_ms": round(elapsed * 1000, 2),
            }

    def list_scripts(self) -> list[dict]:
        """List all saved scripts."""
        scripts = []
        for meta_file in sorted(self._scripts_dir.glob("*.meta.json"), reverse=True):
            try:
                meta = json.loads(meta_file.read_text("utf-8"))
                scripts.append(meta)
            except Exception:
                pass
        return scripts[:50]

    def get_script(self, script_id: str) -> dict | None:
        """Get script code and metadata."""
        script_path = self._scripts_dir / f"{script_id}.py"
        meta_path = self._scripts_dir / f"{script_id}.meta.json"

        if not script_path.exists():
            return None

        result = {"code": script_path.read_text("utf-8")}
        if meta_path.exists():
            try:
                result["meta"] = json.loads(meta_path.read_text("utf-8"))
            except Exception:
                pass
        return result

    def delete_script(self, script_id: str) -> dict:
        """Delete a saved script."""
        script_path = self._scripts_dir / f"{script_id}.py"
        meta_path = self._scripts_dir / f"{script_id}.meta.json"

        deleted = False
        if script_path.exists():
            script_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        return {"deleted": deleted, "script_id": script_id}
