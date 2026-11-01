//! Ordinary Rust comparison only; this is not a verified production module.
pub fn add_assign(dst: &mut [u64], rhs: &[u64]) -> u64 {
    assert!(dst.len() == rhs.len());
    let mut i = 0;
    let mut carry = 0;
    while i < dst.len() {
        let total = (dst[i] as u128) + (rhs[i] as u128) + (carry as u128);
        dst[i] = total as u64;
        carry = (total >> 64) as u64;
        i += 1;
    }
    carry
}

fn sub_limb(a:u64,b:u64,borrow:u64)->(u64,u64){
    let difference=a.wrapping_sub(b);let first=a<b;
    let low=difference.wrapping_sub(borrow);let second=difference<borrow;
    (low,(first||second) as u64)
}
pub fn sub_assign(dst:&mut[u64],rhs:&[u64])->u64 {
    assert!(dst.len()==rhs.len());let mut i=0;let mut borrow=0;
    while i<dst.len() {
        let (low,next)=sub_limb(dst[i],rhs[i],borrow);dst[i]=low;
        borrow=next;i+=1;
    }
    borrow
}
