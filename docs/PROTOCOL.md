# Wolf Custom VPN 协议手册（PROTOCOL.md）

> 给二次开发/对接方。本文档 = 「不读逆向过程也能实现」级。
> 所有常量均可从 APK 现场复现；真实凭证已脱敏。

## 1. 架构总览

```
Wolf Custom VPN v1.11.06.1 (core.vpn3jx.xtreme)
├── v2rayNG fork 壳 (com.v2ray.ang.*)          — UI/订阅/路由
├── sandok tunnel 家族                          — OpenVPN/SSH/DNSTT/SlowDNS
│   └── com.sandok.tunnel.* + com.vpn.sandok.ultrasshservice.*
├── libgojni.so 30.7MB (Go 1.24, gomobile)     — Xray-core + 解密
│   └── github.com/2dust/AndroidLibXrayLite (fork)
├── libovpncli.so 10MB                         — OpenVPN3
└── libuz.so 24.7MB (C++)                      — Hysteria/apernet quic-go
```

## 2. 配置下发模型

```
assets/configfile.json (2.73MB base64 AES-GCM 信封)
    │  首启: do_() 解密
    ▼
ConfigData {Version, DefOVPNUser/Pass, HysteriaUser/OBFS,
            DefaultOVPNCert, isTimerOn, timetoadd,
            Servers[60], Networks[1857]}
    │
    ├── 远端刷新: Libv2ray.cu(currentVersion) → gfc() → 新密文
    │             存 MMKV: MMCONFIGKEY1 (密文) + CurrentConfigVersion
    ▼
匹配规则: Networks.V2rayServerNeed == Servers.ServerType
         Networks 的 [host]/[id]/[path]/[server] 占位符 ← Servers 字段替换
```

### MMKV 存储布局（`MMJSONCONFIG1` store）

| key | 内容 |
|-----|------|
| `OOOa` | protobuf-wrapped app name (`0f` + "Wolf Custom VPN") |
| `BoostedServer` | `02[]`（空数组 protobuf） |
| `Proto` | `\nDirect TCP` |
| `CurrentConfigVersion` | `\x041.17` |
| `MMCONFIGKEY1` | `[total-len varint][2735008B base64 密文]` |

MMKV entry 格式：`[klen varint][key][vlen varint][value]`；
`MMCONFIGKEY1` 的 value 前还有 4 字节长度 varint（双写）。

## 3. 加密层（3 层）

### L1: ConfigData 信封
- `assets/configfile.json` = base64(salt16 ‖ nonce12 ‖ AES-256-GCM(ct‖tag))
- key 在 Go 侧运行时构造（闭包捕获，静态不可见），与 APK 签名相关
- **解密路径**：`Libv2ray.do_(str)` JNI → AndroidLibXrayLite.DO → AES-GCM Open

### L2: 字段级密文（Servers/Networks 的所有敏感字段）
- 同样 base64 + AES-256-GCM
- **同一个 `do_` 即可解**：`Libv2ray.do_(fieldCipher)` → 明文
- 2495 个字段实测 100% 解密成功

### L3: lsparanoid 字符串混淆（Java 层）
- `Deobfuscator$WolfCustomVPN$app.getString(<int seed>)`
- 还原器：`tools/dump_strings.py`（7638 条，通用工具）

## 4. JNI 接口表（libv2ray.Libv2ray）

| 方法 | 签名 | 用途 |
|------|------|------|
| `do_` | `static native String do_(String) throws Exception` | **主解密器**：ConfigData 信封 + 字段级密文 |
| `eo` | `static native String eo(String)` | 二次加密路径（对 do_ 输出再加密） |
| `encrypt` | `static native String encrypt(String)` | AiH 完整性上报用 |
| `gv` | `static native String gv(String)` | parseConfig 后按 key 取值（Name/TunnelType） |
| `gfc` | `static native String gfc()` | 取远端配置（写 MMCONFIGKEY1） |
| `cu` | `static native boolean cu(String)` | 版本检查（触发配置刷新） |
| `ao/sp/po/so` | `static native void x(String)` | app 标签/源路径/包名/签名上报（SoCheck） |

## 5. ConfigData 字段语义（解密后）

### ServerList（60 项）

| 字段 | 语义 | 实测值示例 |
|------|------|-----------|
| `ServerIPHost` | 唯一出口（域名/IP/分号分隔多值） | `dexray-<12digits>.europe-west1.run.app` |
| `ServerType` | profile 类别（匹配 Networks） | GCP / Normal Server / XHTTP / DNS V2ray / CF Worker / Cloudfront / Alibaba / Fastly |
| `V2rayProtocol` | VLESS / Trojan | |
| `V2rayUUID` | VLESS id / Trojan user | `12345678-1234-1234-1234567B9o` |
| `V2rayPath` | ws/xhttp 路径 | `/sandok`、`/xhttp`、`/trojanws` |
| `OpenVPNTCPPort/UdpPort` | 110 | |
| `SSH_Port / SSLPort` | 22 / 443 | |
| `SlowDNSHost/Key` | DNSTT 服务器与 hex key | `nsde.strongteam.co` |
| `UDP_obfs / UDP_user` | hysteria obfs/user（Go 侧再解） | `sandok` |
| `TrojanPass` | Trojan 密码 | `trojanpassword` |
| `Flag / Name` | 国家旗标 / 显示名（emoji 装饰） | `de`, `⚡GCP GEMANY⚡💥💰` |

