#!/usr/bin/env python3
"""
Production-Ready Telegram Group Music Bot
Hybrid Architecture:
- Bot Control Plane: Async Telegram HTTP Bot API (aiohttp) -> Zero MTProto ImportBotAuthorization FloodWait,
  instantaneous command & callback polling, native 64-bit group/user ID support.
- Voice Streaming Plane: Pyrogram v2 Userbot + PyTgCalls + yt-dlp (YouTube + SoundCloud full-track fallback).
"""

import asyncio
import html
import json
import logging
import os
import signal
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from pyrogram import Client
import pyrogram.utils
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    FloodWait,
    InviteRequestSent,
    PeerIdInvalid,
    UserAlreadyParticipant,
    UserNotParticipant,
)
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    GroupCallNotFound,
    NoActiveGroupCall,
    NotInGroupCallError,
)
from pytgcalls.types import AudioPiped, StreamAudioEnded
import yt_dlp

import config

# ==========================================================
# Logging Configuration
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MusicBot")
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.INFO)

# Patch Pyrogram 2.0.106 32-bit peer ID limits so modern 64-bit Telegram
# groups and supergroups (e.g. -1004338179393) resolve without ValueError.
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999999

# Bind main-thread event loop BEFORE instantiating Pyrogram & PyTgCalls
MAIN_LOOP = asyncio.get_event_loop()

if not config.BOT_TOKEN:
    logger.error("BOT_TOKEN is missing in config.py or environment variables.")
    sys.exit(1)

if not config.STRING_SESSION:
    logger.warning(
        "⚠️ WARNING: STRING_SESSION is empty. Assistant won't be able to join voice calls until STRING_SESSION is set."
    )

# ==========================================================
# Async Telegram HTTP Bot API Client
# ==========================================================
class TelegramBotAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"
        self._session: Optional[aiohttp.ClientSession] = None
        self.me: Dict[str, Any] = {}

    async def start(self) -> Dict[str, Any]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=45, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        self.me = await self.call("getMe")
        return self.me

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None, timeout_sec: int = 35) -> Any:
        if self._session is None or self._session.closed:
            await self.start()
        assert self._session is not None
        url = f"{self.base_url}/{method}"
        req_timeout = aiohttp.ClientTimeout(total=timeout_sec, connect=10)
        async with self._session.post(url, json=payload or {}, timeout=req_timeout) as resp:
            data = await resp.json(content_type=None)
            if not data.get("ok"):
                desc = data.get("description", "Unknown Bot API error")
                code = data.get("error_code", resp.status)
                raise RuntimeError(f"[{code}] {desc}")
            return data.get("result")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        disable_web_page_preview: bool = True,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.call("sendMessage", payload)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        disable_web_page_preview: bool = True,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return await self.call("editMessageText", payload)
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                logger.debug(f"editMessageText notice: {e}")
            return None

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        try:
            await self.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
            return True
        except Exception:
            return False

    async def send_photo(
        self,
        chat_id: int,
        photo: str,
        caption: str,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.call("sendPhoto", payload)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> bool:
        payload: Dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            payload["text"] = text
        try:
            await self.call("answerCallbackQuery", payload)
            return True
        except Exception:
            return False

    async def get_chat(self, chat_id: int) -> Dict[str, Any]:
        return await self.call("getChat", {"chat_id": chat_id})

    async def get_chat_member(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        return await self.call("getChatMember", {"chat_id": chat_id, "user_id": user_id})

    async def unban_chat_member(self, chat_id: int, user_id: int) -> bool:
        await self.call(
            "unbanChatMember",
            {"chat_id": chat_id, "user_id": user_id, "only_if_banned": True},
        )
        return True

    async def create_chat_invite_link(self, chat_id: int) -> str:
        res = await self.call(
            "createChatInviteLink",
            {
                "chat_id": chat_id,
                "name": "Music Assistant AutoJoin",
                "creates_join_request": False,
            },
        )
        return res["invite_link"]

    async def export_chat_invite_link(self, chat_id: int) -> str:
        return await self.call("exportChatInviteLink", {"chat_id": chat_id})

    async def approve_chat_join_request(self, chat_id: int, user_id: int) -> bool:
        await self.call("approveChatJoinRequest", {"chat_id": chat_id, "user_id": user_id})
        return True

    async def download_file(self, file_id: str, dest_path: str) -> str:
        file_info = await self.call("getFile", {"file_id": file_id})
        file_path = file_info["file_path"]
        url = f"{self.file_base_url}/{file_path}"
        assert self._session is not None
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(65536):
                    f.write(chunk)
        return dest_path


# ==========================================================
# Initialize Clients
# ==========================================================
bot_api = TelegramBotAPI(config.BOT_TOKEN)

user = Client(
    name="MusicAssistantUser",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.STRING_SESSION if config.STRING_SESSION else None,
    in_memory=True,
)

pytgcalls = PyTgCalls(user)

# ==========================================================
# In-Memory Queue & State System
# ==========================================================
QUEUES: Dict[int, List[dict]] = {}
CURRENT_PLAYING: Dict[int, dict] = {}
PAUSED_CHATS: set[int] = set()
ASSISTANT_USERNAME: str = "mariomusicAssistant"
DOWNLOAD_DIR = "/tmp/musicbot_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YTDL_BASE_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
}


# ==========================================================
# Formatting & Extraction Helpers
# ==========================================================
def esc(text: Any) -> str:
    return html.escape(str(text or ""))


def user_mention_html(from_user: Optional[Dict[str, Any]]) -> str:
    if not from_user:
        return "Member"
    uid = from_user.get("id")
    name = esc(from_user.get("first_name") or from_user.get("username") or "User")
    if uid:
        return f'<a href="tg://user?id={uid}">{name}</a>'
    return name


def format_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "Live / Stream"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def build_control_buttons(chat_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "⏸ Pause", "callback_data": f"pause|{chat_id}"},
                {"text": "▶️ Resume", "callback_data": f"resume|{chat_id}"},
            ],
            [
                {"text": "⏭ Skip", "callback_data": f"skip|{chat_id}"},
                {"text": "⏹ Stop", "callback_data": f"stop|{chat_id}"},
            ],
        ]
    }


