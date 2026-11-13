"""Wolf Custom VPN config decryptor (AES-256-GCM, fixed keys from libgojni.so)."""
import base64, json, re, sys
from Crypto.Cipher import AES

KEY = b'qkKG+glMDxozePe5/Kcm+ZLeba+jJIrF'      # libgojni.so VA 0x363810
INJECTOR_KEY = b'Li96biGlJWFeNwKxWR6RrC3IGBu0CsXO'  # libgoinjector.so: Payload/SNI/CustomProxy


def decrypt(value: str, key: bytes = KEY) -> str:
    raw = base64.b64decode(value.replace('\r', '').replace('\n', ''))
    clear = AES.new(key, AES.MODE_GCM, nonce=raw[:12]).decrypt_and_verify(raw[12:-16], raw[-16:])
    return clear.decode('utf-8')


def _deepdec(o):
    if isinstance(o, dict):
        return {k: _deepdec(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_deepdec(v) for v in o]
    if isinstance(o, str) and len(o) >= 40 and re.fullmatch(r'[A-Za-z0-9+/]*={0,2}', o):
        for k in (KEY, INJECTOR_KEY):
            try:
                return decrypt(o, k)
            except Exception:
                pass
    return o


def main():
    text = open(sys.argv[1], encoding='utf-8').read().strip()
    doc = json.loads(decrypt(text))
    full = _deepdec(doc)
    out = sys.argv[2] if len(sys.argv) > 2 else 'config_decrypted.json'
    json.dump(full, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('servers:', len(full.get('Servers', [])), 'networks:', len(full.get('Networks', [])), '->', out)


if __name__ == '__main__':
    main()
