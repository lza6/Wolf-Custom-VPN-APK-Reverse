"""Dump all lsparanoid-obfuscated strings from a jadx-decompiled source tree.

Usage: python dump_strings.py <sources_root> <DeobfuscatorClass.java> <out.json> <loc.json>
Works for any APK whose strings use org.lsposed.lsparanoid (Deobfuscator$<APP>$<module> naming).
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lsparanoid_deobf import deobf, load_chunks


def main():
    root, chunk_path, out_path, loc_path = sys.argv[1:5]
    cls_name = os.path.basename(chunk_path).split('$')[1].split('.')[0]
    CHUNKS = load_chunks(chunk_path)
    pat = re.compile(r'Deobfuscator\$' + re.escape(cls_name) + r'\$app\.getString\((-?\d+L?)\)')
    out, loc = {}, {}
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.endswith('.java'):
                continue
            p = os.path.join(dirpath, f)
            try:
                t = open(p, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            ms = pat.findall(t)
            if not ms:
                continue
            rel = os.path.relpath(p, root)
            for m in set(ms):
                v = int(m.rstrip('L'), 10)
                if v not in out:
                    try:
                        out[v] = deobf(v & 0xFFFFFFFFFFFFFFFF, CHUNKS)
                    except Exception:
                        out[v] = '<ERR>'
                loc.setdefault(v, []).append(rel)

    def clean(s):
        return s.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')

    json.dump({str(k): clean(v) for k, v in out.items()}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({str(k): v for k, v in loc.items()}, open(loc_path, 'w', encoding='utf-8'), indent=1)
    print('unique strings:', len(out), '->', out_path)


if __name__ == '__main__':
    main()
