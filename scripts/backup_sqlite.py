import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def backup(db_path: Path, backup_dir: Path) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    target = backup_dir / f'{db_path.stem}-{stamp}.sqlite3'
    shutil.copy2(db_path, target)
    manifest = {'database': str(db_path), 'backup': str(target), 'bytes': target.stat().st_size, 'sha256': sha256(target), 'created_at': stamp}
    (target.with_suffix('.json')).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default=os.getenv('APP_DATABASE', str(ROOT / 'data' / 'factorypulse.sqlite3')))
    parser.add_argument('--backup-dir', default=str(ROOT / 'data' / 'backups'))
    args = parser.parse_args()
    print(json.dumps(backup(Path(args.database), Path(args.backup_dir)), indent=2))
