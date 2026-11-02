"""Independent integer products and convolution-supplied coefficient buffers."""
import random
B=1<<64;MASK=B-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8a55261102);rows=[];counts={'general':0,'monomial':0}
    def add(k,a,b,padded,category):
        n=len(a);aa=[integer(a[j*k:min((j+1)*k,n)]) for j in range(8)];bb=[integer(b[j*k:min((j+1)*k,n)]) for j in range(8)]
        c=[sum(aa[i]*bb[d-i] for i in range(8) if 0<=d-i<8) for d in range(15)]
        coeffs='|'.join(encode(digits(v,2*(k+1) if padded else (v.bit_length()+63)//64)) for v in c)
        cmd=f'recompose|{k}|{encode(a)}|{encode(b)}|{coeffs}|{rng.choice([0,1,17])}'
        expected=' '.join(map(str,digits(integer(a)*integer(b),2*n)))
        rows.append((cmd,expected));counts[category]+=1
    for k in [0,1,2,3,7,8,23,24,25,63,64,65,127,128,129]:
        for h in sorted({0,k//2,k}):
            n=7*k+h
            arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([MASK if (i//max(k,1))%2 else 0 for i in range(n)],[0 if (i//max(k,1))%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
            for a,b in arrays:
                for padded in [False,True]:add(k,a,b,padded,'general')
    for k in [1,2]:
        for i in range(8):
            for j in range(8):
                a=[0]*(8*k);b=[0]*(8*k);a[i*k]=MASK;b[j*k]=MASK
                add(k,a,b,bool((i+j)%2),'monomial')
    return rows,counts
def invalid():
    good='recompose|0|-|-|'+'|'.join(['-']*15)+'|0'
    return ['',good.replace('recompose','unknown',1),good.replace('|0|','|-1|',1),good.replace('|0|-|-|','|0|1|-|',1),
        good.replace('|0|-|-|','|0|1|1|',1),good.replace('|0|-|-|','|1|1|1|',1),
        good[:-1]+'65',good+'|extra',good.replace('|-|-|','|18446744073709551616|-|',1),
        good.replace('|-|-|','|-1|-|',1),'|'.join(good.split('|')[:-1]),good.replace('|-|-|','|x|-|',1)]
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
