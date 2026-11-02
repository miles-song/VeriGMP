#[path="specs/radix.rs"] mod radix;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="specs/signed_evaluation.rs"] mod signed_evaluation_spec;
#[path="verified/signed_evaluation.rs"] mod signed_evaluation;
#[path="specs/toom8_evaluation.rs"] mod toom8_evaluation_spec;
#[path="verified/toom8_evaluation.rs"] mod toom8_evaluation;

#[no_mangle] pub fn verified_eval8_limb(x:[u64;8],w:[u64;8],carry:i64,negative:bool)->(u64,i64){toom8_evaluation::limb(x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],w,carry,negative)}
#[no_mangle] pub fn verified_eval8_generic(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64],w:[u64;8],negative:bool)->bool{toom8_evaluation::evaluate(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,w,negative)}
#[no_mangle] pub fn verified_eval8_dyadic(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64],e:u32,r:bool,negative:bool)->bool{toom8_evaluation::dyadic(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,e,r,negative)}
#[no_mangle] pub fn verified_eval8_eight(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64])->bool{toom8_evaluation::dyadic(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,3,false,false)}
#[no_mangle] pub fn verified_eval8_negative_eight(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64])->bool{toom8_evaluation::dyadic(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,3,false,true)}
#[no_mangle] pub fn verified_eval8_negative_eighth(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64])->bool{toom8_evaluation::dyadic(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,3,true,true)}
fn main(){}
