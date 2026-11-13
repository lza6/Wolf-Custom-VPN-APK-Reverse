# Wolf Custom VPN APK Reverse — v1.11.06.1

`core.vpn3jx.xtreme`（v2rayNG fork + sandok tunnel 家族，strongteam.co 后端）逆向知识库：
**配置信封全量解密 → 60 Servers / 1857 Networks 节点矩阵还原 → 字段级 AES-GCM 密文 2495 项 100% 破解**。
含 frida 主动解密工具链、可运行 patch 版 APK 构建方案、demo 看板、new-api 对接文档。

## 状态总表

| 项目 | 状态 |
|------|------|
| APK 架构定性 | v2rayNG fork + sandok 双栈（Xray libgojni 30MB + OpenVPN libovpncli 10MB + libuz Hysteria 24MB） |
| lsparanoid 字符串混淆 | ✅ 7638 条全还原（dump_strings.py） |
| assets/configfile.json 信封 | ✅ 2.73MB base64（AES-GCM，key 在 Go 侧运行时构造） |
| Go runtime on 模拟器 | ✅ 六处 patch 后稳定运行（见 REVERSE_REPORT §崩溃链） |
| MMKV 配置落盘 | ✅ MMJSONCONFIG1 8MB → MMCONFIGKEY1 2735008B 密文 |
| ConfigData 明文 | ✅ 2,006,822 字符（frida 主动调 `Libv2ray.do_`） |
| 字段级解密 | ✅ 2495/2495（100%），`do_` 即万能字段解密器 |
| 节点资产 | 60 Servers / 44 unique hosts / 5 UUID / trojan+sandoki 凭证 |
| 真协议拨测 | 中国出口 0 节点可用（终判）：Trojan 101 OK 但认证 0x03e8 待调；VLESS 404；vmess 被 CF WAF 挡（目标用户为印尼住宅网络）；Hysteria2 UDP 静默 |
| new-api 对接 | 文档就绪（docs/NEWAPI_INTEGRATION.md），等 VLESS path 确认后入池 |

## 快速开始

```bash
# 1) 反编译 + 还原 lsparanoid 混淆字符串
jadx -d jadx_out --no-res -j 8 Wolf-Custom-VPN-v1.11.06.1_modyolo.apk
python tools/dump_strings.py jadx_out/sources \
  "jadx_out/sources/org/lsposed/lsparanoid/Deobfuscator\$WolfCustomVPN\$app.java" \
  strings.json strings_loc.json

# 2) 构建 patch 版 APK（minSdk + 崩溃修复，详见 REVERSE_REPORT §3）
python tools/patch_apk.py Wolf-Custom-VPN-v1.11.06.1_modyolo.apk

# 3) 模拟器跑起来后 frida 主动解密（MMKV → 明文 ConfigData）
python tools/frida_spawn_hook.py

# 4) 字段级批量解密 + 重建节点清单
python tools/rebuild_config.py
```

## 文档

| 文件 | 给谁看 |
|------|--------|
| `docs/REVERSE_REPORT.md` | 研究审计：完整逆向过程、崩溃链修复、坑清单 |
| `docs/PROTOCOL.md` | 二次开发：配置模型/字段语义/加密层/最小实现 |
| `docs/NEWAPI_INTEGRATION.md` | **对接会话从这里开始**：new-api 代理池对接交接包 |

## 工具

| 文件 | 用途 |
|------|------|
| `tools/dump_strings.py` + `lsparanoid_deobf.py` | lsparanoid 混淆还原（通用） |
| `tools/pclntab_extract.py` | Go pclntab 函数名提取（通用） |
| `tools/decrypt_wolf.py` | 旧版 v2.8.1.2 静态 key 解密器（参考） |
| `tools/patch_apk.py` | minSdk+崩溃修复 APK 构建 |
| `tools/frida_spawn_hook.py` | spawn + hook do_ 抓明文配置 |
| `tools/frida_native_hook.py` | native 层 hook 变体 |
| `tools/rebuild_config.py` | 字段解密映射 → 节点清单重建 |
| `demo/demo_server.py` + `demo.html` | 分析看板 :12531 |

## samples（全部脱敏）

- `config_redacted.json` — 解密后 ConfigData 精简样例（IP→RFC5737，UUID/hex64 截断）
- `wolf_subscription_redacted.txt` — base64 订阅样例（UUID/名称已脱敏）
- `mmkv_layout.md` — MMKV 解析笔记

## 合规声明

逆向产物仅用于安全研究与协议学习。服务器凭证的获取≠使用权，生产使用由运营方自担；
本项目不绕过上游风控，不分发受版权保护的 APK 资产（PNG/内置配置请用自带 APK 现场提取）。

## 路线图

- [x] 静态分析 + lsparanoid 还原
- [x] 模拟器崩溃链修复（6 处 native patch）
- [x] MMKV → ConfigData 全量解密
- [x] 字段级 2495 项解密
- [ ] 真机抓包确认 VLESS path（`/sandok` 404 待查）
- [ ] Trojan-WS 认证细节（101 OK 但数据帧 0x03e8 待调）
- [ ] Hysteria2 (UDP 443) mihomo 拨测
- [ ] new-api 渠道入池（等上两项）
