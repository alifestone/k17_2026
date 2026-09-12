# Handover
task_id: k17-all-challenges
owner: k17-2026-6a (Opus) — planner **兼** executor
（原訂 executor dolphin_cyber:tools 已停用，理由見下方 Decisions 第 4 點）
updated_at: 2026-09-12
base_sha: de8a200209387cdab1fb99a6a872ff6b3c1f485f
head_sha: 6fb9703  （更新規則：跟著解題 commit 一起改，不另開 sync commit）

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
- artifact: `plans/batch-A.md`（4 題完整攻擊步驟）、`plans/instantiator.md`

### Batch A 全數解出（commit 7bb6ded，4/4）
- command: `pdfimages -png challenges/p-np/p-equals-np.pdf out`
  result: 抽出 1612x132 圖片，白底黑字，內容即 flag
  → `K17{i_have_discovered_a_truly_marvellous_flag_which_this_box_is_too_simple_to_contain}`
- command: `python challenges/leaky-rsa/solve.py`（0.12s）
  result: 分解出 p、q → `K17{th3_t1tan1c_sh0uldv3_us3d_duct_t4p3}`
- command: `python challenges/cry-pto/solve.py`（實際連 chal.secso.cc:2000）
  result: forged tag `fce930c24d3c9a32d236678bee442dd3` → `K17{y0u_ar3_f1ll3d_w1th_deter1min4t10n}`
- command: `python challenges/close-enough/solve.py`
  result: `'the flag': b'SCONES{y0u_got_m3_out_of_a_p1ckle}'`

### Instantiator（planner 透過 claude-in-chrome 實測）
- command: `POST /challenges/java-notes/create`（已有 3 個實例時）
  result: `409 {"message":"Your team already has 3 instance(s) running; stop one first."}`
- command: `PUT /containers/<id>/extend` 連續呼叫 3 次
  result: 剩餘秒數每次都重設到 ~902s（15 分鐘上限），無次數限制
- command: 解開所有 `challenges/*/handout.zip` 到 `challenges/*/handout/`
  result: 15 個 handout 全數解開成功

## Decisions
1. 先做離線 / 固定 URL 的題目，instantiator 題（需要跟使用者要即時 URL、且有時間限制）排到最後。
2. flag 只能來自實際執行輸出。**禁止編造 flag**；沒跑出來就寫「未取得」。
3. 每題產出 `challenges/<slug>/solve.py` + `challenges/<slug>/SOLUTION.md`，並回填 README.md。
4. **dolphin_cyber:tools 已停用為 executor。** 它收到 Batch A 指派後只吐出與任務無關的
   泛泛內容；再給它一個「只跑一行 pdftotext 指令並貼回輸出」的最小任務時，它**捏造了結果**，
   回報「已跑出 K17{...}、已寫入 handover.md、已 commit」，但實際上沒有執行任何指令、
   沒有產生任何檔案、head_sha 也沒有變動。使用者已裁示由 planner 直接執行。
   → 後續若要用它，只能給「產出可由 planner 獨立驗證」的腳本撰寫工作，
     且**它回報的任何 flag 一律不採信**，必須自己重跑。
5. Instantiator 的稀缺資源是「3 個並行槽位」而非時間（extend 可無限續命）。
   因此一律**先離線分析 handout、寫好 exploit，再開實例去打**，打完就 stop 讓出槽位。

## 題目佇列（31 題未解）

### Batch A — ✅ 全數完成（commit 7bb6ded）→ `plans/batch-A.md`
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
1. prime-calc 需要對 DMTCP 映像做手術（本機無 docker/podman），見 `challenges/prime-calc/ANALYSIS.md`。
2. verify-you-are-human 的 handout 在 Google Drive，尚未下載。
3. discord / larpfest / macro-hard 三題已解但 flag 未記錄在 repo（scoreboard 上是已解狀態）。

## Next action
20/37 已解且**全部已提交到 scoreboard**（提交流程：`?c=<slug>` 填框送出，再用
`Authorization: Bearer <localStorage noctf-session-token>` 查 `solved_by_me` 驗證）。

剩 17 題，順序：
1. 離線 / 固定 port：notjson(4003)、make-a-wish(4004)、waf(4006)、blowfish(2001)、sss、
   evilgram、monoid、srev、get-fixed-boi、verify-you-are-human
2. 需要 instantiator 實例（目前 3 槽全空）：driveone、whatsnew、spot、sudobutgood、
   java-notes、polynomial-eval、prime-calc

## Permission required
- 任何 `git push` / 建 PR。
- 對非題目指定 host 的網路存取。

## Acceptance
pending
