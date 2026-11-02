//! No benchmark/FFI linkage; every reachable arithmetic body is emitted for inspection.
#[path="specs/radix.rs"] mod radix;
#[path="specs/precision.rs"] mod precision;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/fast_multiply.rs"] mod fast_multiply;
#[no_mangle]
pub fn verified_fast(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32){fast_multiply::mul_mod(out,a,b,scratch,top);}
#[no_mangle]
pub fn verified_sub(a:u64,b:u64,borrow:u64)->(u64,u64){fast_words::sub_word(a,b,borrow)}
#[no_mangle]
pub fn ordinary_sub(a:u64,b:u64,borrow:u64)->(u64,u64){
    let (d,x)=a.overflowing_sub(b);let(d,y)=d.overflowing_sub(borrow);(d,(x||y) as u64)
}
fn main(){}
