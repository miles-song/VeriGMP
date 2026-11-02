"""Independent unbounded products reduced by the requested bit precision."""
import random
MASK=(1<<64)-1
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def integer(xs):return sum(x<<(64*i) for i,x in enumerate(xs))
def digits(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def cases():
    rng=random.Random(0x8101261102);rows=[];counts={'mul':0,'square':0,'shared_immutable_inputs':0}
    sizes=[1,7,8,9,23,24,25,63,64,65,127,128,129,255,256,257,439,440,441,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096]
    for index,n in enumerate(sizes):
        arrays=[([0]*n,[0]*n),([MASK]*n,[MASK]*n),([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)])]
        for pattern,(a,b) in enumerate(arrays):
            for split in range(3):
                threshold=[56,96,192][(index+pattern+split)%3];low=[24,64,128][(index+2*pattern+split)%3]
                for top in [1,2,31,63,64]:
                    modulus=1<<(64*(n-1)+top)
                    for square in [False,True]:
                        other=a if square else b;name='square' if square else 'mul-alias' if pattern<2 else 'mul'
                        expected=' '.join(map(str,digits((integer(a)*integer(other))%modulus,n)))
                        command=f'{name}|{top}|{threshold}|{low}|{split}|{encode(a)}|{encode(other)}|{rng.choice([0,1,17])}|{rng.choice([0,1,7])}'
                        rows.append((command,expected));counts['square' if square else 'mul']+=1
                        if name=='mul-alias':counts['shared_immutable_inputs']+=1
    return rows,counts
def invalid():
    good='mul|64|56|24|0|1|1|0|0'
    return ['',good.replace('mul','unknown',1),good.replace('|64|','|0|',1),good.replace('|64|','|65|',1),
        good.replace('|56|','|55|',1),good.replace('|24|','|23|',1),good.replace('|0|1|1|','|3|1|1|',1),
        'mul|64|56|24|0|-|-|0|0','mul|64|56|24|0|1|-|0|0',good+'|extra',
        'mul|64|56|24|0|18446744073709551616|1|0|0','mul|64|56|24|0|1|1|65|0',
        'mul|64|56|24|0|1|1|0|65','mul-alias|64|56|24|0|1|2|0|0',
        'square|64|56|24|0|1|2|0|0','mul|64|56|24|0|-1|1|0|0']
if __name__=='__main__':
    rows,counts=cases();print({'cases':len(rows),'counts':counts,'invalid':len(invalid())})
