# 🎵 Mario Music — Telegram Group Voice Chat Music Bot

High-performance 24/7 Telegram Group Voice Chat Music Bot powered by **Async Telegram Bot API + Pyrogram v2 + PyTgCalls + yt-dlp + Pillow Frosted-Glass Artwork Engine**.

---

## 🚀 GitHub + Wispbyte 24/7 Run နည်း (အဆင့်ဆင့် လမ်းညွှန်)

ဤ Repository တွင် **Wispbyte Free/Paid Python Container** အတွက် လိုအပ်သော `FFmpeg` နှင့် `Node.js` binary များကို `requirements.txt` မှတစ်ဆင့် အလိုအလျောက် ထည့်သွင်းပေးထားပြီး ဖြစ်ပါသည် (`sudo` သို့မဟုတ် `apt` မလိုအပ်ပါ)။

### ၁။ GitHub သို့ Push / Export လုပ်ပါ
- AI Studio မှ GitHub Repository (Private repo ထားရန် အကြံပြုပါသည် — `config.py` ထဲတွင် Token နှင့် Session ပါဝင်သောကြောင့်) သို့ Export/Push လုပ်ပါ။

### ၂။ Wispbyte Panel တွင် Server တည်ဆောက်ပါ
1. [Wispbyte Dashboard](https://wispbyte.com) တွင် **Python** Server တစ်ခု ဆောက်ပါ။
2. **Startup** tab သို့ သွားပြီး အောက်ပါအတိုင်း သတ်မှတ်ပါ —
   - **App py file / Main File**: `main.py`
   - **Requirements file**: `requirements.txt`
   - **Python Version (Docker Image)**: `Python 3.10` သို့မဟုတ် `Python 3.11` (အကောင်းဆုံး) — `3.12` လည်း အလုပ်လုပ်အောင် ပြင်ဆင်ပေးထားပါသည်။
3. **Git / GitHub Integration** ဖြင့် ချိတ်မည်ဆိုပါက —
   - **Git Repo Address**: သင့် GitHub Repo URL ထည့်ပါ။
   - **Install Branch**: `main`
   - Private Repo ဖြစ်ပါက GitHub Username နှင့် Personal Access Token (PAT) ထည့်ပေးပါ (သို့မဟုတ် Files tab တွင် ZIP တိုက်ရိုက် Upload လုပ်ပြီး Unarchive လုပ်နိုင်ပါသည်)။
4. **Console** tab သို့သွား၍ **Start** နှိပ်ပါ။ ပထမဆုံးအကြိမ် `requirements.txt` ကို အလိုအလျောက် install လုပ်ပြီးသည်နှင့် `🚀 Mario Music (@marioxnmusic_bot) is fully ACTIVE & READY!` ပေါ်လာပါမည်။

---

## 🎧 Commands (Public)
- `/start` — Live Server Stats + Welcome Banner (`Add Me To Your Group`, `Support`, `Owner`)
- `/play <song name / YouTube / SoundCloud URL>` — Group Voice Chat တွင် သီချင်းဖွင့်မည် (User ရိုက်လိုက်သော `/play` စာကို အလိုအလျောက် ဖျက်ပေးသည်)
- `/pause` — ခေတ္တရပ်မည်
- `/resume` — ပြန်ဖွင့်မည်
- `/skip` — နောက်တစ်ပုဒ် ကျော်မည် (15s auto-delete notice)
- `/stop` — သီချင်းရပ်ပြီး Voice Chat မှ ထွက်မည် (15s auto-delete notice)
- `/queue` — တန်းစီထားသော သီချင်းစာရင်း ကြည့်မည်

## 🔐 Secret Owner Admin Panel
- Bot Owner (`@Yes_Im_Mario`) တစ်ဦးတည်းသာ Bot ၏ Private Chat တွင် `/start` သို့မဟုတ် `/admin` နှိပ်ပါက **⚙️ Admin Panel** ပေါ်လာပြီး Start Photo ပြောင်းခြင်း၊ Welcome စာသားပြင်ခြင်း နှင့် Group/User အားလုံးသို့ Broadcast ပို့ခြင်း ပြုလုပ်နိုင်ပါသည်။
