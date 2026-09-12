#!/usr/bin/env python3
"""cry-pto -- CRYSig is linear over GF(2), so sign(a ^ b) == sign(a) ^ sign(b).

sign() computes M * m over GF(2) (each tag bit is the parity of row & message).
We are handed sign(b"babyuser") for free and may sign one message of our choice.
Query q = b"babyuser" ^ b"chadr00t"  (!= b"chadr00t", so the cheat check passes),
then sign(b"chadr00t") = sign(b"babyuser") ^ sign(q).
"""
import socket
import sys

HOST, PORT = sys.argv[1] if len(sys.argv) > 1 else "chal.secso.cc", 2000
USER, ROOT = b"babyuser", b"chadr00t"

def recv_until(s, tok):
    buf = b""
    while tok not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf

s = socket.create_connection((HOST, PORT), timeout=15)
line = recv_until(s, b"> ")
print(line.decode(errors="replace"), end="")
user_sig = bytes.fromhex(line.split(b"user signature:")[1].split(b"\n")[0].strip().decode())

query = bytes(a ^ b for a, b in zip(USER, ROOT))
assert query != ROOT
s.sendall(query.hex().encode() + b"\n")

line = recv_until(s, b"> ")
print(line.decode(errors="replace"), end="")
q_sig = bytes.fromhex(line.split(b"your signature:")[1].split(b"\n")[0].strip().decode())

forged = bytes(a ^ b for a, b in zip(user_sig, q_sig))
print(f"forged sign(chadr00t) = {forged.hex()}")
s.sendall(forged.hex().encode() + b"\n")

s.settimeout(10)
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