### NetworkList（1857 项）— 隧道矩阵

| 字段 | 语义 |
|------|------|
| `V2rayServerNeed` | 匹配 ServerList.ServerType |
| `TunnelType` | Direct TCP / SSL Direct / Http/Ws Proxy / V2ray / Slow DNS / SSL + Payload + WS / UDP Hysteria |
| `V2rayConfig` | **VLESS/Trojan URI 模板**（占位符 `[id]@[server]:[port]?path=[path]...`） |
| `V2rayAddress` | 连接地址（`[host]`=ServerIPHost 或固定 CDN 域名如 `mistarwolfnet.duckdns.org`） |
| `V2raySNI` / `V2rayHost` | SNI/Host（`[host]` 占位或 `Google.com` 域前置） |
| `V2rayNetwork` | Websocket / Xhttp / Trojan / Custom-1 |
| `Payload / ProxyPort` | Http/Ws Proxy 注入模板（`PROPPATCH VPS Wolf HTTP/1.1[crlf]...`） |

**关键 URI 模板（GCP 型）**：
```
vless://[id]@Google.com:443?path=[path]&security=tls&insecure=1&encryption=none&host=[server]&type=ws&sni=Google.com#NoMoneyNoHoney
trojan://trojanpassword@[server]:443?security=tls&host=[server]&fp=chrome&type=ws&sni=[server]#Nomoney
```
→ **地址/SNI = Google.com（域前置伪装），Host 头 = 真实 Cloud Run 域名**。

## 6. 端点与基础设施

| 域名 | 用途 | 状态 |
|------|------|------|
| `https://strongteam.co/api/wolfcustomv2/` | 配置分发 API（libgojni 内嵌常量） | 根路径 200 "MM Tunnel" 状态页 |
| `https://strongteam.co/nets/` | 服务器图标缓存 | 目录 403 |
| `*xray-*.run.app` / `*ovpn-*.run.app` | GCP Cloud Run 节点 | TCP 443 活 |
| `*.strongteam.co` (de/fi/sg/in/tw) | 直连节点域名 | 国内直连被 RST，需代理出口 |
| `*.phfiles.com` | SSH/SSL 节点 | TCP 443 活 |
| Firebase `corpovpn` (project 487376620554) | 分析/FCM（无 RTDB 公开） | RTDB 404 |

## 7. 最小实现骨架（Python，30 行）

```python
# 前提: 已通过 frida 或真机抓包拿到 do_ 解密能力（key 在 Go 侧运行时构造）
# 下述为拿到 ConfigData 明文后的节点重建
import json, urllib.parse

cfg = json.load(open('config_decrypted_full.json', encoding='utf-8'))
links = []
for s in cfg['Servers']:
    host, uuid = s['ServerIPHost'], s['V2rayUUID']
    proto = s['V2rayProtocol'].lower()
    path = s.get('V2rayPath', '/')
    name = s.get('Name', '')
    if proto == 'vless':
        q = urllib.parse.urlencode({'type': 'ws', 'path': path, 'host': host,
                                    'security': 'tls', 'sni': host, 'fp': 'chrome'})
        links.append(f"vless://{uuid}@{host}:443?{q}#{urllib.parse.quote(name)}")
    elif proto == 'trojan':
        q = urllib.parse.urlencode({'type': 'ws', 'path': '/trojanws', 'host': host,
                                    'security': 'tls', 'sni': host})
        links.append(f"trojan://{s.get('TrojanPass')}@{host}:443?{q}#{urllib.parse.quote(name)}")
open('sub.txt', 'w').write(base64.b64encode('\n'.join(links).encode()).decode())
```

## 8. 必避坑清单

1. **frida Java 返回 String 自动转 JS string** — 用 `.length` 不是 `.length()`；超过 ~2.7MB 的参数会挂 bridge，2MB 实测 OK
2. **MMKV entry 双 varint** — `MMCONFIGKEY1` 的 value 前有两个长度前缀，漏跳一个全错
3. **ndk_translation 不支持 ARM crypto 指令**（sha256su0/h/h2）— Go runtime 必须重定向 blockGeneric
4. **MRS ID 寄存器 stub 地址是硬编码偏移** — 换 APK 版本需重新定位（tombstone r13 = guest vaddr）
5. **xray 26.x 移除 allowInsecure** — 配置里直接删字段（run.app 有合法证书）
6. **strongteam.co 国内直连 RST** — 一切联通性测试走代理出口
7. **jadx 需 `--no-res`**；类名 deobf 后 defpackage 名会变，找 `com.v2ray.ang.*` 原始名要重跑不带 deobf
8. **APK 重签后 v1/v2 都要签**（apksigner 默认）；`resources.arsc` 必须 STORED（R+ 安装校验）
9. **V2rayConfig URI 模板是权威 path/SNI 来源** — ServerList.V2rayPath 只是默认值，Networks 组合可覆盖
