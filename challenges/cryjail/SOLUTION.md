# cryjail — `K17{yaaaaaaay_i_h0pE_yoU_D1dn7_cra5H_0Ut!!!!!!!!!!!}`

## 漏洞

服務把我們送進去的 `(iv, ct)` 拿 **AES-CBC 解密**，然後把解出來的 bytes 直接拼進一份
產生出來的 Python 程式：

```python
print(b"IMPLANTING NEURO LINK CHIP IN INDIVIDUAL IDENTIFIYING AS: <escape(name)>!", file=devnull)
```

`escape()` 只把非可列印字元轉成 `\xNN`，**可列印字元原樣通過 —— 包含 `"` (0x22) 和 `\` (0x5c)**
（原始碼註解自己寫出來了）。所以只要明文裡出現一個 `"`，就會提前關掉那個 bytes literal，
後面接的東西會被當成 Python 程式碼 → 程式碼注入。

問題是我們不知道 `KEY`，沒辦法直接指定明文。

## 1-bit oracle

`main()` fork 出子行程跑產生的程式，然後只根據 exit code 回兩種訊息：

- `[ok] reported name to our database` — 正常結束
- `[!] probably not enough cores or something idk lmao` — 有例外（含 SyntaxError）

在一個「乾淨的基準」下，**crash ⟺ 明文裡含有 `"`**。這就是洩漏用的 1-bit oracle。

## 逐 byte 洩漏 AES_dec

CBC 的性質：`P = AES_dec(C) ⊕ IV`，而且是**逐 byte** 的 —— 改 `IV[i]` 只會影響 `P[i]`。

所以對一個固定的密文 block `C`：

1. 隨機挑一個不會 crash 的基準 `IV_base`（代表此時明文中沒有 `"`）。
2. 對每個位置 `i`、每個值 `v`，送出「把 `IV_base[i]` 換成 `v`」的 IV。
   其他 15 個 byte 維持基準值（已知安全），所以 crash 只可能來自位置 `i`。
3. 唯一造成 crash 的那個 `v` 滿足 `AES_dec(C)[i] ⊕ v == 0x22`
   → `AES_dec(C)[i] = v ⊕ 0x22`。

共 16×255 = 4080 次查詢，但**全部可以 pipeline**（彼此獨立），配一個背景 reader thread
邊送邊收，避免 socket 雙向阻塞死鎖。

事後驗證：算出 `P_base = AES_dec(C) ⊕ IV_base`，必須不含 `0x22` 也不含 `0x5c`
（若某個位置前一個 byte 是 `\`，注入的引號會變成 `\"` 而不會斷開字串，該位置就掃不到 crash，
這時換一個基準重來）。

## CBC-R 構造任意明文

payload 需要 32 bytes（2 個 block）：

```python
b'",print(open("/flag").read()),"X'
```

拼出來的程式會變成合法的：

```python
print(b"IMPLANTING ... AS: ", print(open("/flag").read()), "X!", file=devnull)
```

外層 `print` 寫到 `/dev/null`，但**內層 `print` 寫到真正的 stdout**，flag 就噴出來了。
（landlock 只限制寫入，讀 `/` 是允許的，所以 `open("/flag")` 沒問題。）

倒著推：

```
C_2 = 任意（取 16 個 0x00）
C_1 = AES_dec(C_2) ⊕ P_2
IV  = AES_dec(C_1) ⊕ P_1
```

需要兩次 block 洩漏（第二次依賴第一次的結果，無法平行），共 8162 次查詢。

```bash
CRYJAIL_HOST=vm1.secso.cc CRYJAIL_PORT=20239 CRYJAIL_PW=... python3 challenges/cryjail/solve.py
```

```
[*] leaking AES_dec(C2) ...
    [+] AES_dec = 7b326f33ce725508def0369753100367  (attempt 1)
[*] leaking AES_dec(C1) ...
    [+] AES_dec = 5fbad2131faf832bdc87b0feb26da3d8  (attempt 1)
[*] 8162 oracle queries total
[+] FLAG: K17{yaaaaaaay_i_h0pE_yoU_D1dn7_cra5H_0Ut!!!!!!!!!!!}
```

## 實作上踩到的坑

第一版把兩個 block 洩出來的 `AES_dec` 長得幾乎一樣（只差 3 個 byte）——
那是不可能的，等於直接說明 oracle 讀錯了。原因是回應解析每次都從 buffer 開頭重新掃，
第二批 probe 讀到的其實是第一批的回應。修法是記住已消費到的 offset（`self.pos`）。
