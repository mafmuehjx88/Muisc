#!/usr/bin/env python3
"""
Persistent Telegram Auth & Music Bot Supervisor Daemon (127.0.0.1:8765).
Keeps Pyrogram MTProto TCP session alive in memory between send_code() and sign_in()
so OTP codes do not expire due to client disconnect, updates config.py automatically,
and supervises main.py with real-time log streaming.
"""

import asyncio
import collections
import json
import os
import re
import signal
import sys
import time
from typing import Optional

from aiohttp import web
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.py")
CODEFILES_TS_PATH = os.path.join(ROOT_DIR, "src", "data", "codeFiles.ts")
MAIN_PY_PATH = os.path.join(ROOT_DIR, "main.py")
PYTHON_BIN = "/tmp/tgvenv/bin/python" if os.path.exists("/tmp/tgvenv/bin/python") else sys.executable

API_ID = 38953431
API_HASH = "2ba6fc60c837d5dfa52352304831a7c1"
DEFAULT_PHONE = "+959674354885"


class BotSupervisor:
    def __init__(self):
        self.auth_client: Optional[Client] = None
        self.auth_lock = asyncio.Lock()
        self.otp_state = {
            "status": "idle",  # idle | otp_sent | need_2fa | authenticated
            "phone": DEFAULT_PHONE,
            "phone_code_hash": None,
            "code_type": None,
            "sent_at": None,
            "error": None,
        }
        self.assistant_info: Optional[dict] = None
        self.bot_info: Optional[dict] = None
        self.voice_ready: bool = False
        self.bot_proc: Optional[asyncio.subprocess.Process] = None
        self.logs = collections.deque(maxlen=180)
        self._reader_task: Optional[asyncio.Task] = None

    def read_current_session(self) -> str:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r'STRING_SESSION:\s*str\s*=\s*os\.getenv\("STRING_SESSION",\s*"([^"]*)"\)', content)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
        return ""

    def save_string_session(self, session_str: str):
        # 1. Update config.py
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        updated = re.sub(
            r'STRING_SESSION:\s*str\s*=\s*os\.getenv\("STRING_SESSION",\s*"[^"]*"\)',
            f'STRING_SESSION: str = os.getenv("STRING_SESSION", "{session_str}")',
            content,
        )
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(updated)

        # 2. Update src/data/codeFiles.ts if present so ZIP downloads include it
        if os.path.exists(CODEFILES_TS_PATH):
            try:
                with open(CODEFILES_TS_PATH, "r", encoding="utf-8") as f:
                    ts_content = f.read()
                ts_updated = re.sub(
                    r"'STRING_SESSION: str = os\.getenv\(\"STRING_SESSION\", \"[^\"]*\"\),?'",
                    f'\'STRING_SESSION: str = os.getenv("STRING_SESSION", "{session_str}")\'',
                    ts_content,
                )
                # Also match line without trailing comma inside array
                ts_updated = re.sub(
                    r'STRING_SESSION: str = os\.getenv\("STRING_SESSION", "[^"]*"\)',
                    f'STRING_SESSION: str = os.getenv("STRING_SESSION", "{session_str}")',
                    ts_updated,
                )
                with open(CODEFILES_TS_PATH, "w", encoding="utf-8") as f:
                    f.write(ts_updated)
            except Exception as e:
                self.append_log(f"[Supervisor] Warning updating codeFiles.ts: {e}")

    def append_log(self, line: str):
        ts = time.strftime("%H:%M:%S")
        clean = line.rstrip("\r\n")
        if not clean:
            return
        self.logs.append(f"[{ts}] {clean}")

        # Parse live status markers from main.py logs
        bot_match = re.search(r"Bot started successfully as @([^\s]+)\s+\((\d+)\)", clean)
        if bot_match:
            self.bot_info = {"username": bot_match.group(1), "id": int(bot_match.group(2))}

        asst_match = re.search(r"Assistant User started as @([^\s]+)\s+\((\d+)\)(?:\s+\[([^\]]+)\])?", clean)
        if asst_match:
            uname = None if asst_match.group(1) == "None" else asst_match.group(1)
            fname = asst_match.group(3) or (f"@{uname}" if uname else "Assistant")
            if not self.assistant_info:
                self.assistant_info = {"firstName": fname, "username": uname, "id": int(asst_match.group(2)), "phone": DEFAULT_PHONE}
            else:
                self.assistant_info["id"] = int(asst_match.group(2))
                if fname:
                    self.assistant_info["firstName"] = fname
                if uname:
                    self.assistant_info["username"] = uname

        if "PyTgCalls Voice Client started successfully!" in clean:
            self.voice_ready = True

    async def _stream_output(self, proc: asyncio.subprocess.Process):
        assert proc.stdout is not None
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                self.append_log(line.decode("utf-8", errors="replace"))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.append_log(f"[Supervisor] Log reader error: {e}")

    async def start_bot(self):
        await self.stop_bot()
        self.voice_ready = False
        self.append_log("[Supervisor] Launching Telegram Music Bot (main.py)...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self.bot_proc = await asyncio.create_subprocess_exec(
            PYTHON_BIN,
            "-u",
            MAIN_PY_PATH,
            cwd=ROOT_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._stream_output(self.bot_proc))

    async def stop_bot(self):
        if self.bot_proc and self.bot_proc.returncode is None:
            self.append_log("[Supervisor] Stopping existing bot process...")
            try:
                self.bot_proc.send_signal(signal.SIGTERM)
                await asyncio.wait_for(self.bot_proc.wait(), timeout=4.0)
            except Exception:
                try:
                    self.bot_proc.kill()
                    await self.bot_proc.wait()
                except Exception:
                    pass
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        self.bot_proc = None
        self.voice_ready = False

    async def close_auth_client(self):
        if self.auth_client is not None:
            try:
                if self.auth_client.is_connected:
                    await self.auth_client.disconnect()
            except Exception:
                pass
            self.auth_client = None

    async def send_otp(self, phone: str) -> dict:
        async with self.auth_lock:
            phone = phone.strip()
            if not phone.startswith("+"):
                phone = "+" + phone

            await self.close_auth_client()

            client = Client(
                name="live_assistant_auth",
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=True,
                device_model="Telegram Music Bot",
                system_version="Linux 6.x",
                app_version="2.0.0",
            )
            await client.connect()
            try:
                sent = await client.send_code(phone)
                self.auth_client = client
                self.otp_state = {
                    "status": "otp_sent",
                    "phone": phone,
                    "phone_code_hash": sent.phone_code_hash,
                    "code_type": str(sent.type),
                    "sent_at": int(time.time()),
                    "error": None,
                }
                self.append_log(f"[Auth] Sent fresh OTP to {phone} via {sent.type} (live MTProto connection kept open)")
                return {
                    "ok": True,
                    "phone": phone,
                    "codeType": str(sent.type),
                    "sentAt": self.otp_state["sent_at"],
                }
            except FloodWait as e:
                await client.disconnect()
                msg = f"Telegram FloodWait: Please wait {e.value} seconds before requesting another code."
                self.otp_state["error"] = msg
                return {"ok": False, "error": msg}
            except PhoneNumberInvalid:
                await client.disconnect()
                msg = "ဖုန်းနံပါတ် မှားယွင်းနေပါသည် (PhoneNumberInvalid)။ +959... ပုံစံဖြင့် စစ်ဆေးပါ။"
                self.otp_state["error"] = msg
                return {"ok": False, "error": msg}
            except Exception as e:
                await client.disconnect()
                msg = f"Failed to send OTP: {type(e).__name__}: {e}"
                self.otp_state["error"] = msg
                return {"ok": False, "error": msg}

    async def verify_otp(self, raw_code: str, password: str = "") -> dict:
        async with self.auth_lock:
            if not self.auth_client or not self.auth_client.is_connected:
                return {
                    "ok": False,
                    "expired": True,
                    "error": "OTP Session မရှိတော့ပါ။ 'OTP ကုဒ်အသစ် ပြန်ပို့မည်' ကိုနှိပ်ပြီး ကုဒ်အသစ် ရယူပါ။",
                }

            digits = re.sub(r"\D", "", raw_code or "")
            phone = self.otp_state.get("phone")
            code_hash = self.otp_state.get("phone_code_hash")

            try:
                if self.otp_state.get("status") == "need_2fa":
                    if not password:
                        return {
                            "ok": False,
                            "need2fa": True,
                            "error": "ဤအကောင့်တွင် Two-Step Verification (2FA Password) ခံထားပါသည်။ Password ထည့်ပေးပါ။",
                        }
                    await self.auth_client.check_password(password)
                else:
                    if not digits:
                        return {"ok": False, "error": "OTP ကုဒ် ၅ လုံး ထည့်သွင်းပေးပါ။"}
                    try:
                        await self.auth_client.sign_in(phone, code_hash, digits)
                    except SessionPasswordNeeded:
                        if password:
                            await self.auth_client.check_password(password)
                        else:
                            self.otp_state["status"] = "need_2fa"
                            self.otp_state["error"] = None
                            self.append_log(f"[Auth] OTP accepted for {phone}; 2FA password required.")
                            return {
                                "ok": False,
                                "need2fa": True,
                                "message": "OTP မှန်ကန်ပါသည်! သင့်အကောင့်၏ Two-Step Verification (2FA) Password ကို ဆက်ထည့်ပေးပါ။",
                            }

                me = await self.auth_client.get_me()
                session_str = await self.auth_client.export_session_string()
                self.assistant_info = {
                    "id": me.id,
                    "firstName": me.first_name,
                    "username": me.username,
                    "phone": me.phone_number or phone,
                }
                self.save_string_session(session_str)
                self.otp_state = {
                    "status": "authenticated",
                    "phone": phone,
                    "phone_code_hash": None,
                    "code_type": None,
                    "sent_at": None,
                    "error": None,
                }
                self.append_log(
                    f"[Auth] Assistant authenticated as {me.first_name} (@{me.username or 'no_username'}, ID: {me.id})!"
                )
                await self.close_auth_client()
                await self.start_bot()

                return {
                    "ok": True,
                    "assistantInfo": self.assistant_info,
                    "sessionPreview": f"{session_str[:16]}...{session_str[-12:]}",
                }

            except PhoneCodeExpired:
                self.otp_state["error"] = "PHONE_CODE_EXPIRED"
                self.append_log("[Auth] Telegram returned PHONE_CODE_EXPIRED.")
                return {
                    "ok": False,
                    "expired": True,
                    "error": "OTP ကုဒ် သက်တမ်းကုန်သွားပါသည် (PHONE_CODE_EXPIRED)။ သတိပြုရန် - ကုဒ်ကို Telegram Chat ထဲမှတစ်ဆင့် ပို့လျှင် Telegram က ချက်ချင်း ပယ်ဖျက်ပါသည်။ 'OTP ကုဒ်အသစ် ပြန်ပို့မည်' ကိုနှိပ်ပြီး ဤနေရာတွင် တိုက်ရိုက်ရိုက်ထည့်ပါ။",
                }
            except PhoneCodeInvalid:
                return {
                    "ok": False,
                    "error": "OTP ကုဒ် မှားယွင်းနေပါသည် (PHONE_CODE_INVALID)။ ဂဏန်း ၅ လုံးကို ပြန်စစ်ပေးပါ။",
                }
            except PasswordHashInvalid:
                return {
                    "ok": False,
                    "need2fa": True,
                    "error": "2FA Password မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပြီး ထည့်ပေးပါ။",
                }
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                self.append_log(f"[Auth] Verification error: {err_msg}")
                return {"ok": False, "error": err_msg}


