//! Factored in-place Newton interpolation; stage boundaries inline away.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::{toom_words,scaled_subtraction,wide_odd_division,toom8_newton_spec as model};
verus! {
#[inline(always)]
fn even_phase_0(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_0_0(c),
        value(old(a1)@)==model::even_state_0_1(c),
        value(old(a2)@)==model::even_state_0_2(c),
        value(old(a3)@)==model::even_state_0_3(c),
        value(old(a4)@)==model::even_state_0_4(c),
        value(old(a5)@)==model::even_state_0_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_1_0(c),
        value(final(a1)@)==model::even_state_1_1(c),
        value(final(a2)@)==model::even_state_1_2(c),
        value(final(a3)@)==model::even_state_1_3(c),
        value(final(a4)@)==model::even_state_1_4(c),
        value(final(a5)@)==model::even_state_1_5(c),
{
    proof {
        reveal(model::even_state_0_0);
        reveal(model::even_state_0_1);
        reveal(model::even_state_0_2);
        reveal(model::even_state_0_3);
        reveal(model::even_state_0_4);
        reveal(model::even_state_0_5);
        reveal(model::even_state_1_0);
        reveal(model::even_state_1_1);
        reveal(model::even_state_1_2);
        reveal(model::even_state_1_3);
        reveal(model::even_state_1_4);
        reveal(model::even_state_1_5);
    }
    proof { model::even_difference_1_5(c); }
    assert(value(a5@)==model::even_difference_1_5_before(c));
    assert(value(a4@)==model::even_difference_1_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::even_difference_1_5_after(c);
    proof { lemma_mod_multiples_basic(3int*q,256int); }
    toom_words::divide_exact(a5,256u64);
    assert(value(a5@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a5,3u64);
    assert(value(a5@)==model::even_difference_1_5_after(c));
    proof { model::even_difference_1_4(c); }
    assert(value(a4@)==model::even_difference_1_4_before(c));
    assert(value(a3@)==model::even_difference_1_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::even_difference_1_4_after(c);
    proof { lemma_mod_multiples_basic(3int*q,64int); }
    toom_words::divide_exact(a4,64u64);
    assert(value(a4@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a4,3u64);
    assert(value(a4@)==model::even_difference_1_4_after(c));
    proof { model::even_difference_1_3(c); }
    assert(value(a3@)==model::even_difference_1_3_before(c));
    assert(value(a2@)==model::even_difference_1_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::even_difference_1_3_after(c);
    proof { lemma_mod_multiples_basic(3int*q,16int); }
    toom_words::divide_exact(a3,16u64);
    assert(value(a3@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a3,3u64);
    assert(value(a3@)==model::even_difference_1_3_after(c));
    proof { model::even_difference_1_2(c); }
    assert(value(a2@)==model::even_difference_1_2_before(c));
    assert(value(a1@)==model::even_difference_1_2_rhs(c));
    toom_words::sub_exact(a2,a1);
    let ghost q=model::even_difference_1_2_after(c);
    proof { lemma_mod_multiples_basic(3int*q,4int); }
    toom_words::divide_exact(a2,4u64);
    assert(value(a2@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a2,3u64);
    assert(value(a2@)==model::even_difference_1_2_after(c));
    proof { model::even_difference_1_1(c); }
    assert(value(a1@)==model::even_difference_1_1_before(c));
    assert(value(a0@)==model::even_difference_1_1_rhs(c));
    toom_words::sub_exact(a1,a0);
    let ghost q=model::even_difference_1_1_after(c);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a1,3u64);
    assert(value(a1@)==model::even_difference_1_1_after(c));
}
#[inline(always)]
fn even_phase_1(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_1_0(c),
        value(old(a1)@)==model::even_state_1_1(c),
        value(old(a2)@)==model::even_state_1_2(c),
        value(old(a3)@)==model::even_state_1_3(c),
        value(old(a4)@)==model::even_state_1_4(c),
        value(old(a5)@)==model::even_state_1_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_2_0(c),
        value(final(a1)@)==model::even_state_2_1(c),
        value(final(a2)@)==model::even_state_2_2(c),
        value(final(a3)@)==model::even_state_2_3(c),
        value(final(a4)@)==model::even_state_2_4(c),
        value(final(a5)@)==model::even_state_2_5(c),
{
    proof {
        reveal(model::even_state_1_0);
        reveal(model::even_state_1_1);
        reveal(model::even_state_1_2);
        reveal(model::even_state_1_3);
        reveal(model::even_state_1_4);
        reveal(model::even_state_1_5);
        reveal(model::even_state_2_0);
        reveal(model::even_state_2_1);
        reveal(model::even_state_2_2);
        reveal(model::even_state_2_3);
        reveal(model::even_state_2_4);
        reveal(model::even_state_2_5);
    }
    proof { model::even_difference_2_5(c); }
    assert(value(a5@)==model::even_difference_2_5_before(c));
    assert(value(a4@)==model::even_difference_2_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::even_difference_2_5_after(c);
    proof { lemma_mod_multiples_basic(15int*q,64int); }
    toom_words::divide_exact(a5,64u64);
    assert(value(a5@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a5,15u64);
    assert(value(a5@)==model::even_difference_2_5_after(c));
    proof { model::even_difference_2_4(c); }
    assert(value(a4@)==model::even_difference_2_4_before(c));
    assert(value(a3@)==model::even_difference_2_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::even_difference_2_4_after(c);
    proof { lemma_mod_multiples_basic(15int*q,16int); }
    toom_words::divide_exact(a4,16u64);
    assert(value(a4@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a4,15u64);
    assert(value(a4@)==model::even_difference_2_4_after(c));
    proof { model::even_difference_2_3(c); }
    assert(value(a3@)==model::even_difference_2_3_before(c));
    assert(value(a2@)==model::even_difference_2_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::even_difference_2_3_after(c);
    proof { lemma_mod_multiples_basic(15int*q,4int); }
    toom_words::divide_exact(a3,4u64);
    assert(value(a3@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a3,15u64);
    assert(value(a3@)==model::even_difference_2_3_after(c));
    proof { model::even_difference_2_2(c); }
    assert(value(a2@)==model::even_difference_2_2_before(c));
    assert(value(a1@)==model::even_difference_2_2_rhs(c));
    toom_words::sub_exact(a2,a1);
    let ghost q=model::even_difference_2_2_after(c);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a2,15u64);
    assert(value(a2@)==model::even_difference_2_2_after(c));
}
#[inline(always)]
fn even_phase_2(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_2_0(c),
        value(old(a1)@)==model::even_state_2_1(c),
        value(old(a2)@)==model::even_state_2_2(c),
        value(old(a3)@)==model::even_state_2_3(c),
        value(old(a4)@)==model::even_state_2_4(c),
        value(old(a5)@)==model::even_state_2_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_3_0(c),
        value(final(a1)@)==model::even_state_3_1(c),
        value(final(a2)@)==model::even_state_3_2(c),
        value(final(a3)@)==model::even_state_3_3(c),
        value(final(a4)@)==model::even_state_3_4(c),
        value(final(a5)@)==model::even_state_3_5(c),
{
    proof {
        reveal(model::even_state_2_0);
        reveal(model::even_state_2_1);
        reveal(model::even_state_2_2);
        reveal(model::even_state_2_3);
        reveal(model::even_state_2_4);
        reveal(model::even_state_2_5);
        reveal(model::even_state_3_0);
        reveal(model::even_state_3_1);
        reveal(model::even_state_3_2);
        reveal(model::even_state_3_3);
        reveal(model::even_state_3_4);
        reveal(model::even_state_3_5);
    }
    proof { model::even_difference_3_5(c); }
    assert(value(a5@)==model::even_difference_3_5_before(c));
    assert(value(a4@)==model::even_difference_3_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::even_difference_3_5_after(c);
    proof { lemma_mod_multiples_basic(63int*q,16int); }
    toom_words::divide_exact(a5,16u64);
    assert(value(a5@)==63int*q);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a5,63u64);
    assert(value(a5@)==model::even_difference_3_5_after(c));
    proof { model::even_difference_3_4(c); }
    assert(value(a4@)==model::even_difference_3_4_before(c));
    assert(value(a3@)==model::even_difference_3_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::even_difference_3_4_after(c);
    proof { lemma_mod_multiples_basic(63int*q,4int); }
    toom_words::divide_exact(a4,4u64);
    assert(value(a4@)==63int*q);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a4,63u64);
    assert(value(a4@)==model::even_difference_3_4_after(c));
    proof { model::even_difference_3_3(c); }
    assert(value(a3@)==model::even_difference_3_3_before(c));
    assert(value(a2@)==model::even_difference_3_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::even_difference_3_3_after(c);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a3,63u64);
    assert(value(a3@)==model::even_difference_3_3_after(c));
}
#[inline(always)]
fn even_phase_3(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_3_0(c),
        value(old(a1)@)==model::even_state_3_1(c),
        value(old(a2)@)==model::even_state_3_2(c),
        value(old(a3)@)==model::even_state_3_3(c),
        value(old(a4)@)==model::even_state_3_4(c),
        value(old(a5)@)==model::even_state_3_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_4_0(c),
        value(final(a1)@)==model::even_state_4_1(c),
        value(final(a2)@)==model::even_state_4_2(c),
        value(final(a3)@)==model::even_state_4_3(c),
        value(final(a4)@)==model::even_state_4_4(c),
        value(final(a5)@)==model::even_state_4_5(c),
{
    proof {
        reveal(model::even_state_3_0);
        reveal(model::even_state_3_1);
        reveal(model::even_state_3_2);
        reveal(model::even_state_3_3);
        reveal(model::even_state_3_4);
        reveal(model::even_state_3_5);
        reveal(model::even_state_4_0);
        reveal(model::even_state_4_1);
        reveal(model::even_state_4_2);
        reveal(model::even_state_4_3);
        reveal(model::even_state_4_4);
        reveal(model::even_state_4_5);
    }
    proof { model::even_difference_4_5(c); }
    assert(value(a5@)==model::even_difference_4_5_before(c));
    assert(value(a4@)==model::even_difference_4_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::even_difference_4_5_after(c);
    proof { lemma_mod_multiples_basic(255int*q,4int); }
    toom_words::divide_exact(a5,4u64);
    assert(value(a5@)==255int*q);
    proof { lemma_mod_multiples_basic(q,255int); }
    wide_odd_division::divide_toom8_odd(a5,255u64);
    assert(value(a5@)==model::even_difference_4_5_after(c));
    proof { model::even_difference_4_4(c); }
    assert(value(a4@)==model::even_difference_4_4_before(c));
    assert(value(a3@)==model::even_difference_4_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::even_difference_4_4_after(c);
    proof { lemma_mod_multiples_basic(q,255int); }
    wide_odd_division::divide_toom8_odd(a4,255u64);
    assert(value(a4@)==model::even_difference_4_4_after(c));
}
#[inline(always)]
fn even_phase_4(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_4_0(c),
        value(old(a1)@)==model::even_state_4_1(c),
        value(old(a2)@)==model::even_state_4_2(c),
        value(old(a3)@)==model::even_state_4_3(c),
        value(old(a4)@)==model::even_state_4_4(c),
        value(old(a5)@)==model::even_state_4_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_5_0(c),
        value(final(a1)@)==model::even_state_5_1(c),
        value(final(a2)@)==model::even_state_5_2(c),
        value(final(a3)@)==model::even_state_5_3(c),
        value(final(a4)@)==model::even_state_5_4(c),
        value(final(a5)@)==model::even_state_5_5(c),
{
    proof {
        reveal(model::even_state_4_0);
        reveal(model::even_state_4_1);
        reveal(model::even_state_4_2);
        reveal(model::even_state_4_3);
        reveal(model::even_state_4_4);
        reveal(model::even_state_4_5);
        reveal(model::even_state_5_0);
        reveal(model::even_state_5_1);
        reveal(model::even_state_5_2);
        reveal(model::even_state_5_3);
        reveal(model::even_state_5_4);
        reveal(model::even_state_5_5);
    }
    proof { model::even_difference_5_5(c); }
    assert(value(a5@)==model::even_difference_5_5_before(c));
    assert(value(a4@)==model::even_difference_5_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::even_difference_5_5_after(c);
    proof { lemma_mod_multiples_basic(q,1023int); }
    wide_odd_division::divide_toom8_odd(a5,1023u64);
    assert(value(a5@)==model::even_difference_5_5_after(c));
}
#[inline(always)]
fn even_phase_5(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_5_0(c),
        value(old(a1)@)==model::even_state_5_1(c),
        value(old(a2)@)==model::even_state_5_2(c),
        value(old(a3)@)==model::even_state_5_3(c),
        value(old(a4)@)==model::even_state_5_4(c),
        value(old(a5)@)==model::even_state_5_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_6_0(c),
        value(final(a1)@)==model::even_state_6_1(c),
        value(final(a2)@)==model::even_state_6_2(c),
        value(final(a3)@)==model::even_state_6_3(c),
        value(final(a4)@)==model::even_state_6_4(c),
        value(final(a5)@)==model::even_state_6_5(c),
{
    proof {
        reveal(model::even_state_5_0);
        reveal(model::even_state_5_1);
        reveal(model::even_state_5_2);
        reveal(model::even_state_5_3);
        reveal(model::even_state_5_4);
        reveal(model::even_state_5_5);
        reveal(model::even_state_6_0);
        reveal(model::even_state_6_1);
        reveal(model::even_state_6_2);
        reveal(model::even_state_6_3);
        reveal(model::even_state_6_4);
        reveal(model::even_state_6_5);
    }
    proof { model::even_convert_4_4(c); }
    assert(value(a4@)==model::even_convert_4_4_before(c));
    assert(value(a5@)==model::even_convert_4_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,256u64);
    assert(value(a4@)==model::even_convert_4_4_after(c));
}
#[inline(always)]
fn even_phase_6(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_6_0(c),
        value(old(a1)@)==model::even_state_6_1(c),
        value(old(a2)@)==model::even_state_6_2(c),
        value(old(a3)@)==model::even_state_6_3(c),
        value(old(a4)@)==model::even_state_6_4(c),
        value(old(a5)@)==model::even_state_6_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_7_0(c),
        value(final(a1)@)==model::even_state_7_1(c),
        value(final(a2)@)==model::even_state_7_2(c),
        value(final(a3)@)==model::even_state_7_3(c),
        value(final(a4)@)==model::even_state_7_4(c),
        value(final(a5)@)==model::even_state_7_5(c),
{
    proof {
        reveal(model::even_state_6_0);
        reveal(model::even_state_6_1);
        reveal(model::even_state_6_2);
        reveal(model::even_state_6_3);
        reveal(model::even_state_6_4);
        reveal(model::even_state_6_5);
        reveal(model::even_state_7_0);
        reveal(model::even_state_7_1);
        reveal(model::even_state_7_2);
        reveal(model::even_state_7_3);
        reveal(model::even_state_7_4);
        reveal(model::even_state_7_5);
    }
    proof { model::even_convert_3_3(c); }
    assert(value(a3@)==model::even_convert_3_3_before(c));
    assert(value(a4@)==model::even_convert_3_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,64u64);
    assert(value(a3@)==model::even_convert_3_3_after(c));
    proof { model::even_convert_3_4(c); }
    assert(value(a4@)==model::even_convert_3_4_before(c));
    assert(value(a5@)==model::even_convert_3_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,64u64);
    assert(value(a4@)==model::even_convert_3_4_after(c));
}
#[inline(always)]
fn even_phase_7(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_7_0(c),
        value(old(a1)@)==model::even_state_7_1(c),
        value(old(a2)@)==model::even_state_7_2(c),
        value(old(a3)@)==model::even_state_7_3(c),
        value(old(a4)@)==model::even_state_7_4(c),
        value(old(a5)@)==model::even_state_7_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_8_0(c),
        value(final(a1)@)==model::even_state_8_1(c),
        value(final(a2)@)==model::even_state_8_2(c),
        value(final(a3)@)==model::even_state_8_3(c),
        value(final(a4)@)==model::even_state_8_4(c),
        value(final(a5)@)==model::even_state_8_5(c),
{
    proof {
        reveal(model::even_state_7_0);
        reveal(model::even_state_7_1);
        reveal(model::even_state_7_2);
        reveal(model::even_state_7_3);
        reveal(model::even_state_7_4);
        reveal(model::even_state_7_5);
        reveal(model::even_state_8_0);
        reveal(model::even_state_8_1);
        reveal(model::even_state_8_2);
        reveal(model::even_state_8_3);
        reveal(model::even_state_8_4);
        reveal(model::even_state_8_5);
    }
    proof { model::even_convert_2_2(c); }
    assert(value(a2@)==model::even_convert_2_2_before(c));
    assert(value(a3@)==model::even_convert_2_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,16u64);
    assert(value(a2@)==model::even_convert_2_2_after(c));
    proof { model::even_convert_2_3(c); }
    assert(value(a3@)==model::even_convert_2_3_before(c));
    assert(value(a4@)==model::even_convert_2_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,16u64);
    assert(value(a3@)==model::even_convert_2_3_after(c));
    proof { model::even_convert_2_4(c); }
    assert(value(a4@)==model::even_convert_2_4_before(c));
    assert(value(a5@)==model::even_convert_2_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,16u64);
    assert(value(a4@)==model::even_convert_2_4_after(c));
}
#[inline(always)]
fn even_phase_8(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_8_0(c),
        value(old(a1)@)==model::even_state_8_1(c),
        value(old(a2)@)==model::even_state_8_2(c),
        value(old(a3)@)==model::even_state_8_3(c),
        value(old(a4)@)==model::even_state_8_4(c),
        value(old(a5)@)==model::even_state_8_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_9_0(c),
        value(final(a1)@)==model::even_state_9_1(c),
        value(final(a2)@)==model::even_state_9_2(c),
        value(final(a3)@)==model::even_state_9_3(c),
        value(final(a4)@)==model::even_state_9_4(c),
        value(final(a5)@)==model::even_state_9_5(c),
{
    proof {
        reveal(model::even_state_8_0);
        reveal(model::even_state_8_1);
        reveal(model::even_state_8_2);
        reveal(model::even_state_8_3);
        reveal(model::even_state_8_4);
        reveal(model::even_state_8_5);
        reveal(model::even_state_9_0);
        reveal(model::even_state_9_1);
        reveal(model::even_state_9_2);
        reveal(model::even_state_9_3);
        reveal(model::even_state_9_4);
        reveal(model::even_state_9_5);
    }
    proof { model::even_convert_1_1(c); }
    assert(value(a1@)==model::even_convert_1_1_before(c));
    assert(value(a2@)==model::even_convert_1_1_rhs(c));
    scaled_subtraction::sub_scaled_exact(a1,a2,4u64);
    assert(value(a1@)==model::even_convert_1_1_after(c));
    proof { model::even_convert_1_2(c); }
    assert(value(a2@)==model::even_convert_1_2_before(c));
    assert(value(a3@)==model::even_convert_1_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,4u64);
    assert(value(a2@)==model::even_convert_1_2_after(c));
    proof { model::even_convert_1_3(c); }
    assert(value(a3@)==model::even_convert_1_3_before(c));
    assert(value(a4@)==model::even_convert_1_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,4u64);
    assert(value(a3@)==model::even_convert_1_3_after(c));
    proof { model::even_convert_1_4(c); }
    assert(value(a4@)==model::even_convert_1_4_before(c));
    assert(value(a5@)==model::even_convert_1_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,4u64);
    assert(value(a4@)==model::even_convert_1_4_after(c));
}
#[inline(always)]
fn even_phase_9(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_9_0(c),
        value(old(a1)@)==model::even_state_9_1(c),
        value(old(a2)@)==model::even_state_9_2(c),
        value(old(a3)@)==model::even_state_9_3(c),
        value(old(a4)@)==model::even_state_9_4(c),
        value(old(a5)@)==model::even_state_9_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_10_0(c),
        value(final(a1)@)==model::even_state_10_1(c),
        value(final(a2)@)==model::even_state_10_2(c),
        value(final(a3)@)==model::even_state_10_3(c),
        value(final(a4)@)==model::even_state_10_4(c),
        value(final(a5)@)==model::even_state_10_5(c),
{
    proof {
        reveal(model::even_state_9_0);
        reveal(model::even_state_9_1);
        reveal(model::even_state_9_2);
        reveal(model::even_state_9_3);
        reveal(model::even_state_9_4);
        reveal(model::even_state_9_5);
        reveal(model::even_state_10_0);
        reveal(model::even_state_10_1);
        reveal(model::even_state_10_2);
        reveal(model::even_state_10_3);
        reveal(model::even_state_10_4);
        reveal(model::even_state_10_5);
    }
    proof { model::even_convert_0_0(c); }
    assert(value(a0@)==model::even_convert_0_0_before(c));
    assert(value(a1@)==model::even_convert_0_0_rhs(c));
    scaled_subtraction::sub_scaled_exact(a0,a1,1u64);
    assert(value(a0@)==model::even_convert_0_0_after(c));
    proof { model::even_convert_0_1(c); }
    assert(value(a1@)==model::even_convert_0_1_before(c));
    assert(value(a2@)==model::even_convert_0_1_rhs(c));
    scaled_subtraction::sub_scaled_exact(a1,a2,1u64);
    assert(value(a1@)==model::even_convert_0_1_after(c));
    proof { model::even_convert_0_2(c); }
    assert(value(a2@)==model::even_convert_0_2_before(c));
    assert(value(a3@)==model::even_convert_0_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,1u64);
    assert(value(a2@)==model::even_convert_0_2_after(c));
    proof { model::even_convert_0_3(c); }
    assert(value(a3@)==model::even_convert_0_3_before(c));
    assert(value(a4@)==model::even_convert_0_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,1u64);
    assert(value(a3@)==model::even_convert_0_3_after(c));
    proof { model::even_convert_0_4(c); }
    assert(value(a4@)==model::even_convert_0_4_before(c));
    assert(value(a5@)==model::even_convert_0_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,1u64);
    assert(value(a4@)==model::even_convert_0_4_after(c));
}
#[inline(always)]
fn even_phase_10(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::even_state_10_0(c),
        value(old(a1)@)==model::even_state_10_1(c),
        value(old(a2)@)==model::even_state_10_2(c),
        value(old(a3)@)==model::even_state_10_3(c),
        value(old(a4)@)==model::even_state_10_4(c),
        value(old(a5)@)==model::even_state_10_5(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==model::even_state_11_0(c),
        value(final(a1)@)==model::even_state_11_1(c),
        value(final(a2)@)==model::even_state_11_2(c),
        value(final(a3)@)==model::even_state_11_3(c),
        value(final(a4)@)==model::even_state_11_4(c),
        value(final(a5)@)==model::even_state_11_5(c),
{
    proof {
        reveal(model::even_state_10_0);
        reveal(model::even_state_10_1);
        reveal(model::even_state_10_2);
        reveal(model::even_state_10_3);
        reveal(model::even_state_10_4);
        reveal(model::even_state_10_5);
        reveal(model::even_state_11_0);
        reveal(model::even_state_11_1);
        reveal(model::even_state_11_2);
        reveal(model::even_state_11_3);
        reveal(model::even_state_11_4);
        reveal(model::even_state_11_5);
    }
    proof { lemma_mod_multiples_basic(c[0],1073741824int); }
    toom_words::divide_exact(a0,1073741824u64);
    assert(value(a0@)==c[0]);
    proof { lemma_mod_multiples_basic(c[1],16777216int); }
    toom_words::divide_exact(a1,16777216u64);
    assert(value(a1@)==c[1]);
    proof { lemma_mod_multiples_basic(c[2],262144int); }
    toom_words::divide_exact(a2,262144u64);
    assert(value(a2@)==c[2]);
    proof { lemma_mod_multiples_basic(c[3],4096int); }
    toom_words::divide_exact(a3,4096u64);
    assert(value(a3@)==c[3]);
    proof { lemma_mod_multiples_basic(c[4],64int); }
    toom_words::divide_exact(a4,64u64);
    assert(value(a4@)==c[4]);
}
pub fn even(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==1073741824int*c[0]+16777216int*c[1]+262144int*c[2]+4096int*c[3]+64int*c[4]+1int*c[5],
        value(old(a1)@)==1073741824int*c[0]+67108864int*c[1]+4194304int*c[2]+262144int*c[3]+16384int*c[4]+1024int*c[5],
        value(old(a2)@)==1073741824int*c[0]+268435456int*c[1]+67108864int*c[2]+16777216int*c[3]+4194304int*c[4]+1048576int*c[5],
        value(old(a3)@)==1073741824int*c[0]+1073741824int*c[1]+1073741824int*c[2]+1073741824int*c[3]+1073741824int*c[4]+1073741824int*c[5],
        value(old(a4)@)==1073741824int*c[0]+4294967296int*c[1]+17179869184int*c[2]+68719476736int*c[3]+274877906944int*c[4]+1099511627776int*c[5],
        value(old(a5)@)==1073741824int*c[0]+17179869184int*c[1]+274877906944int*c[2]+4398046511104int*c[3]+70368744177664int*c[4]+1125899906842624int*c[5],
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==c[0],
        value(final(a1)@)==c[1],
        value(final(a2)@)==c[2],
        value(final(a3)@)==c[3],
        value(final(a4)@)==c[4],
        value(final(a5)@)==c[5],
{
    assert!(a1.len()==a0.len() && a2.len()==a0.len() && a3.len()==a0.len() && a4.len()==a0.len() && a5.len()==a0.len());
    proof {
        reveal(model::even_state_0_0);
        reveal(model::even_state_0_1);
        reveal(model::even_state_0_2);
        reveal(model::even_state_0_3);
        reveal(model::even_state_0_4);
        reveal(model::even_state_0_5);
        reveal(model::even_state_11_0);
        reveal(model::even_state_11_1);
        reveal(model::even_state_11_2);
        reveal(model::even_state_11_3);
        reveal(model::even_state_11_4);
        reveal(model::even_state_11_5);
    }
    even_phase_0(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_1(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_2(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_3(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_4(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_5(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_6(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_7(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_8(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_9(a0,a1,a2,a3,a4,a5,Ghost(c));
    even_phase_10(a0,a1,a2,a3,a4,a5,Ghost(c));
}
#[inline(always)]
fn odd_phase_0(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_0_0(c),
        value(old(a1)@)==model::odd_state_0_1(c),
        value(old(a2)@)==model::odd_state_0_2(c),
        value(old(a3)@)==model::odd_state_0_3(c),
        value(old(a4)@)==model::odd_state_0_4(c),
        value(old(a5)@)==model::odd_state_0_5(c),
        value(old(a6)@)==model::odd_state_0_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_1_0(c),
        value(final(a1)@)==model::odd_state_1_1(c),
        value(final(a2)@)==model::odd_state_1_2(c),
        value(final(a3)@)==model::odd_state_1_3(c),
        value(final(a4)@)==model::odd_state_1_4(c),
        value(final(a5)@)==model::odd_state_1_5(c),
        value(final(a6)@)==model::odd_state_1_6(c),
{
    proof {
        reveal(model::odd_state_0_0);
        reveal(model::odd_state_0_1);
        reveal(model::odd_state_0_2);
        reveal(model::odd_state_0_3);
        reveal(model::odd_state_0_4);
        reveal(model::odd_state_0_5);
        reveal(model::odd_state_0_6);
        reveal(model::odd_state_1_0);
        reveal(model::odd_state_1_1);
        reveal(model::odd_state_1_2);
        reveal(model::odd_state_1_3);
        reveal(model::odd_state_1_4);
        reveal(model::odd_state_1_5);
        reveal(model::odd_state_1_6);
    }
    proof { model::odd_difference_1_6(c); }
    assert(value(a6@)==model::odd_difference_1_6_before(c));
    assert(value(a5@)==model::odd_difference_1_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_1_6_after(c);
    proof { lemma_mod_multiples_basic(3int*q,1024int); }
    toom_words::divide_exact(a6,1024u64);
    assert(value(a6@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a6,3u64);
    assert(value(a6@)==model::odd_difference_1_6_after(c));
    proof { model::odd_difference_1_5(c); }
    assert(value(a5@)==model::odd_difference_1_5_before(c));
    assert(value(a4@)==model::odd_difference_1_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::odd_difference_1_5_after(c);
    proof { lemma_mod_multiples_basic(3int*q,256int); }
    toom_words::divide_exact(a5,256u64);
    assert(value(a5@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a5,3u64);
    assert(value(a5@)==model::odd_difference_1_5_after(c));
    proof { model::odd_difference_1_4(c); }
    assert(value(a4@)==model::odd_difference_1_4_before(c));
    assert(value(a3@)==model::odd_difference_1_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::odd_difference_1_4_after(c);
    proof { lemma_mod_multiples_basic(3int*q,64int); }
    toom_words::divide_exact(a4,64u64);
    assert(value(a4@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a4,3u64);
    assert(value(a4@)==model::odd_difference_1_4_after(c));
    proof { model::odd_difference_1_3(c); }
    assert(value(a3@)==model::odd_difference_1_3_before(c));
    assert(value(a2@)==model::odd_difference_1_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::odd_difference_1_3_after(c);
    proof { lemma_mod_multiples_basic(3int*q,16int); }
    toom_words::divide_exact(a3,16u64);
    assert(value(a3@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a3,3u64);
    assert(value(a3@)==model::odd_difference_1_3_after(c));
    proof { model::odd_difference_1_2(c); }
    assert(value(a2@)==model::odd_difference_1_2_before(c));
    assert(value(a1@)==model::odd_difference_1_2_rhs(c));
    toom_words::sub_exact(a2,a1);
    let ghost q=model::odd_difference_1_2_after(c);
    proof { lemma_mod_multiples_basic(3int*q,4int); }
    toom_words::divide_exact(a2,4u64);
    assert(value(a2@)==3int*q);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a2,3u64);
    assert(value(a2@)==model::odd_difference_1_2_after(c));
    proof { model::odd_difference_1_1(c); }
    assert(value(a1@)==model::odd_difference_1_1_before(c));
    assert(value(a0@)==model::odd_difference_1_1_rhs(c));
    toom_words::sub_exact(a1,a0);
    let ghost q=model::odd_difference_1_1_after(c);
    proof { lemma_mod_multiples_basic(q,3int); }
    wide_odd_division::divide_toom8_odd(a1,3u64);
    assert(value(a1@)==model::odd_difference_1_1_after(c));
}
#[inline(always)]
fn odd_phase_1(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_1_0(c),
        value(old(a1)@)==model::odd_state_1_1(c),
        value(old(a2)@)==model::odd_state_1_2(c),
        value(old(a3)@)==model::odd_state_1_3(c),
        value(old(a4)@)==model::odd_state_1_4(c),
        value(old(a5)@)==model::odd_state_1_5(c),
        value(old(a6)@)==model::odd_state_1_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_2_0(c),
        value(final(a1)@)==model::odd_state_2_1(c),
        value(final(a2)@)==model::odd_state_2_2(c),
        value(final(a3)@)==model::odd_state_2_3(c),
        value(final(a4)@)==model::odd_state_2_4(c),
        value(final(a5)@)==model::odd_state_2_5(c),
        value(final(a6)@)==model::odd_state_2_6(c),
{
    proof {
        reveal(model::odd_state_1_0);
        reveal(model::odd_state_1_1);
        reveal(model::odd_state_1_2);
        reveal(model::odd_state_1_3);
        reveal(model::odd_state_1_4);
        reveal(model::odd_state_1_5);
        reveal(model::odd_state_1_6);
        reveal(model::odd_state_2_0);
        reveal(model::odd_state_2_1);
        reveal(model::odd_state_2_2);
        reveal(model::odd_state_2_3);
        reveal(model::odd_state_2_4);
        reveal(model::odd_state_2_5);
        reveal(model::odd_state_2_6);
    }
    proof { model::odd_difference_2_6(c); }
    assert(value(a6@)==model::odd_difference_2_6_before(c));
    assert(value(a5@)==model::odd_difference_2_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_2_6_after(c);
    proof { lemma_mod_multiples_basic(15int*q,256int); }
    toom_words::divide_exact(a6,256u64);
    assert(value(a6@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a6,15u64);
    assert(value(a6@)==model::odd_difference_2_6_after(c));
    proof { model::odd_difference_2_5(c); }
    assert(value(a5@)==model::odd_difference_2_5_before(c));
    assert(value(a4@)==model::odd_difference_2_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::odd_difference_2_5_after(c);
    proof { lemma_mod_multiples_basic(15int*q,64int); }
    toom_words::divide_exact(a5,64u64);
    assert(value(a5@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a5,15u64);
    assert(value(a5@)==model::odd_difference_2_5_after(c));
    proof { model::odd_difference_2_4(c); }
    assert(value(a4@)==model::odd_difference_2_4_before(c));
    assert(value(a3@)==model::odd_difference_2_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::odd_difference_2_4_after(c);
    proof { lemma_mod_multiples_basic(15int*q,16int); }
    toom_words::divide_exact(a4,16u64);
    assert(value(a4@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a4,15u64);
    assert(value(a4@)==model::odd_difference_2_4_after(c));
    proof { model::odd_difference_2_3(c); }
    assert(value(a3@)==model::odd_difference_2_3_before(c));
    assert(value(a2@)==model::odd_difference_2_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::odd_difference_2_3_after(c);
    proof { lemma_mod_multiples_basic(15int*q,4int); }
    toom_words::divide_exact(a3,4u64);
    assert(value(a3@)==15int*q);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a3,15u64);
    assert(value(a3@)==model::odd_difference_2_3_after(c));
    proof { model::odd_difference_2_2(c); }
    assert(value(a2@)==model::odd_difference_2_2_before(c));
    assert(value(a1@)==model::odd_difference_2_2_rhs(c));
    toom_words::sub_exact(a2,a1);
    let ghost q=model::odd_difference_2_2_after(c);
    proof { lemma_mod_multiples_basic(q,15int); }
    wide_odd_division::divide_toom8_odd(a2,15u64);
    assert(value(a2@)==model::odd_difference_2_2_after(c));
}
#[inline(always)]
fn odd_phase_2(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_2_0(c),
        value(old(a1)@)==model::odd_state_2_1(c),
        value(old(a2)@)==model::odd_state_2_2(c),
        value(old(a3)@)==model::odd_state_2_3(c),
        value(old(a4)@)==model::odd_state_2_4(c),
        value(old(a5)@)==model::odd_state_2_5(c),
        value(old(a6)@)==model::odd_state_2_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_3_0(c),
        value(final(a1)@)==model::odd_state_3_1(c),
        value(final(a2)@)==model::odd_state_3_2(c),
        value(final(a3)@)==model::odd_state_3_3(c),
        value(final(a4)@)==model::odd_state_3_4(c),
        value(final(a5)@)==model::odd_state_3_5(c),
        value(final(a6)@)==model::odd_state_3_6(c),
{
    proof {
        reveal(model::odd_state_2_0);
        reveal(model::odd_state_2_1);
        reveal(model::odd_state_2_2);
        reveal(model::odd_state_2_3);
        reveal(model::odd_state_2_4);
        reveal(model::odd_state_2_5);
        reveal(model::odd_state_2_6);
        reveal(model::odd_state_3_0);
        reveal(model::odd_state_3_1);
        reveal(model::odd_state_3_2);
        reveal(model::odd_state_3_3);
        reveal(model::odd_state_3_4);
        reveal(model::odd_state_3_5);
        reveal(model::odd_state_3_6);
    }
    proof { model::odd_difference_3_6(c); }
    assert(value(a6@)==model::odd_difference_3_6_before(c));
    assert(value(a5@)==model::odd_difference_3_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_3_6_after(c);
    proof { lemma_mod_multiples_basic(63int*q,64int); }
    toom_words::divide_exact(a6,64u64);
    assert(value(a6@)==63int*q);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a6,63u64);
    assert(value(a6@)==model::odd_difference_3_6_after(c));
    proof { model::odd_difference_3_5(c); }
    assert(value(a5@)==model::odd_difference_3_5_before(c));
    assert(value(a4@)==model::odd_difference_3_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::odd_difference_3_5_after(c);
    proof { lemma_mod_multiples_basic(63int*q,16int); }
    toom_words::divide_exact(a5,16u64);
    assert(value(a5@)==63int*q);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a5,63u64);
    assert(value(a5@)==model::odd_difference_3_5_after(c));
    proof { model::odd_difference_3_4(c); }
    assert(value(a4@)==model::odd_difference_3_4_before(c));
    assert(value(a3@)==model::odd_difference_3_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::odd_difference_3_4_after(c);
    proof { lemma_mod_multiples_basic(63int*q,4int); }
    toom_words::divide_exact(a4,4u64);
    assert(value(a4@)==63int*q);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a4,63u64);
    assert(value(a4@)==model::odd_difference_3_4_after(c));
    proof { model::odd_difference_3_3(c); }
    assert(value(a3@)==model::odd_difference_3_3_before(c));
    assert(value(a2@)==model::odd_difference_3_3_rhs(c));
    toom_words::sub_exact(a3,a2);
    let ghost q=model::odd_difference_3_3_after(c);
    proof { lemma_mod_multiples_basic(q,63int); }
    wide_odd_division::divide_toom8_odd(a3,63u64);
    assert(value(a3@)==model::odd_difference_3_3_after(c));
}
#[inline(always)]
fn odd_phase_3(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_3_0(c),
        value(old(a1)@)==model::odd_state_3_1(c),
        value(old(a2)@)==model::odd_state_3_2(c),
        value(old(a3)@)==model::odd_state_3_3(c),
        value(old(a4)@)==model::odd_state_3_4(c),
        value(old(a5)@)==model::odd_state_3_5(c),
        value(old(a6)@)==model::odd_state_3_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_4_0(c),
        value(final(a1)@)==model::odd_state_4_1(c),
        value(final(a2)@)==model::odd_state_4_2(c),
        value(final(a3)@)==model::odd_state_4_3(c),
        value(final(a4)@)==model::odd_state_4_4(c),
        value(final(a5)@)==model::odd_state_4_5(c),
        value(final(a6)@)==model::odd_state_4_6(c),
{
    proof {
        reveal(model::odd_state_3_0);
        reveal(model::odd_state_3_1);
        reveal(model::odd_state_3_2);
        reveal(model::odd_state_3_3);
        reveal(model::odd_state_3_4);
        reveal(model::odd_state_3_5);
        reveal(model::odd_state_3_6);
        reveal(model::odd_state_4_0);
        reveal(model::odd_state_4_1);
        reveal(model::odd_state_4_2);
        reveal(model::odd_state_4_3);
        reveal(model::odd_state_4_4);
        reveal(model::odd_state_4_5);
        reveal(model::odd_state_4_6);
    }
    proof { model::odd_difference_4_6(c); }
    assert(value(a6@)==model::odd_difference_4_6_before(c));
    assert(value(a5@)==model::odd_difference_4_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_4_6_after(c);
    proof { lemma_mod_multiples_basic(255int*q,16int); }
    toom_words::divide_exact(a6,16u64);
    assert(value(a6@)==255int*q);
    proof { lemma_mod_multiples_basic(q,255int); }
    wide_odd_division::divide_toom8_odd(a6,255u64);
    assert(value(a6@)==model::odd_difference_4_6_after(c));
    proof { model::odd_difference_4_5(c); }
    assert(value(a5@)==model::odd_difference_4_5_before(c));
    assert(value(a4@)==model::odd_difference_4_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::odd_difference_4_5_after(c);
    proof { lemma_mod_multiples_basic(255int*q,4int); }
    toom_words::divide_exact(a5,4u64);
    assert(value(a5@)==255int*q);
    proof { lemma_mod_multiples_basic(q,255int); }
    wide_odd_division::divide_toom8_odd(a5,255u64);
    assert(value(a5@)==model::odd_difference_4_5_after(c));
    proof { model::odd_difference_4_4(c); }
    assert(value(a4@)==model::odd_difference_4_4_before(c));
    assert(value(a3@)==model::odd_difference_4_4_rhs(c));
    toom_words::sub_exact(a4,a3);
    let ghost q=model::odd_difference_4_4_after(c);
    proof { lemma_mod_multiples_basic(q,255int); }
    wide_odd_division::divide_toom8_odd(a4,255u64);
    assert(value(a4@)==model::odd_difference_4_4_after(c));
}
#[inline(always)]
fn odd_phase_4(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_4_0(c),
        value(old(a1)@)==model::odd_state_4_1(c),
        value(old(a2)@)==model::odd_state_4_2(c),
        value(old(a3)@)==model::odd_state_4_3(c),
        value(old(a4)@)==model::odd_state_4_4(c),
        value(old(a5)@)==model::odd_state_4_5(c),
        value(old(a6)@)==model::odd_state_4_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_5_0(c),
        value(final(a1)@)==model::odd_state_5_1(c),
        value(final(a2)@)==model::odd_state_5_2(c),
        value(final(a3)@)==model::odd_state_5_3(c),
        value(final(a4)@)==model::odd_state_5_4(c),
        value(final(a5)@)==model::odd_state_5_5(c),
        value(final(a6)@)==model::odd_state_5_6(c),
{
    proof {
        reveal(model::odd_state_4_0);
        reveal(model::odd_state_4_1);
        reveal(model::odd_state_4_2);
        reveal(model::odd_state_4_3);
        reveal(model::odd_state_4_4);
        reveal(model::odd_state_4_5);
        reveal(model::odd_state_4_6);
        reveal(model::odd_state_5_0);
        reveal(model::odd_state_5_1);
        reveal(model::odd_state_5_2);
        reveal(model::odd_state_5_3);
        reveal(model::odd_state_5_4);
        reveal(model::odd_state_5_5);
        reveal(model::odd_state_5_6);
    }
    proof { model::odd_difference_5_6(c); }
    assert(value(a6@)==model::odd_difference_5_6_before(c));
    assert(value(a5@)==model::odd_difference_5_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_5_6_after(c);
    proof { lemma_mod_multiples_basic(1023int*q,4int); }
    toom_words::divide_exact(a6,4u64);
    assert(value(a6@)==1023int*q);
    proof { lemma_mod_multiples_basic(q,1023int); }
    wide_odd_division::divide_toom8_odd(a6,1023u64);
    assert(value(a6@)==model::odd_difference_5_6_after(c));
    proof { model::odd_difference_5_5(c); }
    assert(value(a5@)==model::odd_difference_5_5_before(c));
    assert(value(a4@)==model::odd_difference_5_5_rhs(c));
    toom_words::sub_exact(a5,a4);
    let ghost q=model::odd_difference_5_5_after(c);
    proof { lemma_mod_multiples_basic(q,1023int); }
    wide_odd_division::divide_toom8_odd(a5,1023u64);
    assert(value(a5@)==model::odd_difference_5_5_after(c));
}
#[inline(always)]
fn odd_phase_5(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_5_0(c),
        value(old(a1)@)==model::odd_state_5_1(c),
        value(old(a2)@)==model::odd_state_5_2(c),
        value(old(a3)@)==model::odd_state_5_3(c),
        value(old(a4)@)==model::odd_state_5_4(c),
        value(old(a5)@)==model::odd_state_5_5(c),
        value(old(a6)@)==model::odd_state_5_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_6_0(c),
        value(final(a1)@)==model::odd_state_6_1(c),
        value(final(a2)@)==model::odd_state_6_2(c),
        value(final(a3)@)==model::odd_state_6_3(c),
        value(final(a4)@)==model::odd_state_6_4(c),
        value(final(a5)@)==model::odd_state_6_5(c),
        value(final(a6)@)==model::odd_state_6_6(c),
{
    proof {
        reveal(model::odd_state_5_0);
        reveal(model::odd_state_5_1);
        reveal(model::odd_state_5_2);
        reveal(model::odd_state_5_3);
        reveal(model::odd_state_5_4);
        reveal(model::odd_state_5_5);
        reveal(model::odd_state_5_6);
        reveal(model::odd_state_6_0);
        reveal(model::odd_state_6_1);
        reveal(model::odd_state_6_2);
        reveal(model::odd_state_6_3);
        reveal(model::odd_state_6_4);
        reveal(model::odd_state_6_5);
        reveal(model::odd_state_6_6);
    }
    proof { model::odd_difference_6_6(c); }
    assert(value(a6@)==model::odd_difference_6_6_before(c));
    assert(value(a5@)==model::odd_difference_6_6_rhs(c));
    toom_words::sub_exact(a6,a5);
    let ghost q=model::odd_difference_6_6_after(c);
    proof { lemma_mod_multiples_basic(q,4095int); }
    wide_odd_division::divide_toom8_odd(a6,4095u64);
    assert(value(a6@)==model::odd_difference_6_6_after(c));
}
#[inline(always)]
fn odd_phase_6(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_6_0(c),
        value(old(a1)@)==model::odd_state_6_1(c),
        value(old(a2)@)==model::odd_state_6_2(c),
        value(old(a3)@)==model::odd_state_6_3(c),
        value(old(a4)@)==model::odd_state_6_4(c),
        value(old(a5)@)==model::odd_state_6_5(c),
        value(old(a6)@)==model::odd_state_6_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_7_0(c),
        value(final(a1)@)==model::odd_state_7_1(c),
        value(final(a2)@)==model::odd_state_7_2(c),
        value(final(a3)@)==model::odd_state_7_3(c),
        value(final(a4)@)==model::odd_state_7_4(c),
        value(final(a5)@)==model::odd_state_7_5(c),
        value(final(a6)@)==model::odd_state_7_6(c),
{
    proof {
        reveal(model::odd_state_6_0);
        reveal(model::odd_state_6_1);
        reveal(model::odd_state_6_2);
        reveal(model::odd_state_6_3);
        reveal(model::odd_state_6_4);
        reveal(model::odd_state_6_5);
        reveal(model::odd_state_6_6);
        reveal(model::odd_state_7_0);
        reveal(model::odd_state_7_1);
        reveal(model::odd_state_7_2);
        reveal(model::odd_state_7_3);
        reveal(model::odd_state_7_4);
        reveal(model::odd_state_7_5);
        reveal(model::odd_state_7_6);
    }
    proof { model::odd_convert_5_5(c); }
    assert(value(a5@)==model::odd_convert_5_5_before(c));
    assert(value(a6@)==model::odd_convert_5_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,1024u64);
    assert(value(a5@)==model::odd_convert_5_5_after(c));
}
#[inline(always)]
fn odd_phase_7(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_7_0(c),
        value(old(a1)@)==model::odd_state_7_1(c),
        value(old(a2)@)==model::odd_state_7_2(c),
        value(old(a3)@)==model::odd_state_7_3(c),
        value(old(a4)@)==model::odd_state_7_4(c),
        value(old(a5)@)==model::odd_state_7_5(c),
        value(old(a6)@)==model::odd_state_7_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_8_0(c),
        value(final(a1)@)==model::odd_state_8_1(c),
        value(final(a2)@)==model::odd_state_8_2(c),
        value(final(a3)@)==model::odd_state_8_3(c),
        value(final(a4)@)==model::odd_state_8_4(c),
        value(final(a5)@)==model::odd_state_8_5(c),
        value(final(a6)@)==model::odd_state_8_6(c),
{
    proof {
        reveal(model::odd_state_7_0);
        reveal(model::odd_state_7_1);
        reveal(model::odd_state_7_2);
        reveal(model::odd_state_7_3);
        reveal(model::odd_state_7_4);
        reveal(model::odd_state_7_5);
        reveal(model::odd_state_7_6);
        reveal(model::odd_state_8_0);
        reveal(model::odd_state_8_1);
        reveal(model::odd_state_8_2);
        reveal(model::odd_state_8_3);
        reveal(model::odd_state_8_4);
        reveal(model::odd_state_8_5);
        reveal(model::odd_state_8_6);
    }
    proof { model::odd_convert_4_4(c); }
    assert(value(a4@)==model::odd_convert_4_4_before(c));
    assert(value(a5@)==model::odd_convert_4_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,256u64);
    assert(value(a4@)==model::odd_convert_4_4_after(c));
    proof { model::odd_convert_4_5(c); }
    assert(value(a5@)==model::odd_convert_4_5_before(c));
    assert(value(a6@)==model::odd_convert_4_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,256u64);
    assert(value(a5@)==model::odd_convert_4_5_after(c));
}
#[inline(always)]
fn odd_phase_8(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_8_0(c),
        value(old(a1)@)==model::odd_state_8_1(c),
        value(old(a2)@)==model::odd_state_8_2(c),
        value(old(a3)@)==model::odd_state_8_3(c),
        value(old(a4)@)==model::odd_state_8_4(c),
        value(old(a5)@)==model::odd_state_8_5(c),
        value(old(a6)@)==model::odd_state_8_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_9_0(c),
        value(final(a1)@)==model::odd_state_9_1(c),
        value(final(a2)@)==model::odd_state_9_2(c),
        value(final(a3)@)==model::odd_state_9_3(c),
        value(final(a4)@)==model::odd_state_9_4(c),
        value(final(a5)@)==model::odd_state_9_5(c),
        value(final(a6)@)==model::odd_state_9_6(c),
{
    proof {
        reveal(model::odd_state_8_0);
        reveal(model::odd_state_8_1);
        reveal(model::odd_state_8_2);
        reveal(model::odd_state_8_3);
        reveal(model::odd_state_8_4);
        reveal(model::odd_state_8_5);
        reveal(model::odd_state_8_6);
        reveal(model::odd_state_9_0);
        reveal(model::odd_state_9_1);
        reveal(model::odd_state_9_2);
        reveal(model::odd_state_9_3);
        reveal(model::odd_state_9_4);
        reveal(model::odd_state_9_5);
        reveal(model::odd_state_9_6);
    }
    proof { model::odd_convert_3_3(c); }
    assert(value(a3@)==model::odd_convert_3_3_before(c));
    assert(value(a4@)==model::odd_convert_3_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,64u64);
    assert(value(a3@)==model::odd_convert_3_3_after(c));
    proof { model::odd_convert_3_4(c); }
    assert(value(a4@)==model::odd_convert_3_4_before(c));
    assert(value(a5@)==model::odd_convert_3_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,64u64);
    assert(value(a4@)==model::odd_convert_3_4_after(c));
    proof { model::odd_convert_3_5(c); }
    assert(value(a5@)==model::odd_convert_3_5_before(c));
    assert(value(a6@)==model::odd_convert_3_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,64u64);
    assert(value(a5@)==model::odd_convert_3_5_after(c));
}
#[inline(always)]
fn odd_phase_9(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_9_0(c),
        value(old(a1)@)==model::odd_state_9_1(c),
        value(old(a2)@)==model::odd_state_9_2(c),
        value(old(a3)@)==model::odd_state_9_3(c),
        value(old(a4)@)==model::odd_state_9_4(c),
        value(old(a5)@)==model::odd_state_9_5(c),
        value(old(a6)@)==model::odd_state_9_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_10_0(c),
        value(final(a1)@)==model::odd_state_10_1(c),
        value(final(a2)@)==model::odd_state_10_2(c),
        value(final(a3)@)==model::odd_state_10_3(c),
        value(final(a4)@)==model::odd_state_10_4(c),
        value(final(a5)@)==model::odd_state_10_5(c),
        value(final(a6)@)==model::odd_state_10_6(c),
{
    proof {
        reveal(model::odd_state_9_0);
        reveal(model::odd_state_9_1);
        reveal(model::odd_state_9_2);
        reveal(model::odd_state_9_3);
        reveal(model::odd_state_9_4);
        reveal(model::odd_state_9_5);
        reveal(model::odd_state_9_6);
        reveal(model::odd_state_10_0);
        reveal(model::odd_state_10_1);
        reveal(model::odd_state_10_2);
        reveal(model::odd_state_10_3);
        reveal(model::odd_state_10_4);
        reveal(model::odd_state_10_5);
        reveal(model::odd_state_10_6);
    }
    proof { model::odd_convert_2_2(c); }
    assert(value(a2@)==model::odd_convert_2_2_before(c));
    assert(value(a3@)==model::odd_convert_2_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,16u64);
    assert(value(a2@)==model::odd_convert_2_2_after(c));
    proof { model::odd_convert_2_3(c); }
    assert(value(a3@)==model::odd_convert_2_3_before(c));
    assert(value(a4@)==model::odd_convert_2_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,16u64);
    assert(value(a3@)==model::odd_convert_2_3_after(c));
    proof { model::odd_convert_2_4(c); }
    assert(value(a4@)==model::odd_convert_2_4_before(c));
    assert(value(a5@)==model::odd_convert_2_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,16u64);
    assert(value(a4@)==model::odd_convert_2_4_after(c));
    proof { model::odd_convert_2_5(c); }
    assert(value(a5@)==model::odd_convert_2_5_before(c));
    assert(value(a6@)==model::odd_convert_2_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,16u64);
    assert(value(a5@)==model::odd_convert_2_5_after(c));
}
#[inline(always)]
fn odd_phase_10(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_10_0(c),
        value(old(a1)@)==model::odd_state_10_1(c),
        value(old(a2)@)==model::odd_state_10_2(c),
        value(old(a3)@)==model::odd_state_10_3(c),
        value(old(a4)@)==model::odd_state_10_4(c),
        value(old(a5)@)==model::odd_state_10_5(c),
        value(old(a6)@)==model::odd_state_10_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_11_0(c),
        value(final(a1)@)==model::odd_state_11_1(c),
        value(final(a2)@)==model::odd_state_11_2(c),
        value(final(a3)@)==model::odd_state_11_3(c),
        value(final(a4)@)==model::odd_state_11_4(c),
        value(final(a5)@)==model::odd_state_11_5(c),
        value(final(a6)@)==model::odd_state_11_6(c),
{
    proof {
        reveal(model::odd_state_10_0);
        reveal(model::odd_state_10_1);
        reveal(model::odd_state_10_2);
        reveal(model::odd_state_10_3);
        reveal(model::odd_state_10_4);
        reveal(model::odd_state_10_5);
        reveal(model::odd_state_10_6);
        reveal(model::odd_state_11_0);
        reveal(model::odd_state_11_1);
        reveal(model::odd_state_11_2);
        reveal(model::odd_state_11_3);
        reveal(model::odd_state_11_4);
        reveal(model::odd_state_11_5);
        reveal(model::odd_state_11_6);
    }
    proof { model::odd_convert_1_1(c); }
    assert(value(a1@)==model::odd_convert_1_1_before(c));
    assert(value(a2@)==model::odd_convert_1_1_rhs(c));
    scaled_subtraction::sub_scaled_exact(a1,a2,4u64);
    assert(value(a1@)==model::odd_convert_1_1_after(c));
    proof { model::odd_convert_1_2(c); }
    assert(value(a2@)==model::odd_convert_1_2_before(c));
    assert(value(a3@)==model::odd_convert_1_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,4u64);
    assert(value(a2@)==model::odd_convert_1_2_after(c));
    proof { model::odd_convert_1_3(c); }
    assert(value(a3@)==model::odd_convert_1_3_before(c));
    assert(value(a4@)==model::odd_convert_1_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,4u64);
    assert(value(a3@)==model::odd_convert_1_3_after(c));
    proof { model::odd_convert_1_4(c); }
    assert(value(a4@)==model::odd_convert_1_4_before(c));
    assert(value(a5@)==model::odd_convert_1_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,4u64);
    assert(value(a4@)==model::odd_convert_1_4_after(c));
    proof { model::odd_convert_1_5(c); }
    assert(value(a5@)==model::odd_convert_1_5_before(c));
    assert(value(a6@)==model::odd_convert_1_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,4u64);
    assert(value(a5@)==model::odd_convert_1_5_after(c));
}
#[inline(always)]
fn odd_phase_11(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_11_0(c),
        value(old(a1)@)==model::odd_state_11_1(c),
        value(old(a2)@)==model::odd_state_11_2(c),
        value(old(a3)@)==model::odd_state_11_3(c),
        value(old(a4)@)==model::odd_state_11_4(c),
        value(old(a5)@)==model::odd_state_11_5(c),
        value(old(a6)@)==model::odd_state_11_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_12_0(c),
        value(final(a1)@)==model::odd_state_12_1(c),
        value(final(a2)@)==model::odd_state_12_2(c),
        value(final(a3)@)==model::odd_state_12_3(c),
        value(final(a4)@)==model::odd_state_12_4(c),
        value(final(a5)@)==model::odd_state_12_5(c),
        value(final(a6)@)==model::odd_state_12_6(c),
{
    proof {
        reveal(model::odd_state_11_0);
        reveal(model::odd_state_11_1);
        reveal(model::odd_state_11_2);
        reveal(model::odd_state_11_3);
        reveal(model::odd_state_11_4);
        reveal(model::odd_state_11_5);
        reveal(model::odd_state_11_6);
        reveal(model::odd_state_12_0);
        reveal(model::odd_state_12_1);
        reveal(model::odd_state_12_2);
        reveal(model::odd_state_12_3);
        reveal(model::odd_state_12_4);
        reveal(model::odd_state_12_5);
        reveal(model::odd_state_12_6);
    }
    proof { model::odd_convert_0_0(c); }
    assert(value(a0@)==model::odd_convert_0_0_before(c));
    assert(value(a1@)==model::odd_convert_0_0_rhs(c));
    scaled_subtraction::sub_scaled_exact(a0,a1,1u64);
    assert(value(a0@)==model::odd_convert_0_0_after(c));
    proof { model::odd_convert_0_1(c); }
    assert(value(a1@)==model::odd_convert_0_1_before(c));
    assert(value(a2@)==model::odd_convert_0_1_rhs(c));
    scaled_subtraction::sub_scaled_exact(a1,a2,1u64);
    assert(value(a1@)==model::odd_convert_0_1_after(c));
    proof { model::odd_convert_0_2(c); }
    assert(value(a2@)==model::odd_convert_0_2_before(c));
    assert(value(a3@)==model::odd_convert_0_2_rhs(c));
    scaled_subtraction::sub_scaled_exact(a2,a3,1u64);
    assert(value(a2@)==model::odd_convert_0_2_after(c));
    proof { model::odd_convert_0_3(c); }
    assert(value(a3@)==model::odd_convert_0_3_before(c));
    assert(value(a4@)==model::odd_convert_0_3_rhs(c));
    scaled_subtraction::sub_scaled_exact(a3,a4,1u64);
    assert(value(a3@)==model::odd_convert_0_3_after(c));
    proof { model::odd_convert_0_4(c); }
    assert(value(a4@)==model::odd_convert_0_4_before(c));
    assert(value(a5@)==model::odd_convert_0_4_rhs(c));
    scaled_subtraction::sub_scaled_exact(a4,a5,1u64);
    assert(value(a4@)==model::odd_convert_0_4_after(c));
    proof { model::odd_convert_0_5(c); }
    assert(value(a5@)==model::odd_convert_0_5_before(c));
    assert(value(a6@)==model::odd_convert_0_5_rhs(c));
    scaled_subtraction::sub_scaled_exact(a5,a6,1u64);
    assert(value(a5@)==model::odd_convert_0_5_after(c));
}
#[inline(always)]
fn odd_phase_12(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==model::odd_state_12_0(c),
        value(old(a1)@)==model::odd_state_12_1(c),
        value(old(a2)@)==model::odd_state_12_2(c),
        value(old(a3)@)==model::odd_state_12_3(c),
        value(old(a4)@)==model::odd_state_12_4(c),
        value(old(a5)@)==model::odd_state_12_5(c),
        value(old(a6)@)==model::odd_state_12_6(c),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==model::odd_state_13_0(c),
        value(final(a1)@)==model::odd_state_13_1(c),
        value(final(a2)@)==model::odd_state_13_2(c),
        value(final(a3)@)==model::odd_state_13_3(c),
        value(final(a4)@)==model::odd_state_13_4(c),
        value(final(a5)@)==model::odd_state_13_5(c),
        value(final(a6)@)==model::odd_state_13_6(c),
{
    proof {
        reveal(model::odd_state_12_0);
        reveal(model::odd_state_12_1);
        reveal(model::odd_state_12_2);
        reveal(model::odd_state_12_3);
        reveal(model::odd_state_12_4);
        reveal(model::odd_state_12_5);
        reveal(model::odd_state_12_6);
        reveal(model::odd_state_13_0);
        reveal(model::odd_state_13_1);
        reveal(model::odd_state_13_2);
        reveal(model::odd_state_13_3);
        reveal(model::odd_state_13_4);
        reveal(model::odd_state_13_5);
        reveal(model::odd_state_13_6);
    }
    proof { lemma_mod_multiples_basic(c[0],68719476736int); }
    toom_words::divide_exact(a0,68719476736u64);
    assert(value(a0@)==c[0]);
    proof { lemma_mod_multiples_basic(c[1],1073741824int); }
    toom_words::divide_exact(a1,1073741824u64);
    assert(value(a1@)==c[1]);
    proof { lemma_mod_multiples_basic(c[2],16777216int); }
    toom_words::divide_exact(a2,16777216u64);
    assert(value(a2@)==c[2]);
    proof { lemma_mod_multiples_basic(c[3],262144int); }
    toom_words::divide_exact(a3,262144u64);
    assert(value(a3@)==c[3]);
    proof { lemma_mod_multiples_basic(c[4],4096int); }
    toom_words::divide_exact(a4,4096u64);
    assert(value(a4@)==c[4]);
    proof { lemma_mod_multiples_basic(c[5],64int); }
    toom_words::divide_exact(a5,64u64);
    assert(value(a5@)==c[5]);
}
pub fn odd(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires model::nonnegative(c),
        old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==68719476736int*c[0]+1073741824int*c[1]+16777216int*c[2]+262144int*c[3]+4096int*c[4]+64int*c[5]+1int*c[6],
        value(old(a1)@)==68719476736int*c[0]+4294967296int*c[1]+268435456int*c[2]+16777216int*c[3]+1048576int*c[4]+65536int*c[5]+4096int*c[6],
        value(old(a2)@)==68719476736int*c[0]+17179869184int*c[1]+4294967296int*c[2]+1073741824int*c[3]+268435456int*c[4]+67108864int*c[5]+16777216int*c[6],
        value(old(a3)@)==68719476736int*c[0]+68719476736int*c[1]+68719476736int*c[2]+68719476736int*c[3]+68719476736int*c[4]+68719476736int*c[5]+68719476736int*c[6],
        value(old(a4)@)==68719476736int*c[0]+274877906944int*c[1]+1099511627776int*c[2]+4398046511104int*c[3]+17592186044416int*c[4]+70368744177664int*c[5]+281474976710656int*c[6],
        value(old(a5)@)==68719476736int*c[0]+1099511627776int*c[1]+17592186044416int*c[2]+281474976710656int*c[3]+4503599627370496int*c[4]+72057594037927936int*c[5]+1152921504606846976int*c[6],
        value(old(a6)@)==68719476736int*c[0]+4398046511104int*c[1]+281474976710656int*c[2]+18014398509481984int*c[3]+1152921504606846976int*c[4]+73786976294838206464int*c[5]+4722366482869645213696int*c[6],
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==c[0],
        value(final(a1)@)==c[1],
        value(final(a2)@)==c[2],
        value(final(a3)@)==c[3],
        value(final(a4)@)==c[4],
        value(final(a5)@)==c[5],
        value(final(a6)@)==c[6],
{
    assert!(a1.len()==a0.len() && a2.len()==a0.len() && a3.len()==a0.len() && a4.len()==a0.len() && a5.len()==a0.len() && a6.len()==a0.len());
    proof {
        reveal(model::odd_state_0_0);
        reveal(model::odd_state_0_1);
        reveal(model::odd_state_0_2);
        reveal(model::odd_state_0_3);
        reveal(model::odd_state_0_4);
        reveal(model::odd_state_0_5);
        reveal(model::odd_state_0_6);
        reveal(model::odd_state_13_0);
        reveal(model::odd_state_13_1);
        reveal(model::odd_state_13_2);
        reveal(model::odd_state_13_3);
        reveal(model::odd_state_13_4);
        reveal(model::odd_state_13_5);
        reveal(model::odd_state_13_6);
    }
    odd_phase_0(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_1(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_2(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_3(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_4(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_5(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_6(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_7(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_8(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_9(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_10(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_11(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
    odd_phase_12(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
}
}
