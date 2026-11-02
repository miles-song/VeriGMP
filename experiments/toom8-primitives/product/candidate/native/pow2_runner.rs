//! Unverified text driver. Production functions operate on borrowed arrays.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;

fn main() {
    use std::io::{self, BufRead, Write};
    let mut output = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line.expect("input I/O");
        let mut fields = line.split_whitespace();
        let op = fields.next().expect("operation");
        if op == "layout" {
            let bits = fields.next().expect("precision").parse().unwrap();
            let (n, top) = pow2::precision_layout(bits);
            writeln!(output, "{n} {top}").expect("output I/O");
            continue;
        }
        let top: u32 = fields.next().expect("top bits").parse().unwrap();
        let words: Vec<u64> = fields.map(|s| s.parse().expect("u64")).collect();
        let result = match op {
            "mask" => vec![pow2::mask_word(words[0], top)],
            "norm" => { let mut dst = words; pow2::normalize_top(&mut dst, top); dst },
            "add" | "sub" | "subraw" => {
                assert!(words.len() % 2 == 0);
                let n = words.len() / 2;
                let mut dst = vec![u64::MAX;n+2];dst[1..n+1].copy_from_slice(&words[..n]);
                if op=="add" {pow2::add_mod_assign(&mut dst[1..n+1], &words[n..], top);}
                else if op=="sub" {pow2::sub_mod_assign(&mut dst[1..n+1], &words[n..], top);}
                else {let borrow=limbs::sub_assign(&mut dst[1..n+1],&words[n..]);
                    assert_eq!((dst[0],dst[n+1]),(u64::MAX,u64::MAX));
                    let mut result=dst[1..n+1].to_vec();result.push(borrow);
                    writeln!(output,"{}",result.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();continue;}
                assert_eq!((dst[0],dst[n+1]),(u64::MAX,u64::MAX));dst[1..n+1].to_vec()
            },
            _ => panic!("unsupported operation"),
        };
        writeln!(output, "{}", result.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).expect("output I/O");
    }
}
