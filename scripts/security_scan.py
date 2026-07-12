import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    ('private_key', re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('aws_access_key', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('generic_secret_assignment', re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*=\s*[^\s#]+')),
]
SKIP_DIRS = {'data', '.git', '__pycache__'}
ALLOW_FILES = {'.env.example'}

def scan():
    findings = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.name in ALLOW_FILES:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line = text.count('\n', 0, match.start()) + 1
                findings.append({'file': rel, 'line': line, 'rule': name})
    return {'ok': not findings, 'findings': findings}

if __name__ == '__main__':
    result = scan()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
