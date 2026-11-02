"""Independent Python integer oracle for arbitrary odd u64 divisors."""
import random
B=1<<64
FAMILY=(3,15,63,255,1023,4095)
def words(value,n):
    assert 0<=value<B**n
    return [(value>>(64*i))&(B-1) for i in range(n)]
def cases():
    rng=random.Random(0x8D1A1DE)
    divisors=sorted(set([1,*FAMILY,9,5,7,11,13,17,31,127,65535,2**31-1,2**32-1,2**32+1,2**63-1,2**63+1,B-3,B-1]+[rng.getrandbits(64)|1 for _ in range(64)]))
    rows=[];counts={'limb':0,'exact':0,'family':0,'inverse':0}
    def add(op,args,out):
        rows.append((op+' '+' '.join(map(str,args)),out));counts[op]+=1
    for d in divisors:
        inv=pow(d,-1,B)
        carry_values=sorted(set([0,d-1,d//2]+[rng.randrange(d) for _ in range(9)]))
        for carry in carry_values:
            xs=sorted(set([0,1,B-2,B-1,carry,(carry-1)%B,(carry+1)%B,B//2]+[rng.getrandbits(64) for _ in range(9)]))
            for x in xs:
                q=((x-carry)*inv)%B
                total=d*q+carry
                assert total%B==x and 0<=total//B<d
                add('limb',[d,inv,carry,x],[q,total//B])
        for n in [0,1,2,3,4,7,8,15,16,31,32,64]:
            max_q=(B**n-1)//d
            qs=sorted(set([0,max_q,max_q//2]+([1] if max_q else [])+[rng.randrange(max_q+1) for _ in range(8)]))
            for q in qs:
                a=d*q;add('exact',[d,inv,n,*words(a,n)],words(q,n))
                if d in FAMILY:add('family',[d,n,*words(a,n)],words(q,n))
        if d in FAMILY:add('inverse',[d],[inv])
    return rows,counts
def invalid():
    return [
        'limb 0 0 0 0','limb 2 1 0 0','limb 3 1 0 0',
        'limb 3 12297829382473034411 3 0','limb 3 12297829382473034411 0',
        'exact 0 0 0','exact 2 1 0','exact 3 1 0',
        'exact 3 12297829382473034411 1 1','exact 3 12297829382473034411 2 0',
        'family 9 0','family 3 1 1','family 4095 1 1','family 3 2 0',
        'inverse 1','inverse 4097','unknown 0']
