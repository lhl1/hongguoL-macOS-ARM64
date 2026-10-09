import {spawnSync} from 'node:child_process';import fs from 'node:fs';import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');process.chdir(root);
const args=process.argv.slice(2);
if(args.length!==2||args[0]!=='--baseline')throw Error('Usage: npm run pack:mac -- --baseline /path/to/private-.13-arm64.zip');
const baseline=path.resolve(args[1]);if(!fs.statSync(baseline).isFile())throw Error('Baseline must be a local ZIP file.');
const version=JSON.parse(fs.readFileSync('package.json','utf8')).version;
const output='release-macos-'+version+'-arm64';
if(fs.existsSync(output))throw Error('Output already exists; back it up and move it aside before rebuilding.');
function run(exe,parameters,options={}){const r=spawnSync(exe,parameters,{cwd:root,windowsHide:true,stdio:'inherit',...options});if(r.error)throw r.error;if(r.status!==0)process.exit(r.status??1);}
if(process.platform==='win32')run(process.env.ComSpec||'cmd.exe',['/d','/s','/c','npm run build']);
else run('npm',['run','build']);
run(process.execPath,['scripts/stage-macos-asar.mjs',output]);
run(process.execPath,['scripts/run-python.mjs','scripts/package-macos-from-baseline.py','--baseline',baseline,'--output',output]);
