#!/usr/bin/env python3
"""
Production-Ready Telegram Group Music Bot
Hybrid Architecture:
- Bot Control Plane: Async Telegram HTTP Bot API (aiohttp) -> Zero MTProto ImportBotAuthorization FloodWait,
  instantaneous command & callback polling, native 64-bit group/user ID support, multipart generated card upload.
- Custom Artwork Engine: Pillow (PIL) + HarfBuzz/Raqm frosted-glass Apple-Music-style streaming UI generator
  supporting both English & Myanmar Unicode typography.
- Voice Streaming Plane: Pyrogram v2 Userbot + PyTgCalls + yt-dlp (YouTube + SoundCloud full-track fallback).
- Owner-Only Secret Admin Panel: Custom /start photo, customizable welcome header/text, and multi-target broadcast.
"""

import asyncio
import html
import gc
import io
import json
import logging
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Optimize low-memory Linux container allocations (Serverix / Pterodactyl 256MB free tier)
os.environ.setdefault("NODE_OPTIONS", "--max-old-space-size=64")
os.environ.setdefault("UV_THREADPOOL_SIZE", "2")
os.environ.setdefault("MALLOC_ARENA_MAX", "2")


def trim_process_memory() -> None:
    """Aggressively release unused heap pages back to the Linux OS (glibc)."""
    try:
        gc.collect()
        if platform.system() == "Linux":
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


# Ensure an active asyncio event loop exists BEFORE importing Pyrogram & PyTgCalls
# (Prevents RuntimeError on Python 3.11 / 3.12+ containers such as Wispbyte)
try:
    MAIN_LOOP = asyncio.get_running_loop()
except RuntimeError:
    try:
        MAIN_LOOP = asyncio.get_event_loop()
    except RuntimeError:
        MAIN_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(MAIN_LOOP)


def _bootstrap_container_binaries() -> None:
    """Auto-provision Node.js and FFmpeg into .runtime_bin on rootless Free-Tier hosts (e.g. Wispbyte) with minimal RAM."""
    runtime_bin = os.path.join(ROOT_DIR, ".runtime_bin")
    os.makedirs(runtime_bin, exist_ok=True)

    path_parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    if runtime_bin not in path_parts:
        path_parts.insert(0, runtime_bin)
        os.environ["PATH"] = os.pathsep.join(path_parts)

    # Ensure existing cached binaries have executable permissions after ZIP extraction
    for bin_name in ("node", "ffmpeg"):
        cached_bin = os.path.join(runtime_bin, bin_name)
        if os.path.isfile(cached_bin):
            try:
                os.chmod(cached_bin, 0o755)
            except OSError:
                pass

    # 1. Ensure 'node' is in PATH for py-tgcalls 0.9.7 WebRTC bridge
    if not shutil.which("node"):
        print("[Bootstrap] Node.js not found in container PATH. Setting up lightweight Node.js runtime...", flush=True)
        # First check if nodejs_wheel is already installed
        try:
            import nodejs_wheel  # type: ignore

            node_bin_dir = os.path.join(os.path.dirname(nodejs_wheel.__file__), "bin")
            node_exe = os.path.join(node_bin_dir, "node")
            if os.path.isfile(node_exe):
                try:
                    os.chmod(node_exe, 0o755)
                except OSError:
                    pass
                path_parts.insert(0, node_bin_dir)
                os.environ["PATH"] = os.pathsep.join(path_parts)
        except Exception:
            pass

    if not shutil.which("node"):
        # Stream ONLY 'bin/node' directly from nodejs.org in 64KB chunks (< 3 MB RAM, skips npm/headers)
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("aarch64", "arm64") else "x64"
        node_url = f"https://nodejs.org/dist/v18.20.8/node-v18.20.8-linux-{arch}.tar.gz"
        node_dst = os.path.join(runtime_bin, "node")
        node_tmp = os.path.join(runtime_bin, "node.tmp")
        try:
            req = urllib.request.Request(node_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                with tarfile.open(fileobj=resp, mode="r|gz") as tar:
                    for member in tar:
                        if member.isfile() and member.name.endswith("/bin/node"):
                            extracted = tar.extractfile(member)
                            if extracted is not None:
                                with open(node_tmp, "wb") as out_fp:
                                    shutil.copyfileobj(extracted, out_fp, length=65536)
                                os.replace(node_tmp, node_dst)
                                os.chmod(node_dst, 0o755)
                                print("[Bootstrap] Node.js binary ready in .runtime_bin/node ✅", flush=True)
                            break
        except Exception as e:
            print(f"[Bootstrap] Direct Node stream fallback ({e}); trying pip wheel...", flush=True)
            try:
                if os.path.exists(node_tmp):
                    os.remove(node_tmp)
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "nodejs-wheel-binaries==20.18.0"]
                )
                import nodejs_wheel  # type: ignore

                node_bin_dir = os.path.join(os.path.dirname(nodejs_wheel.__file__), "bin")
                os.chmod(os.path.join(node_bin_dir, "node"), 0o755)
                os.environ["PATH"] = node_bin_dir + os.pathsep + os.environ.get("PATH", "")
            except Exception as pip_err:
                print(f"[Bootstrap] Warning: Could not auto-install Node.js: {pip_err}", flush=True)

    # 2. Ensure 'ffmpeg' is in PATH for PyTgCalls & yt-dlp audio streaming
    if not shutil.which("ffmpeg"):
        print("[Bootstrap] FFmpeg not found in container PATH. Installing static FFmpeg (--no-cache-dir)...", flush=True)
        try:
            try:
                import imageio_ffmpeg  # type: ignore
            except ImportError:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "imageio-ffmpeg>=0.5.1"]
                )
                import imageio_ffmpeg  # type: ignore

            ffmpeg_src = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_src and os.path.isfile(ffmpeg_src):
                ffmpeg_dst = os.path.join(runtime_bin, "ffmpeg")
                if not os.path.exists(ffmpeg_dst):
                    try:
                        os.symlink(ffmpeg_src, ffmpeg_dst)
                    except OSError:
                        shutil.copy2(ffmpeg_src, ffmpeg_dst)
                try:
                    os.chmod(ffmpeg_dst, 0o755)
                except OSError:
                    pass
                print("[Bootstrap] FFmpeg binary ready in .runtime_bin/ffmpeg ✅", flush=True)
        except Exception as ff_err:
            print(f"[Bootstrap] Warning: Could not auto-install FFmpeg: {ff_err}", flush=True)


_bootstrap_container_binaries()

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
from pytgcalls.types.input_stream.quality import HighQualityAudio
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

BOT_START_TIME = time.time()

if not config.BOT_TOKEN:
    logger.error("BOT_TOKEN is missing in config.py or environment variables.")
    sys.exit(1)

if not config.STRING_SESSION:
    logger.warning(
        "WARNING: STRING_SESSION is empty. Assistant won't be able to join voice calls until STRING_SESSION is set."
    )

ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
DEFAULT_START_BANNER = os.path.join(ASSETS_DIR, "start_banner.jpg")
BOT_DATA_PATH = os.path.join(ROOT_DIR, "bot_data.json")
DOWNLOAD_DIR = os.path.join(ROOT_DIR, "downloads")

os.makedirs(FONT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================================================
# Default /start Small-Caps Branding & Persistent Store
# ==========================================================
DEFAULT_HEADER_TITLE = "────「 𝑴𝒂𝒓𝒊𝒐 𝑴𝒖𝒔𝒊𝒄 🎧 」────"
DEFAULT_WELCOME_INTRO = (
    "I Aᴍ Tʜᴇ Fᴀsᴛ Aɴᴅ Pᴏᴡᴇʀғᴜʟ Mᴜsɪᴄ Pʟᴀʏᴇʀ Bᴏᴛ Wɪᴛʜ Sᴏᴍᴇ Aᴡᴇsᴏᴍᴇ Fᴇᴀᴛᴜʀᴇs."
)
DEFAULT_WELCOME_FOOTER = (
    "Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ Aɴᴅ Eɴᴊᴏʏ Hɪɢʜ-Qᴜᴀʟɪᴛʏ Vᴏɪᴄᴇ Cʜᴀᴛ Mᴜsɪᴄ."
)
AUTO_DELETE_SECONDS = 15.0


def _default_bot_data() -> Dict[str, Any]:
    owner_id = int(getattr(config, "OWNER_ID", 7670796126) or 0)
    seed_users = [owner_id] if owner_id > 0 else []
    seed_admins = [owner_id] if owner_id > 0 else []
    return {
        "users": seed_users,
        "groups": [-1004338179393],
        "admins": seed_admins,
        "start_photo": "",
        "cached_default_banner_id": "",
        "cached_bot_id": "",
        "header_title": DEFAULT_HEADER_TITLE,
        "welcome_intro": DEFAULT_WELCOME_INTRO,
        "welcome_footer": DEFAULT_WELCOME_FOOTER,
    }


def load_bot_data() -> Dict[str, Any]:
    base = _default_bot_data()
    if os.path.isfile(BOT_DATA_PATH):
        try:
            with open(BOT_DATA_PATH, "r", encoding="utf-8") as fp:
                loaded = json.load(fp)
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    base[k] = v
        except Exception as e:
            logger.warning(f"Could not read bot_data.json, using defaults: {e}")

    # Normalize ID lists
    base["users"] = sorted({int(x) for x in base.get("users", []) if int(x) > 0})
    base["groups"] = sorted({int(x) for x in base.get("groups", []) if int(x) < 0})
    owner_id = int(getattr(config, "OWNER_ID", 7670796126) or 0)
    admins_set = {int(x) for x in base.get("admins", []) if int(x) > 0}
    if owner_id > 0:
        admins_set.add(owner_id)
    base["admins"] = sorted(admins_set)
    return base


BOT_DATA: Dict[str, Any] = load_bot_data()


def save_bot_data() -> None:
    try:
        tmp_path = f"{BOT_DATA_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fp:
            json.dump(BOT_DATA, fp, ensure_ascii=False, indent=2)
        os.replace(tmp_path, BOT_DATA_PATH)
    except Exception as e:
        logger.warning(f"Failed saving bot_data.json: {e}")


def record_chat_activity(chat_id: int, chat_type: str) -> None:
    if chat_type == "private" and chat_id > 0:
        if chat_id not in BOT_DATA["users"]:
            BOT_DATA["users"].append(chat_id)
            save_bot_data()
    elif chat_type in ("group", "supergroup") and chat_id < 0:
        if chat_id not in BOT_DATA["groups"]:
            BOT_DATA["groups"].append(chat_id)
            save_bot_data()


def remove_dead_chat(chat_id: int) -> None:
    changed = False
    if chat_id in BOT_DATA["users"]:
        BOT_DATA["users"].remove(chat_id)
        changed = True
    if chat_id in BOT_DATA["groups"]:
        BOT_DATA["groups"].remove(chat_id)
        changed = True
    if changed:
        save_bot_data()


def is_admin_user(from_user: Optional[Dict[str, Any]]) -> bool:
    """Strictly verify whether the user is the Bot Owner (@Yes_Im_Mario / OWNER_ID)."""
    if not from_user:
        return False
    uid = from_user.get("id")
    uname = (from_user.get("username") or "").strip().lower().lstrip("@")
    owner_uname = (getattr(config, "OWNER_USERNAME", "Yes_Im_Mario") or "").strip().lower().lstrip("@")
    owner_id = int(getattr(config, "OWNER_ID", 7670796126) or 0)

    if uid and owner_id and int(uid) == owner_id:
        return True
    if uname and owner_uname and uname == owner_uname:
        if uid and int(uid) not in BOT_DATA["admins"]:
            BOT_DATA["admins"].append(int(uid))
            save_bot_data()
        return True
    if uid and int(uid) in BOT_DATA.get("admins", []):
        return True
    return False


# ==========================================================
# Live Server Resource Metrics (Pure Linux/Stdlib)
# ==========================================================
_LAST_CPU_SAMPLE: Optional[Tuple[int, int]] = None


def _read_cpu_ticks() -> Optional[Tuple[int, int]]:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as fp:
            first = fp.readline()
        parts = [int(x) for x in first.split()[1:]]
        if len(parts) >= 4:
            idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
            total = sum(parts)
            return total, idle
    except Exception:
        pass
    return None


# Prime initial CPU sample at startup
_LAST_CPU_SAMPLE = _read_cpu_ticks()


def get_live_system_stats() -> Tuple[str, str, str, str]:
    """Return (uptime_str, storage_pct_str, cpu_pct_str, ram_pct_str)."""
    global _LAST_CPU_SAMPLE

    # 1. Uptime (e.g. 15ʜ:9ᴍ:31s)
    elapsed = max(1, int(time.time() - BOT_START_TIME))
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    if days > 0:
        uptime_str = f"{days}ᴅ:{hours}ʜ:{mins}ᴍ:{secs}s"
    else:
        uptime_str = f"{hours}ʜ:{mins}ᴍ:{secs}s"

    # 2. Server Storage %
    try:
        du = shutil.disk_usage(ROOT_DIR)
        storage_pct = (du.used / du.total) * 100.0 if du.total else 0.0
    except Exception:
        storage_pct = 0.0
    storage_str = f"{storage_pct:.1f}%"

    # 3. CPU Load %
    cpu_pct = 0.0
    cur_sample = _read_cpu_ticks()
    if cur_sample and _LAST_CPU_SAMPLE:
        d_total = cur_sample[0] - _LAST_CPU_SAMPLE[0]
        d_idle = cur_sample[1] - _LAST_CPU_SAMPLE[1]
        if d_total > 0:
            cpu_pct = max(0.4, min(100.0, ((d_total - d_idle) / d_total) * 100.0))
            _LAST_CPU_SAMPLE = cur_sample
    if cpu_pct == 0.0:
        try:
            cores = max(1, os.cpu_count() or 1)
            cpu_pct = max(0.8, min(100.0, (os.getloadavg()[0] / cores) * 100.0))
        except Exception:
            cpu_pct = 4.2
    cpu_str = f"{cpu_pct:.1f}%"

    # 4. RAM Consumption %
    ram_pct = 0.0
    try:
        mem_info: Dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as fp:
            for line in fp:
                if ":" in line:
                    k, v = line.split(":", 1)
                    num = v.strip().split()[0]
                    if num.isdigit():
                        mem_info[k.strip()] = int(num)
        total_kb = mem_info.get("MemTotal", 0)
        avail_kb = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
        if total_kb > 0:
            ram_pct = max(1.0, min(100.0, ((total_kb - avail_kb) / total_kb) * 100.0))
    except Exception:
        ram_pct = 25.0
    ram_str = f"{ram_pct:.1f}%"

    return uptime_str, storage_str, cpu_str, ram_str


# ==========================================================
# Font Loader & Artwork Generators
# ==========================================================
def ensure_card_fonts() -> None:
    specs = [
        ("Noto Sans Myanmar", 700, os.path.join(FONT_DIR, "NotoSansMyanmar-Bold.ttf")),
        ("Noto Sans Myanmar", 400, os.path.join(FONT_DIR, "NotoSansMyanmar-Regular.ttf")),
        ("Inter", 700, os.path.join(FONT_DIR, "Inter-Bold.ttf")),
        ("Inter", 500, os.path.join(FONT_DIR, "Inter-Medium.ttf")),
    ]
    for family, weight, out_path in specs:
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 10_000:
            continue
        try:
            css_url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}"
            req = urllib.request.Request(css_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1)"})
            css = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
            m = re.search(r"url\((https://[^)]+\.(?:ttf|otf))\)", css)
            if m:
                urllib.request.urlretrieve(m.group(1), out_path)
                logger.info(f"Downloaded font: {os.path.basename(out_path)}")
        except Exception as font_err:
            logger.warning(f"Could not auto-download font {family} ({weight}): {font_err}")


