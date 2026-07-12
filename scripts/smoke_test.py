import argparse
import json
import urllib.request


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()
    health = get_json(args.base_url.rstrip("/") + "/api/health")
    if not health.get("ok"):
        raise SystemExit("health check failed")
    print("PASS health")
    if args.health_only:
        return


if __name__ == "__main__":
    main()
