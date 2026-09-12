This repo is base on a flagship CTF event run by UNSW Security Society. There'll be a wide range of cybersecurity challenges in the categories of Pwn, Web, Crypto, Rev and Misc. Additionally, there will be challenges in the Golf and Beginner categories. The event is designed to be beginner-friendly, but there will be a wide range of challenge difficulties.

All flags will start with K17{ and end with }, unless otherwise specified. e.g. K17{hopefully_funny_message}

Start Time: September 11 @ 10:00AM (UTC)
Duration: 24h

# 題目
各小題資訊請看 README.md

# Other
可以使用 tool list 中的工具
# Cross-Session 協作協定

這個 repo 可能同時被多個 Claude session 協作，包括 dolphin_cyber:tools（本地 Ollama
模型，能收到跨 session 訊息，但無法主動呼叫 SendMessage 這類工具呼叫）。

## 兩層規則

1. **handover.md（狀態層，永久存在）**：任何 session 要回報進度、交接工作，一律更新
   repo 根目錄的 `handover.md`（欄位：task_id / owner / updated_at / base_sha / head_sha /
   Scope / Verified evidence / Decisions / Open questions / Next action /
   Permission required / Acceptance）。`Verified evidence` 只能寫真的執行過並看到結果的
   東西，不能寫「應該可以」。每次有實質進展就 commit，`head_sha` 更新成當下的 commit SHA。
   單一 owner 負責寫一個 task，避免多人同時改同一段。

2. **SendMessage（訊號層，僅限有能力可靠呼叫工具的 session）**：如果你的模型能可靠
   呼叫跨 session 工具，在 handover.md 出現重大變化（新 head_sha、新的 Open questions、
   卡住需要別人 review）時，主動用 SendMessage 通知相關 session，格式：

   ```
   [SYNC run=<task_id> round=<n>/2]
   head_sha=<完整 commit SHA>
   need=<具體問題，一句話>
   reply=只能回 PASS，或 BLOCKED 加最多三點
   limits=200 字內；不要 push、merge 或 deploy
   ```

   每個 task 最多 2 輪往返，超過就停下來交還使用者判斷。相同內容短時間內不要重發。

3. **dolphin_cyber:tools 專屬規則**：這個 session 不會主動呼叫 SendMessage（模型能力
   限制，不是設定問題）。它只透過更新 handover.md 溝通，其他 session 不要等它主動發
   訊號，而是自己定期讀 handover.md 的 head_sha 有沒有變化。建議在需要即時掌握
   dolphin_cyber:tools 進度的 session（例如負責 review 的 Opus session）用 `/loop`
   自我排程，每隔幾分鐘檢查一次 `handover.md`，而不是被動等通知。

4. 任務完成的認定只看 handover.md 的 `Acceptance` 欄位是否被寫成
   `accepted by <human/reviewer> at <head_sha>`——沒人簽收之前一律視為未完成。

## 自動啟動 dolphin_cyber:tools（給有 shell 權限的 session，例如 Opus）

如果你需要 dolphin_cyber:tools 協助（例如需要牠的 cybersecurity 專長分析某個 challenge），
但 `ListAgents` 裡沒看到它在線上，不要等使用者手動開，自己用背景執行的方式啟動它：

```bash
nohup ollama launch claude --model dolphin_cyber:tools >/tmp/dolphin_cyber_launch.log 2>&1 &
```

啟動後給它幾秒鐘完成初始化（它需要載入模型），再重新呼叫 `ListAgents` 確認它已出現在名單裡，
然後才透過 `handover.md`／`SendMessage` 跟它交接工作（實際規則見上面「Cross-Session 協作協定」）。

注意事項：
- 不要重複啟動：先檢查 `ListAgents`，如果 dolphin_cyber:tools 已經在線就不要再開一個新的。
- 這個指令會開一個新的長駐 session，不是一次性任務——用完不需要主動關閉它，讓它留著給後續
  訊息使用即可，除非使用者要求關閉。
- 如果背景啟動後多次確認仍未出現在 `ListAgents`，停止重試並回報使用者，不要無限重複啟動。