def ensure_default_start_banner() -> str:
    """Guarantee a sleek dark studio 16:9 /start banner exists locally."""
    if os.path.isfile(DEFAULT_START_BANNER) and os.path.getsize(DEFAULT_START_BANNER) > 5_000:
        return DEFAULT_START_BANNER

    os.makedirs(ASSETS_DIR, exist_ok=True)
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (10, 10, 18))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(26 * (1 - t) + 8 * t)
        g = int(12 * (1 - t) + 10 * t)
        b = int(38 * (1 - t) + 22 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    # Neon soundwave arcs
    cy = h // 2
    for offset, col in ((-22, (236, 56, 108)), (0, (152, 82, 255)), (22, (68, 182, 255))):
        pts = []
        for x in range(80, w - 80, 8):
            norm = (x - 80) / (w - 160)
            env = math.sin(norm * math.pi) ** 1.4
            wave = math.sin(norm * 18.0 + offset * 0.15) * 115 * env
            pts.append((x, cy + wave + offset * 0.4))
        draw.line(pts, fill=col, width=4)
    img.save(DEFAULT_START_BANNER, format="JPEG", quality=92)
    return DEFAULT_START_BANNER


def _contains_myanmar(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if (0x1000 <= cp <= 0x109F) or (0xAA60 <= cp <= 0xAA7F) or (0xA9E0 <= cp <= 0xA9FF):
            return True
    return False


def _load_font(text: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates: List[str] = []
    if _contains_myanmar(text):
        candidates.append(
            os.path.join(FONT_DIR, "NotoSansMyanmar-Bold.ttf" if bold else "NotoSansMyanmar-Regular.ttf")
        )
    candidates.extend(
        [
            os.path.join(FONT_DIR, "Inter-Bold.ttf" if bold else "Inter-Medium.ttf"),
            os.path.join(FONT_DIR, "NotoSansMyanmar-Bold.ttf" if bold else "NotoSansMyanmar-Regular.ttf"),
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return ""
    if draw.textlength(clean, font=font) <= max_width:
        return clean
    ellipsis = "..."
    lo, hi = 0, len(clean)
    best = ellipsis
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = clean[:mid].rstrip() + ellipsis
        if draw.textlength(candidate, font=font) <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _upgrade_thumbnail_urls(thumb_url: str) -> List[str]:
    urls: List[str] = []
    if not thumb_url:
        return urls
    if "sndcdn.com" in thumb_url and "-large." in thumb_url:
        urls.append(thumb_url.replace("-large.", "-t500x500."))
    urls.append(thumb_url)
    return urls


def _download_cover_image(thumb_url: str) -> Optional[Image.Image]:
    for url in _upgrade_thumbnail_urls(thumb_url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read()
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                if img.width >= 32 and img.height >= 32:
                    return img
        except Exception:
            continue
    return None


def _create_fallback_cover() -> Image.Image:
    size = 600
    cover = Image.new("RGB", (size, size), (24, 18, 34))
    draw = ImageDraw.Draw(cover)
    for y in range(size):
        t = y / size
        r = int(48 * (1 - t) + 16 * t)
        g = int(20 * (1 - t) + 22 * t)
        b = int(44 * (1 - t) + 52 * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    cx, cy = size // 2, size // 2
    for radius in (210, 175, 140, 105):
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(255, 255, 255, 28),
            width=2,
        )
    draw.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=(215, 72, 96))
    draw.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(24, 18, 34))
    return cover


def _rounded_mask(size: Tuple[int, int], radius: int) -> Image.Image:
    scale = 4
    w, h = size
    mask_hi = Image.new("L", (w * scale, h * scale), 0)
    d = ImageDraw.Draw(mask_hi)
    d.rounded_rectangle([0, 0, w * scale - 1, h * scale - 1], radius=radius * scale, fill=255)
    return mask_hi.resize((w, h), Image.Resampling.LANCZOS)


def _draw_player_vector_icons(card_rgba: Image.Image, card_w: int) -> None:
    scale = 4
    w, h = card_rgba.size
    overlay = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    muted = (195, 195, 206, 165)
    bright = (255, 255, 255, 248)
    cy = 294 * scale

    # 1. Left 5-pointed Star icon
    sx = 66 * scale
    outer_r = 12.5 * scale
    inner_r = 5.2 * scale
    star_pts: List[Tuple[float, float]] = []
    for i in range(10):
        ang = -math.pi / 2 + i * (math.pi / 5)
        rad = outer_r if i % 2 == 0 else inner_r
        star_pts.append((sx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    d.polygon(star_pts, fill=muted)

    # 2. Rewind double-triangle (◀◀)
    rx = 176 * scale
    tri_w = 15 * scale
    tri_h = 10.5 * scale
    d.polygon([(rx - tri_w, cy), (rx, cy - tri_h), (rx, cy + tri_h)], fill=bright)
    d.polygon(
        [(rx - 1 * scale, cy), (rx + tri_w - 1 * scale, cy - tri_h), (rx + tri_w - 1 * scale, cy + tri_h)],
        fill=bright,
    )

    # 3. Center Pause icon (❚❚)
    px = (card_w // 2) * scale
    bar_w = 7.5 * scale
    bar_h = 26 * scale
    gap = 4.5 * scale
    d.rounded_rectangle(
        [px - gap - bar_w, cy - bar_h / 2, px - gap, cy + bar_h / 2],
        radius=2.2 * scale,
        fill=bright,
    )
    d.rounded_rectangle(
        [px + gap, cy - bar_h / 2, px + gap + bar_w, cy + bar_h / 2],
        radius=2.2 * scale,
        fill=bright,
    )

    # 4. Fast-Forward double-triangle (▶▶)
    fx = 400 * scale
    d.polygon(
        [(fx - tri_w + 1 * scale, cy - tri_h), (fx - tri_w + 1 * scale, cy + tri_h), (fx + 1 * scale, cy)],
        fill=bright,
    )
    d.polygon([(fx, cy - tri_h), (fx, cy + tri_h), (fx + tri_w, cy)], fill=bright)

    # 5. Right Earbuds icon
    ax = 510 * scale
    d.ellipse([ax - 13 * scale, cy - 11 * scale, ax - 2 * scale, cy - 1 * scale], fill=muted)
    d.rounded_rectangle([ax - 6.5 * scale, cy - 3 * scale, ax - 3 * scale, cy + 11 * scale], radius=1.5 * scale, fill=muted)
    d.ellipse([ax + 2 * scale, cy - 11 * scale, ax + 13 * scale, cy - 1 * scale], fill=muted)
    d.rounded_rectangle([ax + 3 * scale, cy - 3 * scale, ax + 6.5 * scale, cy + 11 * scale], radius=1.5 * scale, fill=muted)

    # 6. Bottom Volume Row
    vy = 358 * scale
    sp_l = 48 * scale
    d.polygon(
        [
            (sp_l - 5 * scale, vy - 3 * scale),
            (sp_l - 1 * scale, vy - 3 * scale),
            (sp_l + 4 * scale, vy - 7.5 * scale),
            (sp_l + 4 * scale, vy + 7.5 * scale),
            (sp_l - 1 * scale, vy + 3 * scale),
            (sp_l - 5 * scale, vy + 3 * scale),
        ],
        fill=muted,
    )

    v_x1 = 68 * scale
    v_x2 = 496 * scale
    v_fill = v_x1 + int((v_x2 - v_x1) * 0.72)
    v_half_h = 3.2 * scale
    d.rounded_rectangle([v_x1, vy - v_half_h, v_x2, vy + v_half_h], radius=v_half_h, fill=(255, 255, 255, 58))
    d.rounded_rectangle([v_x1, vy - v_half_h, v_fill, vy + v_half_h], radius=v_half_h, fill=(255, 255, 255, 238))

    sp_r = 514 * scale
    d.polygon(
        [
            (sp_r - 5 * scale, vy - 3 * scale),
            (sp_r - 1 * scale, vy - 3 * scale),
            (sp_r + 4 * scale, vy - 7.5 * scale),
            (sp_r + 4 * scale, vy + 7.5 * scale),
            (sp_r - 1 * scale, vy + 3 * scale),
            (sp_r - 5 * scale, vy + 3 * scale),
        ],
        fill=muted,
    )
    d.arc([sp_r + 2 * scale, vy - 6 * scale, sp_r + 9.5 * scale, vy + 6 * scale], start=-55, end=55, fill=muted, width=int(1.6 * scale))
    d.arc([sp_r + 4 * scale, vy - 9.5 * scale, sp_r + 14 * scale, vy + 9.5 * scale], start=-55, end=55, fill=muted, width=int(1.6 * scale))

    overlay_smooth = overlay.resize((w, h), Image.Resampling.LANCZOS)
    card_rgba.alpha_composite(overlay_smooth)


def _render_stream_card_sync(track: dict) -> Optional[str]:
    try:
        canvas_w, canvas_h = 1280, 720
        cover = _download_cover_image(track.get("thumbnail") or "") or _create_fallback_cover()

        bg = ImageOps.fit(cover, (canvas_w, canvas_h), method=Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=18))
        bg = ImageEnhance.Color(bg).enhance(1.15)
        bg = ImageEnhance.Brightness(bg).enhance(0.56)
        canvas = bg.convert("RGBA")

        vignette = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 32))
        canvas.alpha_composite(vignette)

        card_w, card_h = 576, 424
        card_x = (canvas_w - card_w) // 2
        card_y = (canvas_h - card_h) // 2
        card_radius = 38

        shadow_pad = 48
        shadow = Image.new("RGBA", (card_w + shadow_pad * 2, card_h + shadow_pad * 2), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle(
            [shadow_pad, shadow_pad + 12, shadow_pad + card_w, shadow_pad + card_h + 12],
            radius=card_radius,
            fill=(0, 0, 0, 165),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22))
        canvas.alpha_composite(shadow, (card_x - shadow_pad, card_y - shadow_pad))

        inner_art = ImageOps.fit(cover, (card_w, card_h), method=Image.Resampling.LANCZOS)
        inner_art = inner_art.filter(ImageFilter.GaussianBlur(radius=12))
        inner_art = ImageEnhance.Brightness(inner_art).enhance(0.42)
        card_img = inner_art.convert("RGBA")

        glass_tint = Image.new("RGBA", (card_w, card_h), (18, 18, 22, 152))
        card_img.alpha_composite(glass_tint)

        art_size = 154
        art_x, art_y = 42, 40
        art_sq = ImageOps.fit(cover, (art_size, art_size), method=Image.Resampling.LANCZOS).convert("RGBA")
        art_mask = _rounded_mask((art_size, art_size), radius=20)

        art_shadow = Image.new("RGBA", (art_size + 24, art_size + 24), (0, 0, 0, 0))
        asd = ImageDraw.Draw(art_shadow)
        asd.rounded_rectangle([12, 16, 12 + art_size, 16 + art_size], radius=20, fill=(0, 0, 0, 130))
        art_shadow = art_shadow.filter(ImageFilter.GaussianBlur(radius=8))
        card_img.alpha_composite(art_shadow, (art_x - 12, art_y - 12))

        art_layer = Image.new("RGBA", (art_size, art_size), (0, 0, 0, 0))
        art_layer.paste(art_sq, (0, 0), art_mask)
        card_img.alpha_composite(art_layer, (art_x, art_y))

        cd = ImageDraw.Draw(card_img)
        text_x = art_x + art_size + 22
        max_text_w = card_w - text_x - 36

        raw_title = track.get("title") or "Unknown Track"
        raw_channel = track.get("channel") or "Music Stream"
        brand_label = config.BOT_NAME or "Mario Music"

        font_brand = _load_font(brand_label, size=14, bold=False)
        font_title = _load_font(raw_title, size=23, bold=True)
        font_channel = _load_font(raw_channel, size=18, bold=False)
        font_time = _load_font("0:24 -5:24", size=13, bold=False)

        brand_str = _truncate_to_width(cd, brand_label, font_brand, max_text_w)
        title_str = _truncate_to_width(cd, raw_title, font_title, max_text_w)
        channel_str = _truncate_to_width(cd, raw_channel, font_channel, max_text_w)

        cd.text((text_x, art_y + 28), brand_str, font=font_brand, fill=(190, 190, 202, 195))
        cd.text((text_x, art_y + 52), title_str, font=font_title, fill=(255, 255, 255, 255))
        cd.text((text_x, art_y + 98), channel_str, font=font_channel, fill=(205, 205, 216, 215))

        dur_sec = int(track.get("duration_sec") or 0)
        if dur_sec > 30:
            elapsed = min(24, max(5, dur_sec // 10))
            rem = max(0, dur_sec - elapsed)
            left_ts = f"{elapsed // 60}:{elapsed % 60:02d}"
            rem_m, rem_s = divmod(rem, 60)
            rem_h, rem_m = divmod(rem_m, 60)
            right_ts = f"-{rem_h}:{rem_m:02d}:{rem_s:02d}" if rem_h > 0 else f"-{rem_m}:{rem_s:02d}"
            prog_ratio = max(0.12, min(0.35, elapsed / dur_sec))
        elif dur_sec > 0:
            left_ts = "0:03"
            right_ts = f"-0:{max(0, dur_sec - 3):02d}"
            prog_ratio = 0.22
        else:
            left_ts = "0:00"
            right_ts = "LIVE"
            prog_ratio = 0.35

        prog_y = 236
        cd.text((42, prog_y - 7), left_ts, font=font_time, fill=(190, 190, 202, 195))
        rt_w = cd.textlength(right_ts, font=font_time)
        cd.text((card_w - 42 - rt_w, prog_y - 7), right_ts, font=font_time, fill=(190, 190, 202, 195))

        lt_w = cd.textlength(left_ts, font=font_time)
        bar_x1 = int(42 + lt_w + 12)
        bar_x2 = int(card_w - 42 - rt_w - 12)
        if bar_x2 > bar_x1 + 40:
            fill_x2 = bar_x1 + int((bar_x2 - bar_x1) * prog_ratio)
            cd.rounded_rectangle([bar_x1, prog_y - 2.5, bar_x2, prog_y + 2.5], radius=3, fill=(255, 255, 255, 58))
            cd.rounded_rectangle([bar_x1, prog_y - 2.5, fill_x2, prog_y + 2.5], radius=3, fill=(255, 255, 255, 240))

        _draw_player_vector_icons(card_img, card_w)

        border_hi = Image.new("RGBA", (card_w * 2, card_h * 2), (0, 0, 0, 0))
        bd = ImageDraw.Draw(border_hi)
        bd.rounded_rectangle(
            [1, 1, card_w * 2 - 2, card_h * 2 - 2],
            radius=card_radius * 2,
            outline=(255, 255, 255, 36),
            width=2,
        )
        card_img.alpha_composite(border_hi.resize((card_w, card_h), Image.Resampling.LANCZOS))

        card_mask = _rounded_mask((card_w, card_h), radius=card_radius)
        card_masked = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        card_masked.paste(card_img, (0, 0), card_mask)
        canvas.alpha_composite(card_masked, (card_x, card_y))

        out_path = os.path.join(DOWNLOAD_DIR, f"card_{int(time.time() * 1000)}_{os.getpid()}.jpg")
        canvas.convert("RGB").save(out_path, format="JPEG", quality=90, optimize=True)
        del canvas, card_img, card_masked, bg, cover
        trim_process_memory()
        return out_path
    except Exception as card_err:
        logger.warning(f"Stream card generation fallback notice: {card_err}")
        trim_process_memory()
        return None


async def generate_stream_card(track: dict) -> Optional[str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _render_stream_card_sync, track)


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
                params = data.get("parameters") or {}
                retry_after = params.get("retry_after")
                if retry_after:
                    raise RuntimeError(f"[{code}] RETRY_AFTER:{retry_after} {desc}")
                raise RuntimeError(f"[{code}] {desc}")
            return data.get("result")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        disable_web_page_preview: bool = True,
        parse_mode: Optional[str] = "HTML",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
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

    async def delete_message(self, chat_id: int, message_id: Optional[int]) -> bool:
        if not message_id:
            return False
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
        parse_mode: Optional[str] = "HTML",
    ) -> Dict[str, Any]:
        if os.path.isfile(photo):
            if self._session is None or self._session.closed:
                await self.start()
            assert self._session is not None
            form = aiohttp.FormData()
            form.add_field("chat_id", str(chat_id))
            form.add_field("caption", caption)
            if parse_mode:
                form.add_field("parse_mode", parse_mode)
            if reply_to_message_id:
                form.add_field("reply_to_message_id", str(reply_to_message_id))
                form.add_field("allow_sending_without_reply", "true")
            if reply_markup:
                form.add_field("reply_markup", json.dumps(reply_markup))
            with open(photo, "rb") as fp:
                photo_bytes = fp.read()
            form.add_field(
                "photo",
                photo_bytes,
                filename=os.path.basename(photo),
                content_type="image/jpeg",
            )
            url = f"{self.base_url}/sendPhoto"
            async with self._session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                data = await resp.json(content_type=None)
                if not data.get("ok"):
                    desc = data.get("description", "Unknown Bot API sendPhoto error")
                    code = data.get("error_code", resp.status)
                    raise RuntimeError(f"[{code}] {desc}")
                return data.get("result")

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            payload["allow_sending_without_reply"] = True
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.call("sendPhoto", payload)

    async def copy_message(
        self,
        chat_id: int,
        from_chat_id: int,
        message_id: int,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.call("copyMessage", payload)

    async def set_my_commands(self, commands: List[Dict[str, str]]) -> bool:
        try:
            await self.call("setMyCommands", {"commands": commands})
            return True
        except Exception as e:
            logger.debug(f"setMyCommands notice: {e}")
            return False

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
# Initialize Clients & In-Memory Runtime State
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

QUEUES: Dict[int, List[dict]] = {}
CURRENT_PLAYING: Dict[int, dict] = {}
PAUSED_CHATS: set[int] = set()
ACTIVE_STREAM_CARD_MSG: Dict[int, int] = {}
ADMIN_STATES: Dict[int, str] = {}
ASSISTANT_USERNAME: str = "mariomusicAssistant"
BOT_USERNAME_CACHE: str = "marioxnmusic_bot"

YTDL_BASE_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 6,
    "retries": 1,
    "skip_download": True,
    "extractor_args": {
        "youtube": {
            "skip": ["dash", "hls", "translated_subs", "comments"],
            "player_client": ["android", "web"],
        }
    },
}

SEARCH_CACHE: Dict[str, Tuple[float, dict]] = {}


def get_cached_search(query: str) -> Optional[dict]:
    clean = query.strip().lower()
    if clean in SEARCH_CACHE:
        ts, data = SEARCH_CACHE[clean]
        if time.time() - ts < 3600:
            return dict(data)
    return None


def set_cached_search(query: str, data: dict) -> None:
    clean = query.strip().lower()
    if len(SEARCH_CACHE) > 80:
        try:
            oldest = min(SEARCH_CACHE.keys(), key=lambda k: SEARCH_CACHE[k][0])
            SEARCH_CACHE.pop(oldest, None)
        except Exception:
            SEARCH_CACHE.clear()
    SEARCH_CACHE[clean] = (time.time(), dict(data))


def cleanup_storage_and_memory(active_chat_id: Optional[int] = None) -> None:
    """Instantly delete finished tracks, cache files, card images, and release RAM to Linux OS."""
    # 1. Clean cache_audio/
    cache_dir = os.path.join(ROOT_DIR, "cache_audio")
    if os.path.isdir(cache_dir):
        active_files = set()
        for t in CURRENT_PLAYING.values():
            if isinstance(t, dict) and t.get("local_file"):
                active_files.add(os.path.abspath(t["local_file"]))
        try:
            for fname in os.listdir(cache_dir):
                fp = os.path.abspath(os.path.join(cache_dir, fname))
                if fp not in active_files:
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
        except Exception:
            pass

    # 2. Clean downloads/
    dl_dir = os.path.join(ROOT_DIR, "downloads")
    if os.path.isdir(dl_dir):
        try:
            for fname in os.listdir(dl_dir):
                fp = os.path.join(dl_dir, fname)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass
        except Exception:
            pass

    # 3. Clean root temporary files
    try:
        for fname in os.listdir(ROOT_DIR):
            if (fname.startswith("card_") and fname.endswith(".jpg")) or fname.endswith(".tmp"):
                try:
                    os.remove(os.path.join(ROOT_DIR, fname))
                except Exception:
                    pass
    except Exception:
        pass

    # 4. Aggressively trim RAM back to OS
    trim_process_memory()



# ==========================================================
# Auto-Delete & Formatting Helpers
# ==========================================================
def esc(text: Any) -> str:
    return html.escape(str(text or ""))


async def _delayed_delete_task(chat_id: int, message_id: int, delay: float) -> None:
    try:
        await asyncio.sleep(delay)
        await bot_api.delete_message(chat_id, message_id)
    except Exception:
        pass


def schedule_delete(chat_id: int, message_id: Optional[int], delay: float = AUTO_DELETE_SECONDS) -> None:
    if chat_id and message_id:
        asyncio.create_task(_delayed_delete_task(chat_id, message_id, delay))


async def send_temp_message(
    chat_id: int,
    text: str,
    delay: float = AUTO_DELETE_SECONDS,
    reply_to_message_id: Optional[int] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        sent = await bot_api.send_message(
            chat_id,
            text,
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup,
        )
        if sent and sent.get("message_id"):
            schedule_delete(chat_id, sent["message_id"], delay=delay)
        return sent
    except Exception as e:
        logger.debug(f"send_temp_message notice in {chat_id}: {e}")
        return None


async def clear_active_stream_card(chat_id: int) -> None:
    old_mid = ACTIVE_STREAM_CARD_MSG.pop(chat_id, None)
    if old_mid:
        await bot_api.delete_message(chat_id, old_mid)


def user_display_name(from_user: Optional[Dict[str, Any]]) -> str:
    if not from_user:
        return "Member"
    first = (from_user.get("first_name") or "").strip()
    last = (from_user.get("last_name") or "").strip()
    full = f"{first} {last}".strip()
    if full:
        return esc(full)
    if from_user.get("username"):
        return esc(from_user["username"])
    return "User"


def user_mention_html(from_user: Optional[Dict[str, Any]]) -> str:
    if not from_user:
        return "Member"
    uid = from_user.get("id")
    name = user_display_name(from_user)
    if uid:
        return f'<a href="tg://user?id={uid}">{name}</a>'
    return name


def format_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "Live Stream"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def format_duration_label(track: dict) -> str:
    dur = track.get("duration") or "Live Stream"
    if dur == "Live Stream":
        return "Live Stream"
    return f"{esc(dur)} Minutes"


def build_stream_caption(track: dict, header: str = "Started Streaming") -> str:
    return (
        f"➜ <b>{esc(header)}</b> |\n\n"
        f"‣ <b>Title :</b> <a href=\"{esc(track['link'])}\">{esc(track['title'])}</a>\n"
        f"‣ <b>Duration :</b> {format_duration_label(track)}\n"
        f"‣ <b>Requested By :</b> {track.get('req_plain') or track.get('req_by') or 'Member'}"
    )


def build_control_buttons(chat_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "▷", "callback_data": f"resume|{chat_id}"},
                {"text": "II", "callback_data": f"pause|{chat_id}"},
                {"text": "↻", "callback_data": f"replay|{chat_id}"},
                {"text": "‣‣I", "callback_data": f"skip|{chat_id}"},
                {"text": "▢", "callback_data": f"stop|{chat_id}"},
            ],
            [
                {"text": "Close", "callback_data": f"close|{chat_id}"},
            ],
        ]
    }


def build_close_button(chat_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "Close", "callback_data": f"close|{chat_id}"}],
        ]
    }


