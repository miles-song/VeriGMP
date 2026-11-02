//! Unverified I/O harness for arbitrary-length limb inputs.
#[path = "specs/radix.rs"]
mod radix;
#[path = "verified/kernel.rs"]
mod kernel;
#[path = "verified/limbs.rs"]
mod limbs;

fn main() {
    use std::io::{self, BufRead, Write};
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line.expect("input I/O");
        let words: Vec<u64> = line.split_whitespace().map(|s| s.parse().expect("u64")).collect();
        assert!(words.len() % 2 == 0);
        let n = words.len() / 2;
        let mut dst = words[..n].to_vec();
        let carry = limbs::add_assign(&mut dst, &words[n..]);
        write!(output, "{carry}").expect("output I/O");
        for limb in dst { write!(output, " {limb}").expect("output I/O"); }
        writeln!(output).expect("output I/O");
    }
}
