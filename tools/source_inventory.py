import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "frontend" / "src"
seen = set()
pending = [root / "main.tsx"]
while pending:
    source = pending.pop()
    if source in seen:
        continue
    seen.add(source)
    for relative in re.findall(r"""(?:from\s*|import\s*\(?\s*)["'](\.[^"']+)["']""", source.read_text(encoding="utf-8")):
        target = source.parent / relative
        choices = [target, Path(str(target) + ".tsx"), Path(str(target) + ".ts"), Path(str(target) + ".css"), target / "index.ts"]
        match = next((candidate.resolve() for candidate in choices if candidate.is_file()), None)
        if match is None:
            raise RuntimeError(f"Missing dependency: {source.name} -> {relative}")
        if match.suffix in {".ts", ".tsx", ".css"}:
            pending.append(match)
        else:
            seen.add(match)
unused = [str(source.relative_to(root.parent.parent)) for source in root.rglob("*") if source.is_file() and source.resolve() not in seen and source.name != "vite-env.d.ts"]
print(json.dumps(unused))
