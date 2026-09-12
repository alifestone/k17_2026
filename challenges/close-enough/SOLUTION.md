# close enough — `SCONES{y0u_got_m3_out_of_a_p1ckle}`

（注意：這題 flag 前綴是 `SCONES` 不是 `K17`。）

`out.pkl.part` 是一個**被截斷**的 pickle（下載到一半斷掉），沒有 STOP opcode，
`pickle.load()` 會直接拒絕。但「截斷」其實是紅鯡魚——真正需要的東西全都還在，
掉的只有最後一筆 `admin password for the scoreboard` 的值。

用 `pickletools.genops` 逐 opcode 走，讓它在檔尾丟 `ValueError` 時接住就好：

```
 53: \x8a LONG1  437985254...   <- secret（完整）
107: 'the three digits on the back of my credit card'
156: \x8a LONG1  ...            <- 完整
203: 'an album you should listen to'
235: \x8a LONG1  ...            <- 完整
282: 'the flag'
293: \x8a LONG1  ...            <- 完整（結束於 offset 340）
340: 'admin password for the scoreboard'
                                <- 值被截掉，檔案在 376 bytes 結束
```

`EncryptedKV.__setitem__` 只是 `int.from_bytes(value.encode()) ^ secret`，
所以拿到 secret 後 XOR 回去再 `to_bytes` 就是明文。

```bash
python3 challenges/close-enough/solve.py
```

```
'the three digits on the back of my credit card': b'067'
'an album you should listen to': b'Mercurial World'
'the flag': b'SCONES{y0u_got_m3_out_of_a_p1ckle}'
```