def _pick_stream_url(info: dict) -> Optional[str]:
    if info.get("url"):
        return info["url"]
    formats = info.get("formats") or []
    audio_formats = [
        f
        for f in formats
        if f.get("url")
        and f.get("acodec") not in (None, "none")
        and not f.get("has_drm")
    ]
    if audio_formats:
        return audio_formats[-1]["url"]
    any_formats = [f for f in formats if f.get("url") and not f.get("has_drm")]
    if any_formats:
        return any_formats[-1]["url"]
    return None


def _build_track_dict(info: dict, fallback_link: str) -> Optional[dict]:
    stream_url = _pick_stream_url(info)
    if not stream_url:
        return None
    return {
        "title": (info.get("title") or "Unknown Track").strip(),
        "duration": format_duration(info.get("duration")),
        "duration_sec": int(info.get("duration") or 0),
        "link": info.get("webpage_url") or fallback_link,
        "stream_url": stream_url,
        "thumbnail": info.get("thumbnail") or "",
        "channel": info.get("uploader") or "Music Stream",
    }


def _fetch_youtube_oembed_title(url: str) -> Optional[str]:
    try:
        endpoint = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")
        req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            title = data.get("title")
            author = data.get("author_name")
            if title and author and author.lower() not in title.lower():
                return f"{title} {author}"
            return title
    except Exception:
        return None


async def search_ytdl(query: str) -> Optional[dict]:
    """
    Search YouTube first, and automatically fall back to SoundCloud full-length
    non-DRM audio streams if YouTube blocks datacenter IPs.
    """
    loop = asyncio.get_running_loop()

    def _extract() -> Optional[dict]:
        is_url = query.startswith("http://") or query.startswith("https://")
        fallback_search_term = query

        # 1. Try direct URL or YouTube search first
        try:
            with yt_dlp.YoutubeDL(YTDL_BASE_OPTIONS) as ytdl:
                target = query if is_url else f"ytsearch1:{query}"
                info = ytdl.extract_info(target, download=False)
                if info and "entries" in info:
                    entries = [e for e in (info["entries"] or []) if e]
                    info = entries[0] if entries else None
                if info:
                    track = _build_track_dict(info, query)
                    if track:
                        return track
        except Exception as yt_err:
            logger.warning(f"Primary extractor notice ({query}): {yt_err}")
            if is_url and ("youtube.com" in query or "youtu.be" in query):
                resolved_title = _fetch_youtube_oembed_title(query)
                if resolved_title:
                    fallback_search_term = resolved_title
                else:
                    return None
            elif is_url:
                return None

        # 2. Automatic SoundCloud full-track non-DRM fallback
        sc_opts = {**YTDL_BASE_OPTIONS, "ignoreerrors": True}
        try:
            with yt_dlp.YoutubeDL(sc_opts) as sc_ytdl:
                sc_info = sc_ytdl.extract_info(f"scsearch5:{fallback_search_term}", download=False)
                raw_entries = (sc_info or {}).get("entries") or []
                valid_tracks = []
                for entry in raw_entries:
                    if not entry:
                        continue
                    built = _build_track_dict(entry, entry.get("webpage_url") or "https://soundcloud.com")
                    if built:
                        valid_tracks.append(built)

                if valid_tracks:
                    full_tracks = [t for t in valid_tracks if t["duration_sec"] > 45]
                    return full_tracks[0] if full_tracks else valid_tracks[0]
        except Exception as sc_err:
            logger.error(f"Fallback SoundCloud extraction error: {sc_err}")

        return None

    return await loop.run_in_executor(None, _extract)


