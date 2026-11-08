use std::io::{self, BufRead, Write};
use verigmp::{arithmetic, fast_multiply, fast_words, square};

fn main() {
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        let mut fields = line.split_whitespace();
        let op = fields.next().unwrap();
        let args: Vec<u64> = fields.map(|s| s.parse().unwrap()).collect();
        let canary = 0xc0ffeecafef00d17u64;
        let out = if op == "cross" {
            let alias = args[0] != 0;
            let n = args[1] as usize;
            let m = args[2] as usize;
            let negative = args[3] != 0;
            assert!(m <= n);
            assert_eq!(args.len(), 4 + 2 * n + if alias { 0 } else { m });
            let mut dst = vec![canary; n + 2];
            dst[1..n + 1].copy_from_slice(&args[4..4 + n]);
            let z0 = &args[4 + n..4 + 2 * n];
            let z2 = if alias { &z0[n - m..] } else { &args[4 + 2 * n..] };
            let high = fast_words::combine_cross(&mut dst[1..n + 1], z0, z2, negative);
            assert_eq!((dst[0], dst[n + 1]), (canary, canary));
            let mut result = vec![high];
            result.extend_from_slice(&dst[1..n + 1]);
            result
        } else {
            let n = args[0] as usize;
            let parameter = args[1];
            assert!(n > 0);
            let same_input = matches!(op, "square" | "default_square" | "full_same" | "default_same");
            assert_eq!(args.len(), 2 + n * if same_input { 1 } else { 2 });
            let a = &args[2..2 + n];
            let b = if same_input { a } else { &args[2 + n..] };
            let full = matches!(op, "full" | "full_same" | "square");
            let size = if full { 2 * n } else { n };
            let capacity = match op {
                "full" | "full_same" | "square" => 3 * n,
                "default_mul" | "default_same" => 12 * n,
                "default_square" => 10 * n,
                _ => panic!("unknown operation"),
            };
            let mut dst = vec![canary; size + 2];
            let mut scratch = vec![canary; capacity + 2];
            match op {
                "full" | "full_same" => fast_multiply::full(&mut dst[1..size + 1], a, b, &mut scratch[1..capacity + 1], parameter as usize),
                "square" => square::full(&mut dst[1..size + 1], a, &mut scratch[1..capacity + 1], parameter as usize),
                "default_mul" | "default_same" => arithmetic::mul_mod(&mut dst[1..size + 1], a, b, &mut scratch[1..capacity + 1], parameter as u32),
                "default_square" => arithmetic::square_mod(&mut dst[1..size + 1], a, &mut scratch[1..capacity + 1], parameter as u32),
                _ => unreachable!(),
            }
            assert_eq!((dst[0], dst[size + 1]), (canary, canary));
            assert_eq!((scratch[0], scratch[capacity + 1]), (canary, canary));
            dst[1..size + 1].to_vec()
        };
        writeln!(output, "{}", out.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
