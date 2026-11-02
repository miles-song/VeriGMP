"""Independent integer expansion of the even and odd diagonal pair products."""
import random
B=1<<64;MASK=B-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def cases():
    rng=random.Random(0x8c0120261102);rows=[];counts={'dyadic':0,'generic':0}
    weight_sets=[]
    for p,q in [(1,8),(1,4),(1,2),(1,1),(2,1),(4,1),(8,1)]:weight_sets.append(([p**j*q**(7-j) for j in range(8)],'dyadic'))
    for ws in [[0]*8,[2097152]+[0]*7,[0,2097152]+[0]*6,[2097152,2097151]+[0]*6,[524287]*8]:weight_sets.append((ws,'generic'))
    for _ in range(8):
        ws=[0]*8;left=4194303
        for j in range(8):ws[j]=rng.randrange(min(left,2097152)+1);left-=ws[j]
        rng.shuffle(ws);weight_sets.append((ws,'generic'))
    for k in [0,1,2,3,7,8,23,24,25,63,64,65]:
        for h in sorted({0,k//2,k}):
            n=7*k+h
            arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([MASK if (i//max(k,1))%2 else 0 for i in range(n)],[0 if (i//max(k,1))%2 else MASK for i in range(n)]),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
            for ws,kind in weight_sets:
                for a,b in arrays:
                    aa=[integer(a[i*k:min((i+1)*k,n)]) for i in range(8)];bb=[integer(b[i*k:min((i+1)*k,n)]) for i in range(8)]
                    even=sum(aa[i]*bb[j]*ws[i]*ws[j] for i in range(8) for j in range(8) if (i+j)%2==0)
                    odd=sum(aa[i]*bb[j]*ws[i]*ws[j] for i in range(8) for j in range(8) if (i+j)%2==1)
                    width=2*(k+1);assert 0<=even<B**width and 0<=odd<B**width
                    command=f'pair|{k}|24|{encode(ws)}|{encode(a)}|{encode(b)}|{rng.choice([0,1,17])}'
                    expected=' '.join(map(str,digits(even,width)+digits(odd,width)));rows.append((command,expected));counts[kind]+=1
    return rows,counts
def invalid():
    z='0,0,0,0,0,0,0,0'
    return ['',f'unknown|0|24|{z}|-|-|0',f'pair|0|23|{z}|-|-|0',f'pair|0|24|{z}|1|-|0',f'pair|0|24|{z}|1|1|0',f'pair|1|24|{z}|1|1|0',f'pair|0|24|{z}|-|-|65',f'pair|0|24|{z}|-|-|0|extra','pair|0|24|2097153,0,0,0,0,0,0,0|-|-|0','pair|0|24|2097152,2097152,0,0,0,0,0,0|-|-|0','pair|0|24|0,0|-|-|0',f'pair|0|24|{z}|18446744073709551616|-|0']
if __name__=='__main__':
    r,c=cases();print({'cases':len(r),'counts':c,'invalid':len(invalid())})