# ==========================================================
# Bulletproof Assistant Auto-Join & Peer Resolution
# ==========================================================
async def ensure_assistant_joined(chat_id: int) -> Tuple[bool, str]:
    """
    Ensure the Assistant Userbot is an active member of `chat_id`
    and has `chat_id` cached in `user`'s peer storage so PyTgCalls can join immediately.
    """
    global ASSISTANT_USERNAME
    assistant_username = ASSISTANT_USERNAME
    try:
        assistant_user = await user.get_me()
        assistant_id = assistant_user.id
        if assistant_user.username:
            assistant_username = assistant_user.username
            ASSISTANT_USERNAME = assistant_username

        # 1. Fast path: check if `user` itself already knows `chat_id` and is inside
        try:
            me_member = await user.get_chat_member(chat_id, "me")
            if me_member.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                await user.resolve_peer(chat_id)
                return True, ""
        except (UserNotParticipant, PeerIdInvalid, ValueError, KeyError):
            pass
        except Exception as self_err:
            logger.debug(f"Assistant self-check in {chat_id}: {self_err}")

        # 2. Check via HTTP Bot API if Assistant is banned/kicked or already in the group
        try:
            member_info = await bot_api.get_chat_member(chat_id, assistant_id)
            status = member_info.get("status", "")
            if status == "kicked":
                logger.info(f"Assistant @{assistant_username} was banned in {chat_id}; auto-unbanning via Bot...")
                try:
                    await bot_api.unban_chat_member(chat_id, assistant_id)
                    await asyncio.sleep(0.5)
                except Exception as unban_err:
                    return (
                        False,
                        f"❌ <b>Assistant အကောင့် Ban ခံထားရပါသည်!</b>\n\n"
                        f"ကျေးဇူးပြု၍ <code>@{esc(assistant_username)}</code> ကို Group ၏ Removed/Banned စာရင်းမှ Unban လုပ်ပေးပါ။\n"
                        f"<i>({esc(unban_err)})</i>",
                    )
            elif status in ("creator", "administrator", "member") or (
                status == "restricted" and member_info.get("is_member", False)
            ):
                # Assistant is already in the group; make sure `user` peer cache knows `chat_id`
                try:
                    await user.resolve_peer(chat_id)
                    return True, ""
                except Exception:
                    async for _ in user.get_dialogs(limit=250):
                        pass
                    try:
                        await user.resolve_peer(chat_id)
                        return True, ""
                    except Exception:
                        pass  # Fall through to join via link/username to populate peer cache
        except Exception as chk_err:
            logger.debug(f"Bot API getChatMember check in {chat_id}: {chk_err}")

        # 3. Join via public username or fresh Bot API invite link
        chat_info = await bot_api.get_chat(chat_id)
        joined = False
        chat_username = chat_info.get("username")

        if chat_username:
            try:
                await user.join_chat(chat_username)
                joined = True
                logger.info(f"Assistant @{assistant_username} joined @{chat_username} ({chat_id}) via username!")
            except UserAlreadyParticipant:
                joined = True
            except InviteRequestSent:
                await bot_api.approve_chat_join_request(chat_id, assistant_id)
                await asyncio.sleep(1.0)
                joined = True
            except Exception as u_err:
                logger.warning(f"Username join fallback in {chat_id}: {u_err}")

        if not joined:
            invite_link: Optional[str] = None
            try:
                invite_link = await bot_api.create_chat_invite_link(chat_id)
            except Exception as create_err:
                logger.debug(f"createChatInviteLink fallback in {chat_id}: {create_err}")

            if not invite_link:
                try:
                    invite_link = await bot_api.export_chat_invite_link(chat_id)
                except Exception as export_err:
                    logger.debug(f"exportChatInviteLink fallback in {chat_id}: {export_err}")
                    invite_link = chat_info.get("invite_link")

            if not invite_link:
                raise RuntimeError("Bot သည် Invite Link ထုတ်ယူ၍မရပါ (Invite Users via Link permission စစ်ဆေးပါ)")

            invite_link = invite_link.replace("https://telegram.me/", "https://t.me/")
            logger.info(f"Joining Assistant @{assistant_username} into {chat_id} via invite link...")

            try:
                await user.join_chat(invite_link)
                joined = True
                logger.info(f"Assistant @{assistant_username} auto-joined chat {chat_id} successfully! ✅")
            except UserAlreadyParticipant:
                joined = True
                logger.info(f"Assistant @{assistant_username} is already a participant in {chat_id}")
            except InviteRequestSent:
                logger.info(f"Approving Assistant join request in {chat_id}...")
                await bot_api.approve_chat_join_request(chat_id, assistant_id)
                await asyncio.sleep(1.0)
                joined = True
            except FloodWait as fw:
                if fw.value <= 20:
                    await asyncio.sleep(fw.value + 1)
                    await user.join_chat(invite_link)
                    joined = True
                else:
                    raise

        # 4. Final guarantee that `user` peer storage resolves `chat_id` cleanly
        try:
            await user.resolve_peer(chat_id)
        except Exception:
            async for _ in user.get_dialogs(limit=250):
                pass
            await user.resolve_peer(chat_id)

        return True, ""

    except Exception as e:
        logger.error(f"Failed to join assistant to chat {chat_id}: [{type(e).__name__}] {e}")
        return (
            False,
            f"⚠️ <b>Assistant အကောင့် Group ထဲသို့ အလိုအလျောက် ဝင်မရပါ</b>\n\n"
            f"၁။ Bot ကို <b>Invite Users via Link</b> Admin permission ပေးထားကြောင်း စစ်ဆေးပါ (သို့မဟုတ်)\n"
            f"၂။ အကူအညီအကောင့် <code>@{esc(assistant_username)}</code> ကို Group ထဲသို့ တိုက်ရိုက် Add ပေးပါ။\n"
            f"<i>(အသေးစိတ်: <code>{esc(type(e).__name__)}: {esc(e)}</code>)</i>",
        )


