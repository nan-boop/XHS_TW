"""Local-only Creator login panel.

The browser receives status only. Creator Auth and all session material stay in
this process memory and are never serialized into the HTML or API responses.
"""

from __future__ import annotations

import argparse
import builtins
import ctypes
import ctypes.wintypes
import json
import mimetypes
import os
import secrets
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
from typing import Any
from urllib.parse import parse_qs, urlsplit


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required for persistent login")
    source = ctypes.create_string_buffer(data)
    source_blob = _DataBlob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(ctypes.byref(source_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required for persistent login")
    source = ctypes.create_string_buffer(data)
    source_blob = _DataBlob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(ctypes.byref(source_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


class SessionStore:
    """Persist only an OS-encrypted, minimal Creator session snapshot."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, auth: Any) -> None:
        cookie_store = getattr(auth, "_cookie_store", None)
        payload = {
            "version": 1,
            "cookies": auth.cookies,
            "host_cookies": auth.host_cookies_snapshot(),
            "host_cookie_state": cookie_store.export_state() if cookie_store else {},
        }
        protected = _dpapi_protect(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_bytes(protected)
        os.replace(temp, self.path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        payload = json.loads(_dpapi_unprotect(self.path.read_bytes()).decode("utf-8"))
        if payload.get("version") != 1 or not payload.get("cookies"):
            raise ValueError("Unsupported local session format")
        return payload

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)


class LoginController:
    def __init__(self, root: Path, qr_dir: Path, session_file: Path) -> None:
        self.root = root
        self.qr_dir = qr_dir
        self.session_store = SessionStore(session_file)
        self.qr_path = qr_dir / "xiaohongshu-creator-login.png"
        self.lock = threading.RLock()
        self.inputs: Queue[tuple[str, str]] = Queue()
        self.worker: threading.Thread | None = None
        self.auth: Any = None
        self.status = "idle"
        self.message = "尚未开始"
        self.qr_revision = 0
        self.persistent = False

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "message": self.message,
                "authenticated": self.auth is not None,
                "persistent": self.persistent,
                "qr_available": self.qr_path.is_file(),
                "qr_revision": self.qr_revision,
            }

    def start(self, mode: str) -> dict[str, Any]:
        if mode not in {"phone", "qr"}:
            raise ValueError("不支持的登录方式")
        with self.lock:
            if self.auth is not None:
                return self.state()
            if self.worker and self.worker.is_alive():
                return self.state()
            self.inputs = Queue()
            self.status = "starting"
            self.message = "正在启动 Creator 登录"
            self.worker = threading.Thread(target=self._run, args=(mode,), daemon=True)
            self.worker.start()
            return self.state()

    def submit(self, kind: str, value: str) -> dict[str, Any]:
        if kind not in {"phone", "code"} or not value or len(value) > 64:
            raise ValueError("输入无效")
        with self.lock:
            expected = "awaiting_phone" if kind == "phone" else "awaiting_code"
            if self.status != expected:
                raise ValueError("当前不需要此输入")
            self.inputs.put((kind, value))
            self.message = "正在处理"
            return self.state()

    def close_session(self) -> dict[str, Any]:
        with self.lock:
            auth = self.auth
            self.auth = None
            self.persistent = False
            self.status = "idle"
            self.message = "本机会话已结束"
        if auth is not None:
            auth.close()
        return self.state()

    def forget_session(self) -> dict[str, Any]:
        self.close_session()
        self.session_store.remove()
        with self.lock:
            self.message = "本地登录缓存已清除"
        return self.state()

    def restore_session(self) -> None:
        try:
            payload = self.session_store.load()
            if not payload:
                return
            from apis.xhs_creator_apis import XHS_Creator_Apis
            from xhs_utils.xhs_creator.auth import XHSCreatorAuth

            auth = XHSCreatorAuth.from_cookie(
                payload["cookies"],
                host_cookies=payload.get("host_cookies") or {},
                host_cookie_state=payload.get("host_cookie_state") or {},
            )
            XHS_Creator_Apis(auth).bootstrap()
            with self.lock:
                self.auth = auth
                self.persistent = True
                self.status = "authenticated"
                self.message = "已恢复本地 Creator 会话"
        except Exception:
            if "auth" in locals() and auth is not None:
                auth.close()
            self.session_store.remove()
            with self.lock:
                self.status = "idle"
                self.message = "本地登录缓存不可用，请重新登录"

    def _prompt(self, prompt: str) -> str:
        kind = "code" if "验证码" in prompt else "phone"
        with self.lock:
            self.status = "awaiting_code" if kind == "code" else "awaiting_phone"
            self.message = "等待输入"
        received_kind, value = self.inputs.get()
        if received_kind != kind:
            raise RuntimeError("输入顺序无效")
        return value

    def _run(self, mode: str) -> None:
        auth = None
        login_module = None
        original_input = None
        try:
            from apis.xhs_creator_apis import XHS_Creator_Apis
            from apis.xhs_creator_login_apis import XHSCreatorLoginApi
            from xhs_utils.xhs_creator.auth import XHSCreatorAuth

            if mode == "phone":
                import apis.xhs_creator_login_apis as login_module

                original_input = login_module.__dict__.get("input", builtins.input)
                login_module.input = self._prompt
                auth = XHSCreatorAuth.from_phone_login()
            else:
                import qrcode

                self.qr_dir.mkdir(parents=True, exist_ok=True)

                def save_qr(url: str) -> None:
                    qrcode.make(url).save(self.qr_path)
                    with self.lock:
                        self.qr_revision += 1
                        self.status = "awaiting_scan"
                        self.message = "等待扫码和手机确认"

                XHSCreatorLoginApi.show_qrcode_image = staticmethod(save_qr)
                auth = XHSCreatorAuth.from_qrcode_login(show_in_terminal=False)

            with self.lock:
                self.status = "starting"
                self.message = "正在验收 Creator 会话"
            XHS_Creator_Apis(auth).bootstrap()
            with self.lock:
                self.auth = auth
                self.persistent = False
                self.status = "authenticated"
                self.message = "Creator 登录成功"
            try:
                self.session_store.save(auth)
            except Exception:
                with self.lock:
                    self.message = "Creator 登录成功，但本地加密保存失败"
            else:
                with self.lock:
                    self.persistent = True
                    self.message = "Creator 登录成功，本地加密会话已保存"
            auth = None
        except Exception:
            with self.lock:
                self.status = "failed"
                self.message = "登录失败，请重新尝试"
        finally:
            if login_module is not None and original_input is not None:
                login_module.input = original_input
            if auth is not None:
                auth.close()


class PanelHandler(BaseHTTPRequestHandler):
    server: "PanelServer"

    def log_message(self, format: str, *args: object) -> None:
        # Do not log query strings or request bodies, which could contain QR data.
        return

    def _authorized(self) -> bool:
        query_token = parse_qs(urlsplit(self.path).query).get("token", [""])[0]
        return secrets.compare_digest(
            self.headers.get("X-Local-UI-Token", "") or query_token,
            self.server.ui_token,
        )

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4096:
            raise ValueError("请求过大")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(value, dict):
            raise ValueError("请求格式无效")
        return value

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/":
            template = self.server.template.read_text(encoding="utf-8")
            body = template.replace("__UI_TOKEN__", self.server.ui_token).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)
            return
        if not self._authorized():
            self._json({"message": "未授权"}, HTTPStatus.FORBIDDEN)
            return
        if self.path.split("?", 1)[0] == "/api/state":
            self._json(self.server.controller.state())
            return
        if self.path.split("?", 1)[0] == "/api/qr":
            if not self.server.controller.qr_path.is_file():
                self._json({"message": "二维码尚未生成"}, HTTPStatus.NOT_FOUND)
                return
            body = self.server.controller.qr_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(str(self.server.controller.qr_path))[0] or "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        self._json({"message": "不存在"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not self._authorized():
            self._json({"message": "未授权"}, HTTPStatus.FORBIDDEN)
            return
        path = self.path.split("?", 1)[0]
        try:
            data = self._read_json()
            if path == "/api/start":
                result = self.server.controller.start(str(data.get("mode", "")))
            elif path == "/api/input":
                result = self.server.controller.submit(str(data.get("kind", "")), str(data.get("value", "")))
            elif path == "/api/close":
                result = self.server.controller.close_session()
            elif path == "/api/forget":
                result = self.server.controller.forget_session()
            else:
                self._json({"message": "不存在"}, HTTPStatus.NOT_FOUND)
                return
            self._json(result)
        except (ValueError, RuntimeError) as exc:
            self._json({"message": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            self._json({"message": "本机登录服务异常"}, HTTPStatus.INTERNAL_SERVER_ERROR)


class PanelServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], controller: LoginController, template: Path) -> None:
        super().__init__(address, PanelHandler)
        self.controller = controller
        self.template = template
        self.ui_token = secrets.token_urlsafe(24)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Spider_XHS checkout")
    parser.add_argument("--output-dir", required=True, help="Local non-C directory for the QR image")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--session-file", default="")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    qr_dir = Path(args.output_dir).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit("Spider_XHS directory not found")
    if qr_dir.drive.lower() == "c:":
        raise SystemExit("QR output must be on a non-C drive")
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("The login panel must bind to localhost only")
    sys.path.insert(0, str(root))
    session_file = Path(args.session_file).expanduser().resolve() if args.session_file else qr_dir / "creator-session.dpapi"
    if session_file.drive.lower() == "c:":
        raise SystemExit("Persistent session must be stored on a non-C drive")
    template = Path(__file__).with_name("creator_login_panel.html")
    controller = LoginController(root, qr_dir, session_file)
    controller.restore_session()
    server = PanelServer((args.host, args.port), controller, template)
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Creator login panel: {url}", flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.close_session()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
