import React from 'react';
import { Bot, UserCheck, Radio, Music, Youtube, Database, ArrowRight, CheckCircle2, Shield } from 'lucide-react';

interface ArchitectureViewProps {
  lang: 'mm' | 'en';
}

export const ArchitectureView: React.FC<ArchitectureViewProps> = ({ lang }) => {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Header */}
      <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider">
          <Database className="h-4 w-4" />
          <span>{lang === 'mm' ? 'စနစ်ဖွဲ့စည်းပုံ' : 'System Architecture'}</span>
        </div>
        <h2 className="mt-1 text-xl font-bold text-white sm:text-2xl">
          {lang === 'mm'
            ? 'Telegram Group Voice Chat Music Bot တည်ဆောက်ပုံ'
            : 'Dual-Client MTProto & PyTgCalls Architecture'}
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-400">
          {lang === 'mm'
            ? 'Bot Client (Command Handlers) နှင့် Userbot Assistant (PyTgCalls Voice Streaming) အချင်းချင်း ချိတ်ဆက် အလုပ်လုပ်ပုံ။'
            : 'How the Pyrogram Bot Client, Assistant MTProto Userbot, PyTgCalls audio pipeline, and yt-dlp extractor interact seamlessly.'}
        </p>
      </div>

      {/* Visual Pipeline Flow */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {/* Step 1 */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 relative">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 mb-3">
            <Bot className="h-5 w-5" />
          </div>
          <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Step 1</span>
          <h3 className="text-sm font-bold text-slate-100 mt-1">Bot Client (Pyrogram)</h3>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            {lang === 'mm'
              ? 'Group ထဲမှ /play, /pause, /skip command များကို ဖတ်ယူပြီး စစ်ဆေးသည်။'
              : 'Listens to Telegram messages, checks admin permissions, and manages inline callback buttons.'}
          </p>
        </div>

        {/* Step 2 */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 relative">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-600/20 text-rose-400 border border-rose-500/30 mb-3">
            <Youtube className="h-5 w-5" />
          </div>
          <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider">Step 2</span>
          <h3 className="text-sm font-bold text-slate-100 mt-1">yt-dlp Extractor</h3>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            {lang === 'mm'
              ? 'YouTube မှ အကောင်းဆုံး အသံ stream URL နှင့် သီချင်းအချက်အလက်များကို Async ရှာဖွေသည်။'
              : 'Non-blocking executor extracts best opus/mp3 stream URL, title, duration, and thumbnail.'}
          </p>
        </div>

        {/* Step 3 */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 relative">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 mb-3">
            <Database className="h-5 w-5" />
          </div>
          <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Step 3</span>
          <h3 className="text-sm font-bold text-slate-100 mt-1">In-Memory Queue</h3>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            {lang === 'mm'
              ? 'Chat ID အလိုက် သီချင်းစာရင်းများကို Queue Dictionary ဖြင့် တန်းစီသိမ်းဆည်းသည်။'
              : 'Tracks state per chat_id in QUEUES dictionary for continuous multi-track streaming.'}
          </p>
        </div>

        {/* Step 4 */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 relative">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 mb-3">
            <Radio className="h-5 w-5" />
          </div>
          <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Step 4</span>
          <h3 className="text-sm font-bold text-slate-100 mt-1">PyTgCalls Stream</h3>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            {lang === 'mm'
              ? 'Assistant Account မှ Voice Chat ထဲ join ပြီး AudioPiped ဖြင့် အသံ stream သည်။'
              : 'Assistant userbot joins WebRTC voice chat session and pipes high-bitrate live audio.'}
          </p>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-sm font-bold text-cyan-300 mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-cyan-400" />
            {lang === 'mm' ? 'အဘယ်ကြောင့် Dual Client လိုအပ်သနည်း?' : 'Why Dual-Client Architecture?'}
          </h3>
          <ul className="space-y-2.5 text-xs text-slate-300">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              <span><strong>Bot Account (@BotFather)</strong> handles incoming /play commands, inline menus, permissions, and status notifications.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              <span><strong>Assistant Account (Userbot)</strong> utilizes MTProto protocol via String Session to join the Telegram Voice Call room as a speaker.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              <span><strong>PyTgCalls</strong> connects FFmpeg audio pipe directly into Telegram's WebRTC voice group channels without latency.</span>
            </li>
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-sm font-bold text-emerald-300 mb-3 flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-400" />
            {lang === 'mm' ? 'Auto-Play Next Event Listener' : 'Auto-Play Next Stream Listener'}
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Whenever an active audio track concludes in the group voice chat, the PyTgCalls listener:
          </p>
          <div className="mt-3 rounded-xl bg-slate-950 p-3 text-xs font-mono text-cyan-300 border border-slate-800">
            <pre className="whitespace-pre-wrap">{`@pytgcalls.on_stream_end()
async def stream_end_handler(_, update):
    await play_next_track(update.chat_id)`}</pre>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Automatically pops the next song from QUEUES[chat_id] and streams it seamlessly without manual intervention.
          </p>
        </div>
      </div>
    </div>
  );
};
