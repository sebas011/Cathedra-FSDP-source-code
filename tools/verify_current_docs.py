"""Verify current release documentation identities, links and export headers."""

import argparse
import ast
import json
import re
from pathlib import Path


def verify(root: Path, package: Path | None = None) -> list[str]:
    issues = []
    version = (root / "VERSION").read_text().strip()
    frontend = json.loads((root / "frontend/package.json").read_text())
    lock = json.loads((root / "frontend/package-lock.json").read_text())
    if {version, frontend["version"], lock["version"], lock["packages"][""]["version"]} != {version}:
        issues.append("Source/frontend/lockfile versions disagree")
    tree = ast.parse((root / "backend/app/migrations.py").read_text(encoding="utf-8-sig"))
    migrations = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "MIGRATIONS" for target in node.targets))
    ceiling = max(item.elts[0].value for item in migrations.elts)
    current = root / "docs/current"
    names = ("README", "IMPLEMENTATION_PLAN", "BACKEND_SCHEMA", "DESIGN_BRIEF", "APP_FLOW", "TECHNICAL_REQUIREMENTS", "PRODUCT_REQUIREMENTS")
    for name in names:
        text = (current / f"{name}.md").read_text(encoding="utf-8-sig")
        if f"**Baseline:** release {version}; database schema {ceiling}" not in text:
            issues.append(f"Incorrect baseline: {name}")
    files = [*current.glob("*.md"), *(root / "docs/analysis").glob("*.md"),
             root / "docs/EXPORT_SCHEMAS.md", root / "docs/OFFICE_GUIDE.md",
             root / f"docs/VALIDATION_{version}.md", root / "docs/plans/2026-10-09-audit-corrections.md"]
    for file in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text(encoding="utf-8-sig")):
            if "://" not in target and not target.startswith("#") and not (file.parent / target.split("#")[0]).exists():
                issues.append(f"Missing link in {file.name}: {target}")
    export_text = (root / "docs/EXPORT_SCHEMAS.md").read_text()
    for contract in json.loads((current / "EXPORT_CONTRACTS.json").read_text()).values():
        for header in contract["sections"].values():
            if ",".join(header) not in export_text:
                issues.append(f"Export prose/header contract disagree: {contract['path']}")
    technical = (current / "TECHNICAL_REQUIREMENTS.md").read_text()
    if f"Automatic migration runs through version {ceiling}" not in technical:
        issues.append("Technical migration ceiling disagrees")
    if "Reconcile the three-term requirement" in (current / "IMPLEMENTATION_PLAN.md").read_text():
        issues.append("Superseded Summer-removal stage remains")
    if package:
        manifest = json.loads((package / "release-manifest.json").read_text())
        if {manifest["version"], (package / "VERSION").read_text().strip(),
            (package / "_internal/VERSION").read_text().strip()} != {version}:
            issues.append("Package identities disagree with source")
    return issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    failures = verify(args.root, args.package)
    if failures:
        raise SystemExit("\n".join(failures))
    print("Current documentation identities, migration ceiling, links and export headers verified.")
