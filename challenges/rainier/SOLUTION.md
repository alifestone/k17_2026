# rainier — `K17{Victoria,Middle}`

一張大雨中的路口照片，要找出交叉的兩條路名（去掉 St / Rd 之類的後綴）。

把照片幾個區域裁切放大後，可讀出四條線索：

1. **`Victoria St`** —— 對街號誌桿上的綠色路牌，直接給了第一條路。
2. **`NORTH BRIDGE CENTRE`** —— 遠處左方大樓的立面字。
   查 OneMap：`lat=1.297216, lng=103.8549446`，JLL 的網址路徑甚至直接寫
   `north-bridge-rd-middle-rd` → 它在 North Bridge Road × **Middle Road** 口。
3. **藍底白字的 `Nationa…` 橫幅** —— 對應 111 Middle Road 的 **National Design Centre**
   （資料明確寫它「occupies a strategic location visible from Victoria Street」）。
4. **建築本體** —— 弧形外牆、一整排圓柱、斜置的金屬遮陽箱體，是
   **National Library Building（100 Victoria Street）**，它的四面正好是
   Victoria St / North Bridge Rd / **Middle Rd** / Bain St。

外加左上角的 `MRT 320m` 指標（Bugis 站距此約 300 多公尺）與整片紅色施工圍籬，
全部指向同一個路口。

所以是 **Victoria Street × Middle Road**：

```
K17{Victoria,Middle}
```

（題目說大小寫與順序都不拘。）
