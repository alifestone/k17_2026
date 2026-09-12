# 通用版：Cross-Session Handover 協定

用途：當你的專案裡混合了「能力有限、不會主動呼叫跨 session 工具的本地模型
session（例如透過 Ollama 跑的 fine-tune）」跟「一般正常的 Claude session」，
兩者要協作同一份工作，又不想每次重新設計一套溝通方式時，把這份文件複製
到新專案，填掉 `<...>` 佔位符即可直接用。

原始設計依據：https://www.alphalab.site/claude-code-cross-session-messaging
（兩層架構：SendMessage 即時訊號 + handover.md 持久狀態）

---

## 0. 先填這幾個佔位符

| 佔位符 | 說明 | 範例 |
|---|---|---|
| `<WEAK_SESSION_NAME>` | 能力有限、無法主動呼叫工具的 session 名稱（`ListAgents` 顯示的名字） | `dolphin_cyber:tools` |
| `<STRONG_SESSION_NAME>` | 負責 review／整合、能可靠呼叫工具的 session 名稱 | `k17-2026-6a` |
| `<REPO_PATH>` | 兩邊都能存取的共享 repo 路徑 | `~/k17_2026` |
| `<LAUNCH_CMD>` | 用來非互動啟動 `<WEAK_SESSION_NAME>` 的完整指令 | `ollama launch claude --model dolphin_cyber:tools` |
| `<POLL_INTERVAL>` | `<STRONG_SESSION_NAME>` 自我檢查 handover.md 的頻率 | `3 分鐘` |

---

## 1. 為什麼要這樣設計（判斷是否適用）

適用前提：`<WEAK_SESSION_NAME>` 這個 session **收得到**其他 session 傳來的訊息
（純文字進入對話，不需要它呼叫任何工具），但**發不出去**——不是格式錯誤，
是它從沒被訓練過這個 harness 專屬的跨 session 工具呼叫 schema，所以不會主動
決定呼叫。這是模型能力上限，不是設定問題，硬要它學會不划算。

對策：把 `<WEAK_SESSION_NAME>` 的職責限縮到牠擅長的事——用一般檔案編輯動作
寫檔案（Edit/Write 是任何 coding 導向模型都大量見過的樣式，遠比一個客製化的
`SendMessage(to, message)` schema 常見）。真正「發送訊號」的動作，交給
`<STRONG_SESSION_NAME>` 自己主動去讀檔案確認，而不是等對方通知。

---

## 2. 兩層協定

### 第一層：SendMessage 訊號（僅限有能力可靠呼叫工具的 session 使用）

格式：

```
[SYNC run=<task_id> round=<n>/<max_round>]
head_sha=<完整 commit SHA>
need=<具體問題，一句話>
reply=<回覆限制，例如「只能回 PASS，或 BLOCKED 加最多三點」>
limits=<邊界，例如「200 字內；不要 push/merge/deploy」>
```

規則：
- 每個 task 最多 2 輪往返（round 1/2, round 2/2）。超過就停止、交還使用者判斷。
- 短時間內內容完全相同的訊息會被丟棄，發送前先比對 `head_sha` 是否真的變了。
- 只有 `<STRONG_SESSION_NAME>` 這類能可靠呼叫工具的 session 會用到這一層；
  `<WEAK_SESSION_NAME>` 完全不需要知道這個機制存在。

### 第二層：handover.md 狀態（`<WEAK_SESSION_NAME>` 的唯一溝通管道）

檔案位置：`<REPO_PATH>/handover.md`（進版控，跨 session 靠 `git pull` 同步）。

```markdown
# Handover
task_id:
owner:
updated_at:
base_sha:
head_sha:

## Scope
要完成什麼，以及明確不做什麼。

## Verified evidence
- command:
- result:
- artifact / diff:

## Decisions
已定案內容與理由。

## Open questions
尚未確認、不可自行假設的事項。

## Next action
下一個可驗證動作。

## Permission required
仍須使用者或 reviewer 明確批准的操作。

## Acceptance
pending | accepted by <human/reviewer> at <head_sha>
```

規則：
- 單一 owner 負責一個 task，避免多人同時改同一段（要多人 append 就改成
  「每段加 author + timestamp + SHA」的 append-only 寫法）。
- `Verified evidence` 只能寫真的執行過、看到結果的東西，不能寫「應該可以」。
- 每次完成一個可驗證的小階段就更新，尤其是 `head_sha`、`Verified evidence`、
  `Next action`。
- 沒人把 `Acceptance` 簽成 `accepted by <human/reviewer> at <head_sha>` 之前，
  一律視為未完成。

---

## 3. 貼進專案 `CLAUDE.md` 的通用片段

直接複製下面整段（先替換佔位符）到專案的 `CLAUDE.md` 尾端：

