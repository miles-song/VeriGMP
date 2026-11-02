extern crate experiment;
use std::io::{self, BufRead, Write};

fn main() {
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        let mut fields = line.split_whitespace();
        let operation = fields.next().unwrap();
        let top: u32 = fields.next().unwrap().parse().unwrap();
        let n: usize = fields.next().unwrap().parse().unwrap();
        let words: Vec<u64> = fields.map(|x| x.parse().unwrap()).collect();
        assert!(n > 0 && (1..=64).contains(&top));
        assert_eq!(words.len(), 2 * n);
        let (a, b) = words.split_at(n);
        let capacity = if operation == "square" { 10 * n } else { 12 * n };
        let mut out = vec![u64::MAX; n + 2];
        let mut scratch = vec![u64::MAX; capacity + 2];
        match operation {
            "mul" => experiment::arithmetic::mul_mod(&mut out[1..n + 1], a, b,
                &mut scratch[1..capacity + 1], top),
            "same" => experiment::arithmetic::mul_mod(&mut out[1..n + 1], a, a,
                &mut scratch[1..capacity + 1], top),
            "square" => experiment::arithmetic::square_mod(&mut out[1..n + 1], a,
                &mut scratch[1..capacity + 1], top),
            _ => panic!("operation"),
        }
        assert_eq!((out[0], out[n + 1]), (u64::MAX, u64::MAX));
        assert_eq!((scratch[0], scratch[capacity + 1]), (u64::MAX, u64::MAX));
        writeln!(output, "{}", out[1..n + 1].iter().map(u64::to_string)
            .collect::<Vec<_>>().join(" ")).unwrap();
    }
}
