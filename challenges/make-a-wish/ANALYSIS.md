# make-a-wish — 分析（尚未解出）

## 已確認的 bug：有號取模造成負 index

`create` 與 `delete` 都做：

```
imul rdx,rdx,0x66666667 ; shr rdx,0x20 ; sar edx,1 ; sub edx,ecx ; ... ; sub eax,edx
```

這是 `idx = idx % 5`，而且是 **C 的有號取模** —— 負數輸入會得到負的餘數，
所以 `idx ∈ {-4,-3,-2,-1,0,1,2,3,4}`。

`wishes` 陣列在 `main` 的 `rbp-0x60`，於是負 index 會落到它下方的區域變數：

| idx | 位址 | 內容 |
|---:|---|---|
| 0 | `rbp-0x60` | `wishes[0]` |
| -1 | `rbp-0x68` | `read()` 的回傳值 `nread` |
| **-2** | **`rbp-0x70`** | **`name2` 指標（指向 `rbp-0x30` 的 30-byte 姓名緩衝區）** |
| -3 | `rbp-0x78` | 未使用，但與 `rbp-0x74` 的 menu `choice` 重疊 |
| -4 | `rbp-0x80` | frame 底部 |

- `create(idx)`：把 `malloc(0x90)` 的結果寫進去
- `delete(idx)`：對該處的值呼叫 `free()`，然後歸零

## 試過但行不通：house of spirit（free 堆疊上的偽造 chunk）

`delete(-2)` 會 `free(name2)`，而 `name2` 指向我們可控的姓名緩衝區 —— 看起來正是
house of spirit。但對齊要求把它堵死了：

- `free()` 的 `misaligned_chunk(p)` 要求 `mem` 必須 16-byte 對齊。
  `name_buffer = rbp-0x30` 本身 16 對齊，`name2 = buffer + space_pos + 1`，
  所以 **空格只能放在 index 15**（緩衝區只有 30 bytes，下一個對齊點 31 超出範圍）。
- 偽造的 size 欄位在 `mem-8` = `buffer + space_pos - 7`，
  它這個 qword 的範圍是 `buffer[space_pos-7 .. space_pos+1)`，
  **最高位元組正好是 `buffer[space_pos]`，也就是那個空格 `0x20`**。

於是 `size ≈ 0x20xxxxxxxxxxxxxx`：

- `p > -size` 通過（`-size ≈ 0xE0...` 比堆疊位址大）
- `size < MINSIZE` 通過
- 但 `csize2tidx(size)` 遠大於 `mp_.tcache_bins`(64) → **進不了 tcache**
- 於是走一般 `_int_free`，去讀 `chunk_at_offset(p, size)` → 位址爆掉 → segfault

空格位置決定了 size 的 MSB，這是結構性的，換位置也躲不掉。

## 其他試過的死路

- **double free**：`delete` 一定會把 slot 歸零，而 `create` 每次都是新的 `malloc`，
  同一個指標不可能同時存在兩個 slot，湊不出 double free / UAF。
- **`idx=-3`**：寫進去的 heap 指標高 32 bits 會被下一輪的 menu `choice` 蓋掉
  （non-PIE 的 heap 位址本來就 < 2^32，高位是 0），free 出來變成 `0x00000002_xxxxxxxx`。
- **ROP**：binary 裡**沒有任何 `pop rdi` / `pop rsi` / `pop rdx` / `syscall`**
  （只有 `ret`、`pop rbp; ret`、`leave; ret`），就算拿到堆疊寫入也缺 rdi 控制。
  `system@plt` 存在但 `main` 只用常數字串 `"clear"` 呼叫它。

## 還沒試的方向

1. `fgets(chunk, 0x90, stdin)` 寫進 `malloc(0x90)`（usable 0x98）—— 沒有溢位，
   但若能讓 `malloc` 回傳非堆積位址（tcache poisoning）就等於任意寫。
   問題是目前沒有取得 tcache 控制的入口。
2. 覆寫 `name1`（`rbp-0x8`）之後，`create` 的 `printf("...%s...", name1)`
   就是任意位址讀 → 可洩漏 GOT 裡的 libc 位址，再用 libc 的 gadget 補上缺的 `pop rdi`。
   但要先有堆疊寫入才能改 `name1`，目前是雞生蛋問題。
