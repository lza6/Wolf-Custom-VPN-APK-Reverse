"""Extract Go pclntab function names from libgojni.so (found via magic scan)."""
import struct, sys, re

path = sys.argv[1] if len(sys.argv) > 1 else 'recon/libgojni.so'
pcln_off = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x13fde80
data = open(path, 'rb').read()

nfunc = struct.unpack_from('<q', data, pcln_off + 8)[0]
textStart = struct.unpack_from('<Q', data, pcln_off + 24)[0]
funcnameOff = struct.unpack_from('<Q', data, pcln_off + 32)[0]
pclnOff = struct.unpack_from('<Q', data, pcln_off + 64)[0]

names = []
for i in range(nfunc):
    entryoff, funcoff = struct.unpack_from('<II', data, pcln_off + pclnOff + i * 8)
    nameOff = struct.unpack_from('<i', data, pcln_off + pclnOff + funcoff + 4)[0]
    ns = pcln_off + funcnameOff + nameOff
    ne = data.find(b'\0', ns)
    name = data[ns:ne].decode('utf-8', 'replace')
    names.append((textStart + entryoff, name))

with open('recon/gofuncs.txt', 'w', encoding='utf-8') as f:
    for va, n in names:
        f.write(f'{va:#x} {n}\n')
print('funcs:', len(names), '-> recon/gofuncs.txt')

interesting = [n for _, n in names if re.search(r'(?i)(encrypt|decrypt|argon|gcm|payload|updateurl|newdecrypt|libpassword|wolf|injector|fetch|config)', n)]
for n in interesting[:60]:
    print(n)