async def send_stream_ui_card(
    chat_id: int,
    track: dict,
    header: str = "Started Streaming",
    reply_to_message_id: Optional[int] = None,
    with_controls: bool = True,
    track_as_active: bool = True,
    auto_delete_after: Optional[float] = None,
) -> Optional[int]:
    if track_as_active:
        await clear_active_stream_card(chat_id)

    caption = build_stream_caption(track, header=header)
    markup = build_control_buttons(chat_id) if with_controls else build_close_button(chat_id)
    sent_res: Optional[Dict[str, Any]] = None

    card_path = await generate_stream_card(track)
    if card_path and os.path.isfile(card_path):
        try:
            sent_res = await bot_api.send_photo(
                chat_id,
                photo=card_path,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=markup,
            )
        except Exception as send_err:
            logger.warning(f"Generated card upload fallback in {chat_id}: {send_err}")
        finally:
            try:
                os.remove(card_path)
            except Exception:
                pass

    if not sent_res and track.get("thumbnail"):
        try:
            sent_res = await bot_api.send_photo(
                chat_id,
                photo=track["thumbnail"],
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=markup,
            )
        except Exception:
            pass

    if not sent_res:
        sent_res = await bot_api.send_message(
            chat_id,
            text=caption,
            reply_to_message_id=reply_to_message_id,
            reply_markup=markup,
            disable_web_page_preview=True,
        )

    sent_mid = (sent_res or {}).get("message_id")
    if sent_mid:
        if track_as_active:
            ACTIVE_STREAM_CARD_MSG[chat_id] = sent_mid
        if auto_delete_after:
            schedule_delete(chat_id, sent_mid, delay=auto_delete_after)
    return sent_mid


