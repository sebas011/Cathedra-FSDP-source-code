import argparse
import importlib.metadata
import platform
import struct
import subprocess
import sys
from pathlib import Path

EXPECTED_PYTHON = (3, 14, 7)
EXPECTED_NODE = "v26.8.1"


def verify_runtime(python_version, system, architecture, node_version, pointer_bits=64) -> list[str]:
    mismatches = []
    if tuple(python_version) != EXPECTED_PYTHON:
        mismatches.append(f"Python: expected 3.14.7, found {'.'.join(map(str, python_version))}")
    if system != "Windows" or architecture.upper() not in {"AMD64", "X86_64"} or pointer_bits != 64:
        mismatches.append(
            f"Platform: expected Windows x64, found {system} {architecture}, "
            f"{pointer_bits}-bit Python"
        )
    if node_version.strip() != EXPECTED_NODE:
        mismatches.append(f"Node: expected {EXPECTED_NODE}, found {node_version.strip()}")
    return mismatches


def verify_constraints(path: Path) -> list[str]:
    mismatches = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        package, expected = line.split("==", 1)
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = "missing"
        if actual != expected:
            mismatches.append(f"{package}: expected {expected}, installed {actual}")
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the pinned Windows x64 build environment.")
    parser.add_argument("constraints", type=Path)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--runtime-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        node = subprocess.run([str(args.node), "--version"], capture_output=True,
                              text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Node runtime verification failed: {error}") from error
    mismatches = verify_runtime(sys.version_info[:3], platform.system(),
                                platform.machine(), node.stdout, struct.calcsize("P") * 8)
    if mismatches:
        raise SystemExit("Build input verification failed:\n" + "\n".join(mismatches))
    if not args.runtime_only:
        mismatches = verify_constraints(args.constraints)
        if mismatches:
            raise SystemExit("Build input verification failed:\n" + "\n".join(mismatches))
    print("Windows x64, Python 3.14.7 and Node 26.8.1 verified." if args.runtime_only else
          "Pinned Windows x64 runtime and backend/packaging dependencies verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