# ==========================================================
# Queue & Playback Transitions
# ==========================================================
async def play_next_track(chat_id: int):
    """Play the next track from the queue or leave the voice chat."""
    old = CURRENT_PLAYING.get(chat_id)
    if old and old.get("local_file") and os.path.exists(old["local_file"]):
        try:
            os.remove(old["local_file"])
        except Exception:
            pass

    if chat_id in QUEUES and len(QUEUES[chat_id]) > 0:
        next_track = QUEUES[chat_id].pop(0)
        CURRENT_PLAYING[chat_id] = next_track
        PAUSED_CHATS.discard(chat_id)

        try:
            await pytgcalls.change_stream(
                chat_id,
                AudioPiped(next_track["stream_url"]),
            )

            caption = (
                f"🎶 <b>Now Playing Next Track</b>\n\n"
                f"🏷 <b>Title:</b> <a href=\"{esc(next_track['link'])}\">{esc(next_track['title'])}</a>\n"
                f"⏱ <b>Duration:</b> <code>{esc(next_track['duration'])}</code>\n"
                f"👤 <b>Requested by:</b> {next_track['req_by']}\n\n"
                f"⚡ <i>Use /pause, /resume, /skip, or /stop to control.</i>"
            )
            buttons = build_control_buttons(chat_id)

            if next_track.get("thumbnail"):
                try:
                    await bot_api.send_photo(
                        chat_id,
                        photo=next_track["thumbnail"],
                        caption=caption,
                        reply_markup=buttons,
                    )
                    return
                except Exception:
                    pass

            await bot_api.send_message(
                chat_id,
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error while playing next track in {chat_id}: {e}")
            await play_next_track(chat_id)
    else:
        CURRENT_PLAYING.pop(chat_id, None)
        QUEUES.pop(chat_id, None)
        PAUSED_CHATS.discard(chat_id)
        try:
            await pytgcalls.leave_group_call(chat_id)
            await bot_api.send_message(
                chat_id,
                "✨ <b>Queue ပြီးဆုံးသွားပါပြီ။</b> Assistant သည် Voice Chat မှ ထွက်ခွာသွားပါပြီ။",
            )
        except Exception:
            pass


@pytgcalls.on_stream_end()
async def stream_end_handler(_, update: StreamAudioEnded):
    chat_id = update.chat_id
    logger.info(f"Stream ended in chat: {chat_id}. Playing next track...")
    await play_next_track(chat_id)


@pytgcalls.on_closed_voice_chat()
async def closed_voice_chat_handler(_, chat_id: int):
    logger.info(f"Voice chat closed in {chat_id}")
    QUEUES.pop(chat_id, None)
    CURRENT_PLAYING.pop(chat_id, None)
    PAUSED_CHATS.discard(chat_id)


# ==========================================================
# Command & Callback Handlers
# ==========================================================
def parse_command(msg: Dict[str, Any], bot_username: str) -> Tuple[Optional[str], str]:
    raw_text = (msg.get("text") or msg.get("caption") or "").strip()
    if not raw_text:
        return None, ""
    prefix_matched = None
    for p in config.COMMAND_PREFIXES:
        if raw_text.startswith(p):
            prefix_matched = p
            break
    if not prefix_matched:
        return None, ""

    without_prefix = raw_text[len(prefix_matched) :].strip()
    if not without_prefix:
        return None, ""

    parts = without_prefix.split(maxsplit=1)
    cmd_token = parts[0]
    args = parts[1].strip() if len(parts) > 1 else ""

    if "@" in cmd_token:
        cmd_name, target_bot = cmd_token.split("@", 1)
        if bot_username and target_bot.lower() != bot_username.lower():
            return None, ""
    else:
        cmd_name = cmd_token

    return cmd_name.lower(), args


async def handle_start(msg: Dict[str, Any], chat_id: int, chat_type: str, bot_username: str):
    from_user = msg.get("from") or {}
    user_name = esc(from_user.get("first_name") or "Friend")
    msg_id = msg.get("message_id")
    logger.info(f"Received /start from {from_user.get('first_name')} in chat {chat_id} ({chat_type})")

    if chat_type == "private":
        text = (
            f"👋 <b>မင်္ဂလာပါ {user_name}!</b>\n\n"
            f"🎵 ကျွန်ုပ်သည် <b>@{esc(bot_username)}</b> — Telegram Group Voice Chat သီချင်းဖွင့် Bot ဖြစ်ပါသည်။\n\n"
            f"🇲🇲 <b>အသုံးပြုနည်း လမ်းညွှန်:</b>\n"
            f"၁။ ကျွန်ုပ် (<code>@{esc(bot_username)}</code>) ကို သင့် Telegram Group ထဲသို့ Add ပြီး <b>Admin</b> ပေးပါ။\n"
            f"၂။ Group ထဲတွင် <b>Voice Chat (Video Chat)</b> ကို စတင်ဖွင့်ထားပါ။\n"
            f"၃။ Group ထဲတွင် <code>/play &lt;သီချင်းအမည်&gt;</code> (ဥပမာ <code>/play နင်စေရင်</code> သို့မဟုတ် <code>/play လွမ်း</code>) ဟု ရိုက်ပို့ပါ!\n\n"
            f"✅ Assistant အကောင့် <code>@{esc(ASSISTANT_USERNAME)}</code> အလိုအလျောက် ချိတ်ဆက်ပြီး ဖြစ်ပါသည်။"
        )
        buttons = {
            "inline_keyboard": [
                [
                    {
                        "text": "➕ Group ထဲသို့ ထည့်ရန် (Add To Group) ➕",
                        "url": f"https://t.me/{bot_username}?startgroup=true",
                    }
                ],
                [{"text": "📖 Commands လမ်းညွှန်", "callback_data": "help_menu"}],
            ]
        }
    else:
        text = (
            f"🎶 <b>@{esc(bot_username)} အသင့်အလုပ်လုပ်နေပါသည်!</b>\n\n"
            f"သီချင်းဖွင့်ရန် <code>/play &lt;သီချင်းအမည် သို့မဟုတ် Link&gt;</code> ဟု ရိုက်ပို့ပါ "
            f"(သို့မဟုတ် MP3 ဖိုင်ကို Reply ပြန်၍ <code>/play</code> ရိုက်ပါ)။"
        )
        buttons = {"inline_keyboard": [[{"text": "📖 Commands လမ်းညွှန်", "callback_data": "help_menu"}]]}

    await bot_api.send_message(chat_id, text, reply_to_message_id=msg_id, reply_markup=buttons)


async def handle_ping(msg: Dict[str, Any], chat_id: int):
    t0 = time.perf_counter()
    sent = await bot_api.send_message(chat_id, "🏓 <b>Pinging...</b>", reply_to_message_id=msg.get("message_id"))
    latency_ms = (time.perf_counter() - t0) * 1000
    asst_status = "Connected ✅" if user.is_connected else "Disconnected ❌"
    await bot_api.edit_message_text(
        chat_id,
        sent["message_id"],
        f"🏓 <b>Pong!</b> <code>{latency_ms:.0f} ms</code>\n"
        f"🤖 <b>Bot:</b> Online ✅\n"
        f"🎙 <b>Voice Assistant:</b> {asst_status}\n"
        f"🎶 <b>Active Streams:</b> <code>{len(CURRENT_PLAYING)}</code>",
    )


def get_help_html() -> str:
    return (
        f"🎧 <b>{esc(config.BOT_NAME)} — Commands လမ်းညွှန်:</b>\n\n"
        f"▶️ <code>/play &lt;သီချင်းအမည် သို့မဟုတ် Link&gt;</code> - Voice Chat တွင် သီချင်းဖွင့်ရန် / Queue ထည့်ရန်\n"
        f"🎵 <code>/play</code> <i>(Audio/MP3 ကို Reply ပြန်၍)</i> - Telegram MP3/Voice ဖိုင်ကို တိုက်ရိုက်ဖွင့်ရန်\n"
        f"⏸ <code>/pause</code> - ဖွင့်နေသော သီချင်းကို ခေတ္တရပ်ရန်\n"
        f"▶️ <code>/resume</code> - ရပ်ထားသော သီချင်းကို ပြန်ဖွင့်ရန်\n"
        f"⏭ <code>/skip</code> - နောက်တစ်ပုဒ် ကျော်ရန်\n"
        f"⏹ <code>/stop</code> သို့ <code>/end</code> - သီချင်းရပ်ပြီး Voice Chat မှ ထွက်ရန်\n"
        f"📜 <code>/queue</code> - တန်းစီထားသော သီချင်းစာရင်း ကြည့်ရန်\n"
        f"🏓 <code>/ping</code> - Bot အခြေအနေ စစ်ဆေးရန်"
    )


async def handle_play_private(msg: Dict[str, Any], chat_id: int, bot_username: str):
    buttons = {
        "inline_keyboard": [
            [
                {
                    "text": "➕ Group ထဲသို့ ထည့်ရန် (Add To Group) ➕",
                    "url": f"https://t.me/{bot_username}?startgroup=true",
                }
            ]
        ]
    }
    await bot_api.send_message(
        chat_id,
        f"ℹ️ <b><code>/play</code> ကို Telegram Group ထဲတွင်သာ အသုံးပြုနိုင်ပါသည်!</b>\n\n"
        f"၁။ <code>@{esc(bot_username)}</code> ကို သင့် Group ထဲသို့ Add ပြီး <b>Admin</b> ပေးပါ။\n"
        f"၂။ Group တွင် <b>Voice Chat</b> ဖွင့်ပါ။\n"
        f"၃။ Group ထဲ၌ <code>/play &lt;သီချင်းအမည်&gt;</code> ဟု ရိုက်ပို့ပါ!",
        reply_to_message_id=msg.get("message_id"),
        reply_markup=buttons,
    )


async def handle_play_group(msg: Dict[str, Any], chat_id: int, args: str):
    msg_id = msg.get("message_id")
    logger.info(f"Received /play in group {chat_id}: args='{args}'")

    if not config.STRING_SESSION or not user.is_connected:
        await bot_api.send_message(
            chat_id,
            "⚠️ <b>Assistant Account မချိတ်ဆက်ရသေးပါ!</b>\n"
            "Dashboard တွင် Assistant အကောင့် ချိတ်ဆက်မှုကို စစ်ဆေးပေးပါ။",
            reply_to_message_id=msg_id,
        )
        return

    replied = msg.get("reply_to_message") or {}
    replied_media = replied.get("audio") or replied.get("voice") or replied.get("video")
    own_media = msg.get("audio") or msg.get("voice") or msg.get("video")
    media_target = replied_media or own_media
    media_msg = replied if replied_media else msg

    if not args and not media_target:
        await bot_api.send_message(
            chat_id,
            "⚠️ <b>သီချင်းအမည် သို့မဟုတ် Link ထည့်ပေးပါ!</b>\n"
            "ဥပမာ - <code>/play နင်စေရင်</code> သို့မဟုတ် <code>/play လွမ်း</code>\n"
            "<i>(Telegram MP3/Audio ဖိုင်ကိုလည်း Reply ပြန်၍ <code>/play</code> ရိုက်နိုင်ပါသည်)</i>",
            reply_to_message_id=msg_id,
        )
        return

    status_msg = await bot_api.send_message(
        chat_id,
        "🔍 <b>သီချင်းရှာဖွေ၍ အသံလိုင်း ချိတ်ဆက်နေပါသည်...</b>",
        reply_to_message_id=msg_id,
    )
    status_mid = status_msg["message_id"]

    # Ensure Assistant Userbot is inside the group and peer-cached
    ok, err_html = await ensure_assistant_joined(chat_id)
    if not ok:
        await bot_api.edit_message_text(chat_id, status_mid, err_html)
        return

    from_user = msg.get("from") or {}
    requester_name = user_mention_html(from_user)
    requester_id = from_user.get("id") or 0

    track: Optional[dict] = None
    if media_target and not args:
        try:
            await bot_api.edit_message_text(
                chat_id, status_mid, "📥 <b>Telegram Audio ဖိုင်ကို ဒေါင်းလုဒ်ဆွဲနေပါသည်...</b>"
            )
            ext = ".mp3"
            if media_target.get("file_name"):
                _, parsed_ext = os.path.splitext(media_target["file_name"])
                if parsed_ext:
                    ext = parsed_ext
            dest_path = os.path.join(DOWNLOAD_DIR, f"tg_{chat_id}_{media_msg.get('message_id', int(time.time()))}{ext}")

            file_size = media_target.get("file_size") or 0
            if file_size > 19 * 1024 * 1024:
                # Large file >19MB: download directly via Pyrogram Assistant Userbot
                pyro_msg = await user.get_messages(chat_id, media_msg["message_id"])
                file_path = await pyro_msg.download(file_name=dest_path)
            else:
                file_path = await bot_api.download_file(media_target["file_id"], dest_path)

            raw_title = media_target.get("title") or media_target.get("file_name") or "Telegram Audio"
            dur_sec = int(media_target.get("duration") or 0)
            track = {
                "title": raw_title,
                "duration": format_duration(dur_sec),
                "duration_sec": dur_sec,
                "link": "https://t.me",
                "stream_url": file_path,
                "local_file": file_path,
                "thumbnail": "",
                "req_by": requester_name,
                "req_id": requester_id,
            }
        except Exception as dl_err:
            logger.error(f"Telegram media download failed: {dl_err}")
            await bot_api.edit_message_text(
                chat_id, status_mid, f"❌ <b>Audio ဒေါင်းလုဒ်မရပါ:</b> <code>{esc(dl_err)}</code>"
            )
            return
    else:
        track = await search_ytdl(args)
        if not track or not track.get("stream_url"):
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                "❌ <b>သီချင်းရှာမတွေ့ပါ (သို့) ဆွဲထုတ်၍မရပါ!</b>\n"
                "အခြား သီချင်းအမည်တစ်ခုဖြင့် ထပ်မံစမ်းကြည့်ပါ (သို့မဟုတ် MP3 ဖိုင်ကို Reply ပြန်၍ <code>/play</code> ပို့ပါ)။",
            )
            return
        track["req_by"] = requester_name
        track["req_id"] = requester_id

    if chat_id not in QUEUES:
        QUEUES[chat_id] = []

    is_active = False
    try:
        active_call = [call for call in pytgcalls.active_calls if call.chat_id == chat_id]
        is_active = len(active_call) > 0
    except Exception:
        is_active = chat_id in CURRENT_PLAYING

    if is_active:
        QUEUES[chat_id].append(track)
        pos = len(QUEUES[chat_id])
        queue_text = (
            f"📌 <b>Queue စာရင်းထဲ ထည့်သွင်းပြီးပါပြီ (#{pos})</b>\n\n"
            f"🏷 <b>Title:</b> <a href=\"{esc(track['link'])}\">{esc(track['title'])}</a>\n"
            f"⏱ <b>Duration:</b> <code>{esc(track['duration'])}</code>\n"
            f"👤 <b>Requested by:</b> {requester_name}"
        )
        await bot_api.delete_message(chat_id, status_mid)
        if track.get("thumbnail"):
            try:
                await bot_api.send_photo(
                    chat_id,
                    photo=track["thumbnail"],
                    caption=queue_text,
                    reply_to_message_id=msg_id,
                )
                return
            except Exception:
                pass
        await bot_api.send_message(chat_id, queue_text, reply_to_message_id=msg_id)
        return

    # Start Playing Immediately in Group Voice Chat
    try:
        CURRENT_PLAYING[chat_id] = track
        PAUSED_CHATS.discard(chat_id)

        try:
            await pytgcalls.join_group_call(
                chat_id,
                AudioPiped(track["stream_url"]),
            )
        except AlreadyJoinedError:
            await pytgcalls.change_stream(
                chat_id,
                AudioPiped(track["stream_url"]),
            )

        await bot_api.delete_message(chat_id, status_mid)
        logger.info(f"Started streaming '{track['title']}' in chat {chat_id} ✅")

        caption = (
            f"🎶 <b>Now Playing in Voice Chat</b>\n\n"
            f"🏷 <b>Title:</b> <a href=\"{esc(track['link'])}\">{esc(track['title'])}</a>\n"
            f"⏱ <b>Duration:</b> <code>{esc(track['duration'])}</code>\n"
            f"👤 <b>Requested by:</b> {requester_name}"
        )
        buttons = build_control_buttons(chat_id)

        if track.get("thumbnail"):
            try:
                await bot_api.send_photo(
                    chat_id,
                    photo=track["thumbnail"],
                    caption=caption,
                    reply_to_message_id=msg_id,
                    reply_markup=buttons,
                )
                return
            except Exception:
                pass

        await bot_api.send_message(
            chat_id,
            caption,
            reply_to_message_id=msg_id,
            reply_markup=buttons,
        )

    except (NoActiveGroupCall, GroupCallNotFound):
        CURRENT_PLAYING.pop(chat_id, None)
        await bot_api.edit_message_text(
            chat_id,
            status_mid,
            "❌ <b>Group ထဲတွင် Voice Chat မဖွင့်ရသေးပါ!</b>\n\n"
            "ကျေးဇူးပြု၍ Group တွင် <b>Voice Chat (Video Chat)</b> အရင်ဖွင့်ပြီးမှ <code>/play</code> ပြန်ရိုက်ပေးပါ။",
        )
    except Exception as e:
        logger.error(f"Playback initiation error in {chat_id}: [{type(e).__name__}] {e}")
        CURRENT_PLAYING.pop(chat_id, None)
        if "GROUPCALL_FORBIDDEN" in str(e).upper() or "CALL_PROTOCOL" in str(e).upper():
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                "❌ <b>Group ထဲတွင် Voice Chat မဖွင့်ရသေးပါ (သို့) အသံပိတ်ထားပါသည်!</b>\n"
                f"Group တွင် Voice Chat ဖွင့်ထားကြောင်းနှင့် <code>@{esc(ASSISTANT_USERNAME)}</code> စကားပြောခွင့် (Speak permission) ရထားကြောင်း စစ်ဆေးပေးပါ။",
            )
        else:
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                f"❌ <b>Playback Error:</b> <code>{esc(type(e).__name__)}: {esc(e)}</code>",
            )


