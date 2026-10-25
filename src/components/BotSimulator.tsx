import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  SkipForward,
  Square,
  ListMusic,
  Send,
  Volume2,
  Mic,
  Users,
  Radio,
  Sparkles,
  Info,
  CheckCircle2,
  AlertCircle,
  Disc3,
  HelpCircle,
} from 'lucide-react';
import { ChatMessage, Track } from '../types';

interface BotSimulatorProps {
  lang: 'mm' | 'en';
}

const PRESET_SONGS: Track[] = [
  {
    id: '1',
    title: 'Alan Walker - Faded (Official Music Video)',
    duration: '03:32',
    durationSec: 212,
    link: 'https://youtube.com/watch?v=60ItHLz5WEA',
    channel: 'Alan Walker',
    thumbnail: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80',
    requester: 'Ko Min Thant',
  },
  {
    id: '2',
    title: 'The Weeknd - Blinding Lights (Audio)',
    duration: '03:20',
    durationSec: 200,
    link: 'https://youtube.com/watch?v=4NRXx6U8ABQ',
    channel: 'The Weeknd',
    thumbnail: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400&auto=format&fit=crop&q=80',
    requester: 'Su Myat',
  },
  {
    id: '3',
    title: 'Ed Sheeran - Shape of You',
    duration: '03:53',
    durationSec: 233,
    link: 'https://youtube.com/watch?v=JGwWNGJdvx8',
    channel: 'Ed Sheeran',
    thumbnail: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&auto=format&fit=crop&q=80',
    requester: 'Aung Kyaw',
  },
  {
    id: '4',
    title: 'Coldplay - Viva La Vida',
    duration: '04:02',
    durationSec: 242,
    link: 'https://youtube.com/watch?v=dvgZkm1xWPE',
    channel: 'Coldplay',
    thumbnail: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&auto=format&fit=crop&q=80',
    requester: 'Zayar Lin',
  },
];

