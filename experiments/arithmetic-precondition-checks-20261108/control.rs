//! Ordinary Rust control for the checked entry and identical private recursion.
use verigmp::{fast_multiply,fast_words as words};

pub fn full(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize) {
    assert!(a.len()>0 && a.len()==b.len());assert!(a.len()<=usize::MAX/3);
    assert!(dst.len()==2*a.len() && scratch.len()>=3*a.len());assert!(threshold>=8);
    if a.len()<=threshold {fast_multiply::base_full(dst,a,b);return;}
    full_inner(dst,a,b,scratch,threshold);
}

fn full_inner(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize) {
    let n=a.len();
    if n<=threshold {fast_multiply::base_full(dst,a,b);return;}
    let h=n/2;
    let k=n-h;
    let neg_a=words::abs_difference(&mut dst[..k],&a[..k],&a[k..]);
    let neg_b=words::abs_difference(&mut dst[k..2*k],&b[..k],&b[k..]);
    let negative=neg_a!=neg_b;
    let (diff_product,child_scratch)=scratch.split_at_mut(2*k);
    full_inner(diff_product,&dst[..k],&dst[k..2*k],child_scratch,threshold);
    full_inner(&mut dst[2*k..],&a[k..],&b[k..],child_scratch,threshold);
    full_inner(&mut dst[..2*k],&a[..k],&b[..k],child_scratch,threshold);
    let high=words::combine_cross(diff_product,&dst[..2*k],&dst[2*k..],negative);
    words::add_cross(&mut dst[k..],diff_product,high);
}
