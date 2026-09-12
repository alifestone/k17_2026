package com.k17.javanotes;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.io.Serializable;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public class Main {

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));

        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0);
        server.createContext("/", new IndexHandler());
        server.createContext("/api/export", new ExportHandler());
        server.createContext("/api/save", new SaveHandler());
        server.createContext("/api/restore", new RestoreHandler());
        server.setExecutor(Executors.newFixedThreadPool(8));
        server.start();
        System.out.println("Listening on port " + port);
    }

    public static class Session implements Serializable {
        private static final long serialVersionUID = 1L;
        String username;
        String theme;
        List<String> notes;

        Session(String username, String theme, List<String> notes) {
            this.username = username;
            this.theme = theme;
            this.notes = notes;
        }

        @Override
        public String toString() {
            return "Session{user=" + username + ", theme=" + theme
                    + ", notes=" + (notes == null ? 0 : notes.size()) + "}";
        }
    }

    private static Session demoSession() {
        List<String> notes = new ArrayList<>();
        notes.add("Day 1: Drink java");
        notes.add("Day 2: i wrote my first Hello World Program!  !!");
        notes.add("passing an unparameterised input into a function completely abandons the parameterisation of the output strictly even if the type of the input and output do not depend on a common generic parameter");
        notes.add("only unchecked exceptions can be thrown from lambdas due to the language's lack of ability to declare checked exceptions on lambdas, meaning error handling and stream-based function programming do not mesh well");
        notes.add("for some reason there is no overarching hierarchy for classifying unchecked exceptions; one must know via cult knowledge that such exceptions are necessarily and sufficiently java.lang.RuntimeException or java.lang.Error");
        notes.add("my favourite enterprise-level programming language hogs up 30% of my RAM at baseline, takes 2 minutes to load code and takes 5 minutes to run unit tests, god forbid you perform spying in mockito");
        return new Session("guest", "dark", notes);
    }

    private static String serializeToken(Session s) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ObjectOutputStream oos = new ObjectOutputStream(baos)) {
            oos.writeObject(s);
        }
        return Base64.getEncoder().encodeToString(baos.toByteArray());
    }

    private static String sessionJson(Session s) {
        StringBuilder b = new StringBuilder();
        b.append("{\"username\":\"").append(jsonEscape(s.username))
                .append("\",\"theme\":\"").append(jsonEscape(s.theme))
                .append("\",\"notes\":[");
        if (s.notes != null) {
            for (int i = 0; i < s.notes.size(); i++) {
                if (i > 0) {
                    b.append(',');
                }
                b.append('"').append(jsonEscape(String.valueOf(s.notes.get(i)))).append('"');
            }
        }
        b.append("]}");
        return b.toString();
    }

    static class IndexHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange ex) throws IOException {
            if (!"GET".equals(ex.getRequestMethod())) {
                send(ex, 405, "text/plain", "method not allowed".getBytes(StandardCharsets.UTF_8));
                return;
            }
            send(ex, 200, "text/html; charset=utf-8", PAGE.getBytes(StandardCharsets.UTF_8));
        }
    }

    static class ExportHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange ex) throws IOException {
            try {
                String token = serializeToken(demoSession());
                send(ex, 200, "application/json",
                        ("{\"token\":\"" + token + "\"}").getBytes(StandardCharsets.UTF_8));
            } catch (Exception e) {
                send(ex, 500, "text/plain", "export failed".getBytes(StandardCharsets.UTF_8));
            }
        }
    }

    static class SaveHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange ex) throws IOException {
            if (!"POST".equals(ex.getRequestMethod())) {
                send(ex, 405, "text/plain", "POST your notes".getBytes(StandardCharsets.UTF_8));
                return;
            }
            Map<String, String> q = parseQuery(ex.getRequestURI().getRawQuery());
            String username = q.getOrDefault("username", "guest");
            String theme = q.getOrDefault("theme", "dark");

            String body = readAll(ex.getRequestBody());
            List<String> notes = new ArrayList<>();
            for (String line : body.split("\n", -1)) {
                if (line.endsWith("\r")) {
                    line = line.substring(0, line.length() - 1);
                }
                if (!line.trim().isEmpty()) {
                    notes.add(line);
                }
            }

            try {
                String token = serializeToken(new Session(username, theme, notes));
                send(ex, 200, "application/json",
                        ("{\"token\":\"" + token + "\"}").getBytes(StandardCharsets.UTF_8));
            } catch (Exception e) {
                send(ex, 500, "text/plain", "save failed".getBytes(StandardCharsets.UTF_8));
            }
        }
    }

    static class RestoreHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange ex) throws IOException {
            if (!"POST".equals(ex.getRequestMethod())) {
                send(ex, 405, "text/plain", "POST a token".getBytes(StandardCharsets.UTF_8));
                return;
            }

            String body = readAll(ex.getRequestBody());
            String token = body;
            if (token.startsWith("token=")) {
                token = java.net.URLDecoder.decode(token.substring("token=".length()),
                        StandardCharsets.UTF_8.name());
            }
            token = token.trim();

            byte[] raw;
            try {
                raw = Base64.getDecoder().decode(token);
            } catch (IllegalArgumentException e) {
                send(ex, 400, "text/plain", "invalid base64 token".getBytes(StandardCharsets.UTF_8));
                return;
            }

            try (ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(raw))) {
                Object obj = ois.readObject(); // <-- the bug
                if (obj instanceof Session) {
                    send(ex, 200, "application/json",
                            sessionJson((Session) obj).getBytes(StandardCharsets.UTF_8));
                } else {
                    send(ex, 400, "text/plain",
                            "that token is not a session".getBytes(StandardCharsets.UTF_8));
                }
            } catch (Exception e) {
                send(ex, 400, "text/plain",
                        ("could not restore session: " + e.getClass().getSimpleName())
                                .getBytes(StandardCharsets.UTF_8));
            }
        }
    }

    private static Map<String, String> parseQuery(String q) {
        Map<String, String> m = new HashMap<>();
        if (q == null || q.isEmpty()) {
            return m;
        }
        for (String pair : q.split("&")) {
            int i = pair.indexOf('=');
            if (i < 0) {
                continue;
            }
            try {
                String k = java.net.URLDecoder.decode(pair.substring(0, i), "UTF-8");
                String v = java.net.URLDecoder.decode(pair.substring(i + 1), "UTF-8");
                m.put(k, v);
            } catch (Exception ignored) {
                // skip malformed pair
            }
        }
        return m;
    }

    private static String jsonEscape(String s) {
        if (s == null) {
            return "";
        }
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        b.append(String.format("\\u%04x", (int) c));
                    } else {
                        b.append(c);
                    }
            }
        }
        return b.toString();
    }

    private static String readAll(InputStream in) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) != -1) {
            baos.write(buf, 0, n);
        }
        return new String(baos.toByteArray(), StandardCharsets.UTF_8);
    }

    private static void send(HttpExchange ex, int code, String contentType, byte[] body)
            throws IOException {
        ex.getResponseHeaders().set("Content-Type", contentType);
        ex.sendResponseHeaders(code, body.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(body);
        }
    }

    private static final String PAGE = "<!doctype html>\n"
            + "<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
            + "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            + "<title>Java Notes</title>\n"
            + "<style>\n"
            + ":root{color-scheme:dark}\n"
            + "*{box-sizing:border-box}\n"
            + "body{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"
            + "background:#0e1116;color:#e6edf3}\n"
            + ".wrap{max-width:760px;margin:0 auto;padding:48px 20px}\n"
            + "h3{font-size:22px;margin:0 0 4px}\n"
            + ".tag{color:#7d8590;margin:0 0 32px}\n"
            + ".card{background:#161b22;border:1px solid #30363d;border-radius:12px;"
            + "padding:24px;margin-bottom:20px}\n"
            + "label{display:block;font-size:13px;color:#7d8590;margin-bottom:8px}\n"
            + "input,textarea{width:100%;background:#0d1117;color:#e6edf3;"
            + "border:1px solid #30363d;border-radius:8px;padding:12px;font:inherit}\n"
            + "input{margin-bottom:16px}\n"
            + "textarea{min-height:150px;resize:vertical}\n"
            + "#token{min-height:80px}\n"
            + "button{margin-top:12px;margin-right:8px;background:#238636;color:#fff;border:0;"
            + "border-radius:8px;padding:10px 18px;font:inherit;cursor:pointer}\n"
            + "button.secondary{background:#21262d;border:1px solid #30363d}\n"
            + "pre{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px;"
            + "overflow:auto;white-space:pre-wrap;word-break:break-all;min-height:20px;margin:0}\n"
            + "</style></head><body><div class=\"wrap\">\n"
            + "<h3>&#128221; Java Notes</h3>\n"
            + "<p class=\"tag\">Your notes: for Java&trade;, by Java&trade;. "
            + "Save to get a portable token; restore it anywhere to get your notes back.</p>\n"
            + "<div class=\"card\">\n"
            + "<label>Name</label>\n"
            + "<input id=\"username\" value=\"guest\" placeholder=\"your name\">\n"
            + "<label>Notes (one per line)</label>\n"
            + "<textarea id=\"notes\" placeholder=\"write your notes, one per line...\"></textarea>\n"
            + "<div><button onclick=\"save()\">Save</button>\n"
            + "<button class=\"secondary\" onclick=\"sample()\">Load sample</button></div>\n"
            + "</div>\n"
            + "<div class=\"card\">\n"
            + "<label>Session token</label>\n"
            + "<textarea id=\"token\" placeholder=\"your token appears here after saving; "
            + "paste one and Restore to load it\"></textarea>\n"
            + "<div><button onclick=\"restore()\">Restore</button></div>\n"
            + "</div>\n"
            + "<div class=\"card\"><label>Status</label><pre id=\"out\"></pre></div>\n"
            + "</div>\n"
            + "<script>\n"
            + "function status(m){document.getElementById('out').textContent=m;}\n"
            + "async function save(){\n"
            + " const u=encodeURIComponent(document.getElementById('username').value||'guest');\n"
            + " const notes=document.getElementById('notes').value;\n"
            + " const r=await fetch('/api/save?username='+u+'&theme=dark',{method:'POST',\n"
            + "  headers:{'Content-Type':'text/plain'},body:notes});\n"
            + " const j=await r.json();\n"
            + " document.getElementById('token').value=j.token;\n"
            + " status('Saved. Your token was regenerated - copy it to sync another device.');\n"
            + "}\n"
            + "async function restore(){\n"
            + " const t=document.getElementById('token').value.trim();\n"
            + " const r=await fetch('/api/restore',{method:'POST',\n"
            + "  headers:{'Content-Type':'text/plain'},body:t});\n"
            + " const txt=await r.text();\n"
            + " try{\n"
            + "  const j=JSON.parse(txt);\n"
            + "  document.getElementById('username').value=j.username||'';\n"
            + "  document.getElementById('notes').value=(j.notes||[]).join('\\n');\n"
            + "  status('Restored '+((j.notes||[]).length)+' note(s) for '+(j.username||'?')+'.');\n"
            + " }catch(e){ status(txt); }\n"
            + "}\n"
            + "async function sample(){\n"
            + " const r=await fetch('/api/export');const j=await r.json();\n"
            + " document.getElementById('token').value=j.token;\n"
            + " status('Loaded a sample token. Hit Restore to load its notes.');\n"
            + " restore();\n"
            + "}\n"
            + "</script></body></html>\n";
}