async def handle_message_update(msg: Dict[str, Any], bot_username: str):
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    if not chat_id:
        return

    cmd, args = parse_command(msg, bot_username)
    if not cmd:
        return

    is_group = chat_type in ("group", "supergroup")
    msg_id = msg.get("message_id")

    if cmd == "start":
        await handle_start(msg, chat_id, chat_type, bot_username)
    elif cmd in ("ping", "alive"):
        await handle_ping(msg, chat_id)
    elif cmd == "help":
        await bot_api.send_message(chat_id, get_help_html(), reply_to_message_id=msg_id)
    elif cmd in ("play", "p"):
        if is_group:
            await handle_play_group(msg, chat_id, args)
        else:
            await handle_play_private(msg, chat_id, bot_username)
    elif cmd == "pause" and is_group:
        if chat_id in PAUSED_CHATS:
            await bot_api.send_message(
                chat_id,
                "⏸ သီချင်း ခေတ္တရပ်ထားပြီးသား ဖြစ်ပါသည်။ ပြန်ဖွင့်ရန် <code>/resume</code> ရိုက်ပါ။",
                reply_to_message_id=msg_id,
            )
            return
        try:
            await pytgcalls.pause_stream(chat_id)
            PAUSED_CHATS.add(chat_id)
            await bot_api.send_message(
                chat_id,
                "⏸ <b>သီချင်း ခေတ္တရပ်လိုက်ပါပြီ။</b> ပြန်ဖွင့်ရန် <code>/resume</code> ရိုက်ပါ။",
                reply_to_message_id=msg_id,
            )
        except Exception as e:
            await bot_api.send_message(chat_id, f"❌ Error pausing stream: <code>{esc(e)}</code>", reply_to_message_id=msg_id)
    elif cmd == "resume" and is_group:
        if chat_id not in PAUSED_CHATS:
            await bot_api.send_message(chat_id, "▶️ လက်ရှိ သီချင်း ရပ်မထားပါ။", reply_to_message_id=msg_id)
            return
        try:
            await pytgcalls.resume_stream(chat_id)
            PAUSED_CHATS.discard(chat_id)
            await bot_api.send_message(
                chat_id, "▶️ <b>သီချင်း ပြန်လည်ဖွင့်ပေးနေပါပြီ။</b>", reply_to_message_id=msg_id
            )
        except Exception as e:
            await bot_api.send_message(chat_id, f"❌ Error resuming stream: <code>{esc(e)}</code>", reply_to_message_id=msg_id)
    elif cmd in ("skip", "next") and is_group:
        if chat_id not in CURRENT_PLAYING:
            await bot_api.send_message(chat_id, "⚠️ လက်ရှိ ဖွင့်နေသော သီချင်း မရှိပါ။", reply_to_message_id=msg_id)
            return
        await bot_api.send_message(chat_id, "⏭ <b>နောက်တစ်ပုဒ်သို့ ကျော်နေပါသည်...</b>", reply_to_message_id=msg_id)
        await play_next_track(chat_id)
    elif cmd in ("stop", "end") and is_group:
        old = CURRENT_PLAYING.pop(chat_id, None)
        if old and old.get("local_file") and os.path.exists(old["local_file"]):
            try:
                os.remove(old["local_file"])
            except Exception:
                pass
        QUEUES.pop(chat_id, None)
        PAUSED_CHATS.discard(chat_id)
        try:
            await pytgcalls.leave_group_call(chat_id)
            await bot_api.send_message(
                chat_id,
                "⏹ <b>သီချင်းရပ်၍ Queue ရှင်းလင်းပြီး Voice Chat မှ ထွက်လိုက်ပါပြီ။</b>",
                reply_to_message_id=msg_id,
            )
        except (GroupCallNotFound, NotInGroupCallError):
            await bot_api.send_message(chat_id, "⏹ Bot သည် Voice Chat ထဲတွင် မရှိပါ။", reply_to_message_id=msg_id)
        except Exception as e:
            await bot_api.send_message(chat_id, f"⏹ Left voice chat. (<code>{esc(e)}</code>)", reply_to_message_id=msg_id)
    elif cmd in ("queue", "q") and is_group:
        current = CURRENT_PLAYING.get(chat_id)
        chat_queue = QUEUES.get(chat_id, [])
        if not current and not chat_queue:
            await bot_api.send_message(
                chat_id, "📭 <b>လက်ရှိ Queue စာရင်း အလွတ်ဖြစ်နေပါသည်။</b>", reply_to_message_id=msg_id
            )
            return
        text = "📜 <b>လက်ရှိ သီချင်းစာရင်း (Music Queue):</b>\n\n"
        if current:
            text += (
                f"▶️ <b>Now Playing:</b>\n"
                f"└ <a href=\"{esc(current['link'])}\">{esc(current['title'])}</a> | "
                f"<code>{esc(current['duration'])}</code> | {current['req_by']}\n\n"
            )
        if chat_queue:
            text += "📋 <b>Up Next:</b>\n"
            for idx, song in enumerate(chat_queue[:10], 1):
                text += (
                    f"<code>{idx}.</code> <a href=\"{esc(song['link'])}\">{esc(song['title'])}</a> | "
                    f"<code>{esc(song['duration'])}</code> | {song['req_by']}\n"
                )
            if len(chat_queue) > 10:
                text += f"\n<i>...နောက်ထပ် {len(chat_queue) - 10} ပုဒ် ကျန်ရှိပါသေးသည်။</i>"
        else:
            text += "<i>နောက်ထပ် တန်းစီထားသော သီချင်းမရှိသေးပါ။ <code>/play</code> ဖြင့် ထပ်ထည့်နိုင်ပါသည်!</i>"
        await bot_api.send_message(chat_id, text, reply_to_message_id=msg_id)