# ==========================================================
# Custom /start Card (Photo + Small-Caps Live Server Stats)
# ==========================================================
def build_start_buttons(bot_username: str, show_admin: bool = False) -> Dict[str, Any]:
    support_url = getattr(config, "SUPPORT_URL", "https://t.me/mariostore_1z") or "https://t.me/mariostore_1z"
    owner_uname = (getattr(config, "OWNER_USERNAME", "Yes_Im_Mario") or "Yes_Im_Mario").strip().lstrip("@")
    owner_url = f"https://t.me/{owner_uname}"

    rows: List[List[Dict[str, str]]] = [
        [
            {
                "text": "➕ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ",
                "url": f"https://t.me/{bot_username}?startgroup=true",
            }
        ],
        [
            {"text": "Sᴜᴘᴘᴏʀᴛ", "url": support_url},
            {"text": "Oᴡɴᴇʀ", "url": owner_url},
        ],
    ]
    if show_admin:
        rows.append([{"text": "🛠 Aᴅᴍɪɴ Pᴀɴᴇʟ", "callback_data": "adm_home"}])
    return {"inline_keyboard": rows}


def build_start_caption(from_user: Optional[Dict[str, Any]], plain_escape_custom: bool = True) -> str:
    uptime_str, storage_str, cpu_str, ram_str = get_live_system_stats()
    user_mention = user_mention_html(from_user)
    user_plain = user_display_name(from_user)

    raw_header = BOT_DATA.get("header_title") or DEFAULT_HEADER_TITLE
    raw_intro = BOT_DATA.get("welcome_intro") or DEFAULT_WELCOME_INTRO
    raw_footer = BOT_DATA.get("welcome_footer") or DEFAULT_WELCOME_FOOTER

    # Substitute optional placeholders if Admin used them
    for token, val in (
        ("{name}", user_plain),
        ("{uptime}", uptime_str),
        ("{storage}", storage_str),
        ("{cpu}", cpu_str),
        ("{ram}", ram_str),
    ):
        raw_intro = raw_intro.replace(token, val)
        raw_footer = raw_footer.replace(token, val)

    header_txt = esc(raw_header) if plain_escape_custom else raw_header
    intro_txt = esc(raw_intro) if plain_escape_custom else raw_intro
    footer_txt = esc(raw_footer) if plain_escape_custom else raw_footer

    return (
        f"{header_txt}\n\n"
        f"Hᴏʟᴀᴀ {user_mention} ! !\n\n"
        f"{intro_txt}\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"➥Uᴘᴛɪᴍᴇ: {uptime_str}\n"
        f"➥SᴇʀᴠᴇʀSᴛᴏʀᴀɢᴇ: {storage_str}\n"
        f"➥CPU Lᴏᴀᴅ: {cpu_str}\n"
        f"➥RAM Cᴏɴsᴜᴍᴘᴛɪᴏɴ: {ram_str}\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"{footer_txt}"
    )


async def send_start_card(
    chat_id: int,
    from_user: Optional[Dict[str, Any]],
    chat_type: str,
    bot_username: str,
    reply_to_message_id: Optional[int] = None,
) -> None:
    # Admin button ONLY appears in Owner's private chat — never in groups or to regular users
    show_admin = (chat_type == "private") and is_admin_user(from_user)
    buttons = build_start_buttons(bot_username, show_admin=show_admin)
    caption = build_start_caption(from_user, plain_escape_custom=True)

    custom_photo = (BOT_DATA.get("start_photo") or "").strip()
    if custom_photo:
        try:
            await bot_api.send_photo(
                chat_id,
                photo=custom_photo,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=buttons,
            )
            return
        except Exception as custom_err:
            logger.warning(f"Custom start_photo failed ({custom_err}), falling back to default banner.")

    bot_id_str = str((bot_api.me or {}).get("id") or "")
    cached_id = (BOT_DATA.get("cached_default_banner_id") or "").strip()
    if cached_id and BOT_DATA.get("cached_bot_id") == bot_id_str:
        try:
            await bot_api.send_photo(
                chat_id,
                photo=cached_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=buttons,
            )
            return
        except Exception:
            BOT_DATA["cached_default_banner_id"] = ""

    banner_path = ensure_default_start_banner()
    try:
        sent = await bot_api.send_photo(
            chat_id,
            photo=banner_path,
            caption=caption,
            reply_to_message_id=reply_to_message_id,
            reply_markup=buttons,
        )
        photos = (sent or {}).get("photo") or []
        if photos and bot_id_str:
            BOT_DATA["cached_default_banner_id"] = photos[-1]["file_id"]
            BOT_DATA["cached_bot_id"] = bot_id_str
            save_bot_data()
        return
    except Exception as banner_err:
        logger.warning(f"Default start banner send fallback: {banner_err}")

    await bot_api.send_message(
        chat_id,
        caption,
        reply_to_message_id=reply_to_message_id,
        reply_markup=buttons,
    )


