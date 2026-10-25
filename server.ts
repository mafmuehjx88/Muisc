import express from 'express';
import { createServer as createViteServer } from 'vite';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

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

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Kick off Python bot supervisor immediately on server startup
  ensureBotManager().catch((err) => {
    console.error('Failed to ensure bot_manager.py:', err);
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
