import React, { useState } from 'react';
import {
  Server,
  Smartphone,
  Cloud,
  Terminal,
  Check,
  Copy,
  Download,
  ShieldCheck,
  Loader2,
  AlertTriangle,
} from 'lucide-react';

interface SetupGuideProps {
  lang: 'mm' | 'en';
}

type MethodId = 'codespaces' | 'botpanel' | 'ssh_vps' | 'termux';

export const SetupGuide: React.FC<SetupGuideProps> = ({ lang }) => {
  const [activeMethod, setActiveMethod] = useState<MethodId>('botpanel');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [downloadingScript, setDownloadingScript] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [copyingOneLiner, setCopyingOneLiner] = useState(false);
  const [repoUrl, setRepoUrl] = useState('https://github.com/YOUR_USERNAME/Muisc.git');

  const copyText = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2200);
    } catch {
      // ignore clipboard errors
    }
  };

  const handleDownloadVpsScript = async () => {
    setDownloadingScript(true);
    try {
      const res = await fetch('/api/download-vps-script');
      if (!res.ok) throw new Error('Failed to generate script');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mario-vps-auto.sh';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingScript(false);
    }
  };

  const handleDownloadZip = async () => {
    setDownloadingZip(true);
    try {
      const res = await fetch('/api/download-wispbyte-zip');
      if (!res.ok) throw new Error('Failed to generate ZIP');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mario-music-wispbyte.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingZip(false);
    }
  };

  const handleCopyFullOneLiner = async () => {
    setCopyingOneLiner(true);
    try {
      const res = await fetch('/api/vps-one-liner');
      const data = await res.json();
      if (data?.ok && data?.command) {
        await navigator.clipboard.writeText(data.command);
        setCopiedId('full-oneliner');
        setTimeout(() => setCopiedId(null), 2500);
      }
    } finally {
      setCopyingOneLiner(false);
    }
  };

  const gitShortCommand = `sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nodejs git && rm -rf ~/mario-music && git clone ${repoUrl.trim() || 'https://github.com/YOUR_USERNAME/Muisc.git'} ~/mario-music && cd ~/mario-music && chmod +x install_vps.sh 2>/dev/null; pip3 install -r requirements.txt && nohup python3 -u main.py > bot.log 2>&1 &`;

  const methods: { id: MethodId; labelMm: string; labelEn: string; subMm: string; subEn: string; icon: React.ElementType }[] = [
    {
      id: 'botpanel',
      labelMm: '1. Serverix Cloud / Free Bot Panels (Card မလို 24/7)',
      labelEn: '1. Serverix Cloud / Free Bot Panels (No Card 24/7)',
      subMm: 'Serverix Cloud · Katabump · Wispbyte (ဖုန်းဖြင့် ZIP တင်ရုံသာ)',
      subEn: 'Serverix Cloud · Katabump · Wispbyte (Upload ZIP & Start)',
      icon: Server,
    },
    {
      id: 'codespaces',
      labelMm: '2. GitHub Codespaces (Card မလို Free VPS)',
      labelEn: '2. GitHub Codespaces (Free No-Card VM)',
      subMm: 'ဖုန်း Chrome ဖြင့် အလွယ်ဆုံး Ubuntu VPS',
      subEn: 'Real Ubuntu Linux VM in mobile Chrome',
      icon: Cloud,
    },
    {
      id: 'ssh_vps',
      labelMm: '3. Termius SSH + Free Linux VPS',
      labelEn: '3. Termius SSH + Free Cloud VPS',
      subMm: 'Oracle / AWS / Student VPS 24/7 အမြဲပွင့်',
      subEn: 'Oracle / AWS / Student Ubuntu VPS 24/7',
      icon: Terminal,
    },
    {
      id: 'termux',
      labelMm: '4. Android Termux (ဖုန်းထဲတိုက်ရိုက်)',
      labelEn: '4. Android Termux (On Phone)',
      subMm: 'VPS မလိုဘဲ ဖုန်းထဲတွင် ယာယီ Run ရန်',
      subEn: 'Run directly on Android device',
      icon: Smartphone,
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 space-y-6">
      {/* Top Action Header */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1.5 max-w-3xl">
            <div className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
              {lang === 'mm' ? 'ဖုန်းတစ်လုံးတည်းဖြင့် Free VPS တင်နည်း' : 'Mobile-First Free VPS Deployment'}
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              {lang === 'mm'
                ? 'ကွန်ပျူတာမလို၊ Key ပြန်ရိုက်စရာမလိုဘဲ ဖုန်းဖြင့် Free VPS တွင် Run နည်း'
                : 'Run Your Bot on a Free VPS from Your Phone (All Keys Pre-Installed)'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {lang === 'mm'
                ? 'ဖုန်း Keyboard ဖြင့် Command အရှည်ကြီးများ နှင့် STRING_SESSION ပြန်ရိုက်စရာ လုံးဝမလိုအောင် Key အားလုံး + Start ပုံ + Auto-Installer ထည့်သွင်းပြီးသား ဖိုင်များကို တစ်ချက်နှိပ်ရုံဖြင့် ဒေါင်းယူ သို့မဟုတ် Copy ကူးနိုင်ပါသည်။'
                : 'Zero manual config editing on mobile keyboards. Download the 1-file self-extracting VPS script or flat ZIP with BOT_TOKEN, STRING_SESSION, API_ID, API_HASH, and start artwork pre-configured.'}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0">
            <button
              onClick={handleDownloadVpsScript}
              disabled={downloadingScript}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-600 px-4 py-3 text-xs sm:text-sm font-semibold text-white transition hover:bg-cyan-500 disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {downloadingScript ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              <span>
                {lang === 'mm'
                  ? 'mario-vps-auto.sh ဒေါင်းမည် (VPS အသင့်သုံး)'
                  : 'Download mario-vps-auto.sh (1-File VPS)'}
              </span>
            </button>

            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={handleCopyFullOneLiner}
                disabled={copyingOneLiner}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3.5 py-2.5 text-xs font-semibold text-slate-200 transition hover:bg-slate-700 disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
              >
                {copyingOneLiner ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : copiedId === 'full-oneliner' ? (
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5 text-cyan-400" />
                )}
                <span>
                  {copiedId === 'full-oneliner'
                    ? lang === 'mm'
                      ? 'Command ကူးပြီးပါပြီ!'
                      : 'Copied 1-Line Command!'
                    : lang === 'mm'
                    ? '1-Line SSH Command ကူးမည်'
                    : 'Copy 1-Line SSH Command'}
                </span>
              </button>

              <button
                onClick={handleDownloadZip}
                disabled={downloadingZip}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-2.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20 disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
              >
                {downloadingZip ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                <span>{lang === 'mm' ? 'ZIP ဒေါင်းမည်' : 'Download ZIP'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Method Selector Grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {methods.map((m) => {
          const Icon = m.icon;
          const selected = activeMethod === m.id;
          return (
            <button
              key={m.id}
              onClick={() => setActiveMethod(m.id)}
              className={`text-left rounded-xl p-4 transition cursor-pointer border ${
                selected
                  ? 'border-cyan-500/60 bg-slate-900 text-white'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`h-4 w-4 shrink-0 ${selected ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span className="text-xs font-bold leading-snug">
                  {lang === 'mm' ? m.labelMm : m.labelEn}
                </span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400">
                {lang === 'mm' ? m.subMm : m.subEn}
              </p>
            </button>
          );
        })}
      </div>

      {/* Main Content + Sidebar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-8 space-y-4">
          {/* METHOD 1: GITHUB CODESPACES (NO CREDIT CARD, REAL UBUNTU LINUX ON PHONE CHROME) */}
          {activeMethod === 'codespaces' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-3">
                <h3 className="text-base font-bold text-white">
                  {lang === 'mm'
                    ? 'နည်းလမ်း (၁) — GitHub Codespaces (VPS IP မလို · Visa/Master Card လုံးဝမလို · 8GB RAM Ubuntu Linux)'
                    : 'Method 1 — GitHub Codespaces (No VPS IP Needed · No Credit Card · Free 8GB Ubuntu VM)'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  {lang === 'mm'
                    ? 'VPS IP လည်းမရှိ၊ Visa/Master Card လည်းမရှိသူများအတွက် ဖုန်း Chrome Browser တစ်ခုတည်းဖြင့် တကယ့် Ubuntu Linux Server ကို တစ်လ နာရီ ၁၂၀ အခမဲ့ သုံးနိုင်သော အလွယ်ဆုံးနည်းလမ်းဖြစ်ပါသည်။ Python 3.11၊ FFmpeg နှင့် Key အားလုံး အလိုအလျောက် သွင်းပေးပါမည်။'
                    : 'Runs a real Ubuntu Linux VM with full outbound WebRTC/UDP voice support right inside mobile Chrome. Free 120 core-hours every month on any GitHub account without a credit card.'}
                </p>

                <div className="space-y-3 pt-2 text-xs text-slate-200">
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-1.5">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၁ — အပေါ်ဆုံးမှ mario-vps-auto.sh ဖိုင်ကို ဖုန်းထဲအရင်ဒေါင်းပါ'
                        : 'Step 1 — Download mario-vps-auto.sh to your phone'}
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      {lang === 'mm'
                        ? 'ဤစာမျက်နှာ အပေါ်ဆုံးရှိ အပြာရောင် "mario-vps-auto.sh ဒေါင်းမည်" ခလုတ်ကို နှိပ်ပါ။ ဖုန်း၏ Downloads ထဲသို့ Key အားလုံး + Start ပုံ အပြီးအစီးပါသော mario-vps-auto.sh ဖိုင် ရောက်သွားပါမည်။'
                        : 'Tap "Download mario-vps-auto.sh" above. This single file contains all code, live keys, and start banner.'}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-1.5">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၂ — ဖုန်း Chrome တွင် GitHub Private Repo ဆောက်၍ ဖိုင်တင်ပါ (Right-Click နှိပ်စရာမလိုပါ)'
                        : 'Step 2 — Create a Private Repo on github.com/new & Upload the File'}
                    </div>
                    <div className="space-y-1.5 text-slate-300 leading-relaxed">
                      <p>
                        {lang === 'mm'
                          ? '၁။ ဖုန်း Chrome တွင် github.com/new ကိုဖွင့်ပါ (GitHub အကောင့် မဝင်ရသေးပါက Sign in အရင်ဝင်ပါ)။'
                          : '1. Open github.com/new in Chrome on your phone.'}
                      </p>
                      <p>
                        {lang === 'mm'
                          ? '၂။ Repository name တွင် mario-bot ဟုရိုက်ပါ -> အောက်နားတွင် "Private" ကို ရွေးပါ (Key များ လုံခြုံစေရန်) -> အစိမ်းရောင် "Create repository" ကိုနှိပ်ပါ။'
                          : '2. Name it mario-bot, select Private, and tap Create repository.'}
                      </p>
                      <p>
                        {lang === 'mm'
                          ? '၃။ ပေါ်လာသော စာမျက်နှာတွင် "uploading an existing file" စာသားအပြာလေးကို နှိပ်ပါ -> "choose your files" နှိပ်၍ Downloads ထဲမှ mario-vps-auto.sh ကို ရွေးတင်ပြီး အောက်ဆုံးမှ အစိမ်းရောင် "Commit changes" ကိုနှိပ်ပါ။'
                          : '3. Tap "uploading an existing file", choose mario-vps-auto.sh from Downloads, and tap Commit changes.'}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၃ — Codespace ဖွင့်ပြီး Command တိုလေး တစ်ကြောင်းတည်း ရိုက်ပါ'
                        : 'Step 3 — Open Codespace & Run One Command'}
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      {lang === 'mm'
                        ? '၁။ အစိမ်းရောင် "<> Code" ခလုတ်ကိုနှိပ်ပါ -> "Codespaces" tab ကိုရွေးပါ -> အစိမ်းရောင် "Create codespace on main" ကိုနှိပ်ပါ (၁၅ စက္ကန့်ခန့်စောင့်လျှင် အောက်ခြေ၌ TERMINAL ပွင့်လာပါမည်)။ ၂။ TERMINAL အကွက်ထဲ တစ်ချက်နှိပ်ပြီး အောက်ပါစာကြောင်းကို ကူးထည့်၍ Enter ခေါက်ပါ —'
                        : '1. Tap the green "<> Code" button -> Codespaces -> "Create codespace on main". 2. In the bottom TERMINAL panel, run:'}
                    </p>
                    <div className="relative rounded-xl border border-slate-800 bg-slate-900 p-3 font-mono text-xs text-cyan-300">
                      <pre className="overflow-x-auto pr-10">{`bash mario-vps-auto.sh`}</pre>
                      <button
                        onClick={() => copyText('bash mario-vps-auto.sh', 'cs-cmd')}
                        className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-300 hover:text-white cursor-pointer"
                      >
                        {copiedId === 'cs-cmd' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-1.5">
                    <div className="font-bold text-emerald-400">
                      {lang === 'mm'
                        ? 'အဆင့် ၄ — ၄ နာရီ ဆက်တိုက်ပွင့်နေအောင် Timeout တိုးထားနည်း (အရေးကြီး)'
                        : 'Step 4 — Extend Idle Timeout to 4 Hours (240 Minutes)'}
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      {lang === 'mm'
                        ? 'ဖုန်း Chrome မှ github.com/settings/codespaces သို့သွား၍ Default idle timeout တွင် 30 minutes အစား "240 minutes" ပြောင်းပြီး Save နှိပ်ထားပါ။ နောက်ပိုင်း Codespace ပြန်ဖွင့်တိုင်းလည်း Command ပြန်ရိုက်စရာမလိုဘဲ Bot အလိုအလျောက် ပြန်ပွင့်ပါမည်!'
                        : 'Visit github.com/settings/codespaces and set Default idle timeout to 240 minutes. Whenever you reopen the Codespace later, the bot auto-resumes automatically.'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* METHOD 1: FREE NO-CARD BOT HOSTING PANELS (SERVERIX CLOUD / KATABUMP / BOT-HOSTING / WISPBYTE) */}
          {activeMethod === 'botpanel' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-3">
                <h3 className="text-base font-bold text-white">
                  {lang === 'mm'
                    ? 'နည်းလမ်း (၁) — Serverix Cloud / Free Bot Panels (Card လုံးဝမလို · ဖုန်း Browser ဖြင့် ZIP တင်ရုံသာ)'
                    : 'Method 1 — Serverix Cloud / Free Bot Panels (100% No Card · Upload ZIP in Mobile Browser)'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  {lang === 'mm'
                    ? 'Card လည်းမလို၊ SSH Command လည်း ရိုက်စရာမလိုဘဲ ဖုန်းထဲမှ mario-music-wispbyte.zip ဖိုင်ကို Upload တင်ပြီး Start ခလုတ်နှိပ်ရုံဖြင့် 24/7 အမြဲတမ်း Run ပေးသော အခမဲ့ Hosting များဖြစ်ပါသည် —'
                    : 'No credit card or SSH commands required. Simply download mario-music-wispbyte.zip with all credentials pre-installed, upload to your panel, and tap Start:'}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-xl border border-cyan-500/40 bg-slate-950 p-3.5 space-y-1">
                    <div className="font-bold text-cyan-400">Serverix.cloud (အကြံပြု)</div>
                    <p className="text-slate-400 leading-relaxed">
                      {lang === 'mm'
                        ? 'Card လုံးဝမလိုပါ။ Email ဖြင့် အကောင့်ဖွင့်ပြီး Python Bot Server အခမဲ့ယူနိုင်ပါသည်။ အိပ်မသွားဘဲ 24/7 ပွင့်ပါသည်။'
                        : 'No card required. Free 24/7 Python container without sleeping. Perfect for Telegram bots.'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 space-y-1">
                    <div className="font-bold text-emerald-400">Katabump.com</div>
                    <p className="text-slate-400 leading-relaxed">
                      {lang === 'mm'
                        ? 'Card မလိုပါ။ Python Bot server အခမဲ့ပေးပြီး ၄ ရက်တစ်ခါ Renew ခလုတ်နှိပ်ရုံဖြင့် 24/7 အမြဲပွင့်ပါသည်။'
                        : 'Free Python container with no card required; tap Renew periodically to keep running 24/7.'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 space-y-1">
                    <div className="font-bold text-indigo-400">Bot-Hosting.net</div>
                    <p className="text-slate-400 leading-relaxed">
                      {lang === 'mm'
                        ? 'Discord/Google ဖြင့် ဝင်ပြီး Free Coins စု၍ Python Server 24/7 ဖွင့်နိုင်ပါသည် (RAM ပိုများပါသည်)။'
                        : 'Free coins-based Python container hosting with generous RAM for FFmpeg + PyTgCalls.'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 space-y-1">
                    <div className="font-bold text-slate-300">Wispbyte.com</div>
                    <p className="text-slate-400 leading-relaxed">
                      {lang === 'mm'
                        ? 'Free Python container ပေးပါသည် (Need more RAM တွင် Watch ad နှိပ်၍ +100MB RAM တိုးထားလျှင် ပိုမြန်ပါသည်)။'
                        : 'Free Python server; tap Watch ad for +100 MiB extra RAM headroom if needed.'}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2 text-xs text-slate-300">
                  <div className="font-bold text-white">
                    {lang === 'mm' ? 'Serverix Cloud တွင် ဖုန်းဖြင့် တင်နည်း ၄ ဆင့်' : '4-Step Serverix Cloud Flow'}
                  </div>
                  <p>
                    {lang === 'mm'
                      ? '၁။ ဤစာမျက်နှာ အပေါ်ဆုံးရှိ အစိမ်းရောင် "ZIP ဒေါင်းမည်" ခလုတ်ကို နှိပ်၍ mario-music-wispbyte.zip ကို ဖုန်းထဲဒေါင်းပါ (Bot Token, Session, Start Photo အားလုံး အသင့်ထည့်ပြီးသားဖြစ်ပါသည်)။'
                      : '1. Tap Download ZIP above to save mario-music-wispbyte.zip with all credentials.'}
                  </p>
                  <p>
                    {lang === 'mm'
                      ? '၂။ serverix.cloud တွင် အကောင့်ဖွင့်ပြီး Python (Bot) Server အသစ်တစ်ခု ဖွင့်ပါ။'
                      : '2. Sign up at serverix.cloud and create a new Python server.'}
                  </p>
                  <p>
                    {lang === 'mm'
                      ? '၃။ Server ၏ Files (သို့မဟုတ် home/container) ထဲရှိ ဖိုင်အဟောင်းများကို ဖျက်ပြီး mario-music-wispbyte.zip ကို Upload တင်ကာ ••• -> Unarchive နှိပ်ပါ။'
                      : '3. Upload mario-music-wispbyte.zip into the Files manager and tap Unarchive.'}
                  </p>
                  <p>
                    {lang === 'mm'
                      ? '၄။ Startup tab တွင် Main File ကို main.py (သို့မဟုတ် bot.py) ထားပြီး Console မှ Start (အစိမ်းရောင်) ကိုနှိပ်ပါ။'
                      : '4. Ensure Startup file is main.py and click Start in Console.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* METHOD 3: TERMIUS ANDROID SSH APP + REAL LINUX VPS */}
          {activeMethod === 'ssh_vps' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-4">
                <div>
                  <h3 className="text-base font-bold text-white">
                    {lang === 'mm'
                      ? 'နည်းလမ်း (၃) — ဖုန်း Play Store မှ Termius App + Free Cloud Ubuntu VPS (အခိုင်မာဆုံး 24/7)'
                      : 'Method 3 — Android Termius SSH App + Free Cloud Ubuntu VPS (True 24/7)'}
                  </h3>
                  <p className="mt-1 text-xs sm:text-sm text-slate-300 leading-relaxed">
                    {lang === 'mm'
                      ? 'Ubuntu 22.04 / 24.04 သို့မဟုတ် Debian Linux VPS ပေါ်သို့ ဖုန်းထဲမှ Termius App ဖြင့် ချိတ်ပြီး ၂ မိနစ်အတွင်း systemd 24/7 auto-restart စနစ်ဖြင့် အပြီးအစီး သွင်းနည်းဖြစ်ပါသည် (သွင်းပြီးသည်နှင့် ဖုန်းပိတ်လိုက်လည်း Bot လုံးဝမရပ်တော့ပါ)။'
                      : 'Connect to any Ubuntu/Debian VPS from your phone using Termius and install Mario Music Bot as a permanent 24/7 systemd service.'}
                  </p>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                    <div className="font-bold text-emerald-400">
                      {lang === 'mm'
                        ? 'အဆင့် ၀ — Free Ubuntu VPS မရှိသေးပါက ဖုန်းဖြင့် အခမဲ့လျှောက်နိုင်သော နေရာများ'
                        : 'Step 0 — Where to Get a Free Ubuntu 22.04 VPS'}
                    </div>
                    <div className="space-y-1.5 text-slate-300 leading-relaxed">
                      <p>
                        {lang === 'mm'
                          ? '• Oracle Cloud Always Free (cloud.oracle.com) — Ubuntu 22.04 VM ကို ထာဝရအခမဲ့ ပေးပါသည် (အကောင်းဆုံး)။'
                          : '• Oracle Cloud Always Free (cloud.oracle.com) — Forever-free Ubuntu 22.04 VM.'}
                      </p>
                      <p>
                        {lang === 'mm'
                          ? '• AWS Free Tier (aws.amazon.com/free) / Google Cloud Free (cloud.google.com/free) — Ubuntu 22.04 Free VM ရပါသည်။'
                          : '• AWS 12-Month Free Tier / Google Cloud $300 Free Trial — Ubuntu 22.04 VM.'}
                      </p>
                      <p>
                        {lang === 'mm'
                          ? '• GitHub Student Pack (education.github.com/pack) — ကျောင်းသားကတ်ရှိပါက Card မလိုဘဲ DigitalOcean $200 / Azure $100 VPS အခမဲ့ရပါသည်။ (Firewall Port အပိုဖွင့်စရာ မလိုပါ)။'
                          : '• GitHub Student Pack — $200 DigitalOcean / $100 Azure credits with no card required.'}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-1.5">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၁ — ဖုန်းတွင် Termius App ဒေါင်း၍ VPS ချိတ်ပါ'
                        : 'Step 1 — Install Termius on Android & Connect to Your VPS'}
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      {lang === 'mm'
                        ? '၁။ Play Store မှ "Termius" (သို့မဟုတ် JuiceSSH) ကို ဒေါင်းပါ။ ၂။ App ဖွင့်ပြီး + ခလုတ် -> New Host ကိုနှိပ်ပါ။ ၃။ Address တွင် VPS ၏ IP (ဥပမာ 139.59.xx.xx) ထည့်ပါ -> SSH ဖွင့်ထားပြီး Port 22၊ Username (root သို့မဟုတ် ubuntu) နှင့် Password (သို့မဟုတ် SSH Key .pem) ထည့်၍ Save & Connect နှိပ်ပါ။'
                        : 'Install Termius from Play Store -> tap + -> New Host -> enter VPS IP, Port 22, Username (root or ubuntu), and Password or SSH key -> Connect.'}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၂ — Key အားလုံးပါပြီးသား Bot ကို သွင်းပါ (နည်း A သို့မဟုတ် နည်း B ကြိုက်ရာသုံးပါ)'
                        : 'Step 2 — Install Bot + Pre-Configured Keys (Pick Option A or B)'}
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3.5 space-y-2">
                      <div className="font-semibold text-white">
                        {lang === 'mm'
                          ? 'နည်း (A) — Termius SFTP ဖြင့် mario-vps-auto.sh တင်နည်း (အသေချာဆုံး · Start ပုံအကြီးပါ တစ်ခါတည်းပါသည်)'
                          : 'Option A — Upload mario-vps-auto.sh via Termius SFTP (Recommended)'}
                      </div>
                      <p className="text-slate-400 leading-relaxed">
                        {lang === 'mm'
                          ? '၁။ အပေါ်ဆုံးရှိ အပြာရောင် "mario-vps-auto.sh ဒေါင်းမည်" ခလုတ်ကိုနှိပ်၍ ဖုန်းထဲဒေါင်းပါ။ ၂။ Termius App ထဲရှိ SFTP tab ကိုနှိပ်ပြီး ဖုန်း Downloads ထဲမှ mario-vps-auto.sh ကို သင့် VPS ထဲသို့ Upload တင်ပါ။ ၃။ VPS Terminal မျက်နှာပြင်သို့ ပြန်သွားပြီး အောက်ပါ Command တိုလေးကို ကူးထည့်၍ Enter ခေါက်ပါ —'
                          : '1. Tap Download mario-vps-auto.sh above. 2. In Termius, open SFTP and upload mario-vps-auto.sh to your VPS home folder. 3. Run in SSH terminal:'}
                      </p>
                      <div className="relative rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-cyan-300">
                        <pre className="overflow-x-auto pr-10">{`bash mario-vps-auto.sh`}</pre>
                        <button
                          onClick={() => copyText('bash mario-vps-auto.sh', 'vps-sh')}
                          className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-300 hover:text-white cursor-pointer"
                        >
                          {copiedId === 'vps-sh' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3.5 space-y-2">
                      <div className="font-semibold text-white">
                        {lang === 'mm'
                          ? 'နည်း (B) — SFTP မသုံးဘဲ 1-Line SSH Command တိုက်ရိုက် Paste ချနည်း'
                          : 'Option B — Direct 1-Line SSH Paste (No File Upload Needed)'}
                      </div>
                      <p className="text-slate-400 leading-relaxed">
                        {lang === 'mm'
                          ? 'အပေါ်ဆုံးရှိ "1-Line SSH Command ကူးမည်" ခလုတ်ကိုနှိပ်ပြီး Termius အမည်းရောင် Terminal ထဲတွင် ဖိထား၍ Paste -> Enter ခေါက်ပါ (ဖုန်းအချို့တွင် စာရှည်လွန်း၍ Paste မဝင်ပါက အပေါ်မှ နည်း A ကို သုံးပါ)။'
                          : 'Tap "Copy 1-Line SSH Command" at the top of this page, paste directly into Termius SSH terminal, and press Enter.'}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2.5">
                    <div className="font-bold text-cyan-300">
                      {lang === 'mm'
                        ? 'အဆင့် ၃ — သွင်းပြီးနောက် 24/7 အလုပ်လုပ်နေကြောင်း စစ်ဆေးရန်'
                        : 'Step 3 — Verify 24/7 Service Status'}
                    </div>
                    <p className="text-slate-400 leading-relaxed">
                      {lang === 'mm'
                        ? 'Terminal တွင် Mario Music Bot (@marioxnmusic_bot) is LIVE 24/7! ပေါ်လာပြီဆိုလျှင် Termius App ကို ပိတ်နိုင်ပါပြီ။ Telegram Group ထဲတွင် Voice Chat ဖွင့်ပြီး /play သီချင်းနာမည် ရိုက်စမ်းကြည့်ပါ!'
                        : 'Once you see Mario Music Bot is LIVE 24/7, you can close Termius safely and test /play in your Telegram group.'}
                    </p>
                    <div className="relative rounded-xl border border-slate-800 bg-slate-900 p-3 font-mono text-xs text-cyan-300">
                      <pre className="overflow-x-auto pr-10">{`sudo systemctl status mario-music`}</pre>
                      <button
                        onClick={() => copyText('sudo systemctl status mario-music', 'sys-status')}
                        className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-300 hover:text-white cursor-pointer"
                      >
                        {copiedId === 'sys-status' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Optional GitHub Short Command Builder */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2.5">
                    <div className="font-bold text-slate-200">
                      {lang === 'mm'
                        ? 'GitHub Repo မှ ဆွဲသွင်းချင်သူများအတွက် Command အတို (Optional)'
                        : 'Optional: Short GitHub Clone Command'}
                    </div>
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      placeholder="https://github.com/username/Muisc.git"
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
                    />
                    <div className="relative rounded-xl border border-slate-800 bg-slate-900 p-3 font-mono text-[11px] text-cyan-300">
                      <pre className="overflow-x-auto whitespace-pre-wrap pr-10">{gitShortCommand}</pre>
                      <button
                        onClick={() => copyText(gitShortCommand, 'git-short')}
                        className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-300 hover:text-white cursor-pointer"
                      >
                        {copiedId === 'git-short' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* METHOD 4: ANDROID TERMUX */}
          {activeMethod === 'termux' && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-3">
                <div className="flex items-start gap-2.5 text-amber-300">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed">
                    {lang === 'mm'
                      ? 'သတိပြုရန် — Termux သည် သင့်ဖုန်းအင်တာနက်နှင့် ဘက်ထရီကို သုံး၍ Run ခြင်းဖြစ်သောကြောင့် အင်တာနက်ပိတ်လိုက်လျှင် Bot ရပ်သွားပါမည်။ ဖုန်းပိတ်ထားလည်း 24/7 ပွင့်စေချင်ပါက နည်းလမ်း (၁) သို့မဟုတ် (၂) / (၃) ကို သုံးပါ။'
                      : 'Note: Termux runs directly on your phone battery and data connection. Use Methods 1–3 for cloud 24/7 hosting.'}
                  </p>
                </div>

                <h3 className="text-base font-bold text-white pt-1">
                  {lang === 'mm'
                    ? 'Android ဖုန်း Termux တွင် ချက်ချင်း Run နည်း'
                    : 'Run Directly on Android Termux'}
                </h3>
                <p className="text-xs text-slate-400">
                  {lang === 'mm'
                    ? 'F-Droid.org မှ Termux APK ကို သွင်းပါ။ အပေါ်မှ "1-Line SSH Command ကူးမည်" ကို နှိပ်၍ Termux ထဲ Paste ချနိုင်သလို အောက်ပါ WakeLock ပါသော Command ဖြင့်လည်း Run နိုင်ပါသည် —'
                    : 'Install Termux from F-Droid, grant wake-lock so Android keeps Termux alive in the background, and paste the 1-Line Command from above:'}
                </p>

                <div className="relative rounded-xl border border-slate-800 bg-slate-950 p-3.5 font-mono text-xs text-cyan-300">
                  <pre className="overflow-x-auto whitespace-pre-wrap pr-10">{`termux-wake-lock
pkg update -y && pkg install -y python ffmpeg nodejs-lts curl unzip clang libffi openssl`}</pre>
                  <button
                    onClick={() =>
                      copyText(
                        'termux-wake-lock\npkg update -y && pkg install -y python ffmpeg nodejs-lts curl unzip clang libffi openssl',
                        'termux-prep'
                      )
                    }
                    className="absolute right-2.5 top-2.5 rounded-lg bg-slate-800 p-1.5 text-slate-300 hover:text-white cursor-pointer"
                  >
                    {copiedId === 'termux-prep' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Pre-Configured Keys Summary + Useful VPS Commands */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                {lang === 'mm' ? 'အသင့်ထည့်သွင်းပြီးသား Key များ' : 'Pre-Configured Live Credentials'}
              </h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              {lang === 'mm'
                ? 'mario-vps-auto.sh နှင့် mario-music-wispbyte.zip နှစ်ခုလုံးတွင် အောက်ပါ Key အားလုံး ထည့်ပေးပြီးသားဖြစ်၍ ဘာမှ ထပ်ထည့်စရာမလိုပါ —'
                : 'Both downloads already include all required credentials at the root:'}
            </p>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2 border border-slate-800">
                <span className="text-slate-400">BOT</span>
                <span className="text-emerald-300">@marioxnmusic_bot</span>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2 border border-slate-800">
                <span className="text-slate-400">ASSISTANT</span>
                <span className="text-cyan-300">@mariomusicAssistant</span>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2 border border-slate-800">
                <span className="text-slate-400">STRING_SESSION</span>
                <span className="text-emerald-400">Included ✓</span>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2 border border-slate-800">
                <span className="text-slate-400">API_ID / HASH</span>
                <span className="text-emerald-400">38953431 ✓</span>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2 border border-slate-800">
                <span className="text-slate-400">OWNER_ID</span>
                <span className="text-emerald-400">7670796126 ✓</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              {lang === 'mm' ? 'VPS ထိန်းချုပ်ရန် Command အတိုများ' : 'VPS Control Commands'}
            </h3>
            <div className="space-y-2 text-xs">
              <div className="rounded-xl bg-slate-950 p-3 border border-slate-800">
                <div className="text-slate-400 mb-1">
                  {lang === 'mm' ? 'Log ကြည့်ရန် (Systemd VPS):' : 'View Live Logs (Systemd):'}
                </div>
                <code className="font-mono text-cyan-300 text-[11px]">sudo journalctl -u mario-music -f</code>
              </div>
              <div className="rounded-xl bg-slate-950 p-3 border border-slate-800">
                <div className="text-slate-400 mb-1">
                  {lang === 'mm' ? 'Log ကြည့်ရန် (Codespaces / Container):' : 'View Logs (Codespaces):'}
                </div>
                <code className="font-mono text-cyan-300 text-[11px]">tail -f ~/mario-music/bot.log</code>
              </div>
              <div className="rounded-xl bg-slate-950 p-3 border border-slate-800">
                <div className="text-slate-400 mb-1">
                  {lang === 'mm' ? 'သတိပေးချက် (Conflict ကာကွယ်ရန်):' : 'Avoid Duplicate Session:'}
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {lang === 'mm'
                    ? 'VPS ပေါ်တွင် Run ထားချိန်၌ တစ်နေရာတည်းတွင်သာ ဖွင့်ထားပါ (၂ နေရာပြိုင်ဖွင့်လျှင် Telegram မှ Conflict ဖြစ်တတ်ပါသည်)။'
                    : 'Run only one active instance of STRING_SESSION at a time so Telegram does not disconnect duplicate polling.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