# ==========================================================
# Audio Search & Extraction (YouTube + SoundCloud Fallback)
# ==========================================================
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
        "channel": info.get("uploader") or info.get("artist") or "Music Stream",
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
    cached = get_cached_search(query)
    if cached:
        logger.info(f"Instant search cache hit for: {query}")
        return cached

    loop = asyncio.get_running_loop()

    def _extract() -> Optional[dict]:
        is_url = query.startswith("http://") or query.startswith("https://")
        fallback_search_term = query

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
                        set_cached_search(query, track)
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

        sc_opts = {**YTDL_BASE_OPTIONS, "ignoreerrors": True, "socket_timeout": 5}
        try:
            with yt_dlp.YoutubeDL(sc_opts) as sc_ytdl:
                sc_info = sc_ytdl.extract_info(f"scsearch2:{fallback_search_term}", download=False)
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
                    chosen = full_tracks[0] if full_tracks else valid_tracks[0]
                    set_cached_search(query, chosen)
                    return chosen
        except Exception as sc_err:
            logger.error(f"Fallback SoundCloud extraction error: {sc_err}")

        return None

    return await loop.run_in_executor(None, _extract)


# ==========================================================
# Bulletproof Assistant Auto-Join & Peer Resolution
# ==========================================================
async def ensure_assistant_joined(chat_id: int) -> Tuple[bool, str]:
    global ASSISTANT_USERNAME
    assistant_username = ASSISTANT_USERNAME
    try:
        assistant_user = await user.get_me()
        assistant_id = assistant_user.id
        if assistant_user.username:
            assistant_username = assistant_user.username
            ASSISTANT_USERNAME = assistant_username

        try:
            me_member = await user.get_chat_member(chat_id, "me")
            if me_member.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                await user.resolve_peer(chat_id)
                return True, ""
        except (UserNotParticipant, PeerIdInvalid, ValueError, KeyError):
            pass
        except Exception as self_err:
            logger.debug(f"Assistant self-check in {chat_id}: {self_err}")

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
                        f"➜ <b>Assistant Banned</b> |\n\n"
                        f"‣ Assistant <code>@{esc(assistant_username)}</code> is banned in this group.\n"
                        f"‣ Please unban it from Group Settings → Removed Users and try again.\n"
                        f"<i>({esc(unban_err)})</i>",
                    )
            elif status in ("creator", "administrator", "member") or (
                status == "restricted" and member_info.get("is_member", False)
            ):
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
                        pass
        except Exception as chk_err:
            logger.debug(f"Bot API getChatMember check in {chat_id}: {chk_err}")

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
                raise RuntimeError("Missing 'Invite Users via Link' admin permission")

            invite_link = invite_link.replace("https://telegram.me/", "https://t.me/")
            logger.info(f"Joining Assistant @{assistant_username} into {chat_id} via invite link...")

            try:
                await user.join_chat(invite_link)
                joined = True
                logger.info(f"Assistant @{assistant_username} auto-joined chat {chat_id} successfully!")
            except UserAlreadyParticipant:
                joined = True
            except InviteRequestSent:
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
            f"➜ <b>Assistant Auto-Join Failed</b> |\n\n"
            f"‣ Grant the bot <b>Invite Users via Link</b> admin permission, or\n"
            f"‣ Manually add <code>@{esc(assistant_username)}</code> to this group.\n"
            f"<i>(Details: <code>{esc(type(e).__name__)}: {esc(e)}</code>)</i>",
        )


def get_audio_stream(source: str) -> AudioPiped:
    """Build a heavily buffered, anti-lag FFmpeg audio stream to prevent stuttering on cloud VPS."""
    if source.startswith("http://") or source.startswith("https://"):
        return AudioPiped(
            source,
            audio_parameters=HighQualityAudio(),
            additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -threads 1 -bufsize 8192k",
        )
    return AudioPiped(
        source,
        audio_parameters=HighQualityAudio(),
        additional_ffmpeg_parameters="-threads 1",
    )


async def get_playable_audio_source(track: dict) -> str:
    """Pre-fetch audio locally if possible to eliminate network buffering stuttering."""
    if track.get("local_file") and os.path.isfile(track["local_file"]):
        return track["local_file"]

    stream_url = track.get("stream_url", "")
    web_link = track.get("link") or stream_url
    if not web_link or "m3u8" in stream_url:
        return stream_url

    cache_dir = os.path.join(ROOT_DIR, "cache_audio")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        # Keep disk lean (< 50MB): delete older cache files if count > 3
        cache_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir)]
        if len(cache_files) > 3:
            cache_files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
            for old_p in cache_files[:-3]:
                try:
                    os.remove(old_p)
                except Exception:
                    pass
    except Exception:
        pass

    import hashlib
    h = hashlib.md5(web_link.encode("utf-8")).hexdigest()[:12]
    out_tmpl = os.path.join(cache_dir, f"{h}.%(ext)s")

    for ext in ("m4a", "opus", "mp3", "webm"):
        candidate = os.path.join(cache_dir, f"{h}.{ext}")
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 20000:
            track["local_file"] = candidate
            return candidate

    loop = asyncio.get_running_loop()

    def _download():
        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "socket_timeout": 6,
            "retries": 1,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                    "skip": ["dash", "hls", "translated_subs"],
                }
            },
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([web_link])

    try:
        await asyncio.wait_for(loop.run_in_executor(None, _download), timeout=6.5)
        for ext in ("m4a", "opus", "mp3", "webm"):
            candidate = os.path.join(cache_dir, f"{h}.{ext}")
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 20000:
                track["local_file"] = candidate
                logger.info(f"Using local cached audio for lag-free playback: {candidate}")
                return candidate
    except Exception:
        pass

    return stream_url


# ==========================================================
# Queue & Playback Transitions (15s Auto-Cleanup)
# ==========================================================
async def play_next_track(chat_id: int):
    """Play the next track from the queue or leave Voice Chat with 15s auto-deleting notice."""
    old = CURRENT_PLAYING.pop(chat_id, None)
    if old and old.get("local_file") and os.path.exists(old["local_file"]):
        try:
            os.remove(old["local_file"])
        except Exception:
            pass
    # Wipe finished track, unlinked card pictures and purge RAM
    cleanup_storage_and_memory(chat_id)

    if chat_id in QUEUES and len(QUEUES[chat_id]) > 0:
        next_track = QUEUES[chat_id].pop(0)
        CURRENT_PLAYING[chat_id] = next_track
        PAUSED_CHATS.discard(chat_id)

        try:
            stream_source = await get_playable_audio_source(next_track)
            await pytgcalls.change_stream(
                chat_id,
                get_audio_stream(stream_source),
            )
            await send_stream_ui_card(
                chat_id,
                next_track,
                header="Started Streaming",
                with_controls=True,
                track_as_active=True,
            )
        except Exception as e:
            logger.error(f"Error while playing next track in {chat_id}: {e}")
            await play_next_track(chat_id)
    else:
        QUEUES.pop(chat_id, None)
        PAUSED_CHATS.discard(chat_id)
        await clear_active_stream_card(chat_id)
        try:
            await pytgcalls.leave_group_call(chat_id)
        except Exception:
            pass
        cleanup_storage_and_memory()
        await send_temp_message(
            chat_id,
            "▢ <b>Queue Finished</b> | Left the Voice Chat.",
            delay=AUTO_DELETE_SECONDS,
        )


@pytgcalls.on_stream_end()
async def stream_end_handler(_, update: StreamAudioEnded):
    chat_id = update.chat_id
    logger.info(f"Stream ended in chat: {chat_id}. Advancing queue...")
    await play_next_track(chat_id)


@pytgcalls.on_closed_voice_chat()
async def closed_voice_chat_handler(_, chat_id: int):
    logger.info(f"Voice chat closed in {chat_id}")
    QUEUES.pop(chat_id, None)
    CURRENT_PLAYING.pop(chat_id, None)
    PAUSED_CHATS.discard(chat_id)
    await clear_active_stream_card(chat_id)


# ==========================================================
# Owner-Only Secret Admin Panel & Broadcast Engine
# ==========================================================
def build_admin_panel_View(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    users_count = len(BOT_DATA.get("users", []))
    groups_count = len(BOT_DATA.get("groups", []))
    photo_state = "Custom Photo ✅" if BOT_DATA.get("start_photo") else "Default Banner"
    hdr = esc(BOT_DATA.get("header_title") or DEFAULT_HEADER_TITLE)
    intro = esc(BOT_DATA.get("welcome_intro") or DEFAULT_WELCOME_INTRO)
    footer = esc(BOT_DATA.get("welcome_footer") or DEFAULT_WELCOME_FOOTER)

    text = (
        f"🛠 <b>Owner Admin Panel</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"‣ <b>Private Users :</b> <code>{users_count}</code>\n"
        f"‣ <b>Active Groups :</b> <code>{groups_count}</code>\n"
        f"‣ <b>Start Photo :</b> <code>{photo_state}</code>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"‣ <b>Header :</b>\n<code>{hdr}</code>\n\n"
        f"‣ <b>Welcome Text :</b>\n<i>{intro}</i>\n\n"
        f"‣ <b>Bottom Line :</b>\n<i>{footer}</i>\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"Choose an admin action below:"
    )

    markup = {
        "inline_keyboard": [
            [
                {"text": "🖼 Change Start Photo", "callback_data": "adm_set_photo"},
                {"text": "🔄 Reset Photo", "callback_data": "adm_reset_photo"},
            ],
            [
                {"text": "🏷 Edit Top Header", "callback_data": "adm_set_header"},
                {"text": "✏️ Edit Welcome Text", "callback_data": "adm_set_intro"},
            ],
            [
                {"text": "📝 Edit Bottom Line", "callback_data": "adm_set_footer"},
                {"text": "🔄 Reset Texts", "callback_data": "adm_reset_text"},
            ],
            [
                {"text": "📢 Broadcast Post (Groups + Users)", "callback_data": "adm_bc_all"},
            ],
            [
                {"text": "💬 Post to Groups", "callback_data": "adm_bc_groups"},
                {"text": "👥 Post to Users", "callback_data": "adm_bc_users"},
            ],
            [
                {"text": "👀 Preview /start", "callback_data": "adm_preview"},
                {"text": "✖️ Close", "callback_data": f"close|{chat_id}"},
            ],
        ]
    }
    return text, markup


def _admin_cancel_markup() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "🔙 Cancel & Back to Admin Panel", "callback_data": "adm_cancel"}]
        ]
    }


def _admin_back_markup() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "👀 Preview /start", "callback_data": "adm_preview"},
                {"text": "🛠 Admin Panel", "callback_data": "adm_home"},
            ]
        ]
    }