async def handle_callback_update(cb: Dict[str, Any]):
    cb_id = cb.get("id", "")
    data = cb.get("data") or ""
    msg = cb.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    msg_id = msg.get("message_id")

    if data == "help_menu":
        await bot_api.answer_callback_query(cb_id)
        if chat_id and msg_id:
            await bot_api.edit_message_text(chat_id, msg_id, get_help_html())
        return

    sep = "|" if "|" in data else "_"
    parts = data.split(sep, 1)
    if len(parts) != 2:
        await bot_api.answer_callback_query(cb_id)
        return

    action, raw_chat = parts
    try:
        target_chat = int(raw_chat)
    except ValueError:
        await bot_api.answer_callback_query(cb_id)
        return

    actor = user_mention_html(cb.get("from"))

    if action == "pause":
        if target_chat in PAUSED_CHATS:
            await bot_api.answer_callback_query(cb_id, "သီချင်း ခေတ္တရပ်ထားပြီးသား ဖြစ်ပါသည်!", show_alert=True)
            return
        try:
            await pytgcalls.pause_stream(target_chat)
            PAUSED_CHATS.add(target_chat)
            await bot_api.answer_callback_query(cb_id, "Paused!")
            await bot_api.send_message(target_chat, f"⏸ {actor} မှ သီချင်း ခေတ္တရပ်လိုက်ပါသည်။")
        except Exception as e:
            await bot_api.answer_callback_query(cb_id, f"Error: {e}", show_alert=True)

    elif action == "resume":
        if target_chat not in PAUSED_CHATS:
            await bot_api.answer_callback_query(cb_id, "သီချင်း ပွင့်နေပြီးသား ဖြစ်ပါသည်!", show_alert=True)
            return
        try:
            await pytgcalls.resume_stream(target_chat)
            PAUSED_CHATS.discard(target_chat)
            await bot_api.answer_callback_query(cb_id, "Resumed!")
            await bot_api.send_message(target_chat, f"▶️ {actor} မှ သီချင်း ပြန်ဖွင့်လိုက်ပါသည်။")
        except Exception as e:
            await bot_api.answer_callback_query(cb_id, f"Error: {e}", show_alert=True)

    elif action == "skip":
        await bot_api.answer_callback_query(cb_id, "Skipping track...")
        await bot_api.send_message(target_chat, f"⏭ {actor} မှ နောက်တစ်ပုဒ် ကျော်လိုက်ပါသည်။")
        await play_next_track(target_chat)

    elif action == "stop":
        old = CURRENT_PLAYING.pop(target_chat, None)
        if old and old.get("local_file") and os.path.exists(old["local_file"]):
            try:
                os.remove(old["local_file"])
            except Exception:
                pass
        QUEUES.pop(target_chat, None)
        PAUSED_CHATS.discard(target_chat)
        try:
            await pytgcalls.leave_group_call(target_chat)
        except Exception:
            pass
        await bot_api.answer_callback_query(cb_id, "Stopped!")
        await bot_api.send_message(target_chat, f"⏹ {actor} မှ သီချင်းရပ်လိုက်ပါသည်။")


