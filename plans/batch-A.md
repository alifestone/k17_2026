# Batch A — 四題快速拿分（planner: k17-2026-6a / executor: dolphin_cyber:tools）

通則：
- 每題完成後，把 exploit 腳本存在 `challenges/<slug>/solve.py`、解法說明存在 `challenges/<slug>/SOLUTION.md`。
- flag 一律以實際跑出來的輸出為準，**不可以自己編造或推測 flag**。沒跑出來就寫「未取得」。
- 拿到 flag 後更新 `README.md`：把該題 `狀態` 欄改成 ✅，並在該題小節加一行 `**狀態：✅ 已解**　flag: \`...\``，同時更新頂端「解題進度」計數與表格。
- 每題做完就 `git add -A && git commit`，然後更新 `handover.md` 的 `head_sha` / `Verified evidence`。

---

## A1. cry-pto （crypto, beginner, `nc chal.secso.cc 2000`）

檔案：`challenges/cry-pto/chal.py`

**弱點**：`CRYSig.sign` 是 GF(2) 上的線性映射。
`res` 的每個 bit = `(row & msg_vector).bit_count() % 2`，也就是矩陣乘向量 mod 2。
線性代表：`sign(a XOR b) == sign(a) XOR sign(b)`。

**攻擊步驟**（一次連線就能完成）：
1. 連上去，讀第一行 `user signature: <hex>` → 記為 `user_sig`（16 bytes）。
2. 送出 query = `bytes(x ^ y for x, y in zip(b"babyuser", b"chadr00t"))` 的 hex。
   - 這個 query 不等於 `b"chadr00t"`，所以不會觸發 "holy cheating"。
3. 讀回 `your signature: <hex>` → 記為 `q_sig`。
4. 因為 `b"chadr00t" == b"babyuser" XOR query`，所以
   `sign(chadr00t) = user_sig XOR q_sig`。
5. 把 `user_sig XOR q_sig` 的 hex 當成第二個輸入送出 → 拿到 flag。

用 pwntools `remote("chal.secso.cc", 2000)` 寫 `challenges/cry-pto/solve.py`。

---

## A2. leaky-rsa （crypto, easy，純離線）

檔案：`challenges/leaky-rsa/chal.py`、`challenges/leaky-rsa/out.txt`

**已知**：`N`、`e = 257`、`c`、`leak = dp + dq`，其中 `dp = d mod (p-1)`、`dq = d mod (q-1)`。

**數學推導**：
存在整數 `1 <= kp, kq < e` 使得
```
e*dp = 1 + kp*(p-1)
e*dq = 1 + kq*(q-1)
```
相加：
```
e*leak - 2 + kp + kq = kp*p + kq*q
```
令 `T = e*leak - 2 + kp + kq`，則 `kp*p` 與 `kq*q` 是二次式
```
x^2 - T*x + (kp*kq*N) = 0
```
的兩個根（因為 `(kp*p)*(kq*q) = kp*kq*N`）。

**攻擊步驟**：
1. 對所有 `kp in range(1, e)`、`kq in range(1, e)`（共 256*256 = 65536 組）：
   - `T = e*leak - 2 + kp + kq`
   - `disc = T*T - 4*kp*kq*N`；若 `disc < 0` 或不是完全平方數就跳過
     （用 `math.isqrt` 檢查 `isqrt(disc)**2 == disc`）
   - `root1 = (T + isqrt(disc)) // 2`；檢查 `root1 % kp == 0` 且 `N % (root1 // kp) == 0`
   - 若成立 → `p = root1 // kp`，`q = N // p`
2. 求 `d = pow(e, -1, (p-1)*(q-1))`，`m = pow(c, d, N)`，
   `long_to_bytes(m)` 就是 flag。
3. 若 65536 組都失敗，把 `root2 = (T - isqrt(disc)) // 2` 也一起試（對稱情況）。

寫在 `challenges/leaky-rsa/solve.py`，直接跑出 flag。

---

## A3. P = NP （misc, beginner，純離線）

檔案：`challenges/p-np/p-equals-np.pdf`

**思路**：題目說「用黑色螢光筆蓋住重要部分」。PDF 的黑色矩形只是蓋在上面的繪圖物件，
底下的文字物件通常還在，直接把文字抽出來就看得到。

**步驟（依序試，成功就停）**：
1. `pdftotext -layout challenges/p-np/p-equals-np.pdf - | grep -i K17`
   （若沒有 `pdftotext`：`pip install pdfminer.six` 後用 `pdf2txt.py`，或 `python -c` 配合 `pypdf`）
2. 若抽不到文字，用 `qpdf --qdf --object-streams=disable` 展開後在 stream 裡找 `K17`。
3. 再不行就 `mutool draw -F txt`，或把 PDF 轉圖片後看是否文字被 outline 成路徑。

flag 格式 `K17{...}`。

---

## A4. close enough （forensics, easy，純離線；flag 前綴是 `SCONES` 不是 K17）

檔案：`challenges/close-enough/out.pkl.part`（376 bytes，**下載到一半被截斷**）、`challenges/close-enough/ekv.py`

**觀察**：
- `EncryptedKV.__setitem__` 把 value 存成 `int.from_bytes(value.encode()) ^ self.secret`。
- pickle 會把 `self.secret` 和 `self.d` 一起序列化，但檔案被截斷，後半段可能不見了。

**步驟**：
1. 先 `xxd challenges/close-enough/out.pkl.part` 完整看一遍 376 bytes，
   把 pickle opcode 手動解析出來（`pickletools.dis` 會在截斷處報錯，
   可以用 `python -c "import pickletools; pickletools.dis(open('out.pkl.part','rb'))"` 看它跑到哪裡才斷）。
2. 目標是從已解析出的部分找出 `secret` 這個大整數，以及 `d` 裡各 key 對應的密文整數。
3. 如果 `secret` 在截斷處之後（拿不到），就用**已知明文**還原：
   挑一個你能猜出明文的 entry（例如 key 名稱暗示的值，或值是可讀 ASCII），
   `secret = ciphertext XOR guessed_plaintext`；再拿這個 secret 去解 flag 那一筆。
4. 若截斷讓 flag 密文本身也只剩前半段：XOR 是逐 byte 的，
   還原出 secret 後仍可解出已到手的那幾個 byte，剩下的用 `SCONES{...}` 格式與常識補。
5. 把過程寫進 `challenges/close-enough/SOLUTION.md`。

**注意**：這題 flag 前綴是 `SCONES{`，不是 `K17{`。
