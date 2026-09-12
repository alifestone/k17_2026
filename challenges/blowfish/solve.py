#!/usr/bin/env python3
"""blowfish -- a per-block MAC plus CBC linearity gives arbitrary signed blocks.

    def sign(raw_fish):
        return "".join(sha256(SECRET_SIGNING_KEY + raw_fish[i:i+8]).hexdigest()
                       for i in range(0, len(raw_fish), 8))

Each 8-byte block is MACed **independently of its position**, so a signature is
just a concatenation of per-block tags: blocks (and their tags) can be reordered,
dropped or repeated at will.  We are handed the fish and its signature, which
gives us ~152 signed blocks -- including `{"admin"` , the very first block of the
JSON.

To win we need json.loads(plaintext[8:]) to have admin === True, i.e. the byte
string `{"admin"` followed by `: true }`.  The first block we already have signed;
the second has to be manufactured.

Both oracles echo their input's first block and sign everything they return:

    encrypt(pt) = pt[:8] || CBC_ENC(pad(pt[8:]))      # C_i = E(P_i ^ C_{i-1})
    decrypt(ct) = ct[:8] || unpad(CBC_DEC(ct[8:]))    # P_i = D(C_i) ^ C_{i-1}

Step 1 -- replay the original fish through `blow_fish`.  We then know every
plaintext block P_i *and* every ciphertext block C_i, so

    d_i := D(C_i) = P_i ^ C_{i-1}

is known for ~151 blocks, and every C_i is signed.

Step 2 -- feeding `unblow_fish` the two-block ciphertext [Z][C_i] returns
Z || (d_i ^ Z), so one call XORs a chosen d_i onto any signed block Z and hands
back the tag for the result.  Chaining calls walks the coset Z ^ span{d_i}; with
151 random 64-bit values the span is all of GF(2)^64, so Gaussian elimination
picks the subset that lands exactly on `: true }`.
"""
import os
import re
import socket
import sys

HOST = os.environ.get("BLOWFISH_HOST", "chal.secso.cc")
PORT = int(os.environ.get("BLOWFISH_PORT", "2001"))

TARGET = b": true }"
ADMIN_BLOCK = b'{"admin"'


class Fish:
    def __init__(self, host, port):
        self.s = socket.create_connection((host, port), timeout=30)
        self.s.settimeout(20)
        self.buf = bytearray()

    def until(self, tok):
        while tok not in self.buf:
            c = self.s.recv(65536)
            if not c:
                raise EOFError
            self.buf.extend(c)
        i = self.buf.index(tok) + len(tok)
        out = bytes(self.buf[:i])
        del self.buf[:i]
        return out

    def line(self):
        return self.until(b"\n")

    def op(self, choice, data, sig):
        self.until(b"2? ")
        self.s.sendall(choice + b"\n" + data.hex().encode() + b"\n" + sig.encode() + b"\n")
        out = self.until(b"\n")
        if b"properly" in out or b"EXPLODED" in out or b"IMPLODED" in out:
            raise RuntimeError(out.decode(errors="replace").strip())
        if b"FLAG" in out or b"offishial" in out:
            return out, None
        body = re.search(rb": ([0-9a-f]+)\n", out).group(1)
        newsig = re.search(rb"Signature: ([0-9a-f]+)", self.until(b"\n")).group(1)
        return bytes.fromhex(body.decode()), newsig.decode()


def blocks_of(data):
    return [data[i:i + 8] for i in range(0, len(data), 8)]


def sigs_of(sig, n):
    return [sig[i * 64:(i + 1) * 64] for i in range(n)]


def solve_subset(ds, target):
    """Gaussian elimination over GF(2)^64: find a subset of ds XORing to target."""
    basis = []  # (pivot value, mask of contributing indices)
    for i, d in enumerate(ds):
        v, m = d, 1 << i
        for bv, bm in basis:
            if v ^ bv < v:
                v, m = v ^ bv, m ^ bm
        if v:
            basis.append((v, m))
            basis.sort(key=lambda t: -t[0])
    v, m = target, 0
    for bv, bm in basis:
        if v ^ bv < v:
            v, m = v ^ bv, m ^ bm
    return m if v == 0 else None


def main():
    f = Fish(HOST, PORT)
    fish = bytes.fromhex(re.search(rb"Fish: ([0-9a-f]+)", f.until(b"\n")).group(1).decode())
    sig = re.search(rb"Signature: ([0-9a-f]+)", f.until(b"\n")).group(1).decode()
    pb, ps = blocks_of(fish), sigs_of(sig, (len(fish) + 7) // 8)
    print(f"[*] fish: {len(fish)} bytes, {len(pb)} blocks")
    assert pb[1] == ADMIN_BLOCK, pb[1]

    # 1. replay the signed fish through the encrypt oracle
    ct, ctsig = f.op(b"1", fish, sig)
    cb, cs = blocks_of(ct), sigs_of(ctsig, len(ct) // 8)
    print(f"[*] ciphertext: {len(cb)} blocks")

    # 2. d_i = D(C_i) = P_i ^ C_{i-1}, over the zero-padded plaintext
    padded = fish[8:] + b"\x00" * (-len(fish[8:]) % 8)
    pblocks = blocks_of(padded)
    ds, dsrc = [], []
    for i in range(1, len(cb)):
        d = int.from_bytes(pblocks[i - 1], "big") ^ int.from_bytes(cb[i - 1], "big")
        ds.append(d)
        dsrc.append(i)

    # 3. walk from a known signed block to TARGET along the d-coset
    cur, cursig = pb[0], ps[0]
    mask = solve_subset(ds, int.from_bytes(cur, "big") ^ int.from_bytes(TARGET, "big"))
    if mask is None:
        sys.exit("[-] target not in span")
    picks = [i for i in range(len(ds)) if mask >> i & 1]
    print(f"[*] {len(picks)} XOR steps to reach {TARGET!r}")

    for n, i in enumerate(picks, 1):
        j = dsrc[i]
        out, outsig = f.op(b"2", cur + cb[j], cursig + cs[j])
        if len(out) != 16:
            sys.exit(f"[-] unpad ate trailing zeros at step {n} (len={len(out)})")
        cur, cursig = out[8:], sigs_of(outsig, 2)[1]
    print(f"[*] forged block: {cur!r}")
    assert cur == TARGET

    # 4. {"admin"} + ": true }"  ->  {"admin": true }
    payload = pb[0] + ADMIN_BLOCK + TARGET
    paysig = ps[0] + ps[1] + cursig
    out, _ = f.op(b"1", payload, paysig)
    text = out.decode(errors="replace")
    print(text)
    m = re.search(r"(K17\{[^}]*\}|SCONES\{[^}]*\})", text)
    if m:
        print("[+] FLAG:", m.group(1))
    else:
        sys.exit("[-] no flag")


main()
