# MMKV 文件解析笔记（MMJSONCONFIG1）

## 文件结构
```
[0:4]   written bytes (u32 LE) — 有效数据长度
[4:8]   CRC32 校验
[8:]    entries 连续排布
```

## entry 格式
```
[klen varint][key utf8][vlen varint][value bytes]
```
注意：部分 key（如 `MMCONFIGKEY1`）的 value 前有**两个**长度 varint
（外层 = MMKV 写入时计算的总长，内层 = value 实际长度），解析时先跳第一个。

## 本 APK 的 key 集（MMJSONCONFIG1 store）
| key | value 形态 |
|-----|-----------|
| `OOOa` | `\x0f` + "Wolf Custom VPN"（protobuf length-prefixed string） |
| `BoostedServer` | `\x02[]`（JSON 数组，protobuf 包裹） |
| `Proto` | `\n` + "Direct TCP" |
| `CurrentConfigVersion` | `\x04` + "1.17" |
| `MMCONFIGKEY1` | base64 密文（2,735,008B，do_ 可解） |

## 实用解析片段
```python
def varint(data, p):
    r = s = 0
    while True:
        b = data[p]; p += 1
        r |= (b & 0x7f) << s
        if not (b & 0x80): return r, p
        s += 7
```