export const BotSimulator: React.FC<BotSimulatorProps> = ({ lang }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      sender: 'system',
      senderName: 'Telegram System',
      text: 'Voice Chat started in "Myanmar Telegram Music Club 🇲🇲"',
      timestamp: '10:00 AM',
    },
    {
      id: 'init-2',
      sender: 'bot',
      senderName: 'Telegram Music Bot',
      text: '👋 **Hello everyone!**\n\nI am ready to stream high quality music in this Group Voice Chat.\nSend `/play <song name or link>` to start streaming!',
      timestamp: '10:01 AM',
      buttons: [
        { label: '📖 Help & Commands', action: '/help' },
        { label: '🎵 Play Sample Song', action: '/play Alan Walker Faded' },
      ],
    },
  ]);

  const [inputVal, setInputVal] = useState('');
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [queue, setQueue] = useState<Track[]>([]);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [inVoiceChat, setInVoiceChat] = useState<boolean>(true);
  const [playbackProgress, setPlaybackProgress] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Simulation timer for progress
  useEffect(() => {
    let interval: any;
    if (isPlaying && !isPaused && currentTrack) {
      interval = setInterval(() => {
        setPlaybackProgress((prev) => {
          if (prev >= 100) {
            handleAutoPlayNext();
            return 0;
          }
          return prev + 2;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, isPaused, currentTrack, queue]);

  const handleAutoPlayNext = () => {
    if (queue.length > 0) {
      const nextTrack = queue[0];
      const newQueue = queue.slice(1);
      setQueue(newQueue);
      setCurrentTrack(nextTrack);
      setPlaybackProgress(0);

      const botMsg: ChatMessage = {
        id: Date.now().toString(),
        sender: 'bot',
        senderName: 'Telegram Music Bot',
        text: `🎶 **Now Playing Next Track**\n\n🏷 **Title:** [${nextTrack.title}](${nextTrack.link})\n⏱ **Duration:** \`${nextTrack.duration}\`\n👤 **Requested by:** ${nextTrack.requester}\n\n⚡ _Enjoy the music!_`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        thumbnail: nextTrack.thumbnail,
        buttons: [
          { label: '⏸ Pause', action: '/pause' },
          { label: '⏭ Skip', action: '/skip' },
          { label: '⏹ Stop', action: '/stop' },
        ],
      };
      setMessages((prev) => [...prev, botMsg]);
    } else {
      setIsPlaying(false);
      setCurrentTrack(null);
      setPlaybackProgress(0);
      const botMsg: ChatMessage = {
        id: Date.now().toString(),
        sender: 'bot',
        senderName: 'Telegram Music Bot',
        text: '✨ **Queue Ended.** Assistant has left the voice chat. Add more songs with `/play`!',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    }
  };

  const processCommand = (cmdText: string) => {
    const trimmed = cmdText.trim();
    if (!trimmed) return;

    // Add user message
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      senderName: 'You (Admin)',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputVal('');

    const lower = trimmed.toLowerCase();

    if (lower.startsWith('/play') || lower.startsWith('/p')) {
      const query = trimmed.replace(/^\/(play|p)\s*/i, '').trim();
      if (!query) {
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⚠️ **Please provide a song name or YouTube link!**\nExample: `/play Alan Walker Faded` or `/play https://youtu.be/...`',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }, 300);
        return;
      }

      // Pick matching or generate track
      const matchedSong = PRESET_SONGS.find(
        (s) => s.title.toLowerCase().includes(query.toLowerCase()) || query.toLowerCase().includes(s.channel.toLowerCase())
      ) || {
        id: Date.now().toString(),
        title: query.includes('http') ? 'YouTube Stream Audio' : `${query} (Audio Track)`,
        duration: '03:45',
        durationSec: 225,
        link: 'https://youtube.com/results?search_query=' + encodeURIComponent(query),
        channel: 'YouTube Music',
        thumbnail: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80',
        requester: 'You',
      };

      setTimeout(() => {
        if (isPlaying && currentTrack) {
          // Add to Queue
          setQueue((prev) => [...prev, matchedSong]);
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: `📌 **Added To Queue (#${queue.length + 1})**\n\n🏷 **Title:** [${matchedSong.title}](${matchedSong.link})\n⏱ **Duration:** \`${matchedSong.duration}\`\n👤 **Requested by:** You`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              thumbnail: matchedSong.thumbnail,
            },
          ]);
        } else {
          // Play Immediately
          setIsPlaying(true);
          setIsPaused(false);
          setCurrentTrack(matchedSong);
          setPlaybackProgress(0);
          setInVoiceChat(true);

          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: `🎶 **Now Playing in Voice Chat**\n\n🏷 **Title:** [${matchedSong.title}](${matchedSong.link})\n⏱ **Duration:** \`${matchedSong.duration}\`\n👤 **Requested by:** You`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              thumbnail: matchedSong.thumbnail,
              buttons: [
                { label: '⏸ Pause', action: '/pause' },
                { label: '⏭ Skip', action: '/skip' },
                { label: '⏹ Stop', action: '/stop' },
              ],
            },
          ]);
        }
      }, 400);
    } else if (lower === '/pause') {
      setTimeout(() => {
        if (!isPlaying || !currentTrack) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⚠️ Nothing is currently playing.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else if (isPaused) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⏸ Stream is already paused. Use `/resume` to continue.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else {
          setIsPaused(true);
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⏸ **Audio Stream Paused.** Use `/resume` to continue playback.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }
      }, 300);
    } else if (lower === '/resume') {
      setTimeout(() => {
        if (!isPlaying || !currentTrack) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⚠️ Nothing is currently playing.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else if (!isPaused) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '▶️ Stream is not paused.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else {
          setIsPaused(false);
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '▶️ **Audio Stream Resumed.** Continuing playback...',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }
      }, 300);
    } else if (lower === '/skip' || lower === '/next') {
      setTimeout(() => {
        if (!isPlaying || !currentTrack) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⚠️ Nothing is currently playing to skip.',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '⏭ **Skipping to next track...**',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
          handleAutoPlayNext();
        }
      }, 300);
    } else if (lower === '/stop' || lower === '/end') {
      setTimeout(() => {
        setIsPlaying(false);
        setIsPaused(false);
        setCurrentTrack(null);
        setQueue([]);
        setPlaybackProgress(0);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: 'bot',
            senderName: 'Telegram Music Bot',
            text: '⏹ **Playback stopped & queue cleared.** Left voice chat.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }, 300);
    } else if (lower === '/queue' || lower === '/q') {
      setTimeout(() => {
        if (!currentTrack && queue.length === 0) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: '📭 **The music queue is currently empty.**\nAdd tracks with `/play <song>`!',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        } else {
          let qText = '📜 **Current Music Queue:**\n\n';
          if (currentTrack) {
            qText += `▶️ **Now Playing:**\n└ [${currentTrack.title}](${currentTrack.link}) | \`${currentTrack.duration}\` | ${currentTrack.requester}\n\n`;
          }
          if (queue.length > 0) {
            qText += '📋 **Up Next:**\n';
            queue.forEach((s, idx) => {
              qText += `\`${idx + 1}.\` [${s.title}](${s.link}) | \`${s.duration}\` | ${s.requester}\n`;
            });
          } else {
            qText += '_No upcoming tracks. Add songs with /play!_';
          }
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'bot',
              senderName: 'Telegram Music Bot',
              text: qText,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }
      }, 300);
    } else if (lower === '/help' || lower === '/start') {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: 'bot',
            senderName: 'Telegram Music Bot',
            text: `🎧 **Telegram Music Bot Commands:**\n\n▶️ \`/play <song/link>\` - Play or add song to queue\n⏸ \`/pause\` - Pause active voice chat audio\n▶️ \`/resume\` - Resume paused audio\n⏭ \`/skip\` - Play next song from queue\n⏹ \`/stop\` - Stop audio & clear queue\n📜 \`/queue\` - View current playlist\nℹ️ \`/help\` - Show this guide`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }, 300);
    } else {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: 'bot',
            senderName: 'Telegram Music Bot',
            text: `❓ Unrecognized command. Use \`/play <song name>\` or \`/help\` to see commands!`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }, 300);
    }
  };

  const handleQuickCommand = (cmd: string) => {
    processCommand(cmd);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Top Description */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider">
            <Radio className="h-4 w-4 animate-pulse" />
            <span>{lang === 'mm' ? 'တိုက်ရိုက် စမ်းသပ်ခန်း' : 'Interactive Sandbox'}</span>
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-white mt-0.5">
            {lang === 'mm'
              ? 'Telegram Voice Chat & Bot Simulator'
              : 'Telegram Group Voice Chat Bot Simulator'}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            {lang === 'mm'
              ? 'အောက်ပါ Command များကို ရိုက်ထည့်၍ Bot ၏ အလုပ်လုပ်ပုံနှင့် Voice Chat streaming စနစ်ကို စမ်းသပ်နိုင်ပါသည်။'
              : 'Test your bot commands, voice call join events, yt-dlp playback, and queue system in real-time.'}
          </p>
        </div>

        {/* Status Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <span>PyTgCalls: Online</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-300">
            <Disc3 className="h-3.5 w-3.5 animate-spin" />
            <span>Assistant: Ready</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Live Voice Chat Simulator Widget */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {/* Voice Chat Container */}
          <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-600/20 text-cyan-400 border border-cyan-500/30">
                  <Volume2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-200">
                    Group Voice Chat #1
                  </h3>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    <span>{isPlaying ? 'Active Stream' : 'Idle / Connected'}</span>
                    <span>•</span>
                    <span>{queue.length + (currentTrack ? 1 : 0)} in Queue</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 rounded-lg bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300">
                <Users className="h-3 w-3 text-cyan-400" />
                <span>4 Members</span>
              </div>
            </div>

            {/* Now Playing Card / Visualizer */}
            <div className="mt-4 rounded-xl border border-slate-800/80 bg-slate-950/80 p-4">
              {currentTrack ? (
                <div>
                  <div className="flex items-center gap-3">
                    <img
                      src={currentTrack.thumbnail}
                      alt={currentTrack.title}
                      referrerPolicy="no-referrer"
                      className="h-14 w-14 rounded-lg object-cover border border-slate-700 shadow-md"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
                        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                        {isPaused ? 'Paused' : 'Streaming Now'}
                      </div>
                      <h4 className="text-xs font-bold text-slate-100 truncate mt-0.5" title={currentTrack.title}>
                        {currentTrack.title}
                      </h4>
                      <p className="text-[11px] text-slate-400 truncate">
                        {currentTrack.channel} • Req by {currentTrack.requester}
                      </p>
                    </div>
                  </div>

                  {/* Audio Waveform Animation */}
                  <div className="mt-3 flex items-center justify-between gap-1 h-7 px-2 rounded-lg bg-slate-900/90 border border-slate-800">
                    {[40, 75, 30, 90, 60, 100, 45, 80, 20, 85, 95, 50, 70, 35, 90, 65, 40, 85, 30, 75].map(
                      (height, idx) => (
                        <div
                          key={idx}
                          className={`w-1 rounded-full transition-all duration-300 ${
                            isPaused
                              ? 'bg-slate-700 h-2'
                              : 'bg-gradient-to-t from-cyan-500 to-indigo-400'
                          }`}
                          style={{
                            height: isPaused ? '4px' : `${Math.max(4, (height * (isPlaying ? 1 : 0.2)) / 4)}px`,
                            animationDelay: `${idx * 50}ms`,
                          }}
                        />
                      )
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-3">
                    <div className="flex justify-between text-[10px] text-slate-400 font-mono mb-1">
                      <span>00:{Math.floor((playbackProgress * 2.12) / 100).toString().padStart(2, '0')}</span>
                      <span>{currentTrack.duration}</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-500"
                        style={{ width: `${playbackProgress}%` }}
                      />
                    </div>
                  </div>

                  {/* Playback Controls */}
                  <div className="mt-4 flex items-center justify-center gap-2">
                    <button
                      onClick={() => handleQuickCommand(isPaused ? '/resume' : '/pause')}
                      className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition cursor-pointer"
                    >
                      {isPaused ? <Play className="h-3.5 w-3.5 text-emerald-400" /> : <Pause className="h-3.5 w-3.5 text-amber-400" />}
                      <span>{isPaused ? 'Resume' : 'Pause'}</span>
                    </button>
                    <button
                      onClick={() => handleQuickCommand('/skip')}
                      className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition cursor-pointer"
                    >
                      <SkipForward className="h-3.5 w-3.5 text-cyan-400" />
                      <span>Skip</span>
                    </button>
                    <button
                      onClick={() => handleQuickCommand('/stop')}
                      className="flex items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition cursor-pointer"
                    >
                      <Square className="h-3.5 w-3.5" />
                      <span>Stop</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center">
                  <Disc3 className="mx-auto h-8 w-8 text-slate-600 animate-pulse" />
                  <p className="mt-2 text-xs font-medium text-slate-300">
                    {lang === 'mm' ? 'သီချင်း မဖွင့်ထားပါ' : 'No Audio Currently Playing'}
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {lang === 'mm'
                      ? 'သီချင်းစတင်ဖွင့်ရန် အောက်ပါ Preset သီချင်းကို နှိပ်ပါ'
                      : 'Send /play <song> in the chat to start streaming'}
                  </p>
                </div>
              )}
            </div>

            {/* Queue List Preview */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
                  <ListMusic className="h-3.5 w-3.5 text-cyan-400" />
                  <span>{lang === 'mm' ? 'တန်းစီစာရင်း (Queue)' : 'Up Next Queue'}</span>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">
                  {queue.length} songs
                </span>
              </div>

              {queue.length > 0 ? (
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {queue.map((track, idx) => (
                    <div
                      key={track.id + idx}
                      className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 p-2 text-xs"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono text-cyan-400 text-[11px] w-4 shrink-0">
                          #{idx + 1}
                        </span>
                        <div className="min-w-0">
                          <p className="font-medium text-slate-200 truncate">{track.title}</p>
                          <p className="text-[10px] text-slate-500">{track.channel}</p>
                        </div>
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0 ml-2">
                        {track.duration}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-800 p-3 text-center text-[11px] text-slate-500">
                  {lang === 'mm' ? 'Queue ထဲတွင် နောက်ထပ် သီချင်း မရှိသေးပါ' : 'Queue is empty. Click sample songs to enqueue!'}
                </div>
              )}
            </div>

            {/* Quick Song Preset Pills */}
            <div className="mt-4 border-t border-slate-800/80 pt-3">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                {lang === 'mm' ? 'နမူနာ သီချင်းများ ဖွင့်ရန်:' : 'Quick Sample Songs to Play:'}
              </span>
              <div className="grid grid-cols-2 gap-1.5">
                {PRESET_SONGS.map((song) => (
                  <button
                    key={song.id}
                    onClick={() => handleQuickCommand(`/play ${song.title.split('-')[0].trim()}`)}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/90 p-2 text-left text-xs text-slate-300 hover:border-cyan-500/40 hover:bg-slate-800 hover:text-white transition cursor-pointer"
                  >
                    <Play className="h-3 w-3 text-cyan-400 shrink-0" />
                    <span className="truncate">{song.title.split('-')[0].trim()}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Telegram Group Chat Window */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="flex flex-col h-[640px] rounded-2xl border border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
            {/* Telegram Group Header */}
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-600 to-indigo-600 font-bold text-white text-xs">
                  MM
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-200">
                    Myanmar Telegram Music Club 🇲🇲
                  </h3>
                  <p className="text-[10px] text-cyan-400">
                    {inVoiceChat ? 'Voice Chat Active (2 bots connected)' : 'No Voice Chat'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleQuickCommand('/help')}
                  className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:text-white transition cursor-pointer"
                >
                  <HelpCircle className="h-3 w-3" />
                  <span>/help</span>
                </button>
                <button
                  onClick={() => handleQuickCommand('/queue')}
                  className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:text-white transition cursor-pointer"
                >
                  <ListMusic className="h-3 w-3" />
                  <span>/queue</span>
                </button>
              </div>
            </div>

            {/* Chat Message Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-[#0e1621]">
              {messages.map((msg) => {
                const isUser = msg.sender === 'user';
                const isSystem = msg.sender === 'system';

                if (isSystem) {
                  return (
                    <div key={msg.id} className="flex justify-center my-1">
                      <span className="rounded-full bg-slate-800/80 px-3 py-1 text-[11px] text-cyan-300 border border-slate-700/50">
                        {msg.text}
                      </span>
                    </div>
                  );
                }

                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <span className="text-[10px] text-slate-400 mb-0.5 px-1 font-mono">
                      {msg.senderName} • {msg.timestamp}
                    </span>

                    <div
                      className={`max-w-[85%] rounded-2xl p-3.5 shadow-sm text-xs leading-relaxed ${
                        isUser
                          ? 'bg-cyan-600 text-white rounded-tr-none'
                          : 'bg-[#182533] text-slate-100 border border-slate-800 rounded-tl-none'
                      }`}
                    >
                      {msg.thumbnail && (
                        <img
                          src={msg.thumbnail}
                          alt="Thumbnail"
                          referrerPolicy="no-referrer"
                          className="mb-2.5 h-32 w-full rounded-xl object-cover border border-slate-700"
                        />
                      )}

                      <div className="whitespace-pre-wrap font-sans">
                        {msg.text.split('\n').map((paragraph, pIdx) => (
                          <p key={pIdx} className={pIdx > 0 ? 'mt-1.5' : ''}>
                            {paragraph}
                          </p>
                        ))}
                      </div>

                      {/* Interactive Buttons on Bot Messages */}
                      {msg.buttons && msg.buttons.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-700/60 pt-2.5">
                          {msg.buttons.map((btn, bIdx) => (
                            <button
                              key={bIdx}
                              onClick={() => handleQuickCommand(btn.action)}
                              className="rounded-lg border border-slate-600 bg-slate-800/90 px-2.5 py-1 text-[11px] font-medium text-cyan-300 hover:bg-slate-700 hover:text-white transition cursor-pointer"
                            >
                              {btn.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Command Toolbar */}
            <div className="flex items-center gap-1.5 border-t border-slate-800 bg-slate-950/70 px-3 py-2 overflow-x-auto">
              <span className="text-[10px] uppercase font-bold text-slate-500 shrink-0">
                {lang === 'mm' ? 'Command များ:' : 'Commands:'}
              </span>
              {[
                { label: '/play', cmd: '/play Alan Walker Faded' },
                { label: '/pause', cmd: '/pause' },
                { label: '/resume', cmd: '/resume' },
                { label: '/skip', cmd: '/skip' },
                { label: '/queue', cmd: '/queue' },
                { label: '/stop', cmd: '/stop' },
              ].map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickCommand(item.cmd)}
                  className="rounded-md border border-slate-800 bg-slate-900 px-2 py-0.5 text-[11px] font-mono text-cyan-300 hover:bg-slate-800 transition cursor-pointer shrink-0"
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Chat Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                processCommand(inputVal);
              }}
              className="flex items-center gap-2 border-t border-slate-800 bg-slate-950 px-3 py-2.5"
            >
              <input
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                placeholder={
                  lang === 'mm'
                    ? 'Command ရိုက်ထည့်ပါ (ဥပမာ: /play Alan Walker သို့မဟုတ် /pause)...'
                    : 'Type command (e.g. /play Blinding Lights, /skip, /stop)...'
                }
                className="flex-1 rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              <button
                type="submit"
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-600 text-white shadow-md hover:bg-cyan-500 transition cursor-pointer"
                title="Send Command"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
