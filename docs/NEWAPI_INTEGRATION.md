# Wolf Custom VPN → new-api 代理池对接文档（NEWAPI_INTEGRATION.md）

> **对接会话只需读本文档**。0 上下文要求。
> 结论先行：**Trojan-WS 与 Hysteria2 两类凭证形态完整可对接**；VLESS-WS 的 path 服务端已变更（404），需真机抓一次包确认后再入池。

---

## §0 一句话结论

| 节点类 | 凭证 | 协议栈 | 当前可用 | 入池动作 |
|--------|------|--------|----------|----------|
| Trojan-WS-TLS（strongteam.co ×5） | `trojanpassword` @ host:443 `/trojanws` | trojan over ws over tls | **握手 101 OK**，认证细节待调 | 抓包调通后即可入池 |
| Hysteria2（UDP 443，54 条 network） | `sandoki:sandoki` + obfs `sandok` | hysteria2 | 未拨测 | mihomo 拨测后入池 |
| VLESS-WS-TLS（run.app ×4 + strongteam ×5） | 5 个 UUID，path `/sandok` | vless over ws over tls | wss 404（path 服务端变更） | **先抓真机包拿正确 path** |
| OpenVPN（sandoki:sandoki @110） | TCP/UDP 110 | ovpn | 未测 | 参考 StrongTeam repo gen_ovpn_pool.py |

---

## §1 new-api 侧机制（源码已核实，零业务代码改动）

`relay/channel/tryingopen/proxy_pool.go` → `LoadProxies()`：

| 项 | 规则 |
|---|---|
| 环境变量 | `TRYINGOPEN_PROXY_FILE`，**逗号分隔多文件** |
| 每行 | `socks5://host:port`，`#` 注释跳过，整行去重 |
| 入池属性 | `source="residential"`、`healthScore=1.0`（池内最高权重档） |
| 分池观测 | `origin = 文件名` → 面板独立卡片 |
| 风控 | 429 冷却阶梯 `0/30/90/300/900s`；连续 5 次失败 → 全池熔断 10 分钟 |
| 探测 | **`TraceProbes()` 只探 `source=="free"` 的池**（proxy_pool.go:1179）。`residential` 源不探测，死节点会静默躺池 → **必须自带健康检查** |
| 热更新 | 清单变更**不热加载**（LoadProxies 只在启动/配置变更调用）→ 每天固定时段重启容器 |

**容器内 127.0.0.1 是容器自己的 loopback** — 转换层跑宿主机时三选一：
1. `extra_hosts: host.docker.internal:host-gateway` + 端口绑 `203.0.113.2`
2. `network_mode: host`
3. 转换层进同一 compose 网络

---

## §2 标准链路

```
Wolf 解密节点 (trojan/hysteria2/vless)
   │  xray/mihomo 每节点一份配置
   ▼
本地 socks5 :33xxx（协议转换层，跑宿主机或 WSL）
   │
   ▼
TRYINGOPEN_PROXY_FILE=socks5://127.0.0.1:33xxx,...
   │
   ▼
new-api 渠道出站
```

---

## §3 Wolf 专属参数（本仓库 samples/config_redacted.json 全量）

### Trojan-WS-TLS（优先对接，唯一实测 101 握手成功的类）
```
host:   de/fi/sg/in.strongteam.co   (国内直连 RST，转换层需带出口)
port:   443
path:   /trojanws
password: trojanpassword
```
xray outbound 骨架：
```json
{"protocol":"trojan",
 "settings":{"servers":[{"address":"de.strongteam.co","port":443,"password":"trojanpassword"}]},
 "streamSettings":{"network":"ws","security":"tls",
   "tlsSettings":{"serverName":"de.strongteam.co"},
   "wsSettings":{"path":"/trojanws","headers":{"Host":"de.strongteam.co"}}}}
```