async def execute_broadcast(
    admin_chat_id: int,
    source_msg: Dict[str, Any],
    target_mode: str,
) -> None:
    src_mid = source_msg["message_id"]
    markup = source_msg.get("reply_markup")

    groups_list = list(BOT_DATA.get("groups", [])) if target_mode in ("all", "groups") else []
    users_list = list(BOT_DATA.get("users", [])) if target_mode in ("all", "users") else []
    total_targets = len(groups_list) + len(users_list)

    if total_targets == 0:
        await bot_api.send_message(
            admin_chat_id,
            "➜ <b>No Targets Found</b> | There are no tracked chats in that category yet.",
            reply_markup=_admin_back_markup(),
        )
        return

    status = await bot_api.send_message(
        admin_chat_id,
        f"📡 <b>Broadcasting Post...</b>\n"
        f"‣ Targets: <code>{len(groups_list)}</code> group(s), <code>{len(users_list)}</code> user(s)",
    )
    status_mid = status["message_id"]

    sent_groups = 0
    sent_users = 0
    failed = 0

    async def _copy_one(dest_id: int) -> bool:
        try:
            await bot_api.copy_message(dest_id, admin_chat_id, src_mid, reply_markup=markup)
            return True
        except Exception as err:
            err_s = str(err)
            m = re.search(r"RETRY_AFTER:(\d+)", err_s)
            if m:
                wait_s = min(30, int(m.group(1)) + 1)
                await asyncio.sleep(wait_s)
                try:
                    await bot_api.copy_message(dest_id, admin_chat_id, src_mid, reply_markup=markup)
                    return True
                except Exception:
                    return False
            lower_err = err_s.lower()
            if any(
                tag in lower_err
                for tag in ("blocked", "kicked", "chat not found", "deactivated", "have no rights", "user is deactivated")
            ):
                remove_dead_chat(dest_id)
            return False

    for gid in groups_list:
        if await _copy_one(gid):
            sent_groups += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)

    for uid in users_list:
        if await _copy_one(uid):
            sent_users += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)

    summary_lines = [
        "✅ <b>Broadcast Finished!</b>",
        "➖➖➖➖➖➖➖➖➖➖➖➖➖",
    ]
    if target_mode in ("all", "groups"):
        summary_lines.append(f"‣ <b>Groups Delivered :</b> <code>{sent_groups} / {len(groups_list)}</code>")
    if target_mode in ("all", "users"):
        summary_lines.append(f"‣ <b>Users Delivered :</b> <code>{sent_users} / {len(users_list)}</code>")
    if failed > 0:
        summary_lines.append(f"‣ <b>Failed / Inactive :</b> <code>{failed}</code>")

    await bot_api.edit_message_text(
        admin_chat_id,
        status_mid,
        "\n".join(summary_lines),
        reply_markup=_admin_back_markup(),
    )


async def handle_admin_state_input(msg: Dict[str, Any], chat_id: int, uid: int, state: str) -> None:
    # Handle photo update state
    if state == "set_photo":
        photos = msg.get("photo") or []
        doc = msg.get("document") or {}
        raw_text = (msg.get("text") or "").strip()

        if photos:
            ADMIN_STATES.pop(uid, None)
            BOT_DATA["start_photo"] = photos[-1]["file_id"]
            save_bot_data()
            await bot_api.send_message(
                chat_id,
                "✅ <b>Start Photo Updated!</b>\nYour new image is now active on <code>/start</code>.",
                reply_markup=_admin_back_markup(),
            )
            return

        if doc and str(doc.get("mime_type") or "").startswith("image/"):
            ADMIN_STATES.pop(uid, None)
            tmp_img = os.path.join(DOWNLOAD_DIR, f"admin_start_{int(time.time())}.jpg")
            try:
                await bot_api.download_file(doc["file_id"], tmp_img)
                sent = await bot_api.send_photo(
                    chat_id,
                    photo=tmp_img,
                    caption="✅ <b>Start Photo Updated!</b>",
                    reply_markup=_admin_back_markup(),
                )
                up_photos = (sent or {}).get("photo") or []
                if up_photos:
                    BOT_DATA["start_photo"] = up_photos[-1]["file_id"]
                    save_bot_data()
            finally:
                try:
                    os.remove(tmp_img)
                except Exception:
                    pass
            return

        if raw_text.startswith("http://") or raw_text.startswith("https://"):
            ADMIN_STATES.pop(uid, None)
            BOT_DATA["start_photo"] = raw_text
            save_bot_data()
            await bot_api.send_message(
                chat_id,
                "✅ <b>Start Photo URL Updated!</b>",
                reply_markup=_admin_back_markup(),
            )
            return

        await bot_api.send_message(
            chat_id,
            "⚠️ Please send an <b>Image / Photo</b> (or direct image URL), or press Cancel below.",
            reply_markup=_admin_cancel_markup(),
        )
        return

    # Handle text customization states
    if state in ("set_header", "set_intro", "set_footer"):
        new_text = (msg.get("text") or msg.get("caption") or "").strip()
        if not new_text:
            await bot_api.send_message(
                chat_id,
                "⚠️ Please send the new text message, or press Cancel below.",
                reply_markup=_admin_cancel_markup(),
            )
            return

        ADMIN_STATES.pop(uid, None)
        if state == "set_header":
            BOT_DATA["header_title"] = new_text
            label = "Top Brand Header"
        elif state == "set_intro":
            BOT_DATA["welcome_intro"] = new_text
            label = "Welcome Intro Text"
        else:
            BOT_DATA["welcome_footer"] = new_text
            label = "Welcome Bottom Line"

        save_bot_data()
        await bot_api.send_message(
            chat_id,
            f"✅ <b>{label} Updated!</b>\n\n<code>{esc(new_text)}</code>",
            reply_markup=_admin_back_markup(),
        )
        return

    # Handle broadcast states
    if state in ("bc_all", "bc_groups", "bc_users"):
        ADMIN_STATES.pop(uid, None)
        mode_map = {"bc_all": "all", "bc_groups": "groups", "bc_users": "users"}
        await execute_broadcast(chat_id, msg, mode_map[state])
        return


async def handle_admin_callback(cb: Dict[str, Any], data: str) -> None:
    cb_id = cb.get("id", "")
    from_user = cb.get("from") or {}
    msg = cb.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    msg_id = msg.get("message_id")
    uid = from_user.get("id") or 0

    # Strictly invisible to non-admins or outside private chat
    if chat_type != "private" or not is_admin_user(from_user) or not chat_id:
        await bot_api.answer_callback_query(cb_id)
        return

    is_photo_msg = bool(msg.get("photo"))

    async def _render_or_send(text: str, markup: Dict[str, Any]):
        if is_photo_msg or not msg_id:
            await bot_api.send_message(chat_id, text, reply_markup=markup)
        else:
            await bot_api.edit_message_text(chat_id, msg_id, text, reply_markup=markup)

    if data in ("adm_home", "adm_cancel"):
        ADMIN_STATES.pop(uid, None)
        await bot_api.answer_callback_query(cb_id)
        panel_text, panel_markup = build_admin_panel_View(chat_id)
        await _render_or_send(panel_text, panel_markup)
        return

    if data == "adm_preview":
        ADMIN_STATES.pop(uid, None)
        await bot_api.answer_callback_query(cb_id, "Sending /start preview...")
        await send_start_card(chat_id, from_user, "private", BOT_USERNAME_CACHE)
        return

    if data == "adm_set_photo":
        ADMIN_STATES[uid] = "set_photo"
        await bot_api.answer_callback_query(cb_id)
        await _render_or_send(
            "🖼 <b>Change Start Photo</b>\n\n"
            "Send the new <b>Photo</b> you want to display when users press <code>/start</code>.",
            _admin_cancel_markup(),
        )
        return

    if data == "adm_reset_photo":
        ADMIN_STATES.pop(uid, None)
        BOT_DATA["start_photo"] = ""
        save_bot_data()
        await bot_api.answer_callback_query(cb_id, "Start photo reset to default!")
        panel_text, panel_markup = build_admin_panel_View(chat_id)
        await _render_or_send(panel_text, panel_markup)
        return

    if data == "adm_set_header":
        ADMIN_STATES[uid] = "set_header"
        await bot_api.answer_callback_query(cb_id)
        cur = esc(BOT_DATA.get("header_title") or DEFAULT_HEADER_TITLE)
        await _render_or_send(
            f"🏷 <b>Edit Top Brand Header</b>\n\n"
            f"Current:\n<code>{cur}</code>\n\n"
            f"Send the new top header line now:",
            _admin_cancel_markup(),
        )
        return

    if data == "adm_set_intro":
        ADMIN_STATES[uid] = "set_intro"
        await bot_api.answer_callback_query(cb_id)
        cur = esc(BOT_DATA.get("welcome_intro") or DEFAULT_WELCOME_INTRO)
        await _render_or_send(
            f"✏️ <b>Edit Welcome Text</b>\n\n"
            f"Current:\n<code>{cur}</code>\n\n"
            f"Send the new welcome description text now:",
            _admin_cancel_markup(),
        )
        return

    if data == "adm_set_footer":
        ADMIN_STATES[uid] = "set_footer"
        await bot_api.answer_callback_query(cb_id)
        cur = esc(BOT_DATA.get("welcome_footer") or DEFAULT_WELCOME_FOOTER)
        await _render_or_send(
            f"📝 <b>Edit Bottom Welcome Line</b>\n\n"
            f"Current:\n<code>{cur}</code>\n\n"
            f"Send the new bottom line text now:",
            _admin_cancel_markup(),
        )
        return

    if data == "adm_reset_text":
        ADMIN_STATES.pop(uid, None)
        BOT_DATA["header_title"] = DEFAULT_HEADER_TITLE
        BOT_DATA["welcome_intro"] = DEFAULT_WELCOME_INTRO
        BOT_DATA["welcome_footer"] = DEFAULT_WELCOME_FOOTER
        save_bot_data()
        await bot_api.answer_callback_query(cb_id, "Welcome texts restored to defaults!")
        panel_text, panel_markup = build_admin_panel_View(chat_id)
        await _render_or_send(panel_text, panel_markup)
        return

    if data in ("adm_bc_all", "adm_bc_groups", "adm_bc_users"):
        state_key = data.replace("adm_", "")
        ADMIN_STATES[uid] = state_key
        await bot_api.answer_callback_query(cb_id)
        target_label = {
            "bc_all": f"All Groups ({len(BOT_DATA['groups'])}) + Users ({len(BOT_DATA['users'])})",
            "bc_groups": f"All Groups ({len(BOT_DATA['groups'])})",
            "bc_users": f"All Private Users ({len(BOT_DATA['users'])})",
        }[state_key]
        await _render_or_send(
            f"📢 <b>Broadcast Post</b>\n\n"
            f"‣ <b>Target :</b> <code>{target_label}</code>\n\n"
            f"Send or forward ANY message (text, photo with caption, video, audio, or post with buttons) now to publish immediately:",
            _admin_cancel_markup(),
        )
        return


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


async def handle_ping(msg: Dict[str, Any], chat_id: int, is_group: bool):
    t0 = time.perf_counter()
    msg_id = msg.get("message_id")
    if is_group:
        await bot_api.delete_message(chat_id, msg_id)
    sent = await bot_api.send_message(chat_id, "➜ <b>Pinging...</b>")
    latency_ms = (time.perf_counter() - t0) * 1000
    asst_status = "Online" if user.is_connected else "Offline"
    uptime_str, _, cpu_str, ram_str = get_live_system_stats()
    await bot_api.edit_message_text(
        chat_id,
        sent["message_id"],
        f"➜ <b>{esc(config.BOT_NAME)} Status</b> |\n\n"
        f"‣ <b>Latency :</b> <code>{latency_ms:.0f} ms</code>\n"
        f"‣ <b>Uptime :</b> <code>{uptime_str}</code>\n"
        f"‣ <b>CPU / RAM :</b> <code>{cpu_str} / {ram_str}</code>\n"
        f"‣ <b>Assistant :</b> {asst_status} (<code>@{esc(ASSISTANT_USERNAME)}</code>)\n"
        f"‣ <b>Active Streams :</b> <code>{len(CURRENT_PLAYING)}</code>",
        reply_markup=build_close_button(chat_id),
    )
    if is_group:
        schedule_delete(chat_id, sent["message_id"], delay=AUTO_DELETE_SECONDS)


async def handle_play_private(msg: Dict[str, Any], chat_id: int, bot_username: str):
    buttons = {
        "inline_keyboard": [
            [
                {
                    "text": "➕ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ",
                    "url": f"https://t.me/{bot_username}?startgroup=true",
                }
            ],
            [{"text": "Close", "callback_data": f"close|{chat_id}"}],
        ]
    }
    await bot_api.send_message(
        chat_id,
        f"➜ <b>Group Command Only</b> |\n\n"
        f"‣ <code>/play</code> works inside Telegram Group Voice Chats.\n"
        f"‣ Add <code>@{esc(bot_username)}</code> to your group, start a Voice Chat, and send <code>/play &lt;song name&gt;</code>.",
        reply_to_message_id=msg.get("message_id"),
        reply_markup=buttons,
    )


