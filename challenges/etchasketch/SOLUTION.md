# etch-a-sketch — `K17{my_masterpiece}`

直接跑的話整張畫布都是 `#`，什麼都看不到。

`nm` 顯示這支 binary 沒有 strip，符號很直白：

```
0000000000004020 D brush_r      <- .data，初始值 10
0000000000002020 r points       <- .rodata，線段端點
0000000000004060 b canvas       <- .bss，82 x 120 bytes
0000000000001149 t dab
00000000000011e5 t line
```

`main` 逐點印 `canvas[row*120 + col]`（`0x52` 列 × `0x78` 行），非零印 `#` 否則印空白。

問題單純是**筆刷半徑太大**：

```
$ xxd -s 0x3020 -l 4 etchasketch
00003020: 0a00 0000                      # brush_r = 10
```

半徑 10 的筆刷沿著線段塗下去，整張畫布自然被填滿。

`.data` 的 vaddr 是 `0x4010`、檔案 offset 也是 `0x3010`，所以 `brush_r` 在檔案的
`0x3010 + (0x4020 - 0x4010)` = `0x3020`。把它改成 1 再跑：

```bash
cp etchasketch etch_1
printf '\x01' | dd of=etch_1 bs=1 seek=$((0x3020)) conv=notrunc
./etch_1
```

畫出來的就是 flag 本身：

```
K17{my_
master
piece}
```

（`brush_r=0` 也可以，線條更細但筆畫較難辨識；1 最好讀。）
