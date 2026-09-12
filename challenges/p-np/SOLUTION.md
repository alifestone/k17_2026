# P = NP — `K17{i_have_discovered_a_truly_marvellous_flag_which_this_box_is_too_simple_to_contain}`

題目說「不小心用黑色螢光筆蓋住重要部分」。`pdftotext` 抽出來的頁面在該處只顯示
`this part of the proof is too dangerous to be shown`——那是**蓋在上面的替代文字**，
不是被藏起來的內容，所以純粹抽文字是拿不到 flag 的。

真正的內容是一張圖：

```
$ pdfimages -list challenges/p-np/p-equals-np.pdf
page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
   1     0 image    1612   132  rgb     3   8  image  no        19  0   299   299 22.0K 3.5%
```

把它抽出來後可以看到它根本不是黑條，而是**白底黑字**（顏色分布：255,255,255 佔 194304 px，
0,0,0 只佔 6359 px）——黑色矩形是在 content stream 裡另外畫上去蓋住它的。

```bash
pdfimages -png challenges/p-np/p-equals-np.pdf out   # out-000.png 直接就是明文
```

圖片內容：

```
This proof is left as an exercise to the reader. Hint:
K17{i_have_discovered_a_truly_marvellous_flag_which_this_box_is_too_simple_to_contain}
```

（費馬梗：頁邊空白太窄寫不下。）
