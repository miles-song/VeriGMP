"""Independent unbounded integer squares at exact recursion boundaries."""
import random
MASK=(1<<64)-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8f5a261102);rows=[];counts={name:0 for name in ['zero','max','odd_blocks_only','even_blocks_only','random']}
    sizes=[1,2,7,8,23,24,25,55,56,57,63,64,65,95,96,97,127,128,129,255,256,257,439,440,441,447,448,449,511,512,513,759,760,761,767,768,769,1023,1024,1025,2047,2048,2049,3519,3520,3521,3535,3536,3537,4095,4096]
    for n in sizes:
        k=(n+7)//8
        arrays=[[0]*n,[MASK]*n,[MASK if (i//k)%2 else 0 for i in range(n)],[0 if (i//k)%2 else MASK for i in range(n)],[rng.getrandbits(64) for _ in range(n)]]
        for category,a in zip(counts,arrays):
            expected=' '.join(map(str,digits(integer(a)**2,2*n)))
            for threshold in [56,96,192]:
                rows.append((f'square|{threshold}|{encode(a)}|{rng.choice([0,1,17])}',expected));counts[category]+=1
    return rows,counts
def invalid():
    return ['', 'unknown|56|1|0','square|55|1|0','square|-1|1|0','square|56|-|0','square|56|1|65',
        'square|56|1|0|extra','square|56|18446744073709551616|0','square|56|-1|0','square|56|x|0','square|56|1|-1','square|56|1']
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
