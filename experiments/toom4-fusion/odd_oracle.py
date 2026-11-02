"""Independent integer division oracle; never uses executable answers as specifications."""
from collections import Counter
import random

SEED=20261109
B=1<<64
MASK=B-1
DIVISORS=(3,9,15)
def words(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def text(op,args):return op+' '+' '.join(map(str,args))
def result(args):return ' '.join(map(str,args))

def cases():
    rng=random.Random(SEED);rows=[]
    for d in DIVISORS:
        for carry in range(d):
            xs={0,1,2,MASK,MASK-1,carry,max(0,carry-1),carry+1,d-1,d,d+1}
            xs.update(rng.getrandbits(64) for _ in range(12))
            for x in sorted(xs):
                q=((x-carry)*pow(d,-1,B))%B
                quotient,next_carry=divmod(d*q+carry,B)
                assert next_carry==x and quotient<d
                rows.append((text('oddlimb',[d,carry,x]),result([q,quotient])))
            for q in [0,1,2,MASK,MASK-1,MASK//2,1<<63,*[rng.getrandbits(64) for _ in range(12)]]:
                next_carry,x=divmod(d*q+carry,B)
                rows.append((text('oddlimb',[d,carry,x]),result([q,next_carry])))
    lengths=[0,1,2,3,4,7,8,9,31,32,33,63,64,65,127,128,129,511,512,513,1024,4096]
    general=[1,2,4,8,16,(1<<32)-1,1<<32,(1<<63)-1,1<<63,MASK-1,MASK]
    for n in lengths:
        maximum=(1<<(64*n))-1
        for d in [*DIVISORS,*general]:
            cap=maximum//d
            values=[0,min(1,cap),cap,max(0,cap-1),cap//2,cap//3]
            values += [rng.randrange(cap+1) for _ in range(4)]
            for q in values:
                a=q*d;assert 0<=a<=maximum
                for op in (['exactodd','exactapi'] if d in DIVISORS else ['exactapi']):
                    rows.append((text(op,[d,*words(a,n)]),result(words(a//d,n))))
    return rows

def invalid():
    return ['oddlimb 3 3 0','oddlimb 9 9 0','oddlimb 15 15 0','oddlimb 7 0 0',
            'oddlimb 3 0','exactodd 2 2','exactodd 0','exactodd 3 1','exactodd 9 8',
            'exactodd 15 14','exactapi 0','exactapi 18446744073709551615 1',
            'exactapi 3 18446744073709551614','exactapi']

def summary():
    rows=cases()
    return {'seed':SEED,'cases':len(rows),'by_operation':dict(Counter(x.split()[0] for x,y in rows)),
            'max_limbs':4096,'direct_divisors':list(DIVISORS),'invalid_commands':len(invalid()),
            'coverage':'All allowed incoming carries; x and quotient full-u64 boundaries including MAX; wrapping-borrow cases; empty arrays; exact maximum-capacity quotients; in-place canaries; old API positive full-u64 divisor domain retained'}

if __name__=='__main__':
    import json
    print(json.dumps(summary(),indent=2))
