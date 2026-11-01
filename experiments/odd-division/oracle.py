"""Independent Python integer oracle for forced Toom-4 and its actual evaluators."""
import random
SEED=20261107
MASK=(1<<64)-1
def words(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def integer(a):return sum(x<<(64*i) for i,x in enumerate(a))
def line(op,args):return op+' '+' '.join(map(str,args))
def output(a):return ' '.join(map(str,a))

def cases():
    rng=random.Random(SEED);rows=[]
    shapes=[1,2,3,7,8,9,23,24,25,26,27,28,29,31,32,33,47,48,49,63,64,65,95,96,97,
        127,128,129,191,192,193,255,256,257,383,384,385,511,512,513,1023,1024,1025,2048,4096]
    for n in shapes:
        limit=(1<<(64*n))-1
        patterns=[0,1,limit,integer([MASK if i%2 else 0 for i in range(n)]),
                  1<<(64*(n-1)),rng.randrange(limit+1)]
        for pattern,a in enumerate(patterns):
            b=patterns[(pattern+2)%len(patterns)] if pattern<5 else rng.randrange(limit+1)
            wa,wb=words(a,n),words(b,n)
            for threshold in [24,192,256]:
                for op,expected in [('full4',a*b),('squarefull4',a*a),('full4same',a*a)]:
                    rows.append((line(op,[64,threshold,24,0,*wa,*wb]),output(words(expected,2*n))))
            for split in [0,1,2]:
                for top in [1,63,64]:
                    modulus=1<<(64*(n-1)+top)
                    for op,expected in [('low4',a*b),('squarelow4',a*a)]:
                        rows.append((line(op,[top,24,24,split,*wa,*wb]),output(words(expected%modulus,n))))
            for top in [1,32,63,64]:
                modulus=1<<(64*(n-1)+top)
                for op,expected in [('candidate4',a*b),('candidate4square',a*a)]:
                    rows.append((line(op,[top,256,128,2,*wa,*wb]),output(words(expected%modulus,n))))
    weight_sets=[(0,0,0,0),(1,1,1,1),(1,2,4,8),(8,4,2,1),(8,0,2,0),(0,4,0,1),(1,0,1,0),(0,1,0,1),(7,8,0,0),(0,0,7,8)]
    for n in [0,1,2,3,4,7,8,9,23,24,25,63,64,65,127,128,129,255,256,257,1024]:
        for h in sorted({0,n,max(0,n-1)}):
            maximum=(1<<(64*n))-1;last=(1<<(64*h))-1
            values=[(0,0,0,0),(maximum,maximum,maximum,last),(maximum,0,maximum,0),
                    (0,maximum,0,last),(0,1 if n else 0,0,0),
                    (rng.randrange(maximum+1),rng.randrange(maximum+1),rng.randrange(maximum+1),rng.randrange(last+1))]
            for a in values:
                data=[*words(a[0],n),*words(a[1],n),*words(a[2],n),*words(a[3],h)]
                for w in weight_sets:
                    rows.append((line('weighted4',[*w,n,h,*data]),output(words(sum(x*y for x,y in zip(w,a)),n+1))))
                for half,w in [(0,(1,-1,1,-1)),(1,(8,-4,2,-1))]:
                    expected=sum(x*y for x,y in zip(w,a))
                    rows.append((line('signed4',[half,n,h,*data]),output([*words(abs(expected),n+1),int(expected<0)])))
    return rows