supervisor = BotSupervisor()


async def handle_status(_request: web.Request) -> web.Response:
    session_str = supervisor.read_current_session()
    bot_running = supervisor.bot_proc is not None and supervisor.bot_proc.returncode is None
    if session_str and supervisor.otp_state["status"] == "idle":
        supervisor.otp_state["status"] = "authenticated"
    return web.json_response(
        {
            "ok": True,
            "botRunning": bot_running,
            "botPid": supervisor.bot_proc.pid if bot_running else None,
            "botInfo": supervisor.bot_info,
            "hasStringSession": bool(session_str),
            "sessionPreview": f"{session_str[:14]}...{session_str[-10:]}" if len(session_str) > 30 else "",
            "voiceReady": supervisor.voice_ready,
            "assistantInfo": supervisor.assistant_info,
            "otpState": supervisor.otp_state,
            "logs": list(supervisor.logs),
        }
    )


async def handle_send_code(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        body = {}
    phone = body.get("phone") or DEFAULT_PHONE
    res = await supervisor.send_otp(phone)
    return web.json_response(res)


async def handle_verify_code(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code", ""))
    password = str(body.get("password", ""))
    res = await supervisor.verify_otp(code, password)
    return web.json_response(res)


AUTOSTART_FLAG = os.path.join(ROOT_DIR, ".local_autostart")


async def handle_restart(_request: web.Request) -> web.Response:
    try:
        with open(AUTOSTART_FLAG, "w", encoding="utf-8") as fp:
            fp.write("1")
    except OSError:
        pass
    await supervisor.start_bot()
    return web.json_response({"ok": True})


async def handle_stop(_request: web.Request) -> web.Response:
    try:
        if os.path.exists(AUTOSTART_FLAG):
            os.remove(AUTOSTART_FLAG)
    except OSError:
        pass
    await supervisor.stop_bot()
    return web.json_response({"ok": True})


async def on_startup(_app: web.Application):
    if os.path.exists(AUTOSTART_FLAG):
        await supervisor.start_bot()
    else:
        supervisor.append_log(
            "[Supervisor] Local preview bot is paused so Wispbyte 24/7 server can run without Telegram conflict."
        )


async def on_cleanup(_app: web.Application):
    await supervisor.close_auth_client()
    await supervisor.stop_bot()


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/status", handle_status)
    app.router.add_post("/send-code", handle_send_code)
    app.router.add_post("/verify-code", handle_verify_code)
    app.router.add_post("/restart", handle_restart)
    app.router.add_post("/stop", handle_stop)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8765, print=None)