### VLESS-WS-TLS（path 待确认）
```
host:   dexray-788537295897.europe-west1.run.app 等 4 个 run.app + strongteam ×5
uuid:   12345678-1234-1234-1234567B9o（另有 4 个 UUID 见 samples）
path:   /sandok ← 服务端 404！真机抓包确认实际 path
SNI:    两种玩法：①直连真实域名 ②Google.com 域前置（模板原文），Host 头=真实域名
```
**抓包要点**：模拟器已跑通（`tools/patch_apk.py` 构建版 + frida），真机/模拟器上点连接 →
mitmproxy 抓 `CONNECT dexray-...run.app:443` 后的 ws upgrade 请求 → 拿真实 path 与 header。

### Hysteria2
```
server: 203.0.113.14;203.0.113.59;203.0.113.195;203.0.113.134;203.0.113.146;
        203.0.113.85;203.0.113.193;203.0.113.214;203.0.113.129  (UDP CUSTOM 1/2/3)
auth:   sandoki:sandoki   obfs: sandok   port: 443/udp
```
mihomo 拨测骨架：
```yaml
proxies:
  - name: wolf-hy1
    type: hysteria2
    server: 203.0.113.14
    port: 443
    password: sandoki
    obfs: sandok
```
（注意 `V2rayNetwork: Custom-1` 的条目走自定义模板，先测 Websocket 型）

---

## §4 三层验收（缺一 = 假对接）

1. **隧道层**：`curl --socks5-hostname 127.0.0.1:33xxx https://www.cloudflare.com/cdn-cgi/trace` → 出口 IP == 节点 IP
2. **池层**：`GET /api/twoapi_panel/proxy_pool` → wolf 卡片有条目
3. **业务层**：经 new-api 发真请求 → 上游侧看到的来源 IP == 节点出口

---

## §5 接入前置条件 checklist

- [ ] Trojan：真机/模拟器抓包确认密码（0x03e8 错误码 = 密码或协议变体不对）
- [ ] VLESS：抓包确认 path（/sandok 404）
- [ ] Hysteria2：mihomo 拨测 9 个 UDP IP（hysteria2 auth + obfs sandok）
- [ ] 转换层端口规划：33200-33499 段（**避开** 10808/10809/7890/31000-31007）
- [ ] `TRYINGOPEN_PROXY_FILE` 加 wolf 清单文件
- [ ] 健康检查器 `health_loop.py`（参考 SuperVPN repo tools/）每天跑一轮重写清单
- [ ] 每天固定时段重启 new-api 容器加载新清单

---

## §6 健康检查器要求（new-api 不验 residential 源）

1. 真实协议探测（SOCKS5 握手 + 目标站可达），不是 TCP 连通
2. 出口 IP == 节点 IP，不等则 `exit_mismatch` 摘除
3. 双阈值：连续 2 轮失败才摘；**从未通过的新节点首轮就不入池**
4. `os.replace` 原子重写清单

---

## §7 红线

- 不要改 new-api 的 `TraceProbes` 逻辑（业务代码）
- 不要把 strongteam 凭证当自有资产商用 — 凭证获取≠使用权
- 不要在未确认 path 前把 VLESS 节点写进池（会拖垮健康分）
- 不要用 127.0.0.1 直接写 `TRYINGOPEN_PROXY_FILE` 若 new-api 在容器里（§1 警告）

---

## §8 交接指令模板（粘给对接会话）

```
目标: 把 Wolf Custom VPN 逆向出的 Trojan-WS 节点接入 new-api 代理池
仓库: https://github.com/lza6/Wolf-Custom-VPN-APK-Reverse （读 docs/NEWAPI_INTEGRATION.md + samples/config_redacted.json）
前置: §5 checklist 全打勾才开始
约束: 只改 TRYINGOPEN_PROXY_FILE 环境变量；转换层端口 33200-33499；
      不要动 new-api 业务代码；三层验收（§4）截图留证
健康检查: 用 SuperVPN_Pro-APP- 仓库 tools/health_loop.py 改造，清单必须由它生成
```

---

## §9 复现上游（节点全挂时）

1. `tools/patch_apk.py` 重打 APK → 模拟器/真机安装
2. App 首启自动拉 `strongteam.co/api/wolfcustomv2/` 新配置 → frida `spawn_hook.py` 抓 do_ 输出
3. `tools/rebuild_config.py` 重建字段 → 新 UUID/path 自动带上
4. 对比 `samples/config_redacted.json` diff 出变更节点
