import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', '.env.example', 'Dockerfile', 'docker-compose.yml',
    'backend/factory_erp/app.py', 'backend/factory_erp/store.py',
    'frontend/index.html', 'frontend/app.js', 'frontend/styles.css',
    'frontend/manifest.webmanifest', 'frontend/service-worker.js',
    'docs/api/openapi.json', 'docs/final/01_PRODUCT_AND_FEATURES.md',
    'frappe_app/README.md', 'frappe_app/tools/validate_metadata.py',
]

def check():
    items = []
    for rel in REQUIRED:
        path = ROOT / rel
        items.append({'check': f'file:{rel}', 'ok': path.exists(), 'detail': str(path)})
    db_path = Path(os.getenv('APP_DATABASE', ROOT / 'data' / 'factorypulse.sqlite3'))
    items.append({'check': 'database:path_configured', 'ok': bool(str(db_path)), 'detail': str(db_path)})
    if db_path.exists():
        try:
            con = sqlite3.connect(db_path)
            ok = con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            con.close()
            items.append({'check': 'database:integrity', 'ok': ok, 'detail': str(db_path)})
        except Exception as exc:
            items.append({'check': 'database:integrity', 'ok': False, 'detail': str(exc)})
    backups = ROOT / 'data' / 'backups'
    backups.mkdir(parents=True, exist_ok=True)
    items.append({'check': 'backup_dir:writable', 'ok': os.access(backups, os.W_OK), 'detail': str(backups)})
    return {'ok': all(item['ok'] for item in items), 'items': items}

if __name__ == '__main__':
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
