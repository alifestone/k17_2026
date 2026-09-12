# edwalk — `K17{m3_wh3n_1_v1b3c0de_&^%8}`

> "A cheeky bit of vibe coding never hurt anybody."

站台是一個純前端的假聊天機器人，回覆全是罐頭字串。其中一句就是提示：

```
"Would you like some help pushing your source maps to npm?"
```

側邊欄的假對話紀錄也寫著 `NPM package investigation` / `Help with JavaScript bundles`。

bundle 結尾有：

```js
//# sourceMappingURL=app-DVrlaJt-.js.map
```

而 `/assets/app-DVrlaJt-.js.map` **確實部署上去了**（HTTP 200）。它的 `sourcesContent`
含有完整的 `src/app.js` 原始碼，裡面有一個 **被 tree-shaking 掉、沒進 bundle 的 `getFlag()`**：

```js
/*
 * TODO: will implement when my codex limit refreshes
 */
function getFlag() {
    const _archiveShard = [120, 167, 125, 113, ...];
    ...
}
```

沒有任何地方呼叫它，所以打包後的 JS 裡看不到——只有 source map 留著。

演算法（名字都在誤導）：

- `_reverse` 是 `reduceRight` + `push`，就是把陣列**反轉**
- `_rotateTheWrongWayFirst(b, 3)` 是 8-bit 右旋 3
- `_deriveEphemeralKeyMaterial(i)` 裡的 `lunarPhase` / `entropy` 全都乘上 `& 0`，
  完全沒有貢獻；實際的 key 只有 `((i*73 + 41) ^ ((i % 7) * 19)) & 0xff`
- `checksumThatNobodyChecks` 和 `auditTrail` 正如其名，沒人檢查

```bash
python3 challenges/edwalk/solve.py
```

```
You really shouldn't run random scripts in your console...here's the flag though: K17{m3_wh3n_1_v1b3c0de_&^%8}
```
