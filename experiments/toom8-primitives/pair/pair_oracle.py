"""Independent unbounded integers for signed point-pair transforms."""
import random
B=1<<64;MASK=B-1
def words(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def text(xs):return ','.join(map(str,xs)) if xs else '-'
def cases():
    rng=random.Random(0x8fa120261102);rows=[];counts={'pair':0,'half':0}
    for n in [0,1,2,3,4,7,8,15,16,31,32,64,128,256]:
        bound=B**n-1;values={(0,0),(bound,0),(bound//2,bound//2),((bound+1)//2,bound//2)}
        for k in range(n):
            r=B**k
            for a,d in [(r-1,0),(r,r-1),(r,r),(2*r-1,1),(bound-r,r)]:
                if 0<=d<=a and a+d<=bound:values.add((a,d))
        for _ in range(75):
            a=rng.randrange(bound+1);d=rng.randrange(min(a,bound-a)+1);values.add((a,d))
        for a,d in sorted(values):
            for negative in [False,True]:
                y=-d if negative else d
                for operation in ['pair','half']:
                    if operation=='half' and (a%2)!=(d%2):continue
                    p,m=a+y,a-y
                    if operation=='half':p//=2;m//=2
                    cmd=f'{operation}|{int(negative)}|{text(words(a,n))}|{text(words(d,n))}'
                    expected=' '.join(map(str,words(p,n)+words(m,n)));rows.append((cmd,expected));counts[operation]+=1
    return rows,counts
def invalid():
    return ['','unknown|0|-|-','pair|2|-|-','pair|0|0|1','pair|0|18446744073709551615|1',
        'pair|0|0,1|0','pair|0|0|0,1','half|0|1|0','half|1|2|1','pair|0|-|-|extra',
        'pair|0|-1|0','pair|0|18446744073709551616|0']
if __name__=='__main__':
    r,c=cases();print({'cases':len(r),'counts':c,'invalid':len(invalid())})
