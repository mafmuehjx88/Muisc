export interface CodeFile {
  name: string;
  filename: string;
  language: string;
  description: string;
  content: string;
  iconName: string;
}

export interface Track {
  id: string;
  title: string;
  duration: string;
  durationSec: number;
  link: string;
  channel: string;
  thumbnail: string;
  requester: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot' | 'system';
  senderName: string;
  text: string;
  timestamp: string;
  buttons?: { label: string; action: string }[];
  thumbnail?: string;
}