async def handle_play_group(msg: Dict[str, Any], chat_id: int, args: str):
    msg_id = msg.get("message_id")
    logger.info(f"Received /play in group {chat_id}: args='{args}'")

    if not config.STRING_SESSION or not user.is_connected:
        await send_temp_message(
            chat_id,
            "➜ <b>Assistant Offline</b> |\n\n"
            "‣ The Voice Assistant session is not connected yet.",
            delay=AUTO_DELETE_SECONDS,
            reply_markup=build_close_button(chat_id),
        )
        return

    replied = msg.get("reply_to_message") or {}
    replied_media = replied.get("audio") or replied.get("voice") or replied.get("video")
    own_media = msg.get("audio") or msg.get("voice") or msg.get("video")
    media_target = replied_media or own_media
    media_msg = replied if replied_media else msg

    if not args and not media_target:
        await bot_api.delete_message(chat_id, msg_id)
        await send_temp_message(
            chat_id,
            "➜ <b>Usage</b> |\n\n"
            "‣ <code>/play &lt;song name or link&gt;</code>\n"
            "‣ Or reply <code>/play</code> to an audio/MP3 file.",
            delay=AUTO_DELETE_SECONDS,
            reply_markup=build_close_button(chat_id),
        )
        return

    status_msg = await bot_api.send_message(
        chat_id,
        "🔎 <b>Searching...</b>",
        reply_to_message_id=msg_id,
    )
    status_mid = status_msg["message_id"]

    # Ensure Assistant Userbot is inside the group and peer-cached
    ok, err_html = await ensure_assistant_joined(chat_id)
    if not ok:
        await bot_api.edit_message_text(
            chat_id,
            status_mid,
            err_html,
            reply_markup=build_close_button(chat_id),
        )
        schedule_delete(chat_id, status_mid, delay=AUTO_DELETE_SECONDS)
        return

    from_user = msg.get("from") or {}
    requester_mention = user_mention_html(from_user)
    requester_plain = user_display_name(from_user)
    requester_id = from_user.get("id") or 0

    track: Optional[dict] = None
    if media_target and not args:
        try:
            await bot_api.edit_message_text(chat_id, status_mid, "📥 <b>Downloading audio...</b>")
            ext = ".mp3"
            if media_target.get("file_name"):
                _, parsed_ext = os.path.splitext(media_target["file_name"])
                if parsed_ext:
                    ext = parsed_ext
            dest_path = os.path.join(DOWNLOAD_DIR, f"tg_{chat_id}_{media_msg.get('message_id', int(time.time()))}{ext}")

            file_size = media_target.get("file_size") or 0
            if file_size > 19 * 1024 * 1024:
                pyro_msg = await user.get_messages(chat_id, media_msg["message_id"])
                file_path = await pyro_msg.download(file_name=dest_path)
            else:
                file_path = await bot_api.download_file(media_target["file_id"], dest_path)

            raw_title = media_target.get("title") or media_target.get("file_name") or "Telegram Audio"
            raw_performer = media_target.get("performer") or "Telegram Audio"
            dur_sec = int(media_target.get("duration") or 0)
            track = {
                "title": raw_title,
                "duration": format_duration(dur_sec),
                "duration_sec": dur_sec,
                "link": "https://t.me",
                "stream_url": file_path,
                "local_file": file_path,
                "thumbnail": "",
                "channel": raw_performer,
                "req_by": requester_mention,
                "req_plain": requester_plain,
                "req_id": requester_id,
            }
            # Delete user's /play command once found (do NOT delete if the user's message itself carried the audio file)
            if not own_media:
                await bot_api.delete_message(chat_id, msg_id)
        except Exception as dl_err:
            logger.error(f"Telegram media download failed: {dl_err}")
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                f"➜ <b>Download Failed</b> |\n\n‣ <code>{esc(dl_err)}</code>",
                reply_markup=build_close_button(chat_id),
            )
            schedule_delete(chat_id, status_mid, delay=AUTO_DELETE_SECONDS)
            return
    else:
        track = await search_ytdl(args)
        if not track or not track.get("stream_url"):
            await bot_api.delete_message(chat_id, msg_id)
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                "➜ <b>Track Not Found</b> |\n\n"
                "‣ Could not find an audio stream for that query.",
                reply_markup=build_close_button(chat_id),
            )
            schedule_delete(chat_id, status_mid, delay=AUTO_DELETE_SECONDS)
            return

        # Track found! Immediately auto-delete user's `/play <query>` message in group
        await bot_api.delete_message(chat_id, msg_id)

        track["req_by"] = requester_mention
        track["req_plain"] = requester_plain
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
        await bot_api.delete_message(chat_id, status_mid)
        await send_stream_ui_card(
            chat_id,
            track,
            header=f"Added To Queue #{pos}",
            reply_to_message_id=None,
            with_controls=True,
            track_as_active=False,
            auto_delete_after=AUTO_DELETE_SECONDS,
        )
        return

    # Start Playing Immediately in Group Voice Chat
    try:
        CURRENT_PLAYING[chat_id] = track
        PAUSED_CHATS.discard(chat_id)

        stream_source = await get_playable_audio_source(track)
        try:
            await pytgcalls.join_group_call(
                chat_id,
                get_audio_stream(stream_source),
            )
        except AlreadyJoinedError:
            await pytgcalls.change_stream(
                chat_id,
                get_audio_stream(stream_source),
            )

        await bot_api.delete_message(chat_id, status_mid)
        logger.info(f"Started streaming '{track['title']}' in chat {chat_id} ✅")

        await send_stream_ui_card(
            chat_id,
            track,
            header="Started Streaming",
            reply_to_message_id=None,
            with_controls=True,
            track_as_active=True,
        )

    except (NoActiveGroupCall, GroupCallNotFound):
        CURRENT_PLAYING.pop(chat_id, None)
        await bot_api.edit_message_text(
            chat_id,
            status_mid,
            "➜ <b>No Active Voice Chat</b> |\n\n"
            "‣ Please start a <b>Voice Chat</b> in this group first and send <code>/play</code> again.",
            reply_markup=build_close_button(chat_id),
        )
        schedule_delete(chat_id, status_mid, delay=AUTO_DELETE_SECONDS)
    except Exception as e:
        logger.error(f"Playback initiation error in {chat_id}: [{type(e).__name__}] {e}")
        CURRENT_PLAYING.pop(chat_id, None)
        if "GROUPCALL_FORBIDDEN" in str(e).upper() or "CALL_PROTOCOL" in str(e).upper():
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                "➜ <b>Voice Chat Permission Required</b> |\n\n"
                f"‣ Ensure Voice Chat is active and <code>@{esc(ASSISTANT_USERNAME)}</code> has permission to speak.",
                reply_markup=build_close_button(chat_id),
            )
        else:
            await bot_api.edit_message_text(
                chat_id,
                status_mid,
                f"➜ <b>Playback Error</b> |\n\n‣ <code>{esc(type(e).__name__)}: {esc(e)}</code>",
                reply_markup=build_close_button(chat_id),
            )
        schedule_delete(chat_id, status_mid, delay=AUTO_DELETE_SECONDS)


async def handle_message_update(msg: Dict[str, Any], bot_username: str):
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    if not chat_id:
        return

    record_chat_activity(chat_id, chat_type)

    from_user = msg.get("from") or {}
    uid = from_user.get("id") or 0
    is_group = chat_type in ("group", "supergroup")
    msg_id = msg.get("message_id")
    actor = user_display_name(from_user)

    cmd, args = parse_command(msg, bot_username)

    # Handle Owner conversation state in private chat
    if chat_type == "private" and uid in ADMIN_STATES and is_admin_user(from_user):
        if cmd in ("cancel",):
            ADMIN_STATES.pop(uid, None)
            panel_text, panel_markup = build_admin_panel_View(chat_id)
            await bot_api.send_message(chat_id, panel_text, reply_markup=panel_markup)
            return
        if cmd not in ("start", "admin"):
            await handle_admin_state_input(msg, chat_id, uid, ADMIN_STATES[uid])
            return
        ADMIN_STATES.pop(uid, None)

    if not cmd:
        return

    # Secret Owner-only /admin command (100% silent to everyone else)
    if cmd == "admin":
        if chat_type == "private" and is_admin_user(from_user):
            panel_text, panel_markup = build_admin_panel_View(chat_id)
            await bot_api.send_message(chat_id, panel_text, reply_markup=panel_markup)
        return

    if cmd == "start":
        logger.info(f"Received /start from {from_user.get('first_name')} in chat {chat_id} ({chat_type})")
        await send_start_card(chat_id, from_user, chat_type, bot_username, reply_to_message_id=msg_id)
    elif cmd == "ping":
        await handle_ping(msg, chat_id, is_group)
    elif cmd in ("play", "p"):
        if is_group:
            await handle_play_group(msg, chat_id, args)
        else:
            await handle_play_private(msg, chat_id, bot_username)
    elif cmd == "pause" and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        if chat_id not in CURRENT_PLAYING:
            await send_temp_message(chat_id, "➜ Nothing is currently streaming.")
            return
        if chat_id in PAUSED_CHATS:
            await send_temp_message(chat_id, "II Stream is already paused.")
            return
        try:
            await pytgcalls.pause_stream(chat_id)
            PAUSED_CHATS.add(chat_id)
            await send_temp_message(chat_id, f"II <b>Stream Paused</b> |\n‣ <b>By :</b> {actor}")
        except Exception as e:
            await send_temp_message(chat_id, f"➜ Error pausing stream: <code>{esc(e)}</code>")
    elif cmd == "resume" and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        if chat_id not in CURRENT_PLAYING:
            await send_temp_message(chat_id, "➜ Nothing is currently streaming.")
            return
        if chat_id not in PAUSED_CHATS:
            await send_temp_message(chat_id, "▷ Stream is already playing.")
            return
        try:
            await pytgcalls.resume_stream(chat_id)
            PAUSED_CHATS.discard(chat_id)
            await send_temp_message(chat_id, f"▷ <b>Stream Resumed</b> |\n‣ <b>By :</b> {actor}")
        except Exception as e:
            await send_temp_message(chat_id, f"➜ Error resuming stream: <code>{esc(e)}</code>")
    elif cmd == "replay" and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        current = CURRENT_PLAYING.get(chat_id)
        if not current:
            await send_temp_message(chat_id, "➜ Nothing is currently streaming.")
            return
        try:
            stream_source = await get_playable_audio_source(current)
            await pytgcalls.change_stream(chat_id, get_audio_stream(stream_source))
            PAUSED_CHATS.discard(chat_id)
            await send_temp_message(chat_id, f"↻ <b>Stream Replayed</b> |\n‣ <b>By :</b> {actor}")
        except Exception as e:
            await send_temp_message(chat_id, f"➜ Error replaying stream: <code>{esc(e)}</code>")
    elif cmd in ("skip", "next") and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        if chat_id not in CURRENT_PLAYING:
            await send_temp_message(chat_id, "➜ Nothing is currently streaming.")
            return
        await send_temp_message(
            chat_id,
            f"‣‣I <b>Stream Skipped</b> |\n‣ <b>By :</b> {actor}",
            delay=AUTO_DELETE_SECONDS,
        )
        await play_next_track(chat_id)
    elif cmd in ("stop", "end") and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        old = CURRENT_PLAYING.pop(chat_id, None)
        if old and old.get("local_file") and os.path.exists(old["local_file"]):
            try:
                os.remove(old["local_file"])
            except Exception:
                pass
        QUEUES.pop(chat_id, None)
        PAUSED_CHATS.discard(chat_id)
        await clear_active_stream_card(chat_id)
        cleanup_storage_and_memory()
        try:
            await pytgcalls.leave_group_call(chat_id)
            await send_temp_message(
                chat_id,
                f"▢ <b>Stream Ended</b> |\n‣ <b>By :</b> {actor}",
                delay=AUTO_DELETE_SECONDS,
            )
        except (GroupCallNotFound, NotInGroupCallError):
            await send_temp_message(chat_id, "▢ Bot is not in an active Voice Chat.")
        except Exception as e:
            await send_temp_message(chat_id, f"▢ Left Voice Chat. (<code>{esc(e)}</code>)")
    elif cmd in ("queue", "q") and is_group:
        await bot_api.delete_message(chat_id, msg_id)
        current = CURRENT_PLAYING.get(chat_id)
        chat_queue = QUEUES.get(chat_id, [])
        if not current and not chat_queue:
            await send_temp_message(
                chat_id,
                "➜ <b>Queue Is Empty</b> | No tracks are currently playing.",
                delay=AUTO_DELETE_SECONDS,
            )
            return
        text = "➜ <b>Playback Queue</b> |\n\n"
        if current:
            state_tag = "Paused" if chat_id in PAUSED_CHATS else "Playing"
            text += (
                f"‣ <b>Now {state_tag} :</b> <a href=\"{esc(current['link'])}\">{esc(current['title'])}</a>\n"
                f"  <code>{esc(current['duration'])}</code> • {current.get('req_plain') or current['req_by']}\n\n"
            )
        if chat_queue:
            text += "‣ <b>Up Next :</b>\n"
            for idx, song in enumerate(chat_queue[:10], 1):
                text += (
                    f"  <code>{idx}.</code> <a href=\"{esc(song['link'])}\">{esc(song['title'])}</a> "
                    f"(<code>{esc(song['duration'])}</code>) • {song.get('req_plain') or song['req_by']}\n"
                )
            if len(chat_queue) > 10:
                text += f"\n<i>...and {len(chat_queue) - 10} more track(s) in queue.</i>"
        else:
            text += "<i>No upcoming tracks in queue.</i>"
        await send_temp_message(
            chat_id,
            text,
            delay=AUTO_DELETE_SECONDS,
            reply_markup=build_close_button(chat_id),
        )


