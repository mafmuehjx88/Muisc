# 🎵 Telegram Group Music Bot (Pyrogram v2 + PyTgCalls + yt-dlp)

High-performance, production-ready Telegram Group Voice Chat Music Bot written in Python 3.

---

## 🇲🇲 မြန်မာဘာသာဖြင့် တပ်ဆင်နည်း (Myanmar Setup Guide)

### ၁။ လိုအပ်ချက်များ (Requirements)
1. **Telegram API ID & API HASH**: [my.telegram.org](https://my.telegram.org) မှ ရယူပါ။
2. **Bot Token**: Telegram [@BotFather](https://t.me/BotFather) တွင် bot အသစ်ဆောက်၍ token ရယူပါ။
3. **String Session**: Assistant Account အတွက် Pyrogram String Session ရယူပါ။
4. **FFmpeg**: အသံ stream လုပ်ရန် ကွန်ပျူတာ / VPS / Termux ထဲတွင် ffmpeg ထည့်ထားရမည်။

### ၂။ String Session ထုတ်ယူနည်း
```bash
pip install pyrogram tgcrypto
python generate_session.py
```
ဖုန်းနံပါတ်နှင့် Telegram login code ရိုက်ထည့်ပြီး ထွက်လာသော String Session ကို `config.py` သို့မဟုတ် Environment Variable ထဲ ထည့်ပါ။

### ၃။ Bot စတင် Run နည်း (Local / VPS / Termux)
```bash
# Clone or setup folder
pip install -r requirements.txt

# Run Bot
python main.py
```

### ၄။ Group ထဲ အသုံးပြုနည်း
1. သင့် Telegram Group ထဲသို့ Bot နှင့် Assistant User Account ကို **Admin** အဖြစ် Add ပါ (Voice Chat Permissions ပေးပါ)။
2. Group ထဲတွင် **Voice Chat (Video Chat)** ကို ဖွင့် (Start) ပါ။
3. Group ထဲတွင် `/play <သီချင်းအမည် သို့မဟုတ် YouTube link>` ဟု ရိုက်ပို့ပါ။

---

## 🇬🇧 English Setup Guide

### 1. Requirements
- Python 3.9+
- FFmpeg installed (`apt-get install ffmpeg` on Linux, `brew install ffmpeg` on macOS, `pkg install ffmpeg` on Termux)
- Telegram `API_ID`, `API_HASH`, `BOT_TOKEN`, and `STRING_SESSION`.

### 2. Available Commands
- `/play <song name / yt url>` - Stream audio in Group Voice Chat.
- `/pause` - Pause currently playing stream.
- `/resume` - Resume the paused audio stream.
- `/skip` - Skip current track to the next one in queue.
- `/stop` or `/end` - Stop playback, clear queue, and leave voice chat.
- `/queue` - Display currently active queue.
- `/help` - Show command instructions.
