
# Wolf Custom VPN v1.11.06.1 — 逆向定案报告 (2026-11-13)

## 突破路径 (动态取证全流程)

1. **APK 安装层**: minSdk 32→30 二进制 patch (AXML typed value @0x5a1c) + zipalign -p 4 +
   apksigner v1+v2 重签 (wolfkey.jks) → API30/32 x86_64 模拟器安装成功
2. **崩溃链修复** (ndk_translation 下 Go runtime 逐个击破):
   - `MRS x0, MIDR_EL1` (0xd5380000) 等 6 个 ID 寄存器读取 stub → movz/movk 伪 MIDR (0x411FD400 Cortex-A78)
   - `MPIDR_EL1` 读 (0xd53848ee) → movz 归零
   - `sha256su0/h/h2` ARM crypto 指令不支持 → fips sha256 dispatch (0x101c3b8) 改 bl blockGeneric (0x101c0d0)
   - 关键教训: tombstone 的 r13 寄存器 = guest vaddr (base 相对), fault addr 需要按当次运行的 base 换算
3. **配置解密**: App 稳定运行后 MMKV `MMJSONCONFIG1` 写入 8MB → 从 MMKV 拿 `MMCONFIGKEY1`
   (2735008B base64) → frida 主动调 `Libv2ray.do_(cipher)` → **2,006,822 字符明文 ConfigData**
4. **字段级解密**: ConfigData 里所有 Server/Network 字段仍是 AES-GCM 密文 → frida rpc 批量
   调 `do_` 解密 2,495 个唯一值, 100% 成功 (do_ = 万能字段解密器, key 在 Go 侧)

## 解密产物

- 60 Servers / 1857 Networks / Version 1.17
- DefOVPN: sandoki:sandoki | Hysteria: sandoki:sandoki | TrojanPass: trojanpassword
- 5 个唯一 VLESS UUID (含 12345678-1234-1234-1234567B9o)
- 44 unique hosts: *.run.app (GCP Cloud Run) + *.strongteam.co + *.phfiles.com + CloudFront IP 池
- ServerType: GCP 9 / Normal 19 / XHTTP 17 / DNS V2ray 5 / CF Worker 3 / Cloudfront 2 / Alibaba 4 / Fastly 1
- TunnelType: SSL Direct 459 / Http-Ws Proxy 430 / V2ray 319 / SlowDNS 315 / SSL+Payload+WS 270 / UDP Hysteria 54
- 路径模板: VLESS ws `/sandok` (Cloud Run 404!), Trojan ws `/trojanws` (101 OK!)

## 实测结论

- TCP 22/36 hosts 存活 (直连); strongteam.co 直连被 RST, 经代理出口可达
- VLESS `/sandok` wss 404 — Cloud Run 后端 path 已换或需要额外参数 (待真机抓包确认)
- Trojan `/trojanws` 101 握手成功但数据帧只有 0x03e8 (1000) — 认证细节待调 (可能密码非 trojanpassword 或协议变体)
- Hysteria2 (54 networks, UDP 443) 未测 — mihomo 拨测待做
- new-api 对接: 建议等真机抓包确认 VLESS path 后再入池; Trojan/Hysteria 有可用凭证形态

## 交付文件

- output/wolf_plain.json (加密 ConfigData) / config_decrypted_full.json (全解密)
- output/field_decrypt_map.json (2495 字段映射) / wolf_subscription.txt (base64 订阅)
- output/MMJSONCONFIG1 (MMKV dump) / MMCONFIGKEY1_cipher.txt
- apk/wolf_final_signed.apk (可运行 patch 版) / wolfkey.jks
- frida/native_hook.py + spawn_hook.py
