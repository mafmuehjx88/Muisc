import express from 'express';
import { createServer as createViteServer } from 'vite';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import zlib from 'zlib';
import JSZip from 'jszip';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MANAGER_URL = 'http://127.0.0.1:8765';
let spawningManager = false;

async function isManagerAlive(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1200);
    const res = await fetch(`${MANAGER_URL}/status`, { signal: controller.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureBotManager(): Promise<void> {
  if (await isManagerAlive()) return;
  if (spawningManager) {
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 250));
      if (await isManagerAlive()) return;
    }
    return;
  }

  spawningManager = true;
  try {
    const pyBin = fs.existsSync('/tmp/tgvenv/bin/python')
      ? '/tmp/tgvenv/bin/python'
      : 'python3';
    const scriptPath = path.join(__dirname, 'bot_manager.py');
    const child = spawn(pyBin, ['-u', scriptPath], {
      cwd: __dirname,
      detached: true,
      stdio: 'ignore',
    });
    child.unref();

    for (let i = 0; i < 25; i++) {
      await new Promise((r) => setTimeout(r, 250));
      if (await isManagerAlive()) break;
    }
  } finally {
    spawningManager = false;
  }
}

function extractConfigEnvContent(configSource: string): string {
  const grabStr = (key: string, fallback: string) => {
    const m = configSource.match(new RegExp(`os\\.getenv\\("${key}",\\s*"([^"]*)"\\)`));
    return m ? m[1] : fallback;
  };
  const grabInt = (key: string, fallback: string) => {
    const m = configSource.match(new RegExp(`os\\.getenv\\("${key}",\\s*(\\d+)\\)`));
    return m ? m[1] : fallback;
  };

  return [
    `API_ID=${grabInt('API_ID', '38953431')}`,
    `API_HASH=${grabStr('API_HASH', '2ba6fc60c837d5dfa52352304831a7c1')}`,
    `BOT_TOKEN=${grabStr('BOT_TOKEN', '8975164612:AAFiuzuhMKMxCGkRHesmdopGKThivrxkjes')}`,
    `STRING_SESSION=${grabStr('STRING_SESSION', '')}`,
    `BOT_NAME=${grabStr('BOT_NAME', 'Mario Music')}`,
    `ASSISTANT_NAME=${grabStr('ASSISTANT_NAME', 'Music Assistant')}`,
    `OWNER_ID=${grabInt('OWNER_ID', '7670796126')}`,
    `OWNER_USERNAME=${grabStr('OWNER_USERNAME', 'Yes_Im_Mario')}`,
    `SUPPORT_URL=${grabStr('SUPPORT_URL', 'https://t.me/mariostore_1z')}`,
    '',
  ].join('\n');
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Kick off Python bot supervisor immediately on server startup
  ensureBotManager().catch((err) => {
    console.error('Failed to ensure bot_manager.py:', err);
  });

  // Direct flat Wispbyte/VPS-ready ZIP builder with ALL live keys & assets pre-baked at root level
  app.get('/api/download-wispbyte-zip', async (_req, res) => {
    try {
      const zip = new JSZip();
      const rootTextFiles = [
        'main.py',
        'bot.py',
        'app.py',
        'config.py',
        'requirements.txt',
        'bot_data.json',
        'generate_session.py',
        'install_vps.sh',
        'Procfile',
        'Dockerfile',
        'README.md',
      ];

      let configRaw = '';
      for (const relName of rootTextFiles) {
        const fullPath = path.join(__dirname, relName);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          if (relName === 'config.py') configRaw = content;
          zip.file(relName, content);
        }
      }

      if (configRaw) {
        zip.file('.env', extractConfigEnvContent(configRaw));
      }

      const bannerPath = path.join(__dirname, 'assets', 'start_banner.jpg');
      if (fs.existsSync(bannerPath)) {
        zip.file('assets/start_banner.jpg', fs.readFileSync(bannerPath));
      }

      const zipBuffer = await zip.generateAsync({
        type: 'nodebuffer',
        compression: 'DEFLATE',
        compressionOptions: { level: 6 },
      });

      res.setHeader('Content-Type', 'application/zip');
      res.setHeader('Content-Disposition', 'attachment; filename="mario-music-wispbyte.zip"');
      res.setHeader('Cache-Control', 'no-store');
      res.send(zipBuffer);
    } catch (err: any) {
      console.error('Failed to generate Wispbyte ZIP:', err);
      res.status(500).json({ ok: false, error: err?.message || 'Failed to generate ZIP' });
    }
  });

  // Self-contained zero-auth 1-line terminal installer command (embeds code + live keys in base64 gzip)
  // Works on ANY external Ubuntu/Debian VPS, GitHub Codespaces, Cloud Shell, or Termux without cookie/auth walls
  app.get('/api/vps-one-liner', async (_req, res) => {
    try {
      const zip = new JSZip();
      const coreFiles = [
        'main.py',
        'bot.py',
        'app.py',
        'config.py',
        'requirements.txt',
        'bot_data.json',
        'install_vps.sh',
      ];
      let configRaw = '';
      for (const relName of coreFiles) {
        const fullPath = path.join(__dirname, relName);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          if (relName === 'config.py') configRaw = content;
          zip.file(relName, content);
        }
      }
      if (configRaw) {
        zip.file('.env', extractConfigEnvContent(configRaw));
      }

      const rawZip = await zip.generateAsync({
        type: 'nodebuffer',
        compression: 'DEFLATE',
        compressionOptions: { level: 9 },
      });
      const b64 = rawZip.toString('base64');

      const command = `mkdir -p ~/mario-music && cd ~/mario-music && python3 -c "import base64,io,zipfile; zipfile.ZipFile(io.BytesIO(base64.b64decode('${b64}'))).extractall('.')" && chmod +x install_vps.sh && bash ./install_vps.sh`;
      res.setHeader('Cache-Control', 'no-store');
      res.json({ ok: true, command, sizeBytes: command.length });
    } catch (err: any) {
      res.status(500).json({ ok: false, error: err?.message || 'Failed to build one-liner' });
    }
  });

  // Downloadable single-file self-extracting bash installer (includes start_banner.jpg + all live keys)
  app.get('/api/download-vps-script', async (_req, res) => {
    try {
      const zip = new JSZip();
      const rootTextFiles = [
        'main.py',
        'bot.py',
        'app.py',
        'config.py',
        'requirements.txt',
        'bot_data.json',
        'generate_session.py',
        'install_vps.sh',
        'Procfile',
        'Dockerfile',
      ];
      let configRaw = '';
      for (const relName of rootTextFiles) {
        const fullPath = path.join(__dirname, relName);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          if (relName === 'config.py') configRaw = content;
          zip.file(relName, content);
        }
      }
      if (configRaw) {
        zip.file('.env', extractConfigEnvContent(configRaw));
      }
      const bannerPath = path.join(__dirname, 'assets', 'start_banner.jpg');
      if (fs.existsSync(bannerPath)) {
        zip.file('assets/start_banner.jpg', fs.readFileSync(bannerPath));
      }

      const zipBuf = await zip.generateAsync({
        type: 'nodebuffer',
        compression: 'DEFLATE',
        compressionOptions: { level: 9 },
      });
      const gzB64 = zlib.gzipSync(zipBuf, { level: 9 }).toString('base64');

      const shContent = [
        '#!/usr/bin/env bash',
        'set -euo pipefail',
        'mkdir -p "$HOME/mario-music"',
        'cd "$HOME/mario-music"',
        'echo "[Unpacking] Extracting Mario Music Bot + Live Keys + Start Banner..."',
        'python3 - <<\'PYEOF\'',
        'import base64, gzip, io, zipfile',
        `DATA = "${gzB64}"`,
        'raw_zip = gzip.decompress(base64.b64decode(DATA))',
        'with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:',
        '    zf.extractall(".")',
        'PYEOF',
        'chmod +x install_vps.sh',
        'exec bash ./install_vps.sh',
        '',
      ].join('\n');

      res.setHeader('Content-Type', 'text/x-shellscript; charset=utf-8');
      res.setHeader('Content-Disposition', 'attachment; filename="mario-vps-auto.sh"');
      res.setHeader('Cache-Control', 'no-store');
      res.send(shContent);
    } catch (err: any) {
      res.status(500).json({ ok: false, error: err?.message || 'Failed to build script' });
    }
  });

  app.get('/api/manager/status', async (_req, res) => {
    try {
      await ensureBotManager();
      const upstream = await fetch(`${MANAGER_URL}/status`);
      const data = await upstream.json();
      res.json(data);
    } catch (err: any) {
      res.status(502).json({ ok: false, error: err?.message || 'Supervisor unavailable' });
    }
  });

  app.post('/api/manager/:action', async (req, res) => {
    const { action } = req.params;
    const allowed = new Set(['send-code', 'verify-code', 'restart', 'stop']);
    if (!allowed.has(action)) {
      res.status(404).json({ ok: false, error: 'Unknown action' });
      return;
    }
    try {
      await ensureBotManager();
      const upstream = await fetch(`${MANAGER_URL}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body || {}),
      });
      const data = await upstream.json();
      res.status(upstream.status).json(data);
    } catch (err: any) {
      res.status(502).json({ ok: false, error: err?.message || 'Supervisor request failed' });
    }
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
