"""Independent input convolution for positive-eight and seventh odd normalization."""
import random
B=1<<64;MASK=B-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8f70261102);rows=[];counts={'positive_product':0,'seventh_node':0}
    for k in [0,1,2,3,7,8,23,24,25,63,64,65,127,128,129]:
        for h in sorted({0,k//2,k}):
            n=7*k+h
            arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([MASK if (i//max(k,1))%2 else 0 for i in range(n)],[0 if (i//max(k,1))%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
            for a,b in arrays:
                aa=[integer(a[j*k:min((j+1)*k,n)]) for j in range(8)];bb=[integer(b[j*k:min((j+1)*k,n)]) for j in range(8)]
                c=[sum(aa[i]*bb[d-i] for i in range(8) if 0<=d-i<8) for d in range(15)]
                width=2*(k+1);product=sum(c[d]*8**d for d in range(15));normalized=sum(c[2*j+1]*64**(6+j) for j in range(7))
                assert 0<=product<B**width and 0<=normalized<B**width
                even_fields='|'.join(encode(digits(c[2*j],width)) for j in range(8))
                for threshold in [24,48]:
                    extra=rng.choice([0,1,17]);base=f'{k}|{threshold}|{encode(a)}|{encode(b)}'
                    rows.append((f'product|{base}|{extra}',' '.join(map(str,digits(product,width)))));counts['positive_product']+=1
                    rows.append((f'seventh|{base}|{even_fields}|{extra}',' '.join(map(str,digits(normalized,width)))));counts['seventh_node']+=1
    return rows,counts
def invalid():
    z='0,0';valid='seventh|0|24|-|-|'+'|'.join([z]*8)+'|0'
    return ['','unknown|0|24|-|-|0','product|0|23|-|-|0','product|-1|24|-|-|0',
        'product|0|24|1|-|0','product|0|24|1|1|0','product|1|24|1|1|0',
        'product|0|24|-|-|65','product|0|24|-|-|0|extra','product|0|24|18446744073709551616|-|0',
        valid.replace('|0,0|','|0|',1),valid+'|extra']
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