async def handle_my_chat_member_update(upd: Dict[str, Any]):
    """Automatically invite Assistant into any group the moment Bot is promoted to Admin."""
    try:
        new_member = upd.get("new_chat_member") or {}
        chat = upd.get("chat") or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        if chat_id and chat_type in ("group", "supergroup") and new_member.get("status") == "administrator":
            if user.is_connected:
                logger.info(f"Bot promoted to Admin in {chat_id} ({chat.get('title')}); auto-joining Assistant...")
                await ensure_assistant_joined(chat_id)
    except Exception as e:
        logger.debug(f"my_chat_member auto-join notice: {e}")


# ==========================================================
# Long-Polling Loop
# ==========================================================
async def poll_bot_updates(bot_username: str, stop_event: asyncio.Event):
    offset: Optional[int] = None
    # Advance offset past historical stale updates before entering live loop
    try:
        await bot_api.call("deleteWebhook", {"drop_pending_updates": False})
        initial = await bot_api.call("getUpdates", {"offset": -1, "timeout": 0}, timeout_sec=10)
        if initial:
            offset = initial[-1]["update_id"] + 1
    except Exception as init_err:
        logger.warning(f"Initial update sync notice: {init_err}")

    logger.info(f"Started real-time Bot API update polling for @{bot_username} (offset={offset})")

    while not stop_event.is_set():
        try:
            payload: Dict[str, Any] = {
                "timeout": 25,
                "allowed_updates": ["message", "callback_query", "my_chat_member"],
            }
            if offset is not None:
                payload["offset"] = offset

            updates = await bot_api.call("getUpdates", payload, timeout_sec=35)
            for upd in updates or []:
                offset = upd["update_id"] + 1
                if "message" in upd:
                    asyncio.create_task(handle_message_update(upd["message"], bot_username))
                elif "callback_query" in upd:
                    asyncio.create_task(handle_callback_update(upd["callback_query"]))
                elif "my_chat_member" in upd:
                    asyncio.create_task(handle_my_chat_member_update(upd["my_chat_member"]))
        except asyncio.CancelledError:
            break
        except Exception as poll_err:
            if not stop_event.is_set():
                logger.warning(f"Polling retry in 2s: {poll_err}")
                await asyncio.sleep(2)


