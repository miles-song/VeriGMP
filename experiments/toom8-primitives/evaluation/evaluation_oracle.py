"""Independent Python integers for eight-block signed homogeneous evaluation."""
import random
B=1<<64;MASK=B-1;MAX_WEIGHT=1<<21;MAX_SUM=(1<<22)-1;CARRY=1<<22
def value(words):return sum(x<<(64*i) for i,x in enumerate(words))
def words(x,n):return [(x>>(64*i))&MASK for i in range(n)]
def encode(xs):return ','.join(map(str,xs)) if xs else '-'
def point_weights(e,reciprocal):
    p,q=(1,1<<e) if reciprocal else (1<<e,1)
    return [p**j*q**(7-j) for j in range(8)]
def signed(xs,ws,negative):return sum(x*w*(-1 if negative and j%2 else 1) for j,(x,w) in enumerate(zip(xs,ws)))
def cases():
    rng=random.Random(0x8e1a20261102);rows=[];counts={'scalar':0,'weighted_arrays':0,'dyadic_arrays':0,'point_weights':0}
    weight_sets=[[0]*8,[1]*8]
    for j in range(8):
        w=[0]*8;w[j]=MAX_WEIGHT;weight_sets.append(w)
        for k in range(8):
            if j!=k:w=[0]*8;w[j]=MAX_WEIGHT;w[k]=MAX_WEIGHT-1;weight_sets.append(w)
    weight_sets += [point_weights(e,r) for e in range(4) for r in [False,True]]
    for _ in range(24):
        remaining=MAX_SUM;w=[]
        for _ in range(8):x=rng.randrange(min(MAX_WEIGHT,remaining)+1);w.append(x);remaining-=x
        rng.shuffle(w);weight_sets.append(w)
    scalar_x=[[0]*8,[MASK]*8,[1]*8,[MASK if j%2 else 0 for j in range(8)],[MASK if j%2==0 else 0 for j in range(8)],[1<<63]*8]
    for ws in weight_sets:
        for negative in [False,True]:
            for incoming in [-CARRY,-CARRY+1,-1,0,1,CARRY-1,CARRY]:
                for xs in scalar_x:
                    total=signed(xs,ws,negative)+incoming;q,low=divmod(total,B)
                    assert -CARRY<=q<=CARRY
                    rows.append(('limb|'+str(incoming)+'|'+str(int(negative))+'|'+encode(ws)+'|'+encode(xs),f'{low} {q}'));counts['scalar']+=1
    for _ in range(300):
        ws=rng.choice(weight_sets);xs=[rng.getrandbits(64) for _ in range(8)];negative=bool(rng.randrange(2));incoming=rng.randint(-CARRY,CARRY);q,low=divmod(signed(xs,ws,negative)+incoming,B)
        rows.append(('limb|'+str(incoming)+'|'+str(int(negative))+'|'+encode(ws)+'|'+encode(xs),f'{low} {q}'));counts['scalar']+=1
    for e in range(4):
        for reciprocal in [False,True]:
            ws=point_weights(e,reciprocal);rows.append((f'weights|{e}|{int(reciprocal)}',' '.join(map(str,ws))));counts['point_weights']+=1
    for n in [0,1,2,3,4,7,8,15,16,31,32,64,128]:
        for h in sorted({0,n//2,n}):
            for pattern in range(6):
                arrays=[]
                for j in range(8):
                    length=h if j==7 else n
                    if pattern==0:a=[0]*length
                    elif pattern==1:a=[MASK]*length
                    elif pattern==2:a=[MASK if j%2==0 else 0]*length
                    elif pattern==3:a=[MASK if j%2 else 0]*length
                    elif pattern==4:a=[1 if i==0 else 0 for i in range(length)]
                    else:a=[rng.getrandbits(64) for _ in range(length)]
                    arrays.append(a)
                for negative in [False,True]:
                    selected=[weight_sets[0],weight_sets[1],weight_sets[10],weight_sets[30],rng.choice(weight_sets)]
                    for ws in selected:
                        result=signed([value(a) for a in arrays],ws,negative);assert abs(result)<B**(n+1)
                        command='eval|'+str(int(negative))+'|'+encode(ws)+'|'+'|'.join(encode(a) for a in arrays)
                        rows.append((command,str(int(result<0))+' '+' '.join(map(str,words(abs(result),n+1)))));counts['weighted_arrays']+=1
                    for e in range(4):
                        for reciprocal in [False,True]:
                            ws=point_weights(e,reciprocal);result=signed([value(a) for a in arrays],ws,negative);assert abs(result)<B**(n+1)
                            command=f'dyadic|{e}|{int(reciprocal)}|{int(negative)}|'+'|'.join(encode(a) for a in arrays)
                            rows.append((command,str(int(result<0))+' '+' '.join(map(str,words(abs(result),n+1)))));counts['dyadic_arrays']+=1
    return rows,counts
def invalid():
    zeros='0,0,0,0,0,0,0,0';ones='1,1,1,1,1,1,1,1';empty='|'+'|'.join(['-']*8)
    return ['limb|4194305|0|'+ones+'|'+zeros,'limb|-4194305|0|'+ones+'|'+zeros,
        'limb|0|2|'+ones+'|'+zeros,'limb|0|0|2097153,0,0,0,0,0,0,0|'+zeros,
        'limb|0|0|2097152,2097152,0,0,0,0,0,0|'+zeros,'limb|0|0|1,1|'+zeros,
        'limb|0|0|'+ones+'|1','weights|4|0','weights|0|2','dyadic|4|0|0'+empty,
        'dyadic|0|0|2'+empty,'eval|0|'+ones+'|0|-|-|-|-|-|-|-',
        'eval|0|'+ones+'|0|0|0|0|0|0|0|0,1','eval|0|'+zeros+'|-|-|-|-|-|-|-',
        'unknown','weights|0|0|extra']
if __name__=='__main__':
    r,c=cases();print({'cases':len(r),'counts':c,'invalid':len(invalid())})
