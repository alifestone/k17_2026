# prime calc — 分析（尚未解出，暫緩）

## 攻擊面已確認

### 1. `/api/config` 是 `/app/data` 底下的任意檔案寫入

```python
name = timestamp if Path(timestamp).suffix else timestamp + ".json"
destination = (CONFIG_DIR / name).resolve()
if destination != BASE_DIR.resolve() and BASE_DIR.resolve() not in destination.parents:
    return jsonify(error="invalid config path"), 400
destination.parent.mkdir(parents=True, exist_ok=True)
uploaded.save(destination)          # <-- 先寫檔
try:
    values = json.loads(destination.read_text())   # <-- 後驗證
    ...
except ...:
    return jsonify(error="invalid config contents"), 400
```

兩個重點：

- `timestamp` 只要求 `timestamp[0].isdigit()`，可以是 `1/../../checkpoint.dmtcp`；
  `resolve()` 之後是 `/app/data/checkpoint.dmtcp`，而 `/app/data` 確實在它的 `parents` 裡 → 放行。
- **檔案在 JSON 驗證之前就已經落地**。內容不合法只是回 400，檔案已經被覆蓋了
  → 可寫入任意 bytes，不限於 JSON。

寫入範圍被限制在 `/app/data` 子樹（`/app/*.py` 是 root 所有且不在 data 底下，蓋不到）。

### 2. `/api/run` 會對我們控制的檔案做 `dmtcp_restart`

`worker.py cycle()`：

```python
subprocess.Popen(["dmtcp_restart", "--new-coordinator", "--coord-port", COORD_PORT,
                  "--ckptdir", str(work_dir), str(CHECKPOINT_FILE)])
```

`CHECKPOINT_FILE` = `/app/data/checkpoint.dmtcp`，正是上面能覆蓋的路徑。

### 3. 目標

`/flag` 是 `root:prime` `0440`，webapp 跑在 `USER prime` → **任意以 prime 身分執行程式碼即可**。

### 4. `/api/snapshot` 免費給我們一份合法的 checkpoint

```
GET /api/snapshot -> checkpoint.dmtcp (7,070,054 bytes, gzip)
gunzip -> 31,708,656 bytes, header "DMTCP_CHECKPOINT_IMAGE_v4.0"
```

裡面看得到 Python 層的字串（`active-config` ×3、`latest.txt` ×6、`generator.py` ×8、
`is_mersenne` ×2），代表整個行程的可寫記憶體都在映像裡。

## 卡在哪

題目敘述自己警告「this challenge is sensitive to differences between machines,
some payloads that work locally may not work on the remote」——因為 DMTCP 映像綁定
特定的 glibc / python 版本與記憶體佈局。正規做法是用同一份 Dockerfile 在本機重建環境、
checkpoint 一個會讀 `/flag` 的行程、再上傳。

**本機沒有 docker 也沒有 podman**，無法重建 `python:3.13-slim` + DMTCP 4.2.0 的環境。

## 可行的替代路線（未實作）

不要自己產生 checkpoint，而是**直接改遠端給我們的那一份** —— 它本來就來自遠端，
不存在機器差異問題。候選手法：

1. 在 heap 裡找到 `generator.py` 模組迴圈的 code object，改寫 `co_code` bytecode。
2. DMTCP 的 memory area record 帶有 `(addr, size, prot, flags, offset, name)`，
   對 file-backed 區段會在 restart 時 mmap 該檔名。把某個可執行區段的 name 改成
   `/app/data` 底下我們上傳的檔案（該目錄我們可寫）。
3. 映像裡含可寫的 GOT／data 區段，可考慮改函式指標。

需要先把 `DMTCP_CHECKPOINT_IMAGE_v4.0` 的 header 與 area record 結構解析出來。

## 重現用資料

- snapshot 已下載（未進 repo，7MB）：scratchpad `checkpoint.dmtcp` / 解壓後 `ckpt.raw`
- 實例 endpoint 每次重開都會變，需重新從 instantiator 取得
