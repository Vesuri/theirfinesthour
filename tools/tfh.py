#!/usr/bin/env python3
"""Drive the original Their Finest Hour in FS-UAE through the Barto gdb stub.

  python3 tools/tfh.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/tfh.py <command...>   send one command to the running server, print the reply

Commands (the emulator is left running after each unless noted):
  stop | cont                  halt / resume the CPU
  gdb <text>                   raw gdb CLI command (halts first, resumes after)
  shot <png>                   record one field, save its screenshot
  profile <fields> <bin>       cycle-exact trace of <fields> PAL fields (Barto format)
  wait <seconds>               let it run
  until <addr>                 run to a breakpoint at addr and stay stopped there
  quit                         kill gdb and the emulator
"""
import os, select, signal, socket, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import barto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, 'amiga/.run')
SOCK = os.path.join(RUN, 'tfh.sock')
GDB = os.path.expanduser('~/.local/opt/bin/m68k-amiga-elf-gdb')
SENT = '@@TFH-DONE@@'


class Gdb:
    def __init__(self, port):
        env = dict(os.environ, HOME=os.path.join(RUN, 'gdbhome'))
        os.makedirs(env['HOME'], exist_ok=True)
        self.p = subprocess.Popen([GDB, '-q', '-nx'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, env=env, bufsize=0)
        self.buf = b''
        self.running = False
        for c in ('set pagination off', 'set confirm off', 'set height 0', 'set width 0',
                  'set remotetimeout 120', 'set architecture m68k'):
            self.cmd(c)
        out = self.cmd(f'target remote 127.0.0.1:{port}', timeout=60)
        if 'Remote debugging' not in out and 'in ??' not in out and '0x' not in out:
            raise RuntimeError('connect failed:\n' + out)

    def read_until(self, token, timeout):
        end = time.time() + timeout
        while token.encode() not in self.buf:
            r, _, _ = select.select([self.p.stdout], [], [], max(0, end - time.time()))
            if not r:
                raise TimeoutError(self.buf.decode(errors='replace'))
            chunk = os.read(self.p.stdout.fileno(), 65536)
            if not chunk:
                raise EOFError(self.buf.decode(errors='replace'))
            self.buf += chunk
        i = self.buf.index(token.encode())
        out, self.buf = self.buf[:i], self.buf[i + len(token):]
        return out.decode(errors='replace')

    def cmd(self, text, timeout=30):
        self.p.stdin.write((text + f'\necho {SENT}\\n\n').encode())
        out = self.read_until(SENT, timeout)
        return out.replace('(gdb) ', '').strip()

    def cont(self):
        if not self.running:
            self.p.stdin.write(b'continue &\n')
            time.sleep(0.2)
            self.running = True

    def stop(self):
        if self.running:
            self.p.stdin.write(b'interrupt\n')
            self.cmd('', timeout=30)
            time.sleep(0.3)
            self.running = False


# This FS-UAE build's Barto stub (x86_64, ~/.local/fs-uae) leaves the profiler's PC window
# [baseText, baseText+sizeText) as [0x0100007f, +0) when no --remote_debugger_trigger is given
# (127.0.0.1 lands in baseText), so every trace record comes out without a PC.  Under WHDLoad no
# trigger can name the game, so set the window to everything through lldb before each capture.
# Addresses are this binary's link-time ones (baseText = 0x32dea04, read by start_cpu_profiler).
BASETEXT_VM = 0x32dea04


class Lldb:
    """One lldb attached for the whole session: attaching to this x86_64 FS-UAE under Rosetta
    takes minutes, so it is done once, on the first capture, and the process kept running."""

    def __init__(self):
        pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
        self.p = subprocess.Popen(['lldb', '-O', 'settings set target.preload-symbols false',
                                   '-p', pid], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, bufsize=0)
        self.buf = b''
        out = self.cmd('image list -o -f fs-uae', timeout=900)
        self.base = int(out.split('[  0] ')[1].split()[0], 16) + BASETEXT_VM
        self.cmd('script lldb.debugger.SetAsync(True)')  # else continue blocks the command loop
        self.cmd('process continue')

    read_until = Gdb.read_until

    def cmd(self, text, timeout=60):
        self.p.stdin.write((text + f"\nscript print('{SENT}')\n").encode())
        return self.read_until(SENT + '\n', timeout)


LLDB = None


def fix_profile_window():
    global LLDB
    if LLDB is None:
        LLDB = Lldb()
    a = LLDB.base
    LLDB.cmd('process interrupt')
    while 'stopped' not in LLDB.cmd('process status'):
        time.sleep(0.2)
    LLDB.cmd(f'memory write -s4 {a:#x} 0')
    LLDB.cmd(f'memory write -s4 {a + 4:#x} 0x7fffffff')
    out = LLDB.cmd(f'memory read -s4 -fx -c2 {a:#x}')
    LLDB.cmd('process continue')
    assert '0x00000000 0x7fffffff' in out, out


def serve():
    env = dict(os.environ, DEBUG='1', SILENT=os.environ.get('SILENT', '1'))
    out = subprocess.run(['bash', os.path.join(ROOT, 'amiga/run.sh')], env=env,
                         capture_output=True, text=True, check=True).stdout
    print(out, end='', flush=True)
    port = int(out.rsplit('port ', 1)[1].split(')')[0])
    for _ in range(80):
        if subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN'], capture_output=True).stdout:
            break
        time.sleep(0.25)
    g = Gdb(port)
    print('attached; pc', g.cmd('info registers pc'), flush=True)
    # Arm an address learned in a calibration boot before emulated time advances.
    # This prevents a fast warp boot from passing the anchor during host polling.
    if os.environ.get('BOOT_BREAK'):
        g.cmd(f"break *{os.environ['BOOT_BREAK']}")
        print(g.cmd('continue', timeout=1800), flush=True)
        g.cmd('delete')
    else:
        g.cont()
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    s = socket.socket(socket.AF_UNIX); s.bind(SOCK); s.listen(1)
    print('serving on', SOCK, flush=True)
    while True:
        c, _ = s.accept()
        line = c.recv(65536).decode().strip()
        try:
            reply = handle(g, line)
        except Exception as e:  # report and keep serving
            reply = f'ERROR {type(e).__name__}: {e}'
        try:
            c.sendall((reply + '\n').encode())
        except OSError:
            pass
        c.close()
        if line == 'quit':
            break


def handle(g, line):
    op, _, rest = line.partition(' ')
    if op == 'stop':
        g.stop(); return g.cmd('info registers pc')
    if op == 'cont':
        g.cont(); return 'running'
    if op == 'wait':
        g.cont(); time.sleep(float(rest)); return 'ok'
    if op == 'until':
        g.stop()
        g.cmd(f'break *{rest}')
        out = g.cmd('continue', timeout=1800)
        g.cmd('delete')
        return out
    if op == 'gdb':
        was = g.running; g.stop()
        out = g.cmd(rest, timeout=600)
        if was: g.cont()
        return out
    if op in ('shot', 'profile'):
        was = g.running; g.stop()
        if op == 'shot':
            target, fields, png = os.path.join(RUN, 'shot.bin'), 1, os.path.abspath(rest)
        else:
            fields, target = rest.split(None, 1)
            target = os.path.abspath(target)
        if op == 'profile':
            fix_profile_window()
        out = g.cmd(f'monitor profile {fields} "" "{target}"', timeout=1800)
        if was: g.cont()
        if op == 'shot':
            f = barto.load(target).fields[-1]
            open(png, 'wb').write(f.shot)
            return f'{png} kind={f.shot_kind} {len(f.shot)} bytes {out}'
        return out or 'ok'
    if op == 'quit':
        g.p.kill()
        if LLDB:
            LLDB.p.kill()
        pid = open(os.path.join(RUN, 'fsuae.pid')).read().strip()
        os.kill(int(pid), signal.SIGKILL)
        return 'bye'
    return 'unknown command'


def client(args):
    c = socket.socket(socket.AF_UNIX); c.connect(SOCK)
    c.sendall(' '.join(args).encode())
    out = b''
    while chunk := c.recv(65536):
        out += chunk
    print(out.decode(), end='')


if __name__ == '__main__':
    if sys.argv[1:] == ['serve']:
        serve()
    else:
        client(sys.argv[1:])