```markdown
# Cross-Session 協作協定

這個 repo 可能同時被多個 Claude session 協作，包括 <WEAK_SESSION_NAME>（能收到
跨 session 訊息，但無法主動呼叫 SendMessage 這類工具呼叫）。

## 兩層規則

1. **handover.md（狀態層，永久存在）**：任何 session 要回報進度、交接工作，
   一律更新 repo 根目錄的 `handover.md`（欄位：task_id / owner / updated_at /
   base_sha / head_sha / Scope / Verified evidence / Decisions / Open questions /
   Next action / Permission required / Acceptance）。`Verified evidence` 只能
   寫真的執行過並看到結果的東西，不能寫「應該可以」。每次有實質進展就 commit，
   `head_sha` 更新成當下的 commit SHA。單一 owner 負責寫一個 task。

2. **SendMessage（訊號層，僅限有能力可靠呼叫工具的 session）**：如果你的模型
   能可靠呼叫跨 session 工具，在 handover.md 出現重大變化時，主動用 SendMessage
   通知相關 session，格式：

   ```
   [SYNC run=<task_id> round=<n>/2]
   head_sha=<完整 commit SHA>
   need=<具體問題，一句話>
   reply=只能回 PASS，或 BLOCKED 加最多三點
   limits=200 字內；不要 push、merge 或 deploy
   ```

   每個 task 最多 2 輪往返，超過就停下來交還使用者判斷。相同內容短時間內不要重發。

3. **<WEAK_SESSION_NAME> 專屬規則**：這個 session 不會主動呼叫 SendMessage
   （模型能力限制，不是設定問題）。它只透過更新 handover.md 溝通，其他 session
   不要等它主動發訊號，而是自己定期讀 handover.md 的 head_sha 有沒有變化。
   建議 <STRONG_SESSION_NAME> 用 `/loop` 自我排程，每隔 <POLL_INTERVAL> 檢查一次
   `handover.md`，而不是被動等通知。

4. 任務完成的認定只看 handover.md 的 `Acceptance` 欄位是否被寫成
   `accepted by <human/reviewer> at <head_sha>`——沒人簽收之前一律視為未完成。

## 自動啟動 <WEAK_SESSION_NAME>（給有 shell 權限的 session）

如果你需要 <WEAK_SESSION_NAME> 協助，但 `ListAgents` 裡沒看到它在線上，不要等
使用者手動開，自己用背景執行的方式啟動它：

```bash
nohup <LAUNCH_CMD> >/tmp/<weak_session_slug>_launch.log 2>&1 &
```

啟動後給它幾秒鐘完成初始化，再重新呼叫 `ListAgents` 確認它已出現在名單裡，
然後才透過 handover.md／SendMessage 跟它交接工作。

注意事項：
- 不要重複啟動：先檢查 `ListAgents`，已經在線就不要再開一個新的。
- 用完不需要主動關閉，除非使用者要求。
- 背景啟動後多次確認仍未出現在 `ListAgents`，停止重試並回報使用者。
```

---

## 4. 貼給 `<WEAK_SESSION_NAME>` 本身的 SYSTEM prompt 片段

如果 `<WEAK_SESSION_NAME>` 是自己控制 Modelfile / system prompt 的本地模型，
把下面這段加進它的 SYSTEM prompt（教它別去嘗試呼叫工具，只靠寫檔案溝通）：

```
## Cross-Session Collaboration Protocol

You may be working alongside other sessions on a shared repository. A
cross-session messaging tool (e.g. SendMessage) may appear in your available
tools. Regardless of that:

* Never attempt to call a cross-session messaging tool yourself, even if it
  seems like the obviously correct next step. A separate process/session
  handles notifying others on your behalf — that is not your job.
* Your entire cross-session communication channel is a single file:
  `./handover.md` in the repository root. You communicate by editing this
  file with your normal file-editing ability, not by calling a messaging tool.
* Always fill in handover.md completely — never leave head_sha or Verified
  evidence blank when you update it.
* Verified evidence may only contain things you actually ran and actually
  observed the result of. Never write "should work" instead of a real
  verification.
* Anything you're not sure you're authorized to do goes in
  "Permission required" — do not assume permission and proceed.
* The task is not done until Acceptance is explicitly set by someone else.
  Do not mark it accepted yourself.
* You have at most 2 rounds of back-and-forth on any given task before you
  must stop and leave it for a human — record that in Open questions.
```

---

## 5. 貼給 `<STRONG_SESSION_NAME>` 的 `/loop` prompt

在 `<STRONG_SESSION_NAME>` 那個 session 裡直接下：

```
/loop 每隔 <POLL_INTERVAL> 檢查一次 <REPO_PATH>/handover.md 的 head_sha
有沒有變化，有變化就讀 Next action 跟 Open questions，用一兩句話跟我說
<WEAK_SESSION_NAME> 進度到哪，不用等我開口問；如果 ListAgents 裡沒看到
<WEAK_SESSION_NAME> 但工作需要它，就照 CLAUDE.md 裡的自動啟動規則自己
背景開起來；round 數超過 2 或卡住太久就明講要我自己介入。
```

---

## 6. 一次性建置步驟（新專案照抄）

```bash
cd <REPO_PATH>
cat > handover.md << 'EOF'
# Handover
task_id:
owner:
updated_at:
base_sha:
head_sha:

## Scope

## Verified evidence
- command:
- result:
- artifact / diff:

## Decisions

## Open questions

## Next action

## Permission required

## Acceptance
pending | accepted by <human/reviewer> at <head_sha>
EOF

echo ".relay_state.json" >> .gitignore
git add handover.md .gitignore
git commit -m "chore: add handover.md for cross-session protocol"
```

接著把第 3 節的整段貼進 `CLAUDE.md`、第 4 節貼進弱模型的 SYSTEM prompt、
第 5 節貼給強 session 當 `/loop` 指令即可。
