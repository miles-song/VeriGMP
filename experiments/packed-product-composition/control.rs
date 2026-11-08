//! Ordinary optimized client with the same calls and no Verus specifications.
use verigmp::{packed_layout as layout, toom_multiply};

pub fn consume(
    output: &mut [u64], left: &[u64], right: &[u64],
    packed_left: &mut [u64], packed_right: &mut [u64],
    product: &mut [u64], scratch: &mut [u64],
    count: usize, p: usize, q: usize, slot: usize,
) -> Result<(), layout::PackedLayoutError> {
    let result_count = 2 * count;
    match layout::pack_coefficients(packed_left, left, count, p, slot) {
        Ok(()) => {},
        Err(error) => return Err(error),
    }
    match layout::pack_coefficients(packed_right, right, count, p, slot) {
        Ok(()) => {},
        Err(error) => return Err(error),
    }
    if count > 0 {
        toom_multiply::full(product, packed_left, packed_right, scratch, 24);
    }
    let result = layout::extract_coefficients(output, product, result_count, q, slot);
    match result {
        Ok(()) => {},
        Err(error) => return Err(error),
    }
    Ok(())
}
