#[path="specs/radix.rs"] mod radix;
#[path="specs/wide_odd_division.rs"] mod wide_odd_division_spec;
#[path="verified/wide_odd_division.rs"] mod wide_odd_division;

#[no_mangle] pub fn verified_wide_limb(x:u64,carry:u64,divisor:u64,inv:u64)->(u64,u64){wide_odd_division::quotient_limb(x,carry,divisor,inv)}
#[no_mangle] pub fn verified_wide_exact(dst:&mut[u64],divisor:u64,inv:u64){wide_odd_division::divide_exact_with_inverse(dst,divisor,inv);}
#[no_mangle] pub fn verified_wide_family(dst:&mut[u64],divisor:u64){wide_odd_division::divide_toom8_odd(dst,divisor);}
#[no_mangle] pub fn verified_wide_4095(dst:&mut[u64]){wide_odd_division::divide_toom8_odd(dst,4095);}
fn main(){}
