import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


def restore_test(backup: Path) -> dict:
    if not backup.exists():
        raise FileNotFoundError(backup)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'restore.sqlite3'
        shutil.copy2(backup, target)
        con = sqlite3.connect(target)
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        con.close()
        return {'ok': integrity == 'ok', 'integrity': integrity, 'tables': tables, 'backup': str(backup)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('backup')
    args = parser.parse_args()
    result = restore_test(Path(args.backup))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
