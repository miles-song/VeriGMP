"""Independent Python integer fixtures for the private doubled-cross helper."""
import hashlib,json,random,struct
from pathlib import Path

MAX=(1<<64)-1
SIZES=(0,1,2,3,7,8,9,15,16,17,23,24,25,31,32,33,63,64,65,127,128,129,255,256,257,511,512,513,1024)

def generate(folder):
    folder=Path(folder);folder.mkdir()
    rng=random.Random(0x444f55424c454352);cases=[]
    def add(op,a,b,carry=0):
        n=len(a);x=sum(word<<(64*i) for i,word in enumerate(a))
        y=sum(word<<(64*i) for i,word in enumerate(b));total=x+2*y+carry
        expected=[(total>>(64*i))&MAX for i in range(n)]
        cases.append((op,n,carry,a,b,expected,total>>(64*n)))
    words=(0,1,2,(1<<31)-1,1<<31,(1<<63)-1,1<<63,MAX-1,MAX)
    for a in words:
        for b in words:
            for carry in range(3):add(0,[a],[b],carry)
    for _ in range(192):add(0,[rng.getrandbits(64)],[rng.getrandbits(64)],rng.randrange(3))
    for n in SIZES:
        pairs=[([0]*n,[0]*n),([MAX]*n,[MAX]*n),([0]*n,[MAX]*n),([MAX]*n,[0]*n),
               ([MAX if i%2 else 0 for i in range(n)],[0 if i%2 else MAX for i in range(n)]),
               ([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
        for a,b in pairs:add(1,a,b)
    path=folder/'direct.bin'
    with path.open('wb') as out:
        out.write(b'VGDCR001');out.write(struct.pack('<Q',len(cases)))
        for op,n,carry,a,b,expected,high in cases:
            for word in (op,n,carry,*a,*b,*expected,high):out.write(struct.pack('<Q',word))
    result=dict(cases=len(cases),scalar_cases=sum(row[0]==0 for row in cases),
        array_cases=sum(row[0]==1 for row in cases),sizes=SIZES,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (folder/'direct.json').write_text(json.dumps(result,indent=2)+'\n');return result

def generate_low(folder):
    folder=Path(folder);folder.mkdir()
    rng=random.Random(0x4c4f575351554152)
    sizes=(1,2,7,8,9,23,24,25,63,64,65,95,96,97,127,128,129,191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096)
    rows=[]
    def add(op,a,threshold,limit,split,top):
        n=len(a);value=sum(x<<(64*i) for i,x in enumerate(a));modulus=1<<(64*(n-1)+top)
        expected=(value*value)%modulus
        rows.append((op,n,threshold,limit,split,top,len(rows)%3,a,[(expected>>(64*i))&MAX for i in range(n)]))
    for n in sizes:
        patterns=([0]*n,[MAX]*n,[rng.getrandbits(64) for _ in range(n)])
        for a in patterns:
            for threshold in (24,192):
                for limit in (24,64,128):
                    for split in (0,1,2):add(0,a,threshold,limit,split,64)
            for top in (1,7,17,29,30,53,63,64):add(1,a,192,64,1,top)
    path=folder/'low.bin'
    with path.open('wb') as out:
        out.write(b'VGDLOW01');out.write(struct.pack('<Q',len(rows)))
        for op,n,threshold,limit,split,top,extra,a,expected in rows:
            for value in (op,n,threshold,limit,split,top,extra,*a,*expected):out.write(struct.pack('<Q',value))
    result=dict(cases=len(rows),forced_cases=sum(row[0]==0 for row in rows),default_cases=sum(row[0]==1 for row in rows),
        sizes=sizes,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (folder/'low.json').write_text(json.dumps(result,indent=2)+'\n');return result
