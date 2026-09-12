# Instantiator 操作情報（planner 實測，2026-09-12）

主頁：https://instantiator.secso.cc/ —— 走 noCTF OAuth，**curl 無法直接用**
（session cookie 是 httponly，要靠已登入的 Chrome）。
planner 透過 claude-in-chrome 的 `javascript_tool` 在該頁面 context 內 `fetch(..., {credentials:'include'})` 操作。

## API（相對於 https://instantiator.secso.cc）

| 動作 | 方法 | 路徑 |
|------|------|------|
| 列出全部題目 / 實例 | `GET` | `/challenges` |
| 開實例 | `POST` | `/challenges/<slug>/create`，body `{}` |
| 續命 | `PUT` | `/containers/<id>/extend` |
| 停止 | `DELETE` | `/containers/<id>`（推測，尚未實測） |

`GET /challenges` 回傳陣列，欄位：
`slug, status(running|stopped), id(uuid), endpoint, display, password, meta, expires(unix ts), kind, params`

## 實測到的兩條硬限制

1. **同時最多 3 個實例**。第 4 個會回 `409 {"message":"Your team already has 3 instance(s) running; stop one first."}`
2. **每個實例壽命 15 分鐘**（`expires - now` 上限約 902 秒）。
   `PUT /extend` 會把剩餘時間**重設回 15 分鐘**，可以重複呼叫，沒有次數上限
   → 只要每 10 分鐘 extend 一次就能無限續命。

**結論：真正稀缺的資源是「3 個並行槽位」，不是時間。**
所以正確做法是：**先把 handout 離線分析完、exploit 寫好，再開實例去打**，
不要先開著實例再慢慢想。打完一題就 stop 讓出槽位。

## 可開的 9 個 slug
prime-calc, duplex, macro-hard(已解), cryjail, java-notes, sudo-but-good, spot, driveone, whatsnew

注意 slug 對應：instantiator 的 `sudo-but-good` = README 的 `sudobutgood`。

## 目前佔用的 3 個槽位（planner 會持續 extend 保活）
- prime-calc → https://8000-53ffad35d6f34d35b2301a17375311c5.sbx.secso.cc
- duplex     → http://vm2.secso.cc:20099
- cryjail    → nc vm1.secso.cc 20239   password: `lO_zVP3D315W`

實例 endpoint 每次重開都會變，**exploit 腳本請把 host/port 寫成參數或環境變數，不要寫死**。
