"""Spawn Wolf app with frida, hook do_/encrypt/gv/gfc, dump all crypto I/O to files."""
import frida, sys, time, pathlib

PKG = 'core.vpn3jx.xtreme'
HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / 'output'
OUT.mkdir(exist_ok=True)

SCRIPT = r"""
Java.perform(function () {
    var Libv2ray = Java.use('libv2ray.Libv2ray');

    function save(tag, s) {
        try {
            if (!s) return;
            var len = s.length();
            console.log('[*] ' + tag + ' len=' + len);
            var path = '/data/local/tmp/wolf_' + tag + '_' + Date.now() + '.txt';
            var f = Java.use('java.io.File').$new(path);
            var fw = Java.use('java.io.FileWriter').$new(f);
            fw.write(s);
            fw.close();
            console.log('[+] saved ' + path);
        } catch (e) { console.log('[!] save err ' + tag + ': ' + e); }
    }

    Libv2ray.do_.overload('java.lang.String').implementation = function (s) {
        save('do_in', s);
        var r;
        try { r = this.do_(s); } catch (e) {
            console.log('[!] do_ threw: ' + e);
            r = this.do_(s);
        }
        save('do_out', r);
        return r;
    };

    Libv2ray.eo.overload('java.lang.String').implementation = function (s) {
        var r = this.eo(s);
        save('eo_out', r);
        return r;
    };

    Libv2ray.encrypt.overload('java.lang.String').implementation = function (s) {
        save('encrypt_in', s);
        return this.encrypt(s);
    };

    Libv2ray.gv.overload('java.lang.String').implementation = function (s) {
        var r = this.gv(s);
        save('gv_' + s + '_out', r);
        return r;
    };

    Libv2ray.gfc.overload().implementation = function () {
        var r = this.gfc();
        save('gfc_out', r);
        return r;
    };

    Libv2ray.ao.overload('java.lang.String').implementation = function (s) {
        console.log('[*] ao=' + s);
        return this.ao(s);
    };

    console.log('[*] hooks ready');
});
"""


def on_message(message, data):
    if message.get('type') == 'send':
        print('[console]', message['payload'])
    elif message.get('type') == 'error':
        print('[err]', message.get('description', '')[:300])


def main():
    dev = frida.get_usb_device(timeout=10)
    pid = dev.spawn([PKG])
    session = dev.attach(pid)
    script = session.create_script(SCRIPT)
    script.on('message', on_message)
    script.load()
    dev.resume(pid)
    print('[*] spawned & resumed; dumping for 120s...')
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(2)
    print('[*] pulling dump files...')
    import subprocess
    adb = r'C:\Android\sdk\platform-tools\adb.exe'
    r = subprocess.run([adb, 'shell', 'ls', '/data/local/tmp/'], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if 'wolf_' in line:
            fn = line.split()[-1]
            subprocess.run([adb, 'pull', f'/data/local/tmp/{fn}', str(OUT / fn)],
                           capture_output=True)
            print('[pulled]', fn)
    # keep session alive a bit more
    time.sleep(5)


if __name__ == '__main__':
    main()
