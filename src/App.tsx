import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { LiveControlPanel } from './components/LiveControlPanel';
import { CodeViewer } from './components/CodeViewer';
import { BotSimulator } from './components/BotSimulator';
import { SetupGuide } from './components/SetupGuide';
import { ArchitectureView } from './components/ArchitectureView';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('live');
  const [lang, setLang] = useState<'mm' | 'en'>('mm');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        lang={lang}
        setLang={setLang}
      />

      <main className="flex-1 pb-16">
        {activeTab === 'live' && <LiveControlPanel lang={lang} />}
        {activeTab === 'code' && <CodeViewer lang={lang} />}
        {activeTab === 'simulator' && <BotSimulator lang={lang} />}
        {activeTab === 'setup' && <SetupGuide lang={lang} />}
        {activeTab === 'architecture' && <ArchitectureView lang={lang} />}
      </main>

      <footer className="border-t border-slate-800/80 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>
            Telegram Group Music Bot • Powered by <span className="text-cyan-400 font-mono">Pyrogram v2</span>, <span className="text-indigo-400 font-mono">PyTgCalls</span> & <span className="text-rose-400 font-mono">yt-dlp</span>
          </p>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>Python 3.9+</span>
            <span>•</span>
            <span>MIT License</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
