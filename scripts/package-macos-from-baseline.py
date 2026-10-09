"""Reuse the user-verified .13 Mac payload without changing vendor binaries."""
from pathlib import Path
import argparse, copy, datetime, hashlib, json, plistlib, posixpath, stat, zipfile
from macho_inspect import inspect

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT
parser = argparse.ArgumentParser(description='Build using a privately supplied, verified .13 baseline')
parser.add_argument('--baseline', required=True)
parser.add_argument('--output', default='release-macos-2.3.4-arm64')
args = parser.parse_args()
BASE = Path(args.baseline).resolve()
BASE_SHA = '4c03646010252092f61a8da4c152825c51b1e95f2098087af68e7f8b453bef45'
OUT = APP / args.output
assert OUT.resolve().is_relative_to(APP.resolve()), 'Output must stay inside the checkout'
ASAR = OUT / 'app.asar'
PRODUCT = OUT / 'Hongguo-2.3.4-macOS-arm64.zip'
VERSION = '2.3.4'
BUILD = '2340'

def sha(data): return hashlib.sha256(data).hexdigest()
assert sha(BASE.read_bytes()) == BASE_SHA
assert json.loads((APP / 'package.json').read_text(encoding='utf8'))['version'] == VERSION
assert ASAR.is_file() and not PRODUCT.exists(), 'Refuse to overwrite a release'

import struct
def signature_pages(d):
    n = struct.unpack_from('<I', d, 16)[0]
    offset = 32
    result = []
    for _ in range(n):
        cmd, length = struct.unpack_from('<II', d, offset)
        if cmd == 29:
            pos, size = struct.unpack_from('<II', d, offset + 8)
            blob = d[pos:pos + size]
            cms = False
            for j in range(struct.unpack_from('>I', blob, 8)[0]):
                typ, bo = struct.unpack_from('>II', blob, 12 + j * 8)
                if typ == 65536:
                    cms = True
                b = blob[bo:]
                if struct.unpack_from('>I', b)[0] != 4208856066:
                    continue
                _, _, v, flags, ho, io, special, slots, limit = struct.unpack_from('>9I', b)
                hs, ht, platform, page = struct.unpack_from('4B', b, 36)
                alg = {1: 'sha1', 2: 'sha256', 3: 'sha256', 4: 'sha384'}[ht]
                assert slots == (limit + (1 << page) - 1) // (1 << page)
                for k in range(slots):
                    start = k * (1 << page)
                    actual = hashlib.new(alg, d[start:min(start + (1 << page), limit)]).digest()[:hs]
                    assert actual == b[ho + k * hs:ho + (k + 1) * hs], k
                result.append({'codePages': slots, 'flags': flags, 'hashType': ht, 'codeDirectoryVersion': v, 'specialSlots': special, 'allPageHashesVerified': True})
            for r in result:
                r['cmsPresent'] = cms
        offset += length
    return result

