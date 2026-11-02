#[path="specs/radix.rs"] mod radix;
#[path="specs/product.rs"] mod product;
#[path="specs/precision.rs"] mod precision;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/toom_words.rs"] mod toom_words;
#[path="specs/odd_division.rs"] mod odd_division_spec;
#[path="verified/odd_division.rs"] mod odd_division;
#[path="specs/toom8_pair.rs"] mod toom8_pair_spec;
#[path="verified/toom8_pair.rs"] mod toom8_pair;

#[no_mangle] pub fn verified_pair_generic(a:&mut[u64],b:&mut[u64],negative:bool){toom8_pair::sum_difference(a,b,negative);}
#[no_mangle] pub fn verified_pair_positive(a:&mut[u64],b:&mut[u64]){toom8_pair::sum_difference(a,b,false);}
#[no_mangle] pub fn verified_pair_negative(a:&mut[u64],b:&mut[u64]){toom8_pair::sum_difference(a,b,true);}
#[no_mangle] pub fn verified_pair_half(a:&mut[u64],b:&mut[u64],negative:bool){toom8_pair::half_pair(a,b,negative);}
fn main(){}
