"""Input convolution followed by independent scaled Newton-node polynomials."""
import random
B=1<<64;MASK=B-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8c70261102);rows=[];counts={'fifteen_coefficients':0}
    for k in [0,1,2,3,7,8,23,24,25,63,64,65,127,128,129]:
        for h in sorted({0,k//2,k}):
            n=7*k+h
            arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([MASK if (i//max(k,1))%2 else 0 for i in range(n)],[0 if (i//max(k,1))%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
            for a,b in arrays:
                aa=[integer(a[j*k:min((j+1)*k,n)]) for j in range(8)];bb=[integer(b[j*k:min((j+1)*k,n)]) for j in range(8)]
                c=[sum(aa[i]*bb[d-i] for i in range(8) if 0<=d-i<8) for d in range(15)]
                width=2*(k+1);values=[c[2*j+2] for j in range(6)]+[c[2*j+1] for j in range(7)]
                assert all(0<=v<B**width for v in values)
                expected=' '.join(map(str,digits(c[0],2*k)+[x for v in values for x in digits(v,width)]+digits(c[14],2*h)))
                for threshold in [24,48]:
                    cmd=f'interpolate|{k}|{threshold}|{encode(a)}|{encode(b)}|{rng.choice([0,1,17])}'
                    rows.append((cmd,expected));counts['fifteen_coefficients']+=1
    return rows,counts
def invalid():
    return ['','unknown|0|24|-|-|0','interpolate|0|23|-|-|0','interpolate|-1|24|-|-|0','interpolate|0|-1|-|-|0',
        'interpolate|0|24|1|-|0','interpolate|0|24|1|1|0','interpolate|1|24|1|1|0',
        'interpolate|0|24|-|-|65','interpolate|0|24|-|-|0|extra','interpolate|0|24|18446744073709551616|-|0','interpolate|0|24|-1|-|0']
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
