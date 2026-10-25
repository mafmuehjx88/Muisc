import React, { useState } from 'react';
import {
  Copy,
  Check,
  Download,
  FileCode2,
  Settings,
  Package,
  KeyRound,
  Container,
  TerminalSquare,
  BookOpen,
  Search,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import { CODE_FILES } from '../data/codeFiles';
import { CodeFile } from '../types';

interface CodeViewerProps {
  lang: 'mm' | 'en';
}

const getIcon = (iconName: string) => {
  switch (iconName) {
    case 'FileCode2':
      return <FileCode2 className="h-4 w-4 text-cyan-400" />;
    case 'Settings':
      return <Settings className="h-4 w-4 text-amber-400" />;
    case 'Package':
      return <Package className="h-4 w-4 text-emerald-400" />;
    case 'KeyRound':
      return <KeyRound className="h-4 w-4 text-purple-400" />;
    case 'Container':
      return <Container className="h-4 w-4 text-blue-400" />;
    case 'TerminalSquare':
      return <TerminalSquare className="h-4 w-4 text-rose-400" />;
    case 'BookOpen':
      return <BookOpen className="h-4 w-4 text-teal-400" />;
    default:
      return <FileCode2 className="h-4 w-4 text-cyan-400" />;
  }
};

export const CodeViewer: React.FC<CodeViewerProps> = ({ lang }) => {
  const [selectedFile, setSelectedFile] = useState<CodeFile>(CODE_FILES[0]);
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSingle = () => {
    const blob = new Blob([selectedFile.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const filteredFiles = CODE_FILES.filter((f) =>
    f.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const lines = selectedFile.content.split('\n');

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Top Banner with highlight */}
      <div className="mb-6 rounded-2xl border border-slate-800 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-indigo-950/40 p-5 sm:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-cyan-400">
              <Sparkles className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">
                {lang === 'mm' ? 'အသင့်သုံးနိုင်သော Bot ကုဒ်' : 'Production Ready Codebase'}
              </span>
            </div>
            <h2 className="mt-1 text-xl font-bold text-white sm:text-2xl">
              {lang === 'mm'
                ? 'Telegram Group Voice Chat Music Bot ကုဒ်ဖိုင်များ'
                : 'Telegram Group Voice Chat Music Bot Files'}
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-slate-300">
              {lang === 'mm'
                ? 'Pyrogram v2.0+ နှင့် PyTgCalls သုံးပြီး အလိုအလျောက် သီချင်းဖွင့်စနစ်၊ Queue System၊ Stream End Auto-play များပါဝင်သည်။'
                : 'Built with Pyrogram v2.0+, PyTgCalls audio streaming, yt-dlp YouTube extraction, in-memory queue management, and interactive Telegram buttons.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/90 px-3.5 py-2 text-xs font-medium text-slate-200 shadow-sm transition hover:bg-slate-700 hover:text-white cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-emerald-400" />
                  <span className="text-emerald-400">
                    {lang === 'mm' ? 'ကူးယူပြီးပါပြီ!' : 'Copied!'}
                  </span>
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 text-slate-400" />
                  <span>
                    {lang === 'mm'
                      ? `${selectedFile.filename} ကို Copy ယူမည်`
                      : `Copy ${selectedFile.filename}`}
                  </span>
                </>
              )}
            </button>
            <button
              onClick={handleDownloadSingle}
              className="flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-600/20 px-3.5 py-2 text-xs font-medium text-cyan-300 transition hover:bg-cyan-600/30 hover:text-cyan-200 cursor-pointer"
            >
              <Download className="h-4 w-4" />
              <span>{lang === 'mm' ? 'ဖိုင်ဒေါင်းမည်' : 'Download'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Code Studio Split Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Sidebar: File Explorer */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                {lang === 'mm' ? 'ပရောဂျက် ဖိုင်များ (Project Tree)' : 'Project Workspace Files'}
              </h3>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-400">
                {CODE_FILES.length} files
              </span>
            </div>

            {/* Search Input */}
            <div className="relative mb-3">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder={lang === 'mm' ? 'ဖိုင်ရှာရန်...' : 'Search files...'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/80 py-2 pr-3 pl-8 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {/* File List */}
            <div className="space-y-1.5 max-h-[520px] overflow-y-auto pr-1">
              {filteredFiles.map((file) => {
                const isSelected = selectedFile.filename === file.filename;
                return (
                  <button
                    key={file.filename}
                    onClick={() => setSelectedFile(file)}
                    className={`group flex w-full items-start gap-3 rounded-xl p-3 text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border border-cyan-500/40 bg-cyan-950/30 text-white shadow-sm'
                        : 'border border-transparent hover:border-slate-800 hover:bg-slate-800/50 text-slate-300'
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">{getIcon(file.iconName)}</div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className={`font-mono text-xs font-semibold truncate ${isSelected ? 'text-cyan-300' : 'text-slate-200'}`}>
                          {file.filename}
                        </span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase font-mono text-slate-400">
                          {file.language}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                        {file.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Credential Card */}
          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              {lang === 'mm' ? 'ထည့်သွင်းထားသော Bot Credentials' : 'Embedded Bot Credentials'}
            </h4>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between rounded-lg bg-slate-950/60 p-2 border border-slate-800/60">
                <span className="text-slate-400">API_ID:</span>
                <span className="text-cyan-300">38953431</span>
              </div>
              <div className="flex justify-between rounded-lg bg-slate-950/60 p-2 border border-slate-800/60">
                <span className="text-slate-400">API_HASH:</span>
                <span className="text-cyan-300 truncate max-w-[140px]" title="2ba6fc60c837d5dfa52352304831a7c1">2ba6fc...a7c1</span>
              </div>
              <div className="flex justify-between rounded-lg bg-slate-950/60 p-2 border border-slate-800/60">
                <span className="text-slate-400">BOT_TOKEN:</span>
                <span className="text-cyan-300 truncate max-w-[140px]" title="8975164612:AAFiuzuhMKMxCGkRHesmdopGKThivrxkjes">897516...kjes</span>
              </div>
              <div className="flex justify-between rounded-lg bg-slate-950/60 p-2 border border-amber-500/30">
                <span className="text-slate-400">STRING_SESSION:</span>
                <span className="text-amber-400 truncate max-w-[140px]">Pending New Account</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Code Display Area */}
        <div className="lg:col-span-8 flex flex-col">
          <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
            {/* Code Header Bar */}
            <div className="flex flex-wrap items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 py-3 gap-2">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5 mr-2">
                  <div className="h-3 w-3 rounded-full bg-rose-500/80" />
                  <div className="h-3 w-3 rounded-full bg-amber-500/80" />
                  <div className="h-3 w-3 rounded-full bg-emerald-500/80" />
                </div>
                {getIcon(selectedFile.iconName)}
                <span className="font-mono text-xs font-bold text-slate-200">
                  {selectedFile.filename}
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  ({lines.length} lines)
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white transition cursor-pointer"
                  title="Copy file contents"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400 text-[11px]">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-slate-400" />
                      <span className="text-[11px]">Copy</span>
                    </>
                  )}
                </button>

                <button
                  onClick={handleDownloadSingle}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white transition cursor-pointer"
                  title="Download this file"
                >
                  <Download className="h-3.5 w-3.5 text-slate-400" />
                  <span className="text-[11px]">Save</span>
                </button>
              </div>
            </div>

            {/* Code Content with Line Numbers */}
            <div className="relative max-h-[650px] overflow-auto bg-[#0d1117] p-4 text-xs font-mono">
              <table className="w-full border-collapse">
                <tbody>
                  {lines.map((line, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40">
                      <td className="w-12 select-none pr-4 text-right text-[11px] text-slate-600 font-mono align-top">
                        {idx + 1}
                      </td>
                      <td className="select-text whitespace-pre text-slate-200 font-mono leading-relaxed break-all">
                        {line}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Bottom Footer Info */}
            <div className="flex items-center justify-between border-t border-slate-800/80 bg-slate-950/60 px-4 py-2 text-[11px] text-slate-400">
              <span>File: <strong className="text-slate-300">{selectedFile.filename}</strong></span>
              <span>Encoding: <strong className="text-slate-300">UTF-8</strong> | Mode: <strong className="text-cyan-400">{selectedFile.language.toUpperCase()}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
