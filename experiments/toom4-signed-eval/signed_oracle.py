"""Independent integer answers for signed evaluations and modular negation."""
from collections import Counter
from itertools import product
import random

B=1<<64;MASK=B-1;SEED=20261111
def words(value,n):return [(value>>(64*i))&MASK for i in range(n)]
def weighted(a0,a1,a2,a3,half):return 8*a0-4*a1+2*a2-a3 if half else a0-a1+a2-a3
def cases():
    rng=random.Random(SEED);rows=[]
    edges=[0,1,(1<<63),MASK-1,MASK]
    for half in [0,1]:
        for carry in range(-5,11):
            for xs in product(edges,repeat=4):
                q,r=divmod(weighted(*xs,half)+carry,B)
                assert -5<=q<=10
                rows.append(('signedlimb4 '+' '.join(map(str,[half,carry+5,*xs])),f'{r} {q+5}'))
    for _ in range(1024):
        half=rng.randrange(2);carry=rng.randrange(-5,11);xs=[rng.getrandbits(64) for _ in range(4)]
        q,r=divmod(weighted(*xs,half)+carry,B)
        rows.append(('signedlimb4 '+' '.join(map(str,[half,carry+5,*xs])),f'{r} {q+5}'))
    lengths=[0,1,2,3,4,7,8,9,23,24,25,63,64,65,127,128,129,255,256,257,511,512,513,1024,4096]
    for n in lengths:
        cap=(1<<(64*n))-1
        for value in sorted({0,min(1,cap),cap,cap//2,1<<(64*(n-1)) if n else 0,rng.getrandbits(64*n)}):
            rows.append(('negatewords '+' '.join(map(str,words(value,n))), ' '.join(map(str,words((-value)%(cap+1),n)))))
        for h in sorted({0,n//2,max(0,n-1),n}):
            top=(1<<(64*h))-1
            samples=[(0,0,0,0),(cap,0,cap,0),(0,cap,0,top),(cap,cap,cap,top),
                (cap,cap,0,0),(cap//2,2*(cap//2),0,0)]
            if n:
                samples += [(cap//2+1,cap//2,0,0),(cap//2,cap//2+1,0,0)]
            if h:
                samples += [(cap//2,2*(cap//2),0,1),(0,0,1,1)]
            samples += [tuple(rng.getrandbits(64*x) for x in [n,n,n,h]) for _ in range(12)]
            for half in [0,1]:
                for xs in samples:
                    answer=weighted(*xs,half)
                    command='signeddirect4 '+' '.join(map(str,[half,n,h,*words(xs[0],n),*words(xs[1],n),*words(xs[2],n),*words(xs[3],h)]))
                    rows.append((command,' '.join(map(str,[*words(abs(answer),n+1),int(answer<0)]))))
    return rows
def invalid():
    return ['signedlimb4 0 16 0 0 0 0','signedlimb4 2 5 0 0 0 0','signedlimb4 0 5 0 0 0',
        'signeddirect4 2 0 0','signeddirect4 0 0 1 0','signeddirect4 0 1 0 0 0',
        'signeddirect4 0 0 0 1','signeddirect4 1 1 1 0 0 0']
def summary():
    rows=cases()
    return {'seed':SEED,'cases':len(rows),'max_limbs':4096,'by_operation':dict(Counter(c.split()[0] for c,_ in rows)),
        'invalid_commands':len(invalid()),'coverage':'Every incoming carry -5..10; full-u64 extreme/random digits; both weights and signs; exact zero and +/-1; empty/short fourth blocks; long modular-negation carries; untouched tmp/input and output canaries'}
if __name__=='__main__':
    import json
    print(json.dumps(summary(),indent=2))