# ==========================================================
# Main Async Runner
# ==========================================================
async def main():
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            MAIN_LOOP.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    logger.info("Starting Telegram Music Bot (HTTP Bot API)...")
    bot_me = await bot_api.start()
    bot_username = bot_me.get("username", "marioxnmusic_bot")
    logger.info(f"Bot started successfully as @{bot_username} ({bot_me.get('id')})")

    if config.STRING_SESSION:
        try:
            logger.info("Starting Assistant User Client...")
            await user.start()
            user_me = await user.get_me()
            if user_me.username:
                global ASSISTANT_USERNAME
                ASSISTANT_USERNAME = user_me.username
            logger.info(
                f"Assistant User started as @{user_me.username} ({user_me.id}) [{user_me.first_name or 'Assistant'}]"
            )
            dialog_count = 0
            async for _ in user.get_dialogs(limit=250):
                dialog_count += 1
            logger.info(f"Cached {dialog_count} dialogs in Assistant peer storage.")

            logger.info("Starting PyTgCalls Client...")
            await pytgcalls.start()
            logger.info("PyTgCalls Voice Client started successfully!")

            # Proactively ensure Assistant is inside known active groups right now
            for active_gid in (-1004338179393,):
                try:
                    ok, reason = await ensure_assistant_joined(active_gid)
                    if ok:
                        logger.info(f"Verified Assistant presence in group {active_gid} ✅")
                    else:
                        logger.warning(f"Startup auto-join notice for {active_gid}: {reason}")
                except Exception as gj_err:
                    logger.debug(f"Startup group check skipped for {active_gid}: {gj_err}")
        except Exception as e:
            logger.error(f"Failed to start Userbot / PyTgCalls: {e}")
    else:
        logger.warning("STRING_SESSION not found. PyTgCalls will not start until session is set.")

    logger.info("=" * 60)
    logger.info(f"🚀 {config.BOT_NAME} (@{bot_username}) is fully ACTIVE & READY!")
    logger.info("=" * 60)

    poll_task = asyncio.create_task(poll_bot_updates(bot_username, stop_event))
    await stop_event.wait()

    logger.info("Stopping Bot & Clients gracefully...")
    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass
    try:
        await pytgcalls.stop()
    except Exception:
        pass
    try:
        await user.stop()
    except Exception:
        pass
    await bot_api.close()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        MAIN_LOOP.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot exited.")
