//! Actual endpoint removal and exact scaling for six paired Newton nodes.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::toom8_normalization_spec as model;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::{scaled_subtraction,toom_words,toom4_multiply,toom8_dyadic_producer};
verus! {
#[inline(always)]
pub fn parameters(node:u32)->(out:(u32,bool,u64,u64,u64,u64,u64,u64))
    requires node<6,
    ensures out.0==model::exponent(node),out.1==model::reciprocal(node),
        out.2 as int==model::low_multiplier(node),out.3 as int==model::high_multiplier(node),
        out.4 as int==model::even_divisor(node),out.5 as int==model::odd_divisor(node),
        out.6 as int==model::even_scale(node),out.7 as int==model::odd_scale(node),
{
    assert!(node<6);
    if node==0 {(3,true,4398046511104,1,64,8,1,1)}
    else if node==1 {(2,true,268435456,1,16,4,1024,4096)}
    else if node==2 {(1,true,16384,1,4,2,1048576,16777216)}
    else if node==3 {(0,false,1,1,1,1,1073741824,68719476736)}
    else if node==4 {(1,false,1,16384,4,2,1073741824,68719476736)}
    else {(2,false,1,268435456,16,4,1073741824,68719476736)}
}
#[inline(always)]
pub fn normalize(even:&mut[u64],odd:&mut[u64],low:&[u64],high:&[u64],node:u32,k:usize,Ghost(c):Ghost<Seq<int>>)
    requires node<6,model::bounded(c,radix(k as nat)),
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),low@.len()<=old(even)@.len(),high@.len()<=old(even)@.len(),
        value(old(even)@)==model::raw_even(c,node),value(old(odd)@)==model::raw_odd(c,node),
        value(low@)==c[0],value(high@)==c[14],
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),
        value(final(even)@)==model::normalized_even(c,node),value(final(odd)@)==model::normalized_odd(c,node),
{
    let (_,_,low_word,high_word,even_divisor,odd_divisor,even_scale,odd_scale)=parameters(node);
    proof {model::relations(c,node);model::normalization_capacity(c,node,k as nat);}
    scaled_subtraction::sub_scaled_exact(even,low,low_word);
    scaled_subtraction::sub_scaled_exact(even,high,high_word);
    let ghost eq=model::even_quotient(c,node);let ghost oq=model::odd_quotient(c,node);
    proof {lemma_mod_multiples_basic(eq,even_divisor as int);lemma_mod_multiples_basic(oq,odd_divisor as int);}
    toom_words::divide_exact(even,even_divisor);
    proof {
        assert(value(even@)==eq) by(nonlinear_arith)
            requires (even_divisor as int)*value(even@)==(even_divisor as int)*eq,even_divisor>0;
    }
    toom_words::scale_exact(even,even_scale);
    toom_words::divide_exact(odd,odd_divisor);
    proof {
        assert(value(odd@)==oq) by(nonlinear_arith)
            requires (odd_divisor as int)*value(odd@)==(odd_divisor as int)*oq,odd_divisor>0;
    }
    toom_words::scale_exact(odd,odd_scale);
}

// Self-contained local composition. A full kernel will retain these endpoint
// products once and reuse normalize across all six paired nodes.
pub fn prepare_pair(even:&mut[u64],odd:&mut[u64],a:&[u64],b:&[u64],k:usize,node:u32,scratch:&mut[u64],threshold:usize)
    requires node<6,a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=24,
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),old(scratch)@.len()>=18*(k+1),
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(even)@)==model::normalized_even(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat)),node),
        value(final(odd)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat)),node),
{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/18 && scratch.len()>=18*(k+1));
    assert!(a.len()==b.len() && a.len()>=7*k && a.len()<=8*k);
    assert!(even.len()==2*(k+1) && odd.len()==even.len() && threshold>=24 && node<6);
    let h=a.len()-7*k;
    let (low,rest)=scratch.split_at_mut(2*k);let (high,work)=rest.split_at_mut(2*h);
    toom4_multiply::full(low,&a[..k],&b[..k],work,threshold);
    toom4_multiply::full(high,&a[7*k..],&b[7*k..],work,threshold);
    let (exponent,reciprocal,_,_,_,_,_,_)=parameters(node);
    toom8_dyadic_producer::dyadic_pair(even,odd,a,b,k,exponent,reciprocal,work,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(b@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(b@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
    }
    normalize(even,odd,low,high,node,k,Ghost(c));
}
}
