# ihyh — solve notes

Flag: `K17{50pp1n355_0f_l0v3_f1nd1ng_1t5_way_1n_f1l35!}`
Remote: `nc chal.secso.cc 4007`  (glibc 2.35-0ubuntu3.11, Ubuntu 22.04; Full RELRO + Canary + NX + PIE)

## Bug
`view_history` does `fclose(fp)` but never nulls the global `fp` → dangling `FILE*`.
`fopen("/tmp/log.txt","a+")` mallocs a `locked_FILE` (chunk 0x1e0, usable 0x1d8); fclose frees it to
tcache[0x1e0]. Every later note of size 0x1c9..0x1d8 reclaims that exact chunk, and `edit`/`view_history`
still operate on `fp` (== the reclaimed note).

`create`: `memset(buf,0,size)` for size>16 then `read(0,buf,size)` then NUL first '\n'. So a size-0x1d0
note leaves bytes [0x1d0,0x1d8) of the freed FILE intact.

## Exploit (single connection)
1. **libc leak** — view_history() frees the FILE; create(0x1d0, 'B'*0x1d0) reclaims it; view() prints the
   residual tail = `_IO_wide_data->_wide_vtable` = `_IO_wfile_jumps`. `libc = leak - 0x2170c0`.
2. **heap leak** — delete the note, re-create it (size 0x1d0) as a *write-mode FILE to fd 1* whose buffer
   is full at `&main_arena.top`, with `_IO_IS_APPENDING` set (and read_end==write_base) so `new_do_write`
   skips the lseek that fails ESPIPE on a socket. `edit()`'s `fwrite`→`_IO_file_overflow`→`_IO_do_write`
   does `write(1, &main_arena.top, 8)` → leaks the heap. `fp(=A) = leaked_top - 0x1d0` (A's chunk sits
   immediately before top). The SAME edit's `read()` then writes the House-of-Apple FILE into A.
3. **RCE — House of Apple 2** — vtable=`_IO_wfile_jumps`, `_wide_data`→in-chunk fake with write_base=0,
   buf_base=0, `_wide_vtable`→in-chunk table whose `__doallocate`(+0x68)=`system`; FILE starts "  /bin/sh".
   A final `edit()` → `fwrite`→`_IO_wfile_xsputn`→`_IO_wfile_overflow`→`_IO_wdoallocbuf`→
   `_wide_vtable->__doallocate(fp)` = `system("  /bin/sh")`.

Offsets (glibc 2.35-0ubuntu3.11, buildid 4f7b0c95…): system=0x50d70, /bin/sh=0x1d8678,
_IO_wfile_jumps=0x2170c0, _IO_file_jumps=0x217600, main_arena=0x21ac80 (top +0x60), a rw zero qword @0x21a1d0.

Newlines: create/edit NUL the first '\n'; each payload plants a 0x0a at a harmless early offset so all
address bytes with 0x0a survive.

Run: `python3 solve.py remote`  (needs pwntools; `solve.py local`/`aslr` test the patched local binary).
