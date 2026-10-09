import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createPackage} from '@electron/asar';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(root, process.argv[2] || 'release-macos');
await fs.mkdir(output, {recursive:true});
const stage = await fs.mkdtemp(path.join(output, '.source-stage-'));
for (const name of ['dist', 'electron']) await fs.cp(path.join(root, name), path.join(stage, name), {recursive:true});
const source = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
// The renderer is bundled by Vite and main-process modules use only Node/Electron built-ins.
await fs.writeFile(path.join(stage, 'package.json'), JSON.stringify({name:source.name,version:source.version,main:source.main,description:source.description}, null, 2));
await createPackage(stage, path.join(output, 'app.asar'));
console.log('Staged shared desktop app', source.version, 'without profiles or device identifiers.');
