//! Independent ordinary Rust implementation of the same arithmetic/scratch layout.
fn add(out:&mut[u64],rhs:&[u64])->u64 {
    assert!(out.len()>=rhs.len());
    let mut carry=0u64;
    for (x,y) in out.iter_mut().zip(rhs) {
        let t=(*x as u128)+(*y as u128)+(carry as u128);*x=t as u64;carry=(t>>64) as u64;
    }
    add_small(&mut out[rhs.len()..],carry)
}
fn add_small(out:&mut[u64],mut carry:u64)->u64 {
    for x in out {if carry==0{break;} let t=(*x as u128)+(carry as u128);*x=t as u64;carry=(t>>64) as u64;}
    carry
}
fn abs(out:&mut[u64],a:&[u64],b:&[u64])->bool {
    assert!(out.len()==a.len() && a.len()>=b.len());
    let neg=(0..a.len()).rev().find_map(|i| {
        let y=b.get(i).copied().unwrap_or(0);if a[i]!=y{Some(a[i]<y)}else{None}
    }).unwrap_or(false);
    let (x,y)=if neg{(b,a)}else{(a,b)};let mut borrow=0u64;
    let common=x.len().min(y.len());
    for i in 0..common {
        let (d,b1)=x[i].overflowing_sub(y[i]);let (d,b2)=d.overflowing_sub(borrow);
        out[i]=d;borrow=(b1||b2) as u64;
    }
    for (i,z) in out.iter_mut().enumerate().skip(common) {
        let (d,b1)=x.get(i).copied().unwrap_or(0).overflowing_sub(y.get(i).copied().unwrap_or(0));
        let (d,b2)=d.overflowing_sub(borrow);*z=d;borrow=(b1||b2) as u64;
    }
    neg
}
fn reverse_sub(out:&mut[u64],rhs:&[u64])->u64 {
    assert_eq!(out.len(),rhs.len());let mut borrow=0u64;
    for (x,y) in out.iter_mut().zip(rhs) {let (d,b1)=y.overflowing_sub(*x);let (d,b2)=d.overflowing_sub(borrow);*x=d;borrow=(b1||b2) as u64;}
    borrow
}
fn mul_row(out:&mut[u64],b:&[u64],word:u64,accumulate:bool)->u64 {
    assert!(out.len()<=b.len());let mut carry=0u64;
    for (x,y) in out.iter_mut().zip(b) {let t=(word as u128)*(*y as u128)+(carry as u128)+if accumulate{*x as u128}else{0};
        *x=t as u64;carry=(t>>64) as u64;}
    carry
}
fn full(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize) {
    let n=a.len();assert!(n>0 && n==b.len());assert!(n<=usize::MAX/3);
    assert!(out.len()==2*n && scratch.len()>=3*n && threshold>=8);
    if n<=threshold {
        out[n]=mul_row(&mut out[..n],b,a[0],false);
        for i in 1..n{out[i+n]=mul_row(&mut out[i..i+n],b,a[i],true);}return;
    }
    let k=n-n/2;
    let sign_a=abs(&mut out[..k],&a[..k],&a[k..]);
    let sign_b=abs(&mut out[k..2*k],&b[..k],&b[k..]);
    let (d,work)=scratch.split_at_mut(2*k);
    full(d,&out[..k],&out[k..2*k],work,threshold);
    full(&mut out[2*k..],&a[k..],&b[k..],work,threshold);
    full(&mut out[..2*k],&a[..k],&b[..k],work,threshold);
    let c=if sign_a!=sign_b{add(d,&out[..2*k]) as i64}else{-(reverse_sub(d,&out[..2*k]) as i64)};
    let high=c+add(d,&out[2*k..]) as i64;
    add(&mut out[k..],d);add_small(&mut out[3*k..],high as u64);
}
fn low(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize,limit:usize,unbalanced:bool) {
    let n=a.len();assert!(n>0 && n==b.len());assert!(n<=usize::MAX/4);
    assert!(out.len()==n && scratch.len()>=4*n && threshold>=8 && limit>=8);
    if n<=limit {
        mul_row(out,b,a[0],false);
        for (i,x) in a.iter().copied().enumerate().skip(1){mul_row(&mut out[i..],b,x,true);}return;
    }
    let h=if unbalanced{(n/36)*11+((n%36)*11)/36}else{n/2};let k=n-h;
    {let (product,work)=scratch.split_at_mut(2*k);full(product,&a[..k],&b[..k],work,threshold);out.copy_from_slice(&product[..n]);}
    let (cross,work)=scratch.split_at_mut(h);
    low(cross,&a[k..],&b[..h],work,threshold,limit,unbalanced);add(&mut out[k..],cross);
    low(cross,&a[..h],&b[k..],work,threshold,limit,unbalanced);add(&mut out[k..],cross);
}
pub fn modular(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,limit:usize) {
    assert!((1..=64).contains(&top));low(out,a,b,scratch,threshold,limit,true);
    if top<64{*out.last_mut().unwrap()&=(1u64<<top)-1;}
}
