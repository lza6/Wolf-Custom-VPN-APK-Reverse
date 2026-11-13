"""Wolf Custom VPN v1.11.06.1 — APK patch builder.

Applies all known fixes to make the mod APK installable and runnable on x86_64
emulators (Android 11/12 google_apis images with ndk_translation):

1. minSdk 32 -> 30 (AXML typed value patch)
2. resources.arsc stored uncompressed (R+ requirement)
3. libgojni.so fixes:
   - ID-register MRS stubs (MIDR/PFR0/DFR0/ISAR) -> synthetic Cortex-A78 values
   - MPIDR read -> 0
   - fips sha256 dispatch -> blockGeneric (ARM crypto SIMD unsupported by ndk_translation)
4. zipalign + apksigner v1+v2 signing

Requirements: JDK 17+, Android build-tools (zipalign, apksigner.jar), Python cryptography.
Usage:
  python patch_apk.py <input.apk> [output.apk]
  env: ANDROID_BT  build-tools dir (default: C:/Android/sdk/build-tools/android-14)
  env: KS          keystore (default: ./wolfkey.jks, auto-generated)
"""
import base64
import os
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

BT = os.environ.get('ANDROID_BT', r'C:/Android/sdk/build-tools/android-14')
KS = os.environ.get('KS', 'wolfkey.jks')
KS_PASS = os.environ.get('KS_PASS', 'wolfpass123')


def patch_manifest(m: bytearray) -> bytearray:
    """minSdkVersion typed value 32 -> 30. Value u32 sits at 0x5a1c in this APK."""
    off = 0x5A1C
    cur = struct.unpack_from('<I', m, off)[0]
    if cur == 32:
        struct.pack_into('<I', m, off, 30)
    elif cur == 30:
        pass  # already patched
    else:
        raise SystemExit(f'unexpected minSdk value {cur} at {off:#x} — manifest layout differs')
    return m


def patch_libgojni(so: bytearray) -> bytearray:
    def w_movz(rt, imm16):
        return 0xD2800000 | ((imm16 & 0xFFFF) << 5) | rt

    def w_movk16(rt, imm16):
        return 0x72A00000 | ((imm16 & 0xFFFF) << 5) | (1 << 21) | rt

    n_stub = 0
    # -- ID-register MRS stubs: [MRS x?, CRn=0 CRm=0..7] followed by STR x0,[sp,#8] and RET,
    #    or paired [MRS,MRS,STR,STR,RET]. Layout verified at 0x526ac0 / 0xd119a0-c4.
    for site, shape in ((0x526AC0, 'A'), (0xD119A0, 'A'), (0xD119B0, 'A')):
        # shape A: [MRS x0 MIDR, STR x0, RET]
        struct.pack_into('<I', so, site, w_movz(0, 0xD400))
        struct.pack_into('<I', so, site + 4, w_movk16(0, 0x411F))  # x0 = 0x411FD400
        n_stub += 1
    # 0xd119b0: PFR0 -> 0x00001111
    struct.pack_into('<I', so, 0xD119B0, w_movz(0, 0x1111))
    struct.pack_into('<I', so, 0xD119B0 + 4, w_movk16(0, 0x0000))
    # 0xd119c0/c4 pair: [MRS x0, MRS x1, STR x0, STR x1, RET] -> x0=x1=0x00010000
    struct.pack_into('<I', so, 0xD119C0, w_movz(0, 0x0000))
    struct.pack_into('<I', so, 0xD119C4, w_movk16(0, 0x0001))
    struct.pack_into('<I', so, 0xD119C8, w_movz(1, 0x0000))
    struct.pack_into('<I', so, 0xD119CC, w_movk16(1, 0x0001))
    n_stub += 2
    # -- MPIDR_EL1 read at 0x115f230 -> x14 = 0 (low half only; next word is data)
    struct.pack_into('<I', so, 0x115F230, w_movz(14, 0x0000))
    # -- fips sha256 dispatch: bl 0x101c550 (blockARM64 SIMD) -> bl 0x101c0d0 (generic)
    delta = 0x101C0D0 - 0x101C3B8
    imm26 = (delta >> 2) & 0x3FFFFFF
    struct.pack_into('<I', so, 0x101C3B8, 0x94000000 | imm26)
    print(f'[patch] libgojni: {n_stub} ID stubs + MPIDR + sha256->generic')
    return so


def rebuild(src: Path, dst: Path):
    zin = zipfile.ZipFile(src)
    with zipfile.ZipFile(dst, 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'AndroidManifest.xml':
                data = bytes(patch_manifest(bytearray(zin.read(item.filename))))
            elif item.filename == 'lib/arm64-v8a/libgojni.so':
                data = bytes(patch_libgojni(bytearray(zin.read(item.filename))))
            else:
                data = zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            # R+ requires uncompressed, 4-byte-aligned resources.arsc
            zi.compress_type = zipfile.ZIP_STORED if item.filename == 'resources.arsc' else item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    print(f'[rebuild] {dst} ({dst.stat().st_size // 1024 // 1024} MB)')


def ensure_keystore():
    if Path(KS).exists():
        return
    subprocess.run([
        'keytool', '-genkeypair', '-v', '-keystore', KS, '-alias', 'wolf',
        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000',
        '-storepass', KS_PASS, '-keypass', KS_PASS,
        '-dname', 'CN=Wolf Research, OU=RE, O=Local, L=Local, ST=Local, C=CN',
    ], check=True, capture_output=True)
    print(f'[key] generated {KS}')


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: python patch_apk.py <input.apk> [output.apk]')
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else src.stem + '_patched.apk')
    rebuild(src, dst)
    aligned = dst.with_suffix('.aligned.apk')
    subprocess.run([f'{BT}/zipalign.exe', '-f', '-p', '4', str(dst), str(aligned)], check=True)
    ensure_keystore()
    signed = dst.with_name(dst.stem + '_signed.apk')
    subprocess.run([
        'java', '-jar', f'{BT}/lib/apksigner.jar', 'sign',
        '--ks', KS, '--ks-key-alias', 'wolf',
        '--ks-pass', f'pass:{KS_PASS}', '--key-pass', f'pass:{KS_PASS}',
        '--out', str(signed), str(aligned),
    ], check=True)
    aligned.unlink(missing_ok=True)
    print(f'[sign] {signed} ready for install')


if __name__ == '__main__':
    main()
