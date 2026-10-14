import argparse
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def audit(constraints: Path) -> dict:
    packages = [line.strip().split('==', 1) for line in constraints.read_text().splitlines()
                if line.strip() and not line.startswith('#')]
    payload = {'queries': [{'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': version}
                           for name, version in packages]}
    request = urllib.request.Request('https://api.osv.dev/v1/querybatch',
                                     data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if len(data.get('results', [])) != len(packages):
        raise ValueError('The advisory service returned an incomplete result.')
    findings = [{'package': name, 'version': version, 'advisories': result.get('vulns', [])}
                for (name, version), result in zip(packages, data['results'], strict=True)
                if result.get('vulns')]
    return {'checked_at': datetime.now(UTC).isoformat(), 'source': 'https://api.osv.dev',
            'packages_checked': len(packages), 'findings': findings,
            'limitation': 'No reported advisory is not proof of vulnerability absence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('constraints', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(args.constraints)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(1 if result['findings'] else 0)
