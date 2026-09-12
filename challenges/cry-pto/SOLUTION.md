# cry-pto — `K17{y0u_ar3_f1ll3d_w1th_deter1min4t10n}`

`CRYSig.sign` 是 **GF(2) 上的線性映射**：tag 的每個 bit 是 `(row & msg).bit_count() % 2`，
也就是矩陣乘向量 mod 2。線性 ⇒

```
sign(a XOR b) == sign(a) XOR sign(b)
```

題目免費給我們 `sign(b"babyuser")`，又允許我們對任意一個訊息簽名（只擋 `query == b"chadr00t"`）。
所以送

```
query = b"babyuser" XOR b"chadr00t"
```

這個 query 不等於 `b"chadr00t"`，過得了檢查。又因為 `b"chadr00t" == b"babyuser" XOR query`：

```
sign(chadr00t) = sign(babyuser) XOR sign(query)
```

```bash
python3 challenges/cry-pto/solve.py           # 預設打 chal.secso.cc:2000
```

```
user signature: 973c5279061de5be5d520978a48bce70
your signature: 6bd562bb4b217f8c8f646ef34acfe3a3
forged sign(chadr00t) = fce930c24d3c9a32d236678bee442dd3
K17{y0u_ar3_f1ll3d_w1th_deter1min4t10n}
```
