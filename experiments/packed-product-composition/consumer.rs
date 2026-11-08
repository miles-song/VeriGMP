//! A verified client witness of the existing APIs; no new production entry.
use vstd::prelude::*;
use verigmp::{packed_convolution as convolution, packed_layout as layout, packed_product};
use verigmp::{radix, toom_multiply};

verus! {

pub fn consume(
    output: &mut [u64], left: &[u64], right: &[u64],
    packed_left: &mut [u64], packed_right: &mut [u64],
    product: &mut [u64], scratch: &mut [u64],
    count: usize, p: usize, q: usize, slot: usize,
) -> (out: Result<(), layout::PackedLayoutError>)
    requires
        packed_product::guard_domain(count as nat, p as nat, q as nat, slot as nat),
        layout::compact_coefficients(left@, count as nat, p as nat),
        layout::compact_coefficients(right@, count as nat, p as nat),
        old(packed_left)@.len() == count as int * slot as int,
        old(packed_right)@.len() == count as int * slot as int,
        old(product)@.len() == 2 * count as int * slot as int,
        old(scratch)@.len() >= 12 * count as int * slot as int,
        old(output)@.len() == 2 * count as int * layout::coefficient_limbs(q as nat) as int,
    ensures
        out is Ok,
        final(output)@.len() == old(output)@.len(),
        final(packed_left)@.len() == old(packed_left)@.len(),
        final(packed_right)@.len() == old(packed_right)@.len(),
        final(product)@.len() == old(product)@.len(),
        final(scratch)@.len() == old(scratch)@.len(),
        packed_product::exact_output(
            final(output)@, left@, right@, count as nat, p as nat, q as nat,
        ),
{
    // Bring the machine-sized slice lengths into the proof; these unused reads
    // disappear in the optimized client, as checked against its plain control.
    let _lengths = (
        left.len(), right.len(), output.len(), packed_left.len(),
        packed_right.len(), product.len(), scratch.len(),
    );
    proof {
        assert(layout::coefficient_limbs(q as nat) > 0);
        assert(slot > 0);
        assert(2 * count as int <= usize::MAX as int) by(nonlinear_arith)
            requires 12 * count as int * slot as int <= scratch@.len(),
                scratch@.len() <= usize::MAX as int, slot > 0;
    }
    let result_count = 2 * count;
    match layout::pack_coefficients(packed_left, left, count, p, slot) {
        Ok(()) => {},
        Err(error) => { proof { assert(false); } return Err(error); },
    }
    match layout::pack_coefficients(packed_right, right, count, p, slot) {
        Ok(()) => {},
        Err(error) => { proof { assert(false); } return Err(error); },
    }
    proof {
        let a = packed_product::coefficients(left@, count as nat, p as nat);
        let b = packed_product::coefficients(right@, count as nat, p as nat);
        assert(convolution::slots(packed_left@, slot as nat, count as nat) =~= a);
        assert(convolution::slots(packed_right@, slot as nat, count as nat) =~= b);
        convolution::slots_integer(packed_left@, slot as nat, count as nat);
        convolution::slots_integer(packed_right@, slot as nat, count as nat);
    }
    if count > 0 {
        proof {
            assert(packed_left@.len() > 0) by(nonlinear_arith)
                requires count > 0, slot > 0,
                    packed_left@.len() == count as int * slot as int;
            assert(product@.len() == 2 * packed_left@.len()) by(nonlinear_arith)
                requires product@.len() == 2 * count as int * slot as int,
                    packed_left@.len() == count as int * slot as int;
            assert(scratch@.len() >= 12 * packed_left@.len()) by(nonlinear_arith)
                requires scratch@.len() >= 12 * count as int * slot as int,
                    packed_left@.len() == count as int * slot as int;
        }
        toom_multiply::full(product, packed_left, packed_right, scratch, 24);
    }
    proof {
        if count == 0 {
            assert(product@.len() == 0);
            assert(radix::value(product@) == 0);
        }
        packed_product::exact_product_slots(
            left@, right@, product@, count as nat, p as nat, q as nat, slot as nat,
        );
    }
    let result = layout::extract_coefficients(output, product, result_count, q, slot);
    match result {
        Ok(()) => {},
        Err(error) => { proof { assert(false); } return Err(error); },
    }
    proof {
        packed_product::extracted_exact_output(
            output@, product@, left@, right@, count as nat, p as nat, q as nat, slot as nat,
        );
    }
    Ok(())
}

} // verus!
