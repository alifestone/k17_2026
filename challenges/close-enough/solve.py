#!/usr/bin/env python3
"""close enough -- out.pkl.part is a truncated pickle of an EncryptedKV.

The download died partway, so the pickle has no STOP opcode and the last
value ('admin password for the scoreboard') is missing.  Everything we need
survived though: `secret` and the ciphertext for 'the flag' are both complete.

EncryptedKV stores  d[key] = int.from_bytes(value.encode()) ^ secret,
so decrypting is just XOR with secret and converting back to bytes.
"""
import pickletools
import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out.pkl.part")

# Walk the opcode stream by hand -- pickle.load() refuses a truncated file,
# and genops itself raises once it runs off the end, so consume it defensively.
longs, strs = [], []
try:
    for op, arg, _pos in pickletools.genops(open(path, "rb")):
        if op.name == "LONG1":
            longs.append(arg)
        elif op.name == "SHORT_BINUNICODE":
            strs.append(arg)
except ValueError as e:
    print(f"[*] pickle truncated as expected: {e}\n")

secret = longs[0]
keys = [s for s in strs if s not in ("__main__", "EncryptedKV", "secret", "d")]

def dec(num):
    num ^= secret
    return num.to_bytes(-(num.bit_length() // -8))

for key, ct in zip(keys, longs[1:]):
    print(f"{key!r}: {dec(ct)!r}")
