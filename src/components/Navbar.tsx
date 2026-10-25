import React from 'react';
import { Download, Bot, Radio, Code2, Terminal, BookOpen, Layers } from 'lucide-react';
import JSZip from 'jszip';
import { CODE_FILES } from '../data/codeFiles';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  lang: 'mm' | 'en';
  setLang: (lang: 'mm' | 'en') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  lang,
  setLang,
}) => {
  const [downloading, setDownloading] = React.useState(false);

  const handleDownloadZip = async () => {
    setDownloading(true);
    try {
      const zip = new JSZip();
      CODE_FILES.forEach((file) => {
        zip.file(file.filename, file.content);
      });
      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'telegram-group-music-bot.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  const navItems = [
    { id: 'live', labelEn: 'Live Bot & OTP', labelMm: 'တိုက်ရိုက် Run & OTP', icon: Radio },
    { id: 'code', labelEn: 'Source Code', labelMm: 'ကုဒ်ဖိုင်များ', icon: Code2 },
    { id: 'simulator', labelEn: 'Simulator', labelMm: 'စမ်းသပ်ခန်း', icon: Terminal },
    { id: 'setup', labelEn: 'Setup Guide', labelMm: 'လမ်းညွှန်', icon: BookOpen },
    { id: 'architecture', labelEn: 'Architecture', labelMm: 'တည်ဆောက်ပုံ', icon: Layers },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 shadow-lg shadow-cyan-500/20">
            <Bot className="h-5 w-5 text-white" />
            <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-white sm:text-lg">
                Telegram Music Bot
              </h1>
              <span className="inline-flex items-center gap-1 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
                <Radio className="h-2.5 w-2.5 animate-pulse" />
                Pyrogram v2 + PyTgCalls
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans">
              {lang === 'mm'
                ? 'Group Voice Chat သီချင်းဖွင့် Bot အပြည့်အစုံ'
                : 'Production-ready Python Group Voice Chat Bot'}
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="hidden lg:flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow-md shadow-cyan-500/20'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{lang === 'mm' ? item.labelMm : item.labelEn}</span>
              </button>
            );
          })}
        </div>

        {/* Right Actions: Lang Switcher & Download Button */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="flex rounded-lg border border-slate-800 bg-slate-900 p-0.5 text-xs">
            <button
              onClick={() => setLang('mm')}
              className={`rounded-md px-2 py-1 font-medium transition-colors ${
                lang === 'mm'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Myanmar Unicode"
            >
              🇲🇲 မြန်မာ
            </button>
            <button
              onClick={() => setLang('en')}
              className={`rounded-md px-2 py-1 font-medium transition-colors ${
                lang === 'en'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="English"
            >
              🇬🇧 EN
            </button>
          </div>

          <button
            onClick={handleDownloadZip}
            disabled={downloading}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-500/20 transition-all hover:from-emerald-500 hover:to-teal-500 hover:shadow-emerald-500/30 active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">
              {downloading
                ? lang === 'mm'
                  ? 'ဒေါင်းလုဒ်လုပ်နေသည်...'
                  : 'Packing ZIP...'
                : lang === 'mm'
                ? 'Zip ဖိုင်ဒေါင်းမည် (.zip)'
                : 'Download All (.zip)'}
            </span>
            <span className="sm:hidden">ZIP</span>
          </button>
        </div>
      </div>

      {/* Mobile Tab bar */}
      <div className="flex lg:hidden overflow-x-auto border-t border-slate-800/80 bg-slate-900/60 px-2 py-1.5 gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-cyan-600/30 border border-cyan-500/40 text-cyan-200'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <Icon className="h-3 w-3" />
              <span>{lang === 'mm' ? item.labelMm : item.labelEn}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
};
