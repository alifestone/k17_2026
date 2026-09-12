# Handover
task_id: k17-all-challenges
owner: planner=k17-2026-6a (Opus) / executor=dolphin_cyber:tools (session `k17-2026-1d`)
updated_at: 2026-09-12
base_sha: de8a200209387cdab1fb99a6a872ff6b3c1f485f
head_sha: de8a200209387cdab1fb99a6a872ff6b3c1f485f

## Scope
完成 README.md 中 37 題裡尚未解出的 31 題。已解 6 題（sanity-check / discord /
larpfest / macro-hard / huge-binary / ihyh）不重做。

**不做**：不 push 到 remote、不對 CTF 主辦方基礎建設做 DoS 或掃描，
只針對題目指定的 host/port 與題目給的 handout 進行解題。

分工：
- planner（k17-2026-6a）：讀 handout、決定攻擊路線、把可執行步驟寫進 `plans/batch-*.md`，review 結果。
- executor（dolphin_cyber:tools = `k17-2026-1d`）：照 plan 實作 exploit、實際跑、回填 flag、commit、更新本檔。

## Verified evidence
- command: `timeout 8 bash -c 'exec 3<>/dev/tcp/chal.secso.cc/4000'`
  result: `TCP 4000 OK`（chal.secso.cc = 52.190.194.251，remote 題目可連線）
- command: `curl -s -o /dev/null -w "%{http_code}" https://edwalk.unswsecsoc.workers.dev`
  result: `200`（固定 URL 的 web 題可連線）
- command: `ollama launch claude --model dolphin_cyber:tools`（setsid + script pty，
  且必須 `env -u CLAUDE_CODE_CHILD_SESSION`，否則不會註冊進 ListAgents）
  result: dolphin 以 `k17-2026-1d [7aeb10]` 上線
- artifact: `plans/batch-A.md`（4 題完整攻擊步驟）

## Decisions
1. 先做離線 / 固定 URL 的題目，instantiator 題（需要跟使用者要即時 URL、且有時間限制）排到最後。
2. flag 只能來自實際執行輸出。**禁止編造 flag**；沒跑出來就寫「未取得」。
3. 每題產出 `challenges/<slug>/solve.py` + `challenges/<slug>/SOLUTION.md`，並回填 README.md。

## 題目佇列（31 題未解）

### Batch A — 指派中（executor: dolphin）→ 詳見 `plans/batch-A.md`
| slug | cat | 路線 |
|------|-----|------|
| cry-pto | crypto/beginner | GF(2) 線性 MAC，`sign(a^b)=sign(a)^sign(b)` 偽造 |
| leaky-rsa | crypto/easy | leak=dp+dq，暴力 kp,kq<e 解二次式分解 N |
| p-np | misc/beginner | PDF 黑色遮罩下的文字直接 pdftotext 抽出 |
| close-enough | forensics/easy | 截斷 pickle + XOR secret，已知明文還原（前綴 SCONES） |

### Batch B — 待 planner 出 spec（離線 rev / forensics）
etchasketch(rev/easy)、get-fixed-boi(forensics/medium, Terraria .wld)、
monoid(rev/medium, Haskell dump)、srev(rev/hard)、rainier(osint/beginner, 地標辨識)

### Batch C — 待 planner 出 spec（remote nc pwn/misc）
online-roulette(4000, 已有分析筆記)、big-win(4001)、huge-binary-easy(4002)、
notjson(4003)、make-a-wish(4004)、waf(4006)、archive-trap(3000)、blowfish(2001, 前綴 SCONES)

### Batch D — 待 planner 出 spec（固定 URL web/rev）
edwalk、polynomial-eval、reverse-captcha、evilgram

### Batch E — 需要使用者提供 instantiator 實例 URL（有時間限制，最後做）
driveone、duplex、whatsnew、cryjail、prime-calc、spot、sudobutgood、java-notes

### 其他
sss(crypto/medium) 需要 LLL lattice，planner 另外出 spec；
verify-you-are-human 的 handout 在 Google Drive，需要先下載。

## Open questions
1. Batch E 的 8 題要在 instantiator 開實例，需要使用者提供各題的即時 URL。
2. `verify-you-are-human` 的 Google Drive handout 尚未下載，需確認是否可存取。
3. discord / larpfest / macro-hard 三題雖已解但 flag 未記錄在 repo，要不要補回？

## Next action
executor（dolphin）：依 `plans/batch-A.md` 順序完成 A1→A4，
每題跑出 flag 後 commit 並更新本檔 head_sha 與 Verified evidence。

## Permission required
- 任何 `git push` / 建 PR。
- 對非題目指定 host 的網路存取。

## Acceptance
pending
