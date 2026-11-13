"""Wolf Custom VPN — local demo server.

Serves:
  /               demo UI (analysis dashboard)
  /api/analysis   static analysis summary (from recon artifacts)
  /api/configdata ConfigData template for .wolf import (plaintext JSON)
  /api/configfile raw bundled encrypted asset (for reference)
  /download/wolf_import.json  ready-to-import ConfigData file

Port: 127.0.0.1:12531 (isolated from system proxies).
"""
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'

ANALYSIS = {
    'apk': 'Wolf-Custom-VPN v1.11.06.1 (modyolo mod)',
    'package': 'core.vpn3jx.xtreme',
    'family': 'v2rayNG fork + sandok tunnel (strongteam.co family)',
    'engines': {
        'xray': 'libgojni.so 30.7MB (2dust AndroidLibXrayLite + xtls/xray-core)',
        'hy_engine': 'libuz.so 24.7MB (apernet/quic-go/hysteria)',
        'openvpn': 'libovpncli.so 10MB + com.sandok.tunnel.service.OpenVPNService',
        'slowdns': 'com.vpn.sandok.ultrasshservice.tunnel.DNSTunnelThread',
    },
    'config_model': {
        'bundled': 'assets/configfile.json (2.4MB AES envelope, key = runtime-derived)',
        'remote': 'Libv2ray.cu/gfc -> MMKV MMCONFIGKEY1 + CurrentConfigVersion',
        'import': 'ConfigFileParser accepts plaintext ConfigData JSON (.wolf file)',
        'matrix': 'Networks.V2rayServerNeed == Servers.ServerType',
    },
    'tunnel_types': {
        '0': 'OVPN_DIRECT_TCP', '1': 'DIRECT_WITH_PAYLOAD', '2': 'HTTP_PROXY',
        '3': 'SSL_DIRECT', '4': 'SSL_DIRECT_WITH_PAYLOAD', '5': 'SSL_HTTP_PROXY',
        '6': 'MODE_UDP', '7': 'MODE_V2RAY', '8': 'OVPN_DIRECT_UDP',
    },
    'decrypt_status': 'bundled envelope NOT cracked statically (see docs/RECON_ROUND1.md); dynamic path = emulator + frida',
    'endpoints_probed': {
        'https://strongteam.co/nets/': '403 (icon CDN only)',
        'https://strongteam.co/api/wolfcustom/newv1.txt': '404 (dead, StagVPN-era path)',
        'https://server.stagvpn.com/api/v1/app-data-new': 'connection reset',
    },
}


def configdata():
    p = OUT / 'configdata_ss.json'
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    p2 = OUT / 'configdata_template.json'
    if p2.exists():
        return json.loads(p2.read_text(encoding='utf-8'))
    return {}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            body = (ROOT / 'demo' / 'demo.html').read_bytes()
            self._send(200, body, 'text/html; charset=utf-8')
        elif path == '/api/analysis':
            self._send(200, json.dumps(ANALYSIS, ensure_ascii=False).encode())
        elif path == '/api/configdata':
            self._send(200, json.dumps(configdata(), ensure_ascii=False).encode())
        elif path == '/api/configfile':
            raw = (ROOT / 'recon' / 'configfile.json').read_bytes()
            self._send(200, raw, 'text/plain; charset=utf-8')
        elif path == '/download/wolf_import.json':
            body = json.dumps(configdata(), ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Disposition', 'attachment; filename="wolf_import.json"')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send(404, b'{"error":"not found"}')

    def log_message(self, fmt, *args):
        print('[demo]', fmt % args)


def main():
    port = 12531
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Wolf demo server on http://127.0.0.1:{port}')
    srv.serve_forever()


if __name__ == '__main__':
    main()
