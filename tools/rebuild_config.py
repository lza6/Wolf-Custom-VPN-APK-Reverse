"""Rebuild Wolf ConfigData with decrypted fields → final node inventory.

Input: output/wolf_plain.json (encrypted ConfigData) + output/field_decrypt_map.json
Output: output/config_decrypted_full.json + output/servers_flat.json
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = r'C:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\逆向产物\Wolf-Custom-VPN\output'
d = json.loads(open(f'{BASE}/wolf_plain.json', encoding='utf-8').read())
mapping = json.load(open(f'{BASE}/field_decrypt_map.json', encoding='utf-8'))

B64RE = re.compile(r'[A-Za-z0-9+/=]{40,}')


def walk_replace(obj, path=''):
    """Replace ciphertext strings with decrypted values in-place."""
    if isinstance(obj, dict):
        return {k: walk_replace(v, f'{path}.{k}') for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_replace(v, f'{path}[{i}]') for i, v in enumerate(obj)]
    if isinstance(obj, str) and len(obj) >= 40 and B64RE.fullmatch(obj):
        return mapping.get(obj, obj)
    return obj


full = walk_replace(d)
json.dump(full, open(f'{BASE}/config_decrypted_full.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# flatten servers into node tuples
servers = full['Servers']
networks = full['Networks']

print(f'Servers: {len(servers)}  Networks: {len(networks)}')

# count unique hosts
hosts = {}
for s in servers:
    iph = s.get('ServerIPHost') or ''
    for h in re.split(r'[;,]', iph):
        h = h.strip()
        if h and not h.startswith('<'):
            hosts.setdefault(h, s.get('Name', '?'))

print(f'unique ServerIPHost entries: {len(hosts)}')
for h in list(hosts)[:20]:
    print(' ', h)
