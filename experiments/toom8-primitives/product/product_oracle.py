"""Independent unbounded products for actual input-to-output composition."""
import random
B=1<<64;MASK=B-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8f00261102);rows=[];counts={'balanced':0,'full':0,'shared_immutable_inputs':0}
    def add(mode,parameter,child,a,b,alias):
        expected=' '.join(map(str,digits(integer(a)*integer(b),2*len(a))))
        counts[mode]+=1
        if alias:mode+='-alias';counts['shared_immutable_inputs']+=1
        rows.append((f'{mode}|{parameter}|{child}|{encode(a)}|{encode(b)}|{rng.choice([0,1,17])}',expected))
    for k in [0,1,2,3,7,8,23,24,25,63,64,65,127,128,129]:
        for h in sorted({0,k//2,k}):
            n=7*k+h
            arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([MASK if (i//max(k,1))%2 else 0 for i in range(n)],[0 if (i//max(k,1))%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
            for index,(a,b) in enumerate(arrays):
                for child in [24,48]:add('balanced',k,child,a,b,index<2)
    for n in [1,23,24,25,55,56,57,63,64,65,95,96,97,127,128,129,255,256,257,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096]:
        arrays=[([MASK]*n,[MASK]*n),([MASK if i%2 else 0 for i in range(n)],[0 if i%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
        for index,(a,b) in enumerate(arrays):
            for threshold,child in [(56,24),(56,48),(96,24),(96,48)]:add('full',threshold,child,a,b,index==0)
    return rows,counts
def invalid():
    return ['', 'unknown|0|24|-|-|0','balanced|0|23|-|-|0','balanced|-1|24|-|-|0',
        'balanced|0|24|1|-|0','balanced|0|24|1|1|0','balanced|1|24|1|1|0',
        'balanced|0|24|-|-|65','balanced|0|24|-|-|0|extra','balanced|0|24|18446744073709551616|-|0',
        'full|56|24|-|-|0','full|55|24|1|1|0','full|56|23|1|1|0','full-alias|56|24|1|2|0']
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
