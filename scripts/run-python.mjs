import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const attempts = process.env.HONGGUO_PYTHON ? [[process.env.HONGGUO_PYTHON, []]] : [['python3', []], ['python', []], ['py', ['-3']]];
if (!process.env.HONGGUO_PYTHON && process.platform === 'win32' && process.env.LOCALAPPDATA) {
  const folder = path.join(process.env.LOCALAPPDATA, 'Programs/Python');
  if (fs.existsSync(folder)) for (const name of fs.readdirSync(folder).sort().reverse()) {
    const exe = path.join(folder, name, 'python.exe');
    if (fs.existsSync(exe)) attempts.push([exe, []]);
  }
}
for (const [exe, prefix] of attempts) {
  const check = spawnSync(exe, [...prefix, '-c', 'import sys; assert sys.version_info >= (3,11)'], {windowsHide:true,stdio:'ignore',timeout:10000});
  if (check.status !== 0) continue;
  const result = spawnSync(exe, [...prefix, '-X', 'utf8', ...process.argv.slice(2)], {windowsHide:true,stdio:'inherit'});
  process.exit(result.status ?? 1);
}
console.error('Python 3.11+ is required for source packaging. Set HONGGUO_PYTHON to its executable.');
process.exit(1);
