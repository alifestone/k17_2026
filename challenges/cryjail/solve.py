#!/usr/bin/env python3
"""cryjail -- AES-CBC decryption oracle turned into Python code injection.

The service AES-CBC-*decrypts* whatever (iv, ct) we hand it and splices the
resulting bytes into a generated program:

    print(b"IMPLANTING ... AS: <escape(name)>!", file=devnull)

escape() passes printable ASCII through untouched -- including '"' -- so a
plaintext quote closes the bytes literal and lets us inject code.  We do not
know KEY, but CBC gives us P_i = AES_dec(C_i) ^ C_{i-1} bytewise, and the
child's exit status is a 1-bit oracle:

    crash  <=>  the generated source failed to compile/run
           <=>  the plaintext contains a '"'   (with a clean baseline)

So for a fixed ciphertext block C, pick a baseline IV that does not crash,
then sweep IV[i] over 0..255: the single value that crashes tells us
AES_dec(C)[i] = v ^ ord('"').  16*255 probes, fully pipelined.

With AES_dec(.) available on demand we run CBC-R backwards to force any
plaintext we like:
    C_1 = AES_dec(C_2) ^ P_2      IV = AES_dec(C_1) ^ P_1
"""
import os
import socket
import sys
import threading

HOST = os.environ.get("CRYJAIL_HOST", "vm1.secso.cc")
PORT = int(os.environ.get("CRYJAIL_PORT", "20239"))
PASSWORD = os.environ.get("CRYJAIL_PW", "lO_zVP3D315W")

QUOTE = 0x22
BACKSLASH = 0x5C
OK, BAD = b"[ok]", b"[!] probably"


class Oracle:
    def __init__(self, host, port, password):
        self.s = socket.create_connection((host, port), timeout=30)
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.dead = False
        self._expect(b"password: ")
        self.s.sendall(password.encode() + b"\n")
        self._expect(b"New name")
        with self.lock:
            self.buf.clear()
        self.pos = 0          # how far into buf we have already consumed results
        threading.Thread(target=self._reader, daemon=True).start()
        self.queries = 0

    def _expect(self, tok):
        while tok not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                raise EOFError("closed while waiting for %r" % tok)
            self.buf += chunk

    def _reader(self):
        try:
            while True:
                chunk = self.s.recv(65536)
                if not chunk:
                    break
                with self.lock:
                    self.buf += chunk
        except Exception:
            pass
        self.dead = True

    def probe(self, pairs):
        """Send every (iv, ct) pair, return a list of 'did it crash' booleans."""
        payload = b"".join(iv.hex().encode() + b":" + ct.hex().encode() + b"\n"
                           for iv, ct in pairs)
        # Send in chunks; the reader thread drains responses so we never deadlock.
        view = memoryview(payload)
        while view:
            n = self.s.send(view[:32768])
            view = view[n:]
        self.queries += len(pairs)

        # Results are consumed from self.pos onwards so that successive probe()
        # calls do not re-read the previous batch's replies.
        while True:
            with self.lock:
                data = bytes(self.buf)
            i, results = self.pos, []
            while len(results) < len(pairs):
                a, b = data.find(OK, i), data.find(BAD, i)
                if a < 0 and b < 0:
                    break
                if a < 0 or (0 <= b < a):
                    results.append(True)
                    i = b + len(BAD)
                else:
                    results.append(False)
                    i = a + len(OK)
            if len(results) == len(pairs):
                self.pos = i
                return results
            if self.dead:
                raise EOFError("connection closed after %d/%d results"
                               % (len(results), len(pairs)))
            threading.Event().wait(0.05)

    def send_raw(self, iv, ct):
        self.s.sendall(iv.hex().encode() + b":" + ct.hex().encode() + b"\n")

    def drain(self, seconds=4.0):
        threading.Event().wait(seconds)
        with self.lock:
            return bytes(self.buf)


def leak_block(orc, ct):
    """Recover AES_dec(ct) for a single 16-byte ciphertext block."""
    for attempt in range(8):
        base = os.urandom(16)
        if orc.probe([(base, ct)])[0]:
            continue  # this baseline already contains a quote

        pairs, index = [], []
        for i in range(16):
            for v in range(256):
                if v == base[i]:
                    continue
                iv = bytearray(base)
                iv[i] = v
                pairs.append((bytes(iv), ct))
                index.append((i, v))

        dec = [None] * 16
        for (i, v), crashed in zip(index, orc.probe(pairs)):
            if crashed:
                dec[i] = v ^ QUOTE

        if any(d is None for d in dec):
            continue  # a '\' in the baseline plaintext masked a quote
        dec = bytes(dec)
        plain = bytes(a ^ b for a, b in zip(dec, base))
        if QUOTE in plain or BACKSLASH in plain:
            continue  # baseline was not clean after all -- redo
        print(f"    [+] AES_dec = {dec.hex()}  (attempt {attempt + 1})")
        return dec
    raise RuntimeError("could not leak block after 8 baselines")


def main():
    payload = b'",print(open("/flag").read()),"X'
    assert len(payload) == 32, len(payload)
    p1, p2 = payload[:16], payload[16:]

    orc = Oracle(HOST, PORT, PASSWORD)
    print(f"[*] connected to {HOST}:{PORT}")

    c2 = b"\x00" * 16
    print("[*] leaking AES_dec(C2) ...")
    d2 = leak_block(orc, c2)
    c1 = bytes(a ^ b for a, b in zip(d2, p2))

    print("[*] leaking AES_dec(C1) ...")
    d1 = leak_block(orc, c1)
    iv = bytes(a ^ b for a, b in zip(d1, p1))

    print(f"[*] {orc.queries} oracle queries total")
    print(f"[*] firing payload: {payload!r}")
    orc.send_raw(iv, c1 + c2)
    out = orc.drain(6.0)

    tail = out.decode(errors="replace")
    for line in tail.splitlines():
        if "K17{" in line or "SCONES{" in line:
            print("\n[+] FLAG:", line.strip())
            return
    print("\n[-] no flag seen; raw tail:\n", tail[-1500:])
    sys.exit(1)


if __name__ == "__main__":
    main()
