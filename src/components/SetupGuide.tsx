import React, { useState } from 'react';
import {
  Server,
  Smartphone,
  Container,
  KeyRound,
  ShieldCheck,
  Terminal,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Info,
  AlertTriangle,
} from 'lucide-react';

interface SetupGuideProps {
  lang: 'mm' | 'en';
}

export const SetupGuide: React.FC<SetupGuideProps> = ({ lang }) => {
  const [activePlatform, setActivePlatform] = useState<'vps' | 'termux' | 'docker' | 'session'>('vps');
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedSnippet(id);
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Header Banner */}
      <div className="mb-6 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-5 sm:p-6">
        <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider">
          <Server className="h-4 w-4" />
          <span>{lang === 'mm' ? 'တပ်ဆင်နည်း ပြည့်စုံသော လမ်းညွှန်' : 'Comprehensive Deployment Guide'}</span>
        </div>
        <h2 className="mt-1 text-xl sm:text-2xl font-bold text-white">
          {lang === 'mm'
            ? 'Telegram Music Bot ကို အစမှ အဆုံး တပ်ဆင် Run နည်း'
            : 'How to Deploy & Run Your Telegram Group Music Bot'}
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-300">
          {lang === 'mm'
            ? 'Linux VPS, Android Termux, Docker သို့မဟုတ် Local PC ပေါ်တွင် အလွယ်တကူ တပ်ဆင် run နိုင်သော အဆင့်ဆင့် နည်းလမ်းများ။'
            : 'Step-by-step instructions for Linux VPS, Android Termux, Docker containers, and String Session generation.'}
        </p>
      </div>

      {/* Platform Selector Tabs */}
      <div className="mb-6 flex flex-wrap gap-2">
        {[
          { id: 'vps', labelEn: 'Linux VPS (Ubuntu / Debian)', labelMm: 'Linux VPS (Ubuntu/Debian)', icon: Server },
          { id: 'session', labelEn: 'String Session Generator', labelMm: 'String Session ထုတ်ယူနည်း', icon: KeyRound },
          { id: 'termux', labelEn: 'Android Termux', labelMm: 'Android ဖုန်း (Termux)', icon: Smartphone },
          { id: 'docker', labelEn: 'Docker / Heroku', labelMm: 'Docker / Cloud', icon: Container },
        ].map((tab) => {
          const Icon = tab.icon;
          const isSelected = activePlatform === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActivePlatform(tab.id as any)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold transition-all cursor-pointer ${
                isSelected
                  ? 'border border-cyan-500/50 bg-cyan-600/20 text-cyan-300 shadow-md shadow-cyan-500/10'
                  : 'border border-slate-800 bg-slate-900/70 text-slate-400 hover:border-slate-700 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{lang === 'mm' ? tab.labelMm : tab.labelEn}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-8 space-y-6">
          {/* VPS Tab */}
          {activePlatform === 'vps' && (
            <div className="space-y-4">
              {/* Step 1 */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600/20 text-cyan-400 font-bold text-xs border border-cyan-500/40">
                    1
                  </span>
                  <h3 className="text-sm font-bold text-slate-100">
                    {lang === 'mm' ? 'System Dependencies & FFmpeg တပ်ဆင်ခြင်း' : 'Install System Packages & FFmpeg'}
                  </h3>
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  {lang === 'mm'
                    ? 'Voice Chat သို့ အသံ stream လုပ်ရန် FFmpeg သည် မဖြစ်မနေ လိုအပ်ပါသည်။'
                    : 'FFmpeg is strictly required by PyTgCalls for processing and converting audio streams.'}
                </p>

                <div className="mt-3 relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv ffmpeg git curl -y`}</pre>
                  <button
                    onClick={() => copyCode('sudo apt update && sudo apt upgrade -y\nsudo apt install python3 python3-pip python3-venv ffmpeg git curl -y', 'vps-1')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'vps-1' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>

              {/* Step 2 */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600/20 text-cyan-400 font-bold text-xs border border-cyan-500/40">
                    2
                  </span>
                  <h3 className="text-sm font-bold text-slate-100">
                    {lang === 'mm' ? 'Python Library များကို Install ပြုလုပ်ခြင်း' : 'Install Python Requirements'}
                  </h3>
                </div>

                <div className="mt-3 relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`pip3 install -U pip setuptools wheel
pip3 install -r requirements.txt`}</pre>
                  <button
                    onClick={() => copyCode('pip3 install -U pip setuptools wheel\npip3 install -r requirements.txt', 'vps-2')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'vps-2' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>

              {/* Step 3 */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600/20 text-cyan-400 font-bold text-xs border border-cyan-500/40">
                    3
                  </span>
                  <h3 className="text-sm font-bold text-slate-100">
                    {lang === 'mm' ? 'Bot ကို နောက်ကွယ်တွင် အမြဲ Run ထားနည်း (Screen / Systemd)' : 'Run Bot 24/7 in Background'}
                  </h3>
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  {lang === 'mm'
                    ? 'SSH window ပိတ်သွားသော်လည်း Bot ဆက်လက် run နေစေရန် Screen ကို သုံးနိုင်ပါသည်။'
                    : 'Use screen so the bot stays online 24/7 even after closing terminal.'}
                </p>

                <div className="mt-3 relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`# Start screen session
screen -S musicbot

# Run Python Bot
python3 main.py

# Detach from screen: Press CTRL + A, then D
# Re-attach to screen: screen -r musicbot`}</pre>
                  <button
                    onClick={() => copyCode('screen -S musicbot\npython3 main.py', 'vps-3')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'vps-3' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Session Generator Tab */}
          {activePlatform === 'session' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="flex items-center gap-2 text-amber-400 mb-2">
                  <AlertTriangle className="h-4 w-4" />
                  <h3 className="text-sm font-bold text-slate-100">
                    {lang === 'mm' ? 'String Session ဆိုသည်မှာ အဘယ်နည်း?' : 'Why is STRING_SESSION required?'}
                  </h3>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {lang === 'mm'
                    ? 'Telegram Bot API သည် Group Voice Chat ထဲသို့ တိုက်ရိုက် join ၍ အသံ stream မလုပ်နိုင်ပါ။ ထို့ကြောင့် Voice Chat ထဲသို့ ဝင်ရောက် stream ရန် Assistant User Account (Telegram အကောင့်တစ်ခု) လိုအပ်ပါသည်။ Pyrogram String Session သည် ထိုအကောင့်၏ login session ဖြစ်ပါသည်။'
                    : 'Telegram Bot API bots cannot directly join Voice Chats. A Telegram User Account (Assistant Userbot) is required by PyTgCalls to stream audio. The STRING_SESSION authorizes this assistant.'}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <h3 className="text-sm font-bold text-slate-100 mb-2">
                  {lang === 'mm' ? 'Session ထုတ်ယူရန် Command' : 'Command to Generate Session'}
                </h3>
                <p className="text-xs text-slate-400 mb-3">
                  {lang === 'mm'
                    ? 'သင့်စက် သို့မဟုတ် VPS ထဲတွင် အောက်ပါ command ကို run ပြီး ဖုန်းနံပါတ်၊ Telegram login code ရိုက်ထည့်ပါ။'
                    : 'Run this command in your terminal and enter your phone number with country code:'}
                </p>

                <div className="relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`python3 generate_session.py`}</pre>
                  <button
                    onClick={() => copyCode('python3 generate_session.py', 'session-1')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'session-1' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>

                <div className="mt-4 rounded-xl bg-emerald-950/30 border border-emerald-500/30 p-3.5 text-xs text-emerald-200">
                  <p className="font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    {lang === 'mm' ? 'ရရှိလာသော String Session ကို ထည့်နည်း:' : 'How to set STRING_SESSION:'}
                  </p>
                  <p className="mt-1 text-[11px] text-emerald-300/80 font-mono">
                    export STRING_SESSION="1BVtsOI..." သို့မဟုတ် config.py ထဲတွင် STRING_SESSION = "..."
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Termux Tab */}
          {activePlatform === 'termux' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <h3 className="text-sm font-bold text-slate-100 mb-2">
                  {lang === 'mm' ? 'Android ဖုန်း Termux တွင် Run နည်း' : 'Run on Android using Termux'}
                </h3>
                <p className="text-xs text-slate-400 mb-3">
                  {lang === 'mm'
                    ? 'Android ဖုန်းတွင် F-Droid မှ Termux ကို install ပြုလုပ်ပြီး အောက်ပါ command များကို အစဉ်လိုက် run ပါ။'
                    : 'Download Termux from F-Droid and run the following setup commands:'}
                </p>

                <div className="relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`pkg update && pkg upgrade -y
pkg install python ffmpeg git clang libffi openssl -y
pip install --upgrade pip
pip install -r requirements.txt
python main.py`}</pre>
                  <button
                    onClick={() => copyCode('pkg update && pkg upgrade -y\npkg install python ffmpeg git clang libffi openssl -y\npip install --upgrade pip\npip install -r requirements.txt\npython main.py', 'termux-1')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'termux-1' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Docker Tab */}
          {activePlatform === 'docker' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <h3 className="text-sm font-bold text-slate-100 mb-2">
                  {lang === 'mm' ? 'Docker ဖြင့် Containerize ပြုလုပ်၍ Run နည်း' : 'Build & Run with Docker'}
                </h3>

                <div className="relative rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{`# Build Docker image
docker build -t telegram-music-bot .

# Run Container with environment variables
docker run -d --name tg-music-bot \\
  -e STRING_SESSION="your_string_session_here" \\
  telegram-music-bot`}</pre>
                  <button
                    onClick={() => copyCode('docker build -t telegram-music-bot .\ndocker run -d --name tg-music-bot -e STRING_SESSION="your_string_session_here" telegram-music-bot', 'docker-1')}
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
                  >
                    {copiedSnippet === 'docker-1' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Group Setup Checklist */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg">
            <div className="flex items-center gap-2 text-cyan-400 mb-3">
              <ShieldCheck className="h-5 w-5" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                {lang === 'mm' ? 'Telegram Group တာဝန်ပေးချက် Checklist' : 'Telegram Group Permissions Checklist'}
              </h3>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-2.5 rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">
                  ✓
                </span>
                <div>
                  <p className="font-semibold text-slate-200">
                    {lang === 'mm' ? 'Bot ကို Admin ပေးပါ' : 'Promote Bot as Admin'}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {lang === 'mm'
                      ? 'Messages ဖျက်ခွင့်၊ Links ဖိတ်ခွင့် နှင့် Voice Chat စီမံခွင့်ပေးပါ။'
                      : 'Grant Delete Messages, Invite Users, and Manage Voice Chats.'}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-2.5 rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">
                  ✓
                </span>
                <div>
                  <p className="font-semibold text-slate-200">
                    {lang === 'mm' ? 'Assistant Userbot ကို Group ထဲ ထည့်ပါ' : 'Add Assistant Account'}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {lang === 'mm'
                      ? 'STRING_SESSION ဖွင့်ထားသော Telegram အကောင့်ကို Group ထဲ add ပြီး Admin ပေးပါ။'
                      : 'Ensure the assistant account has permissions to speak in Voice Chat.'}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-2.5 rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">
                  ✓
                </span>
                <div>
                  <p className="font-semibold text-slate-200">
                    {lang === 'mm' ? 'Voice Chat ကို Start လုပ်ပါ' : 'Start Voice Chat'}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {lang === 'mm'
                      ? 'Group title ကို နှိပ်ပြီး "Start Voice Chat" (သို့မဟုတ် Video Chat) ကို ဖွင့်ပါ။'
                      : 'Open group settings and click Start Voice Chat before sending /play.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
