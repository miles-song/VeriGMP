//! Test-only verified callers; supplied coefficient inputs define the ghost witness.
use vstd::prelude::*;
use crate::{radix::*,toom8_newton,toom8_newton_spec as model};
verus! {
#[inline(always)]
pub fn even(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],c0:&[u64],c1:&[u64],c2:&[u64],c3:&[u64],c4:&[u64],c5:&[u64])
    requires old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        value(old(a0)@)==1073741824int*value(c0@)+16777216int*value(c1@)+262144int*value(c2@)+4096int*value(c3@)+64int*value(c4@)+1int*value(c5@),
        value(old(a1)@)==1073741824int*value(c0@)+67108864int*value(c1@)+4194304int*value(c2@)+262144int*value(c3@)+16384int*value(c4@)+1024int*value(c5@),
        value(old(a2)@)==1073741824int*value(c0@)+268435456int*value(c1@)+67108864int*value(c2@)+16777216int*value(c3@)+4194304int*value(c4@)+1048576int*value(c5@),
        value(old(a3)@)==1073741824int*value(c0@)+1073741824int*value(c1@)+1073741824int*value(c2@)+1073741824int*value(c3@)+1073741824int*value(c4@)+1073741824int*value(c5@),
        value(old(a4)@)==1073741824int*value(c0@)+4294967296int*value(c1@)+17179869184int*value(c2@)+68719476736int*value(c3@)+274877906944int*value(c4@)+1099511627776int*value(c5@),
        value(old(a5)@)==1073741824int*value(c0@)+17179869184int*value(c1@)+274877906944int*value(c2@)+4398046511104int*value(c3@)+70368744177664int*value(c4@)+1125899906842624int*value(c5@),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        value(final(a0)@)==value(c0@),
        value(final(a1)@)==value(c1@),
        value(final(a2)@)==value(c2@),
        value(final(a3)@)==value(c3@),
        value(final(a4)@)==value(c4@),
        value(final(a5)@)==value(c5@),
{
    let ghost c=seq![value(c0@),value(c1@),value(c2@),value(c3@),value(c4@),value(c5@),0];
    proof {
        prefix_range(c0@,c0@.len());
        prefix_range(c1@,c1@.len());
        prefix_range(c2@,c2@.len());
        prefix_range(c3@,c3@.len());
        prefix_range(c4@,c4@.len());
        prefix_range(c5@,c5@.len());
        assert(model::nonnegative(c));
    }
    toom8_newton::even(a0,a1,a2,a3,a4,a5,Ghost(c));
}
#[inline(always)]
pub fn odd(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64],c0:&[u64],c1:&[u64],c2:&[u64],c3:&[u64],c4:&[u64],c5:&[u64],c6:&[u64])
    requires old(a1)@.len()==old(a0)@.len(),
        old(a2)@.len()==old(a0)@.len(),
        old(a3)@.len()==old(a0)@.len(),
        old(a4)@.len()==old(a0)@.len(),
        old(a5)@.len()==old(a0)@.len(),
        old(a6)@.len()==old(a0)@.len(),
        value(old(a0)@)==68719476736int*value(c0@)+1073741824int*value(c1@)+16777216int*value(c2@)+262144int*value(c3@)+4096int*value(c4@)+64int*value(c5@)+1int*value(c6@),
        value(old(a1)@)==68719476736int*value(c0@)+4294967296int*value(c1@)+268435456int*value(c2@)+16777216int*value(c3@)+1048576int*value(c4@)+65536int*value(c5@)+4096int*value(c6@),
        value(old(a2)@)==68719476736int*value(c0@)+17179869184int*value(c1@)+4294967296int*value(c2@)+1073741824int*value(c3@)+268435456int*value(c4@)+67108864int*value(c5@)+16777216int*value(c6@),
        value(old(a3)@)==68719476736int*value(c0@)+68719476736int*value(c1@)+68719476736int*value(c2@)+68719476736int*value(c3@)+68719476736int*value(c4@)+68719476736int*value(c5@)+68719476736int*value(c6@),
        value(old(a4)@)==68719476736int*value(c0@)+274877906944int*value(c1@)+1099511627776int*value(c2@)+4398046511104int*value(c3@)+17592186044416int*value(c4@)+70368744177664int*value(c5@)+281474976710656int*value(c6@),
        value(old(a5)@)==68719476736int*value(c0@)+1099511627776int*value(c1@)+17592186044416int*value(c2@)+281474976710656int*value(c3@)+4503599627370496int*value(c4@)+72057594037927936int*value(c5@)+1152921504606846976int*value(c6@),
        value(old(a6)@)==68719476736int*value(c0@)+4398046511104int*value(c1@)+281474976710656int*value(c2@)+18014398509481984int*value(c3@)+1152921504606846976int*value(c4@)+73786976294838206464int*value(c5@)+4722366482869645213696int*value(c6@),
    ensures final(a0)@.len()==old(a0)@.len(),
        final(a1)@.len()==old(a1)@.len(),
        final(a2)@.len()==old(a2)@.len(),
        final(a3)@.len()==old(a3)@.len(),
        final(a4)@.len()==old(a4)@.len(),
        final(a5)@.len()==old(a5)@.len(),
        final(a6)@.len()==old(a6)@.len(),
        value(final(a0)@)==value(c0@),
        value(final(a1)@)==value(c1@),
        value(final(a2)@)==value(c2@),
        value(final(a3)@)==value(c3@),
        value(final(a4)@)==value(c4@),
        value(final(a5)@)==value(c5@),
        value(final(a6)@)==value(c6@),
{
    let ghost c=seq![value(c0@),value(c1@),value(c2@),value(c3@),value(c4@),value(c5@),value(c6@)];
    proof {
        prefix_range(c0@,c0@.len());
        prefix_range(c1@,c1@.len());
        prefix_range(c2@,c2@.len());
        prefix_range(c3@,c3@.len());
        prefix_range(c4@,c4@.len());
        prefix_range(c5@,c5@.len());
        prefix_range(c6@,c6@.len());
        assert(model::nonnegative(c));
    }
    toom8_newton::odd(a0,a1,a2,a3,a4,a5,a6,Ghost(c));
}
}