async def handle_callback_update(cb: Dict[str, Any]):
    cb_id = cb.get("id", "")
    data = cb.get("data") or ""
    msg = cb.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    msg_id = msg.get("message_id")

    if data.startswith("adm_"):
        await handle_admin_callback(cb, data)
        return

    if data == "close":
        await bot_api.answer_callback_query(cb_id)
        if chat_id and msg_id:
            await bot_api.delete_message(chat_id, msg_id)
        return

    sep = "|" if "|" in data else "_"
    parts = data.split(sep, 1)
    if len(parts) != 2:
        await bot_api.answer_callback_query(cb_id)
        return

    action, raw_chat = parts
    if action == "close":
        await bot_api.answer_callback_query(cb_id)
        if chat_id and msg_id:
            if ACTIVE_STREAM_CARD_MSG.get(chat_id) == msg_id:
                ACTIVE_STREAM_CARD_MSG.pop(chat_id, None)
            await bot_api.delete_message(chat_id, msg_id)
        return

    try:
        target_chat = int(raw_chat)
    except ValueError:
        await bot_api.answer_callback_query(cb_id)
        return

    actor = user_display_name(cb.get("from"))

    if action == "pause":
        if target_chat not in CURRENT_PLAYING:
            await bot_api.answer_callback_query(cb_id, "Nothing is currently streaming!", show_alert=True)
            return
        if target_chat in PAUSED_CHATS:
            await bot_api.answer_callback_query(cb_id, "Stream is already paused!", show_alert=True)
            return
        try:
            await pytgcalls.pause_stream(target_chat)
            PAUSED_CHATS.add(target_chat)
            await bot_api.answer_callback_query(cb_id, "Stream Paused!")
            await send_temp_message(
                target_chat,
                f"II <b>Stream Paused</b> |\n‣ <b>By :</b> {actor}",
                delay=AUTO_DELETE_SECONDS,
            )
        except Exception as e:
            await bot_api.answer_callback_query(cb_id, f"Error: {e}", show_alert=True)

    elif action == "resume":
        if target_chat not in CURRENT_PLAYING:
            await bot_api.answer_callback_query(cb_id, "Nothing is currently streaming!", show_alert=True)
            return
        if target_chat not in PAUSED_CHATS:
            await bot_api.answer_callback_query(cb_id, "Stream is already playing!", show_alert=True)
            return
        try:
            await pytgcalls.resume_stream(target_chat)
            PAUSED_CHATS.discard(target_chat)
            await bot_api.answer_callback_query(cb_id, "Stream Resumed!")
            await send_temp_message(
                target_chat,
                f"▷ <b>Stream Resumed</b> |\n‣ <b>By :</b> {actor}",
                delay=AUTO_DELETE_SECONDS,
            )
        except Exception as e:
            await bot_api.answer_callback_query(cb_id, f"Error: {e}", show_alert=True)

    elif action == "replay":
        current = CURRENT_PLAYING.get(target_chat)
        if not current:
            await bot_api.answer_callback_query(cb_id, "Nothing is currently streaming!", show_alert=True)
            return
        try:
            stream_source = await get_playable_audio_source(current)
            await pytgcalls.change_stream(target_chat, get_audio_stream(stream_source))
            PAUSED_CHATS.discard(target_chat)
            await bot_api.answer_callback_query(cb_id, "Replaying current track!")
            await send_temp_message(
                target_chat,
                f"↻ <b>Stream Replayed</b> |\n‣ <b>By :</b> {actor}",
                delay=AUTO_DELETE_SECONDS,
            )
        except Exception as e:
            await bot_api.answer_callback_query(cb_id, f"Error: {e}", show_alert=True)

    elif action == "skip":
        if target_chat not in CURRENT_PLAYING:
            await bot_api.answer_callback_query(cb_id, "Nothing is currently streaming!", show_alert=True)
            return
        await bot_api.answer_callback_query(cb_id, "Skipping track...")
        await send_temp_message(
            target_chat,
            f"‣‣I <b>Stream Skipped</b> |\n‣ <b>By :</b> {actor}",
            delay=AUTO_DELETE_SECONDS,
        )
        await play_next_track(target_chat)

    elif action == "stop":
        if target_chat not in CURRENT_PLAYING and not QUEUES.get(target_chat):
            await bot_api.answer_callback_query(cb_id, "Nothing is currently streaming!", show_alert=True)
            return
        old = CURRENT_PLAYING.pop(target_chat, None)
        if old and old.get("local_file") and os.path.exists(old["local_file"]):
            try:
                os.remove(old["local_file"])
            except Exception:
                pass
        QUEUES.pop(target_chat, None)
        PAUSED_CHATS.discard(target_chat)
        await clear_active_stream_card(target_chat)
        cleanup_storage_and_memory()
        try:
            await pytgcalls.leave_group_call(target_chat)
        except Exception:
            pass
        await bot_api.answer_callback_query(cb_id, "Stream Stopped!")
        await send_temp_message(
            target_chat,
            f"▢ <b>Stream Ended</b> |\n‣ <b>By :</b> {actor}",
            delay=AUTO_DELETE_SECONDS,
        )


async def handle_my_chat_member_update(upd: Dict[str, Any]):
    """Track group membership changes and auto-invite Assistant when Bot becomes Admin."""
    try:
        new_member = upd.get("new_chat_member") or {}
        new_status = new_member.get("status", "")
        chat = upd.get("chat") or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type", "")
        if not chat_id:
            return

        if chat_type in ("group", "supergroup"):
            if new_status in ("left", "kicked"):
                remove_dead_chat(chat_id)
                return
            record_chat_activity(chat_id, chat_type)
            if new_status == "administrator" and user.is_connected:
                logger.info(f"Bot promoted to Admin in {chat_id} ({chat.get('title')}); auto-joining Assistant...")
                await ensure_assistant_joined(chat_id)
        elif chat_type == "private":
            if new_status == "kicked":
                remove_dead_chat(chat_id)
            elif new_status == "member":
                record_chat_activity(chat_id, "private")
    except Exception as e:
        logger.debug(f"my_chat_member update notice: {e}")


# ==========================================================
# Long-Polling Loop
# ==========================================================
async def poll_bot_updates(bot_username: str, stop_event: asyncio.Event):
    offset: Optional[int] = None
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
    global BOT_USERNAME_CACHE, ASSISTANT_USERNAME
    ensure_card_fonts()
    ensure_default_start_banner()
    save_bot_data()

    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            MAIN_LOOP.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    logger.info("Starting Telegram Music Bot (HTTP Bot API)...")
    bot_me = await bot_api.start()
    bot_username = bot_me.get("username", "marioxnmusic_bot")
    BOT_USERNAME_CACHE = bot_username
    logger.info(f"Bot started successfully as @{bot_username} ({bot_me.get('id')})")

    # Register only clean essential public commands (zero clutter, zero admin leakage)
    await bot_api.set_my_commands(
        [
            {"command": "start", "description": "Start the music player"},
            {"command": "play", "description": "Play a song in Voice Chat"},
            {"command": "skip", "description": "Skip to the next queued track"},
            {"command": "pause", "description": "Pause current playback"},
            {"command": "resume", "description": "Resume paused playback"},
            {"command": "stop", "description": "Stop music and leave Voice Chat"},
            {"command": "queue", "description": "Show current song queue"},
        ]
    )

    if config.STRING_SESSION:
        try:
            logger.info("Starting Assistant User Client...")
            await user.start()
            user_me = await user.get_me()
            if user_me.username:
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

            for active_gid in list(BOT_DATA.get("groups", [])):
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

    # Optional HTTP health-check server when PORT env var is provided (e.g. Koyeb / Render / HF Spaces Docker)
    health_runner = None
    port_env = os.getenv("PORT", "").strip()
    if port_env.isdigit():
        try:
            from aiohttp import web

            async def _health_handler(_request: web.Request) -> web.Response:
                return web.json_response(
                    {
                        "ok": True,
                        "service": config.BOT_NAME,
                        "bot": f"@{bot_username}",
                        "uptime_seconds": int(time.time() - BOT_START_TIME),
                    }
                )

            health_app = web.Application()
            health_app.router.add_get("/", _health_handler)
            health_app.router.add_get("/health", _health_handler)
            health_runner = web.AppRunner(health_app, access_log=None)
            await health_runner.setup()
            health_site = web.TCPSite(health_runner, "0.0.0.0", int(port_env))
            await health_site.start()
            logger.info(f"HTTP health-check server listening on 0.0.0.0:{port_env}")
        except Exception as he:
            logger.warning(f"Optional health-check server skipped: {he}")

    async def _memory_trimmer_loop():
        while not stop_event.is_set():
            try:
                await asyncio.sleep(30)
                cleanup_storage_and_memory()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    mem_task = asyncio.create_task(_memory_trimmer_loop())
    poll_task = asyncio.create_task(poll_bot_updates(bot_username, stop_event))
    await stop_event.wait()

    logger.info("Stopping Bot & Clients gracefully...")
    mem_task.cancel()
    poll_task.cancel()
    try:
        await asyncio.gather(mem_task, poll_task, return_exceptions=True)
    except Exception:
        pass
    if health_runner is not None:
        try:
            await health_runner.cleanup()
        except Exception:
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
