from pathlib import Path


class FileTool:
    """يقرأ ويكتب ملفات — يستخدمه كل الوكلاء"""

    name = "file_operations"
    description = "Read, write, and list files"

    def __init__(self, workspace_root: str = "workspace"):
        self.root = Path(workspace_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("Invalid path: absolute/outside paths are not allowed")
        target = (self.root / p).resolve()
        if self.root not in [target, *target.parents]:
            raise ValueError("Path escapes workspace root")
        return target

    async def read(self, path: str) -> dict:
        try:
            target = self._resolve_safe(path)
            if not target.exists() or not target.is_file():
                return {"ok": False, "path": path, "error": "File not found"}
            content = target.read_text(encoding="utf-8")
            return {"ok": True, "path": str(target), "content": content}
        except Exception as e:
            return {"ok": False, "path": path, "error": str(e)}

    async def write(self, path: str, content: str) -> dict:
        try:
            target = self._resolve_safe(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"ok": True, "path": str(target), "bytes": len(content.encode('utf-8'))}
        except Exception as e:
            return {"ok": False, "path": path, "error": str(e)}

    async def list_dir(self, path: str = ".") -> dict:
        try:
            target = self._resolve_safe(path)
            if not target.exists() or not target.is_dir():
                return {"ok": False, "path": path, "error": "Directory not found"}
            items = []
            for x in sorted(target.iterdir(), key=lambda a: a.name.lower()):
                items.append({"name": x.name, "type": "dir" if x.is_dir() else "file"})
            return {"ok": True, "path": str(target), "items": items, "total": len(items)}
        except Exception as e:
            return {"ok": False, "path": path, "error": str(e)}
