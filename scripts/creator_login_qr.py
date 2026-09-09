"""Run Creator QR login and expose the QR as a local image without printing secrets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def emit(status: str, **extra: str) -> None:
    payload = {"status": status, **extra}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Spider_XHS checkout")
    parser.add_argument("--output-dir", required=True, help="Local non-C directory for the QR image")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not root.is_dir():
        emit("blocked", reason="Spider_XHS directory not found")
        return 2
    if str(output_dir).lower().startswith("c:\\"):
        emit("blocked", reason="QR output must be on a non-C drive")
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root))

    try:
        import qrcode
        from apis.xhs_creator_apis import XHS_Creator_Apis
        from apis.xhs_creator_login_apis import XHSCreatorLoginApi
        from xhs_utils.xhs_creator.auth import XHSCreatorAuth
    except Exception as exc:
        emit("blocked", reason=f"Spider_XHS import failed: {exc}")
        return 2

    qr_path = output_dir / "xiaohongshu-creator-login.png"

    def save_qr(url: str) -> None:
        qrcode.make(url).save(qr_path)
        emit("qr_ready", path=str(qr_path))

    XHSCreatorLoginApi.show_qrcode_image = staticmethod(save_qr)
    emit("login_check")
    try:
        auth = XHSCreatorAuth.from_qrcode_login(show_in_terminal=False)
        XHS_Creator_Apis(auth).bootstrap()
    except Exception as exc:
        emit("login_failed", reason=str(exc))
        return 1
    finally:
        try:
            auth.close()
        except Exception:
            pass
    emit("login_success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
