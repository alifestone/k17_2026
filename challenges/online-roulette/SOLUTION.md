# online-roulette — `K17{th1s_minib0lt_guy_must_b3_rlly_lucky_huh}`

## 那個任意寫其實是陷阱，直接跳過它

```c
printf("[addr]> ");
scanf("%lx", &addr);
if (addr > (uintptr_t)&wager) {
    puts("intruder neutralised");
} else {
    ...
    *(unsigned char *)addr = (unsigned char)value;
}
```

`balance` 是 `main` 的區域變數，`wager` 是 `game` 的區域變數。`game` 由 `main` 呼叫，
堆疊往低位址長，所以 **`&wager` < `&balance`**——這個寫入永遠碰不到 `balance`，
限制條件擺明就是要擋掉這條路。

反過來看，`else` 分支是唯一會 dereference `addr` 的地方。送一個超大位址
（`ffffffffffffffff`）會走 "intruder neutralised" 那一邊，**整個寫入被跳過**：
不會 segfault，也完全不需要先洩漏任何堆疊位址。

## 真正的洞在賠付

```c
*balance -= wager;
...
if (lotto == 1) { *balance += 2 * wager; }
```

`wager` 除了 `> 0` 之外沒有任何上限（`< 0` 直接 exit，`== 0` 離開迴圈），
而 `balance` 起始值是 10。中獎一次：

```
balance = 10 - w + 2w = 10 + w
```

取 `w = 1e9` → `balance = 1000000010 > 999999999` → `main` 呼叫 `win()`。

沒中的話 `balance = 10 - 1e9 < 0`，觸發 `damn no more money` 直接 return，
所以**每條連線只有一次 1/36 的機會**，重連重試即可。

```bash
ROULETTE_HOST=chal.secso.cc ROULETTE_PORT=4000 python3 challenges/online-roulette/solve.py
```

```
[+] won on attempt 14
[+] FLAG: K17{th1s_minib0lt_guy_must_b3_rlly_lucky_huh}
```
