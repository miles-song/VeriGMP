//! Unverified fixture driver; all expected words come from the Python oracle.
use packed_product_consumer::consume;
use std::{env, fs};

struct Reader { bytes: Vec<u8>, position: usize }
impl Reader {
    fn word(&mut self) -> u64 {
        let end = self.position.checked_add(8).unwrap();
        let value = u64::from_le_bytes(self.bytes[self.position..end].try_into().unwrap());
        self.position = end;
        value
    }
    fn vector(&mut self) -> Vec<u64> {
        let length: usize = self.word().try_into().unwrap();
        (0..length).map(|_| self.word()).collect()
    }
}

const CANARY: u64 = 0x3519_7fab_24de_608c;
fn guarded(length: usize) -> Vec<u64> {
    let mut result = vec![u64::MAX; length.checked_add(2).unwrap()];
    result[0] = CANARY;
    result[length + 1] = CANARY;
    result
}
fn middle(words: &mut [u64]) -> &mut [u64] {
    let end = words.len() - 1;
    &mut words[1..end]
}
fn intact(words: &[u64], case: usize) {
    assert_eq!(words.first(), Some(&CANARY), "leading canary case {case}");
    assert_eq!(words.last(), Some(&CANARY), "trailing canary case {case}");
}

fn main() {
    let bytes = fs::read(env::args().nth(1).expect("fixture path")).unwrap();
    assert_eq!(&bytes[..8], b"VGMPPRD1");
    let mut reader = Reader { bytes, position: 8 };
    let cases: usize = reader.word().try_into().unwrap();
    for expected_id in 0..cases {
        let id: usize = reader.word().try_into().unwrap();
        assert_eq!(id, expected_id);
        let n: usize = reader.word().try_into().unwrap();
        let p: usize = reader.word().try_into().unwrap();
        let q: usize = reader.word().try_into().unwrap();
        let slot: usize = reader.word().try_into().unwrap();
        let extra: usize = reader.word().try_into().unwrap();
        let left = reader.vector();
        let right = reader.vector();
        let expected_left = reader.vector();
        let expected_right = reader.vector();
        let expected_product = reader.vector();
        let expected_output = reader.vector();
        let mut left_guard = guarded(left.len());
        let mut right_guard = guarded(right.len());
        middle(&mut left_guard).copy_from_slice(&left);
        middle(&mut right_guard).copy_from_slice(&right);
        let mut packed_left = guarded(expected_left.len());
        let mut packed_right = guarded(expected_right.len());
        let mut product = guarded(expected_product.len());
        let mut output = guarded(expected_output.len());
        let mut scratch = guarded(12 * n * slot + extra);
        let result = consume(middle(&mut output), middle(&mut left_guard), middle(&mut right_guard),
                             middle(&mut packed_left), middle(&mut packed_right),
                             middle(&mut product), middle(&mut scratch), n, p, q, slot);
        assert!(result.is_ok(), "consumer returned error for valid case {id}");
        assert_eq!(middle(&mut packed_left), expected_left, "packed left case {id}");
        assert_eq!(middle(&mut packed_right), expected_right, "packed right case {id}");
        assert_eq!(middle(&mut product), expected_product, "integer product case {id}");
        assert_eq!(middle(&mut output), expected_output, "exact coefficients case {id}");
        assert_eq!(middle(&mut left_guard), left, "left changed case {id}");
        assert_eq!(middle(&mut right_guard), right, "right changed case {id}");
        for buffer in [&left_guard, &right_guard, &packed_left, &packed_right,
                       &product, &output, &scratch] { intact(buffer, id); }
    }
    assert_eq!(reader.position, reader.bytes.len(), "unconsumed fixture bytes");
    println!("passed {cases} exact packed-product fixtures with all intermediate words and canaries");
}
