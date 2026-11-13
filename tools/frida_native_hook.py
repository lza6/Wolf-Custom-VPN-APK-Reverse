"""Native Interceptor hook on Java_libv2ray_Libv2ray_do_1 — capture decrypted config.

Usage: python -I frida/native_hook.py
"""
import frida
import time
import pathlib
import subprocess

OUT = pathlib.Path(r'C:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\逆向产物\Wolf-Custom-VPN\output')
ADB = r'C:\Android\sdk\platform-tools\adb.exe'
PKG = 'core.vpn3jx.xtreme'

SCRIPT = r"""
function armHook() {
    var mod = Process.findModuleByName('libgojni.so');
    if (!mod) return false;
    console.log('libgojni base: ' + mod.base);
    var doAddr = mod.base.add(0x106b6a8);  // Java_libv2ray_Libv2ray_do_1
    Interceptor.attach(doAddr, {
        onLeave: function (retval) {
            if (retval.isNull()) { console.log('[do_] null'); return; }
            try {
                var env = Java.vm.getEnv();
                var str = env.getStringUtfChars(retval, null).readUtf8String();
                console.log('[do_] out len=' + str.length);
                if (str.length > 1000) {
                    var f = new File('/data/local/tmp/wolf_do_out.txt', 'wb');
                    f.write(str);
                    f.close();
                    console.log('[+] saved');
                }
            } catch (e) { console.log('[err] ' + e); }
        }
    });
    console.log('[*] native hook armed');
    return true;
}

if (!armHook()) {
    console.log('[*] lib not loaded; polling');
    var t = setInterval(armHook, 500);
}
"""

def main():
    dev = frida.get_usb_device(timeout=10)
    pid = dev.spawn([PKG])
    session = dev.attach(pid)
    script = session.create_script(SCRIPT)
    script.on('message', lambda m, d: print('[js]', m.get('payload') or str(m.get('description', ''))[:200]))
    script.load()
    dev.resume(pid)
    print('[*] spawned, listening 200s')
    time.sleep(200)
    r = subprocess.run([ADB, 'pull', '/data/local/tmp/wolf_do_out.txt', str(OUT / 'wolf_do_out.txt')], capture_output=True, text=True)
    print('pull:', (r.stdout or r.stderr)[:150])

if __name__ == '__main__':
    main()