modified = set()
preserved = []
inventory = {}
with zipfile.ZipFile(BASE) as source, zipfile.ZipFile(PRODUCT, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as target:
    assert source.testzip() is None
    for entry in source.infolist():
        name = entry.filename
        assert not name.startswith('/') and '..' not in name.split('/')
        if name in ['bundle-SHA256SUMS.txt', 'bundle-symlinks.txt']:
            continue
        data = source.read(entry)
        if name == 'Hongguo.app/Contents/Resources/app.asar':
            data = ASAR.read_bytes(); modified.add(name)
        elif name == 'Hongguo.app/Contents/Info.plist' or (
                name.startswith('Hongguo.app/Contents/Frameworks/Hongguo Helper') and name.endswith('/Contents/Info.plist')):
            meta = plistlib.loads(data)
            meta.update(CFBundleVersion=BUILD, CFBundleShortVersionString=VERSION)
            data = plistlib.dumps(meta); modified.add(name)
        elif name == 'macOS使用说明.md':
            data = (ROOT / 'docs/INSTALL_MACOS.md').read_bytes(); modified.add(name)
        elif name == 'Mac验证说明.txt':
            data = ('红果 2.3.4 macOS ARM64。直接复用用户确认正常播放的 .13 运行资源与安装流程。'
                    '解压到新目录后运行 sh 准备Mac版.command；后台视频首帧自检通过才安装。'
                    '未获 Apple Developer ID 签名或公证，需本机 ad-hoc 准备。游客不访问钥匙串。'
                    '不需要管理员权限，不修改系统代理、全局证书或 Gatekeeper。'
                    '构建与共用链路测试在 Windows 完成，不等同 Mac 实机验收。').encode('utf8'); modified.add(name)
        else:
            preserved.append(name)
        # Copy the original ZipInfo so Unix executable modes and symbolic links survive.
        copied_entry = copy.copy(entry)
        # This offset belongs to the source archive; retaining it makes the
        # new archive's in-memory entries appear to overlap on Python 3.14.
        copied_entry._end_offset = None
        target.writestr(copied_entry, data)
    links = []
    records = []
    for entry in target.infolist():
        if stat.S_ISLNK(entry.external_attr >> 16):
            links.append(entry.filename + '\t' + target.read(entry).decode('utf8'))
        elif not entry.is_dir():
            records.append(sha(target.read(entry)) + '  ' + entry.filename)
    def text_file(name, data):
        entry = zipfile.ZipInfo(name, datetime.datetime.now().timetuple()[:6])
        entry.create_system = 3; entry.external_attr = (stat.S_IFREG | 0o644) << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        target.writestr(entry, data)
    link_data = ('\n'.join(links) + '\n').encode('utf8')
    text_file('bundle-symlinks.txt', link_data)
    records.append(sha(link_data) + '  bundle-symlinks.txt')
    text_file('bundle-SHA256SUMS.txt', ('\n'.join(records) + '\n').encode('utf8'))

with zipfile.ZipFile(BASE) as base, zipfile.ZipFile(PRODUCT) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == set(base.namelist())
    for name in preserved:
        assert z.read(name) == base.read(name), name
        assert z.getinfo(name).external_attr == base.getinfo(name).external_attr, name
    prefix = 'Hongguo.app/Contents/'
    for name in ['MacOS/Hongguo', 'Resources/apk-native/media/ffmpeg', 'Resources/apk-native/jre/bin/java']:
        inventory[name] = inspect(z.read(prefix + name))
        assert [v['arch'] for v in inventory[name]] == ['arm64']
        assert z.getinfo(prefix + name).external_attr >> 16 & 0o111
    meta = plistlib.loads(z.read(prefix + 'Info.plist'))
    assert meta['CFBundleShortVersionString'] == VERSION and meta['CFBundleVersion'] == BUILD
    assert meta['HongguoArchitecture'] == 'arm64'
    vendor = signature_pages(z.read(prefix + 'Resources/apk-native/media/ffmpeg'))
    assert vendor[0]['cmsPresent'] and vendor[0]['allPageHashesVerified']
    checks = {}
    for line in z.read('bundle-SHA256SUMS.txt').decode().splitlines():
        digest, name = line.split('  ', 1)
        assert sha(z.read(name)) == digest, name
        checks[name] = digest
    actual = {e.filename for e in z.infolist() if not e.is_dir() and not stat.S_ISLNK(e.external_attr >> 16)} - {'bundle-SHA256SUMS.txt'}
    assert actual == set(checks)
    links = {e.filename: z.read(e).decode('utf8') for e in z.infolist() if stat.S_ISLNK(e.external_attr >> 16)}
    assert links == dict(line.split('\t', 1) for line in z.read('bundle-symlinks.txt').decode().splitlines())
    for name, target in links.items():
        value = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
        for _ in range(40):
            parts = value.split('/'); found = False
            for j in range(1, len(parts) + 1):
                part = '/'.join(parts[:j])
                if part in links:
                    value = posixpath.normpath(posixpath.join(posixpath.dirname(part), links[part], *parts[j:])); found = True; break
            if not found: break
        else: raise ValueError('Cyclic link')
        assert value.startswith('Hongguo.app/') and any(x == value or x.startswith(value + '/') for x in z.namelist())
    assert not any(n.endswith(('/apk-guest.bin', '/account-v1.bin', '/diagnostic-log-v1.json', '/preferences-v2.json', '/Cookies')) for n in z.namelist())
    native_count = len([n for n in preserved if n.startswith(prefix + 'Resources/apk-native/')])

report = dict(version=VERSION, arch='arm64', bundleVersion=BUILD, minimumOS=meta['LSMinimumSystemVersion'],
              file=PRODUCT.name, bytes=PRODUCT.stat().st_size, sha256=sha(PRODUCT.read_bytes()),
              baseline=dict(file=BASE.name, sha256=BASE_SHA, playbackConfirmedByUser=True),
              changedPayloadFiles=sorted(modified), preservedPayloadFiles=len(preserved), preservedNativeFiles=native_count,
              inventory=inventory, ffmpegVendorBytesAndCodePagesPreserved=True, payloadChecksumsVerified=len(checks), symlinksVerified=len(links),
              developerIDSigned=False, appleNotarized=False, localMacPreparationRequired=True,
              macOSActualStartupVerified=False, macOSActualPlaybackVerified=False, publishedToGitHub=False,
              generatedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT / 'macOS发布校验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(OUT / 'SHA256SUMS.txt').write_text(report['sha256'] + '  ' + PRODUCT.name + '\n', encoding='utf8')
print(json.dumps(report, ensure_ascii=False, indent=2))
