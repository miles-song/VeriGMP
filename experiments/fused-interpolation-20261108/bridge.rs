//! Verified test adapter: coefficient meanings come from independent input slices.
use vstd::prelude::*;
use verigmp::radix::*;
verus! {
pub fn interpolate(p1:&mut[u64],pm:&mut[u64],p2:&mut[u64],z0:&[u64],z4:&[u64],negative:bool,
    scratch:&mut[u64],c1:&[u64],c2:&[u64],c3:&[u64])
    requires old(p1)@.len()==old(pm)@.len(),old(p1)@.len()==old(p2)@.len(),
        old(scratch)@.len()==old(p1)@.len(),z0@.len()<=old(p1)@.len(),z4@.len()<=old(p1)@.len(),
        64*(value(z0@)+value(c1@)+value(c2@)+value(c3@)+value(z4@))<radix(old(p1)@.len()),
        value(old(p1)@)==value(z0@)+value(c1@)+value(c2@)+value(c3@)+value(z4@),
        (if negative {-value(old(pm)@)}else{value(old(pm)@)})
            ==value(z0@)-value(c1@)+value(c2@)-value(c3@)+value(z4@),
        value(old(p2)@)==value(z0@)+2*value(c1@)+4*value(c2@)+8*value(c3@)+16*value(z4@),
    ensures final(p1)@.len()==old(p1)@.len(),final(pm)@.len()==old(pm)@.len(),
        final(p2)@.len()==old(p2)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(p1)@)==value(c1@),value(final(pm)@)==value(c2@),value(final(p2)@)==value(c3@),
{
    proof {
        prefix_range(z0@,z0@.len());prefix_range(c1@,c1@.len());prefix_range(c2@,c2@.len());
        prefix_range(c3@,c3@.len());prefix_range(z4@,z4@.len());
    }
    let ghost coefficients=seq![value(z0@),value(c1@),value(c2@),value(c3@),value(z4@)];
    verigmp::toom_interpolate::interpolate(p1,pm,p2,z0,z4,negative,scratch,Ghost(coefficients));
}
}
