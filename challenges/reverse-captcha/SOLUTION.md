# reverse captcha — `K17{y0u_w1ll_noW_b3_sp@red_froM_tHe_AI_rev0lu+1on}`

題目要你在 8 秒內連續答對 10 題「證明你是機器人」的挑戰。但 flag **從頭到尾沒有離開瀏覽器**——
`app.js` 裡的 `printFlag()` 自己就會把它解出來：

```js
function printFlag(){
  if(state !== String.fromCharCode(99,111,109,112,108,101,116,101)   // "complete"
     || !Number.isInteger(numCorrect) || numCorrect < requiredCorrect
     || !(requiredCorrect > 0)) return false;
  const _0x91=[0x25,0x71,0x64,...];
  let _0x42 = 0x35 + state.length * 0x11;
  const _0x17 = new TextDecoder().decode(Uint8Array.from(_0x91,(_0x6a,_0x2b)=>{
      _0x42 = (_0x42*0x21 + _0x2b + 0x11) & 0xff;
      return _0x6a ^ _0x42;
  }));
  ...
}
```

那些檢查全都是**前端狀態**，而且解碼用的 key 只跟 `state.length` 有關
（`state` 固定是 `"complete"`，長度 8 → 種子 `0x35 + 8*0x11 = 0xbd`）。
沒有任何一次 server 請求，所以整段滾動 XOR 可以直接在本機重算：

```bash
python3 challenges/reverse-captcha/solve.py
```

```
K17{y0u_w1ll_noW_b3_sp@red_froM_tHe_AI_rev0lu+1on}
```

（也可以直接在 console 打 `state="complete"; numCorrect=10; printFlag()`。）
