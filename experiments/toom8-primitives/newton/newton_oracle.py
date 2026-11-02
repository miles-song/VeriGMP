"""Independent polynomial-evaluation inputs and original coefficient answers."""
import random
B=1<<64
def words(value,n):
    assert 0<=value<B**n
    return [(value>>(64*i))&(B-1) for i in range(n)]
def cases():
    rng=random.Random(0x8E7700)
    rows=[];counts={5:0,6:0}
    for d in [5,6]:
        nodes=[4**i for i in range(d+1)]
        weights=[64**(d-j)*nodes[-1]**j for j in range(d+1)]
        for n in [0,1,2,3,4,7,8,15,16,31,32,64,128]:
            bound=B**n-1;vectors={(0,)*(d+1)}
            for j in range(d+1):
                maximum=bound//weights[j]
                for q in [min(maximum,1),maximum//2,maximum]:
                    c=[0]*(d+1);c[j]=q;vectors.add(tuple(c))
            if sum(weights)<=bound:vectors.add((1,)*(d+1))
            for _ in range(24):
                left=bound;c=[0]*(d+1);order=list(range(d+1));rng.shuffle(order)
                for j in order:
                    maximum=left//weights[j];c[j]=rng.randrange(maximum+1);left-=c[j]*weights[j]
                vectors.add(tuple(c))
            for c in sorted(vectors):
                evaluations=[sum(c[j]*64**(d-j)*x**j for j in range(d+1)) for x in nodes]
                assert all(0<=v<=bound for v in evaluations)
                args=[d,n]+[w for v in evaluations for w in words(v,n)]+[w for v in c for w in words(v,n)]
                expected=[w for v in c for w in words(v,n)]
                rows.append((' '.join(map(str,args)),' '.join(map(str,expected))))
                counts[d]+=1
    return rows,counts
def invalid():
    return ['','4 0','7 0','5','6 1 0','5 1 0 0 0 0 0','5 0 0','6 0 0','5 -1','6 18446744073709551615']
