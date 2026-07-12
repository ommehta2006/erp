from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "factorypulse_erp" / "factorypulse_erp" / "doctype"
required = {"doctype", "name", "module", "fields", "permissions"}
files = sorted(DOCTYPE_ROOT.glob("*/*.json"))
if len(files) < 30:
    raise SystemExit(f"expected at least 30 DocTypes, found {len(files)}")
for path in files:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = required - set(data)
    if missing:
        raise SystemExit(f"{path} missing {sorted(missing)}")
    if data["doctype"] != "DocType":
        raise SystemExit(f"{path} is not a DocType metadata file")
    if not data["name"].startswith("FactoryPulse "):
        raise SystemExit(f"{path} is not FactoryPulse namespaced")
    names = [field.get("fieldname") for field in data.get("fields", [])]
    if len(names) != len(set(names)):
        raise SystemExit(f"{path} has duplicate fieldnames")
print(f"PASS {len(files)} Frappe DocType metadata files")
