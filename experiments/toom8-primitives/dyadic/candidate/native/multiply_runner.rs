//! Unverified I/O driver; production arithmetic uses caller-provided slices.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "specs/product.rs"] mod product;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;
#[path = "verified/multiply.rs"] mod multiply;

fn main() {
    use std::io::{self, BufRead, Write};
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line.expect("input I/O");
        let mut fields = line.split_whitespace();
        let op = fields.next().expect("operation");
        let args: Vec<u64> = fields.map(|s| s.parse().expect("u64")).collect();
        let result = match op {
            "mac" => {
                assert_eq!(args.len(), 4);
                let (lo, hi) = multiply::mac(args[0], args[1], args[2], args[3]);
                vec![lo, hi]
            },
            "mul" | "low" => {
                let top: u32 = args[0].try_into().expect("u32");
                assert_eq!((args.len() - 1) % 3, 0);
                let n = (args.len() - 1) / 3;
                let mut dst = args[1..1+n].to_vec();
                let lhs = &args[1+n..1+2*n];
                let rhs = &args[1+2*n..];
                if op == "mul" { multiply::mul_mod(&mut dst, lhs, rhs, top); }
                else { multiply::mul_low(&mut dst, lhs, rhs); }
                dst
            },
            "square" => {
                let top: u32 = args[0].try_into().expect("u32");
                let lhs = &args[1..];
                let mut dst = vec![u64::MAX; lhs.len()];
                multiply::mul_mod(&mut dst, lhs, lhs, top);
                dst
            },
            "row" => {
                let offset: usize = args[0].try_into().unwrap();
                let word = args[1];
                assert_eq!((args.len()-2) % 2, 0);
                let n = (args.len()-2) / 2;
                let mut dst = args[2..2+n].to_vec();
                multiply::add_mul_at(&mut dst, &args[2+n..], word, offset);
                dst
            },
            "word" => {
                let n: usize = args[0].try_into().unwrap();
                let word = args[1];
                let mut dst = args[2..2+n].to_vec();
                let carry = multiply::add_mul_word(&mut dst, &args[2+n..], word);
                dst.insert(0,carry);
                dst
            },
            "badshape" => {
                let mut dst = [1u64;2];
                multiply::mul_mod(&mut dst,&[1],&[2],64);
                dst.to_vec()
            },
            _ => panic!("unsupported operation"),
        };
        writeln!(output, "{}", result.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).expect("output I/O");
    }
}
