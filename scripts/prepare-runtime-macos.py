"""Extract privately supplied baseline resources into a new local folder only."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, platform, stat, zipfile

ROOT=Path(__file__).resolve().parents[1]
EXPECTED='4c03646010252092f61a8da4c152825c51b1e95f2098087af68e7f8b453bef45'
parser=argparse.ArgumentParser()
parser.add_argument('--baseline',required=True)
args=parser.parse_args()
if platform.system()!='Darwin' or platform.machine()!='arm64':
    raise SystemExit('Development runtime preparation requires an Apple Silicon Mac.')
baseline=Path(args.baseline).resolve()
with baseline.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==EXPECTED, 'Baseline checksum mismatch'
out=ROOT/'native-resources-macos/arm64'
assert not out.exists(), 'Back up and move aside existing runtime before preparing it'
prefix='Hongguo.app/Contents/Resources/apk-native/'
with zipfile.ZipFile(baseline) as z:
    assert z.testzip() is None
    entries=[e for e in z.infolist() if e.filename.startswith(prefix) and e.filename!=prefix]
    for e in entries:
        p=PurePosixPath(e.filename[len(prefix):])
        assert not p.is_absolute() and '..' not in p.parts
        if stat.S_ISLNK(e.external_attr>>16):
            target=z.read(e).decode('utf8')
            assert not Path(target).is_absolute() and (out.joinpath(*p.parts).parent/target).resolve().is_relative_to(out.resolve())
    out.mkdir(parents=True)
    for e in entries:
        if stat.S_ISLNK(e.external_attr>>16): continue
        p=out.joinpath(*PurePosixPath(e.filename[len(prefix):]).parts)
        if e.is_dir(): p.mkdir(parents=True,exist_ok=True)
        else:
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(e));p.chmod(stat.S_IMODE(e.external_attr>>16))
    for e in entries:
        if stat.S_ISLNK(e.external_attr>>16):
            p=out.joinpath(*PurePosixPath(e.filename[len(prefix):]).parts)
            p.parent.mkdir(parents=True,exist_ok=True);os.symlink(z.read(e).decode('utf8'),p)
    c=json.loads((out/'msconfig.json').read_text())
    assert isinstance(c,list) and all(c[i]=='' for i in [6,7,8,9,13]), 'Captured identity fields must be empty'
print('Prepared locally supplied ARM64 resources. Directory is ignored by Git; no system settings changed.')
