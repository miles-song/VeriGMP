//! Recombine fifteen coefficients using the existing modular shifted adder.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::toom8_recomposition_spec as model;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::toom_words;
verus! {
pub fn assemble(dst:&mut[u64],z0:&[u64],z1:&[u64],z2:&[u64],z3:&[u64],z4:&[u64],z5:&[u64],z6:&[u64],z7:&[u64],z8:&[u64],z9:&[u64],z10:&[u64],z11:&[u64],z12:&[u64],z13:&[u64],z14:&[u64],k:usize,Ghost(c):Ghost<Seq<int>>)
    requires c.len()==15,14*(k as int)<=old(dst)@.len(),
        value(z0@)==c[0],
        value(z1@)==c[1],
        value(z2@)==c[2],
        value(z3@)==c[3],
        value(z4@)==c[4],
        value(z5@)==c[5],
        value(z6@)==c[6],
        value(z7@)==c[7],
        value(z8@)==c[8],
        value(z9@)==c[9],
        value(z10@)==c[10],
        value(z11@)==c[11],
        value(z12@)==c[12],
        value(z13@)==c[13],
        value(z14@)==c[14],
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==model::coefficient_sum(c,k as nat)%radix(old(dst)@.len()),
{
    let _capacity=dst.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,14);}
    assert!(k<=usize::MAX/14 && 14*k<=dst.len());
    toom_words::zero(dst);
    toom_words::add_shifted(dst,z0,0*k);
    toom_words::add_shifted(dst,z1,1*k);
    toom_words::add_shifted(dst,z2,2*k);
    toom_words::add_shifted(dst,z3,3*k);
    toom_words::add_shifted(dst,z4,4*k);
    toom_words::add_shifted(dst,z5,5*k);
    toom_words::add_shifted(dst,z6,6*k);
    toom_words::add_shifted(dst,z7,7*k);
    toom_words::add_shifted(dst,z8,8*k);
    toom_words::add_shifted(dst,z9,9*k);
    toom_words::add_shifted(dst,z10,10*k);
    toom_words::add_shifted(dst,z11,11*k);
    toom_words::add_shifted(dst,z12,12*k);
    toom_words::add_shifted(dst,z13,13*k);
    toom_words::add_shifted(dst,z14,14*k);
    proof {
        let q=radix(dst@.len());radix_positive(dst@.len());assert(radix(0)==1);
        lemma_add_mod_noop_right(radix((1*k) as nat)*c[1],radix((0*k) as nat)*c[0],q);
        lemma_add_mod_noop_right(radix((2*k) as nat)*c[2],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1],q);
        lemma_add_mod_noop_right(radix((3*k) as nat)*c[3],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2],q);
        lemma_add_mod_noop_right(radix((4*k) as nat)*c[4],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3],q);
        lemma_add_mod_noop_right(radix((5*k) as nat)*c[5],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4],q);
        lemma_add_mod_noop_right(radix((6*k) as nat)*c[6],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5],q);
        lemma_add_mod_noop_right(radix((7*k) as nat)*c[7],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6],q);
        lemma_add_mod_noop_right(radix((8*k) as nat)*c[8],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7],q);
        lemma_add_mod_noop_right(radix((9*k) as nat)*c[9],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8],q);
        lemma_add_mod_noop_right(radix((10*k) as nat)*c[10],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8]+radix((9*k) as nat)*c[9],q);
        lemma_add_mod_noop_right(radix((11*k) as nat)*c[11],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8]+radix((9*k) as nat)*c[9]+radix((10*k) as nat)*c[10],q);
        lemma_add_mod_noop_right(radix((12*k) as nat)*c[12],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8]+radix((9*k) as nat)*c[9]+radix((10*k) as nat)*c[10]+radix((11*k) as nat)*c[11],q);
        lemma_add_mod_noop_right(radix((13*k) as nat)*c[13],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8]+radix((9*k) as nat)*c[9]+radix((10*k) as nat)*c[10]+radix((11*k) as nat)*c[11]+radix((12*k) as nat)*c[12],q);
        lemma_add_mod_noop_right(radix((14*k) as nat)*c[14],radix((0*k) as nat)*c[0]+radix((1*k) as nat)*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5]+radix((6*k) as nat)*c[6]+radix((7*k) as nat)*c[7]+radix((8*k) as nat)*c[8]+radix((9*k) as nat)*c[9]+radix((10*k) as nat)*c[10]+radix((11*k) as nat)*c[11]+radix((12*k) as nat)*c[12]+radix((13*k) as nat)*c[13],q);
    }
}
pub fn assemble_exact(dst:&mut[u64],z0:&[u64],z1:&[u64],z2:&[u64],z3:&[u64],z4:&[u64],z5:&[u64],z6:&[u64],z7:&[u64],z8:&[u64],z9:&[u64],z10:&[u64],z11:&[u64],z12:&[u64],z13:&[u64],z14:&[u64],a:&[u64],b:&[u64],k:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,old(dst)@.len()==2*a@.len(),
        value(z0@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[0],
        value(z1@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[1],
        value(z2@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[2],
        value(z3@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[3],
        value(z4@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[4],
        value(z5@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[5],
        value(z6@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[6],
        value(z7@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[7],
        value(z8@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[8],
        value(z9@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[9],
        value(z10@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[10],
        value(z11@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[11],
        value(z12@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[12],
        value(z13@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[13],
        value(z14@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[14],
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(a@)*value(b@),
{
    let ghost c=convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat));
    assemble(dst,z0,z1,z2,z3,z4,z5,z6,z7,z8,z9,z10,z11,z12,z13,z14,k,Ghost(c));
    proof {
        model::recover_input_product(a@,b@,k as nat);
        lemma_small_mod(value(a@)*value(b@),radix(dst@.len()));
    }
}
}
