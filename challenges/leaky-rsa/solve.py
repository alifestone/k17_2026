#!/usr/bin/env python3
"""leaky rsa -- recover p,q from leak = dp + dq.

e*dp = 1 + kp*(p-1)  and  e*dq = 1 + kq*(q-1)  for some 1 <= kp,kq < e.
Adding:   e*leak - 2 + kp + kq = kp*p + kq*q =: T
Since (kp*p)*(kq*q) = kp*kq*N, the two values kp*p and kq*q are the roots of
    x^2 - T*x + kp*kq*N = 0
so brute force the (kp,kq) pair (e = 257 -> 65536 combos) and test the discriminant.
"""
from math import isqrt
from Crypto.Util.number import long_to_bytes

ns = {}
for line in open(__file__.rsplit('/', 1)[0] + '/out.txt'):
    if '=' in line:
        k, v = line.split('=', 1)
        ns[k.strip()] = int(v.strip())
N, e, leak, c = ns['N'], ns['e'], ns['leak'], ns['c']

def solve():
    base = e * leak - 2
    for kp in range(1, e):
        for kq in range(1, e):
            T = base + kp + kq
            disc = T * T - 4 * kp * kq * N
            if disc < 0:
                continue
            r = isqrt(disc)
            if r * r != disc:
                continue
            for root in ((T + r) // 2, (T - r) // 2):
                if root % kp:
                    continue
                p = root // kp
                if p > 1 and N % p == 0:
                    return p, N // p
    return None, None

p, q = solve()
assert p and p * q == N, "factorisation failed"
print(f"p = {p}")
print(f"q = {q}")
d = pow(e, -1, (p - 1) * (q - 1))
print(long_to_bytes(pow(c, d, N)).decode())
