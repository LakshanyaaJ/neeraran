/**
 * Root dev starter script for NEERARAN
 * Spawns FastAPI backend on port 8000 and Vite frontend on port 5173
 */
import { spawn } from 'child_process';
import path from 'path';

const isWindows = process.platform === 'win32';
const pythonCmd = isWindows ? 'python' : 'python3';
const npmCmd = isWindows ? 'npm.cmd' : 'npm';

console.log('🌊 Starting NEERARAN Monorepo Dev Environment...');

// Start FastAPI API
const apiProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'apps.api.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'], {
  stdio: 'inherit',
  shell: true,
});

// Start Vite React Web
const webProcess = spawn(npmCmd, ['run', 'dev'], {
  cwd: path.resolve(process.cwd(), 'apps/web'),
  stdio: 'inherit',
  shell: true,
});

function cleanup() {
  console.log('\nShutting down dev servers...');
  apiProcess.kill();
  webProcess.kill();
  process.exit();
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

