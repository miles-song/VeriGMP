"""Independent integer cases for fused scaled subtraction."""
import random
SEED=20261106
MASK=(1<<64)-1

def words(value,n):return [(value>>(64*i))&MASK for i in range(n)]

def cases():
    rng=random.Random(SEED);rows=[]
    small=[*range(17),23,24,25,31,32,33,63,64,65,127,128,129,255,256,257]
    for n in small+[511,512,513,1024,2048,4096]:
        limit=(1<<(64*n))-1
        for m in sorted({0,min(1,n),max(0,n-1),n}):
            for word in ([0,1,2,16,1<<63,MASK] if n<=257 else [2,16,MASK]):
                maximum=min((1<<(64*m))-1,limit//word if word else limit)
                values=[0,min(1,maximum),maximum,rng.randrange(maximum+1)]
                for rhs in values:
                    product=word*rhs
                    destinations=[product,limit]
                    if n<=257:destinations.append(product+rng.randrange(limit-product+1))
                    for old in destinations:
                        args=[word,n,m,*words(old,n),*words(rhs,m)]
                        rows.append(('subscaled '+' '.join(map(str,args)), ' '.join(map(str,words(old-product,n)))))
    return rows
