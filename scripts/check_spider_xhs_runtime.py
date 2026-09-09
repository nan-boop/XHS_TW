"""Check the local Spider_XHS runtime without network access or login."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


MODULES = (
    "xhs_utils.xhs_auth",
    "apis.xhs_creator_apis",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Spider_XHS checkout")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    result = {
        "root": str(root),
        "python": sys.executable,
        "ok": False,
        "modules": {},
        "errors": [],
    }
    if not root.is_dir():
        result["errors"].append(f"Spider_XHS directory not found: {root}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    sys.path.insert(0, str(root))
    for module_name in MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # import diagnostics are the purpose of this script
            result["modules"][module_name] = False
            result["errors"].append(f"{module_name}: {exc}")
        else:
            result["modules"][module_name] = True

    try:
        from curl_cffi.requests.impersonate import BrowserType

        result["curl_cffi_chrome150"] = "chrome150" in {item.value for item in BrowserType}
        if not result["curl_cffi_chrome150"]:
            result["errors"].append("curl_cffi does not provide the chrome150 profile required by Creator")
    except Exception as exc:
        result["curl_cffi_chrome150"] = False
        result["errors"].append(f"curl_cffi chrome150 check failed: {exc}")

    result["ok"] = not result["errors"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
