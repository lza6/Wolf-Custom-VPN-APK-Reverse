import sys, re, codecs

M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
MAX_CHUNK = 8191

def s16(v):
    v &= 0xFFFF
    return v - (1 << 16) if v >= (1 << 15) else v

def se16(v):
    # sign-extend short to 64-bit two's complement (as unsigned repr)
    return s16(v) & M64

def i32(v):
    v &= M32
    return v - (1 << 32) if v >= (1 << 31) else v

def rotl(s, i):
    # rotl(short s, int i) = (short)((s >>> (32-i)) | (s << i)) with s promoted to signed 32-bit int
    si = i32(se16(s))  # signed int
    si_u = si & M32
    a = si_u >> (32 - i)          # unsigned shift on 32-bit
    b = ((si << i) & M32)         # 32-bit wrapping shl
    return s16(a | b)

def next(j):
    j &= M64
    s = s16(j & 0xFFFF)
    s2 = s16((j >> 16) & 0xFFFF)
    t = s16(s + s2)
    rotl_v = s16(rotl(t, 9) + s)          # (short)(rotl(...) + s) : int add then short
    s3 = s16(s2 ^ s)
    a = se16(rotl(s3, 10))                # short -> Long (sign extended)
    b = (se16(rotl_v) << 16) & M64        # Long shl 16
    hi = ((a | b) << 16) & M64            # Long shl 16
    inner = s16(rotl(s, 13) ^ s3)         # (short)(rotl ^ s3) : int xor then short
    d = i32(i32(se16(s3) << 5))           # s3 shl 5 as Int (32-bit)
    low = s16(inner ^ d)                  # xor ints, cast short
    low_se = se16(low)
    return (hi | low_se) & M64

def seed(j):
    j &= M64
    j2 = ((j ^ (j >> 33)) * 7109453100751455733) & M64
    return (((j2 ^ (j2 >> 28)) * (-3808689974395783757 & M64)) & M64) >> 32

def get_char_at(i, chunks, state):
    c = ord(chunks[i // MAX_CHUNK][i % MAX_CHUNK])
    return ((c << 32) ^ next(state)) & M64

def deobf(seed_val, chunks):
    if seed_val >= (1 << 63):
        seed_val -= (1 << 64)
    su = seed_val & M64
    st = next(seed(su & 0xFFFFFFFF))
    length_field = (st >> 32) & 0xFFFF
    next2 = next(st)
    idx = (su >> 32) ^ length_field ^ ((next2 >> 16) & 0xFFFF0000)
    idx &= M32
    state = get_char_at(idx, chunks, next2)
    n = (state >> 32) & 0xFFFF
    chars = []
    for k in range(n):
        state = get_char_at(idx + k + 1, chunks, state)
        chars.append(chr((state >> 32) & 0xFFFF))
    return ''.join(chars)

def load_chunks(path):
    src = open(path, encoding='utf-8').read()
    start = src.index('chunks')
    end = src.index('};', start)
    body = src[start:end]
    # split elements: strings separated by commas
    strs = re.findall(r'"((?:[^"\\]|\\u[0-9a-fA-F]{4}|\\.)*)"', body)
    out = []
    for s in strs:
        s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
        s = s.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n').replace('\\t', '\t')
        out.append(s)
    return out

if __name__ == '__main__':
    chunks = load_chunks(sys.argv[1])
    total = sum(len(c) for c in chunks)
    print('chunks:', len(chunks), 'total chars:', total, file=sys.stderr)
    for arg in sys.argv[2:]:
        v = int(arg.rstrip('L'), 10)
        try:
            print(arg, '->', repr(deobf(v, chunks)))
        except Exception as e:
            print(arg, '-> ERROR', e)
