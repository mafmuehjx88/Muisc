import React, { useEffect, useState, useRef } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Download,
  KeyRound,
  Loader2,
  Phone,
  Play,
  Radio,
  RefreshCw,
  Send,
  ShieldAlert,
  Smartphone,
  Square,
  Terminal,
  UserCheck,
} from 'lucide-react';

interface LiveControlPanelProps {
  lang: 'mm' | 'en';
  onOpenVpsGuide?: () => void;
}

interface ManagerStatus {
  ok: boolean;
  botRunning: boolean;
  botPid: number | null;
  botInfo: { username: string; id: number } | null;
  hasStringSession: boolean;
  sessionPreview: string;
  voiceReady: boolean;
  assistantInfo: {
    id: number;
    firstName?: string;
    username?: string | null;
    phone?: string;
  } | null;
  otpState: {
    status: 'idle' | 'otp_sent' | 'need_2fa' | 'authenticated';
    phone: string;
    code_type: string | null;
    sent_at: number | null;
    error: string | null;
  };
  logs: string[];
}

export const LiveControlPanel: React.FC<LiveControlPanelProps> = ({ lang, onOpenVpsGuide }) => {
  const [status, setStatus] = useState<ManagerStatus | null>(null);
  const [phone, setPhone] = useState('+959674354885');
  const [otpCode, setOtpCode] = useState('');
  const [password2fa, setPassword2fa] = useState('Chit2025');
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [restartingBot, setRestartingBot] = useState(false);
  const [downloadingWispbyte, setDownloadingWispbyte] = useState(false);
  const [downloadingVpsScript, setDownloadingVpsScript] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const handleDownloadVpsScript = async () => {
    setDownloadingVpsScript(true);
    try {
      const res = await fetch('/api/download-vps-script');
      if (!res.ok) throw new Error('VPS script generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mario-vps-auto.sh';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setFeedback({
        type: 'success',
        text:
          lang === 'mm'
            ? 'mario-vps-auto.sh ဒေါင်းပြီးပါပြီ! Free VPS သို့မဟုတ် GitHub Codespaces ထဲ တင်ပြီး bash mario-vps-auto.sh ရိုက်လိုက်ရုံဖြင့် Key အားလုံးနှင့် 24/7 အလိုအလျောက် Run ပေးပါမည်။'
            : 'Downloaded mario-vps-auto.sh! Upload to your VPS or Codespaces and run: bash mario-vps-auto.sh',
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to download VPS script' });
    } finally {
      setDownloadingVpsScript(false);
    }
  };

  const handleDownloadWispbyteZip = async () => {
    setDownloadingWispbyte(true);
    try {
      const res = await fetch('/api/download-wispbyte-zip');
      if (!res.ok) throw new Error('ZIP generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mario-music-wispbyte.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setFeedback({
        type: 'success',
        text:
          lang === 'mm'
            ? 'mario-music-wispbyte.zip ဒေါင်းပြီးပါပြီ! Wispbyte -> Files ထဲတွင် ဖိုင်အဟောင်းများဖျက်၍ ဤ ZIP ကို Upload တင်ပြီး Unarchive နှိပ်ရုံဖြင့် တန်း Run နိုင်ပါပြီ (Folder ရွှေ့စရာမလိုပါ၊ Key အားလုံး ပါပြီးသားဖြစ်ပါသည်)။'
            : 'Downloaded mario-music-wispbyte.zip! Upload to Wispbyte Files, click Unarchive, and press Start.',
      });
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Failed to download ZIP' });
    } finally {
      setDownloadingWispbyte(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/manager/status');
      if (!res.ok) return;
      const data: ManagerStatus = await res.json();
      if (data.ok) {
        setStatus(data);
        if (data.otpState?.phone && phone === '+959674354885') {
          setPhone(data.otpState.phone);
        }
      }
    } catch {
      // ignore transient network errors
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(fetchStatus, 2500);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [status?.logs?.length]);

  const handleSendCode = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSendingOtp(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/manager/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      });
      const data = await res.json();
      if (data.ok) {
        setOtpCode('');
        setFeedback({
          type: 'info',
          text:
            lang === 'mm'
              ? `${data.phone} သို့ Telegram App ထဲတွင် OTP ကုဒ်အသစ် ပို့လိုက်ပါပြီ! အောက်က အကွက်တွင် ချက်ချင်း ရိုက်ထည့်ပါ။`
              : `Fresh OTP sent to ${data.phone} inside your Telegram app! Enter the 5 digits below immediately.`,
        });
        await fetchStatus();
      } else {
        setFeedback({ type: 'error', text: data.error || 'Failed to send OTP' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Network error' });
    } finally {
      setSendingOtp(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifyingOtp(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/manager/verify-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: otpCode, password: password2fa }),
      });
      const data = await res.json();
      if (data.ok) {
        setOtpCode('');
        setPassword2fa('');
        setFeedback({
          type: 'success',
          text:
            lang === 'mm'
              ? 'အောင်မြင်ပါသည်! STRING_SESSION ကို သိမ်းဆည်းပြီး Music Bot နှင့် Voice Assistant အားလုံးကို တိုက်ရိုက် Run ပေးထားပါပြီ!'
              : 'Success! STRING_SESSION saved and both Music Bot + Voice Assistant are now running live!',
        });
        await fetchStatus();
      } else if (data.need2fa) {
        setFeedback({
          type: 'info',
          text:
            data.message ||
            data.error ||
            (lang === 'mm'
              ? 'သင့်အကောင့်တွင် 2-Step Verification (2FA Password) ခံထားပါသည်။ Password ဆက်ထည့်ပေးပါ။'
              : 'Please enter your Telegram Two-Step Verification (2FA) password.'),
        });
        await fetchStatus();
      } else {
        setFeedback({ type: 'error', text: data.error || 'Verification failed' });
        await fetchStatus();
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err?.message || 'Network error' });
    } finally {
      setVerifyingOtp(false);
    }
  };

  const handleBotAction = async (action: 'restart' | 'stop') => {
    setRestartingBot(true);
    try {
      await fetch(`/api/manager/${action}`, { method: 'POST' });
      await fetchStatus();
    } finally {
      setRestartingBot(false);
    }
  };

  const isAuthenticated = Boolean(status?.hasStringSession);
  const need2fa = status?.otpState?.status === 'need_2fa';
  const otpSent = status?.otpState?.status === 'otp_sent';

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 space-y-6">
      {/* Direct Wispbyte Ready ZIP Card (All Keys Included, No Folder Nesting) */}
      <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/90 p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <div className="text-xs font-medium text-emerald-400">
              {lang === 'mm'
                ? 'Wispbyte 24/7 တိုက်ရိုက်တင်ရန် အသင့်သုံး ZIP · Key အားလုံး ထည့်သွင်းပြီး'
                : 'Wispbyte 24/7 Direct Deployment Bundle · All Live Keys Pre-Configured'}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {lang === 'mm'
                ? 'GitHub မလိုဘဲ Wispbyte ထဲ တိုက်ရိုက်ထည့်ရန် ZIP ဒေါင်းပါ'
                : 'Download Direct Wispbyte ZIP (No GitHub Needed)'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
              {lang === 'mm'
                ? 'ဤ ZIP ထဲတွင် BOT_TOKEN, STRING_SESSION, API_ID, API_HASH, OWNER_ID နှင့် Start ပုံ အားလုံး အပြီးအစီး ထည့်ပေးထားပြီး Folder အထပ်မပါဝင်ပါ။ Wispbyte Free RAM နှင့် မပြည့်အောင်လည်း အထူးချုံ့ပေးထားပါသည်။'
                : 'Pre-configured with BOT_TOKEN, STRING_SESSION, API_ID, API_HASH, OWNER_ID, and start banner directly at the archive root with low-RAM bootstrap for Wispbyte Free Tier.'}
            </p>
            <div className="pt-1 text-xs text-slate-400 space-y-1">
              <div>
                {lang === 'mm'
                  ? '1. အစိမ်းရောင်ခလုတ်နှိပ်၍ mario-music-wispbyte.zip ဒေါင်းပါ။'
                  : '1. Download mario-music-wispbyte.zip using the button.'}
              </div>
              <div>
                {lang === 'mm'
                  ? '2. Wispbyte -> Files (home / container) ထဲရှိ ဖိုင်အဟောင်းအားလုံး ဖျက်ပြီး ဤ ZIP ကို Upload တင်ကာ ••• -> Unarchive နှိပ်ပါ (Folder ရွှေ့စရာ လုံးဝမလိုပါ)။'
                  : '2. Clear old files in Wispbyte Files (home / container), upload this ZIP, and click ••• -> Unarchive.'}
              </div>
              <div>
                {lang === 'mm'
                  ? '3. Console သို့သွားပြီး Start / Restart နှိပ်ပါ (main.py / bot.py / app.py အားလုံး အလိုအလျောက် အလုပ်လုပ်ပါသည်)။'
                  : '3. Open Console and click Start / Restart (works automatically with main.py, bot.py, or app.py).'}
              </div>
            </div>
          </div>

          <div className="shrink-0 flex flex-col sm:flex-row lg:flex-col gap-2.5">
            <button
              onClick={handleDownloadWispbyteZip}
              disabled={downloadingWispbyte}
              className="w-full lg:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 active:scale-[0.99] disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {downloadingWispbyte ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              <span>
                {downloadingWispbyte
                  ? lang === 'mm'
                    ? 'ZIP ပြင်ဆင်နေပါသည်...'
                    : 'Preparing ZIP...'
                  : lang === 'mm'
                  ? 'All-in-One ZIP ဒေါင်းမည်'
                  : 'Download All-in-One ZIP'}
              </span>
            </button>

            <button
              onClick={handleDownloadVpsScript}
              disabled={downloadingVpsScript}
              className="w-full lg:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-2.5 text-xs font-semibold text-cyan-300 transition hover:bg-cyan-500/20 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {downloadingVpsScript ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Terminal className="h-4 w-4" />
              )}
              <span>
                {lang === 'mm'
                  ? 'VPS 1-File Auto Script (.sh)'
                  : 'Download VPS Auto Script (.sh)'}
              </span>
            </button>

            {onOpenVpsGuide && (
              <button
                onClick={onOpenVpsGuide}
                className="w-full lg:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800/90 px-4 py-2.5 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Smartphone className="h-4 w-4 text-cyan-400" />
                <span>
                  {lang === 'mm'
                    ? 'ဖုန်းဖြင့် Free VPS တင်နည်း ကြည့်မည်'
                    : 'Free Mobile VPS Guide'}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Live Status Header Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Card 1: Bot Client */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {lang === 'mm' ? 'Telegram Bot အခြေအနေ' : 'Telegram Bot Client'}
            </span>
            {status?.botRunning ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                ONLINE
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-xs font-semibold text-rose-400">
                STOPPED
              </span>
            )}
          </div>
          <div className="mt-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-400">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-bold text-white font-mono">
                {status?.botInfo?.username ? `@${status.botInfo.username}` : '8975164612:...'}
              </div>
              <div className="text-xs text-slate-400">
                {status?.botRunning
                  ? `PID: ${status.botPid} • /start, /play Ready`
                  : lang === 'mm'
                  ? 'Bot ရပ်နားထားသည်'
                  : 'Bot process stopped'}
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Assistant User Account */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {lang === 'mm' ? 'အကူအညီအကောင့် (Assistant)' : 'Voice Assistant Account'}
            </span>
            {isAuthenticated ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                CONNECTED
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300">
                {otpSent
                  ? lang === 'mm'
                    ? 'OTP စောင့်ဆိုင်းနေသည်'
                    : 'OTP SENT'
                  : lang === 'mm'
                  ? 'OTP လိုအပ်သည်'
                  : 'NEEDS LOGIN'}
              </span>
            )}
          </div>
          <div className="mt-3 flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                isAuthenticated
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : 'bg-amber-500/15 text-amber-400'
              }`}
            >
              <UserCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-bold text-white font-mono">
                {status?.assistantInfo?.firstName
                  ? `${status.assistantInfo.firstName}${
                      status.assistantInfo.username ? ` (@${status.assistantInfo.username})` : ''
                    }`
                  : status?.otpState?.phone || '+959674354885'}
              </div>
              <div className="text-xs text-slate-400 font-mono">
                {isAuthenticated
                  ? `Session: ${status?.sessionPreview || 'Saved in config.py'}`
                  : lang === 'mm'
                  ? 'အောက်တွင် OTP ကုဒ် ၅ လုံး ရိုက်ထည့်ပါ'
                  : 'Enter 5-digit OTP below to link'}
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: PyTgCalls Voice Engine */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {lang === 'mm' ? 'Voice Chat အသံလွှင့်စနစ်' : 'PyTgCalls Voice Engine'}
            </span>
            {status?.voiceReady ? (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-xs font-semibold text-cyan-300">
                <Radio className="h-3.5 w-3.5 animate-pulse" />
                STREAM READY
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-400">
                STANDBY
              </span>
            )}
          </div>
          <div className="mt-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-bold text-white">
                {status?.voiceReady
                  ? lang === 'mm'
                    ? 'Group VC သီချင်းဖွင့်ရန် အသင့်!'
                    : 'Ready for Group Voice Calls!'
                  : lang === 'mm'
                  ? 'Assistant Login ဝင်ပြီးပါက ပွင့်မည်'
                  : 'Starts automatically after OTP'}
              </div>
              <div className="text-xs text-slate-400">
                FFmpeg + yt-dlp + PyTgCalls v0.9.7
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Split Grid: Left = Instant OTP Login, Right = Live Bot Console */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left: Instant OTP Authentication Box */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="rounded-2xl border border-cyan-500/30 bg-slate-900/90 p-5 sm:p-6 shadow-xl">
            <div className="flex items-center gap-2.5 text-cyan-400 mb-2">
              <KeyRound className="h-5 w-5" />
              <h2 className="text-base font-bold text-white">
                {lang === 'mm'
                  ? 'အကူအညီအကောင့် (+959674354885) တိုက်ရိုက် ချိတ်ဆက်ရန်'
                  : 'Instant Assistant OTP Login'}
              </h2>
            </div>

            <p className="text-xs leading-relaxed text-slate-300 mb-4">
              {lang === 'mm'
                ? 'ဤနေရာမှ OTP ရိုက်ထည့်လျှင် တိုက်ရိုက် ချိတ်ဆက်ထားသောကြောင့် Code သက်တမ်းကုန်ခြင်း (PHONE_CODE_EXPIRED) လုံးဝမဖြစ်တော့ဘဲ ၁ စက္ကန့်အတွင်း STRING_SESSION ထုတ်၍ Bot ကို အပြည့်အစုံ Run ပေးပါမည်။'
                : 'Entering your OTP directly here verifies over a live persistent MTProto connection in <1 second, preventing PHONE_CODE_EXPIRED and starting the voice bot immediately.'}
            </p>

            {/* Important Warning Box about Telegram Anti-Hijack */}
            <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-950/30 p-3.5 text-xs text-amber-200/90 flex gap-2.5">
              <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-amber-300">
                  {lang === 'mm'
                    ? 'အရေးကြီး သတိပေးချက် (OTP မပျက်စီးစေရန်)'
                    : 'Important: Why OTP Codes Expire'}
                </div>
                <p className="leading-relaxed">
                  {lang === 'mm'
                    ? 'Telegram က ပို့လာသော ဂဏန်း ၅ လုံးကို Telegram Chat ထဲတွင် တခြားအကောင့်သို့ ပို့ခြင်း / Forward လုပ်ခြင်း လုံးဝမပြုလုပ်ပါနှင့်! Telegram က ချက်ချင်း Cancel (Expired) လုပ်ပစ်ပါသည်။ ဤအကွက်ထဲတွင်သာ တိုက်ရိုက်ရိုက်ထည့်ပါ။'
                    : 'Never forward or send the 5-digit login code inside any Telegram chat—Telegram immediately invalidates shared login codes. Type the 5 digits directly below!'}
                </p>
              </div>
            </div>

            {feedback && (
              <div
                className={`mb-4 rounded-xl border p-3.5 text-xs flex items-start gap-2.5 ${
                  feedback.type === 'success'
                    ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-200'
                    : feedback.type === 'error'
                    ? 'border-rose-500/40 bg-rose-950/40 text-rose-200'
                    : 'border-cyan-500/40 bg-cyan-950/40 text-cyan-200'
                }`}
              >
                {feedback.type === 'success' ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                )}
                <span className="leading-relaxed">{feedback.text}</span>
              </div>
            )}

            {/* Step 1: Phone + Send / Resend OTP */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  {lang === 'mm'
                    ? '၁။ Assistant ဖုန်းနံပါတ် (Country Code ပါရမည်)'
                    : '1. Assistant Phone Number'}
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Phone className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+959674354885"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-sm font-mono text-white focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleSendCode()}
                    disabled={sendingOtp}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-600/20 px-3.5 py-2 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-600/30 disabled:opacity-50 cursor-pointer shrink-0"
                  >
                    {sendingOtp ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Send className="h-3.5 w-3.5" />
                    )}
                    <span>
                      {otpSent
                        ? lang === 'mm'
                          ? 'OTP အသစ်ပြန်ပို့မည်'
                          : 'Resend OTP'
                        : lang === 'mm'
                        ? 'OTP ကုဒ်ပို့မည်'
                        : 'Send OTP'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Step 2: Verify OTP & optional 2FA */}
              <form onSubmit={handleVerifyCode} className="space-y-3 border-t border-slate-800 pt-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    {lang === 'mm'
                      ? '၂။ Telegram App ထဲသို့ ဝင်လာသော OTP ကုဒ် ၅ လုံး ထည့်ပါ'
                      : '2. Enter 5-Digit Telegram Login Code'}
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    placeholder="ဥပမာ - 12345"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-center text-xl font-bold tracking-[0.35em] font-mono text-cyan-300 placeholder:text-sm placeholder:tracking-normal placeholder:font-normal placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none"
                  />
                </div>

                {need2fa && (
                  <div>
                    <label className="block text-xs font-semibold text-amber-300 mb-1.5">
                      {lang === 'mm'
                        ? 'Two-Step Verification (2FA) Password ထည့်ပါ'
                        : 'Telegram 2FA Cloud Password'}
                    </label>
                    <input
                      type="password"
                      value={password2fa}
                      onChange={(e) => setPassword2fa(e.target.value)}
                      placeholder="Enter your 2FA password..."
                      className="w-full rounded-xl border border-amber-500/50 bg-slate-950 px-3.5 py-2.5 text-sm text-white focus:border-amber-400 focus:outline-none"
                    />
                  </div>
                )}

                <button
                  type="submit"
                  disabled={verifyingOtp || (!otpCode.trim() && !need2fa)}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-cyan-500/20 transition hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-50 cursor-pointer"
                >
                  {verifyingOtp ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>
                        {lang === 'mm' ? 'ချိတ်ဆက်နေပါသည်...' : 'Verifying & Starting Bot...'}
                      </span>
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-current" />
                      <span>
                        {lang === 'mm'
                          ? 'အတည်ပြုပြီး Music Bot အပြည့်အစုံ Run မည်'
                          : 'Verify OTP & Launch Full Voice Bot'}
                      </span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right: Real-Time main.py Process Console */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="flex flex-1 flex-col rounded-2xl border border-slate-800 bg-slate-900/95 shadow-xl overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-slate-950 px-4 py-3">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-emerald-400" />
                <span className="font-mono text-xs font-bold text-slate-200">
                  Live Python Console (main.py)
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleBotAction('restart')}
                  disabled={restartingBot}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/25 disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${restartingBot ? 'animate-spin' : ''}`} />
                  <span>{lang === 'mm' ? 'Bot ပြန်စမည် (Restart)' : 'Restart Bot'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleBotAction('stop')}
                  disabled={restartingBot || !status?.botRunning}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/15 px-3 py-1.5 text-xs font-semibold text-rose-300 transition hover:bg-rose-500/25 disabled:opacity-50 cursor-pointer"
                >
                  <Square className="h-3.5 w-3.5" />
                  <span>{lang === 'mm' ? 'ရပ်မည်' : 'Stop'}</span>
                </button>
              </div>
            </div>

            <div
              ref={logContainerRef}
              className="flex-1 min-h-[380px] max-h-[500px] overflow-y-auto bg-slate-950/90 p-4 font-mono text-xs leading-relaxed text-slate-300 space-y-1"
            >
              {!status?.logs?.length ? (
                <div className="flex items-center gap-2 text-slate-500 py-8 justify-center">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Starting Python supervisor & connecting to Telegram...</span>
                </div>
              ) : (
                status.logs.map((line, i) => {
                  const isSuccess =
                    line.includes('started successfully') ||
                    line.includes('ACTIVE & READY') ||
                    line.includes('authenticated as');
                  const isWarn = line.includes('WARNING') || line.includes('not found');
                  const isErr = line.includes('ERROR') || line.includes('Failed') || line.includes('EXPIRED');
                  return (
                    <div
                      key={i}
                      className={`break-all ${
                        isSuccess
                          ? 'text-emerald-400 font-semibold'
                          : isErr
                          ? 'text-rose-400'
                          : isWarn
                          ? 'text-amber-300'
                          : 'text-slate-300'
                      }`}
                    >
                      {line}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
