// Unverified harness input checks. Kernel assertions and canary failures are not rejections.
fn harness_reject(site: &str) -> ! {
    eprintln!("COMPOSITION_HARNESS_REJECTED {}", site);
    std::process::exit(2)
}

fn harness_require(ok: bool, site: &str) {
    if !ok { harness_reject(site); }
}

fn harness_capacity(provided: usize, required: usize) {
    harness_require(provided >= required, "scratch_capacity");
}

fn harness_validate(op: &str, args: &[u64]) {
    match op {
        "weighted4" | "signed4" | "signeddirect4" => {
            let offset = if op == "weighted4" { 4 } else { 1 };
            harness_require(args.len() >= offset + 2, "evaluation_shape");
            let n = args[offset] as usize;
            let h = args[offset + 1] as usize;
            harness_require(h <= n && n <= (args.len() - offset - 2) / 3
                && args.len() == offset + 2 + 3 * n + h, "evaluation_shape");
            harness_require(if op == "weighted4" {
                args[..4].iter().all(|x| *x <= 8) && args[..4].iter().sum::<u64>() <= 15
            } else { args[0] <= 1 }, "evaluation_weights");
        }
        "signedlimb4" => {
            harness_require(args.len() == 6, "signed_limb_shape");
            harness_require(args[0] <= 1 && args[1] <= 15, "signed_limb_domain");
        }
        "negatewords" => {}
        "oddlimb" => {
            harness_require(args.len() == 3, "odd_limb_shape");
            harness_require(matches!(args[0], 3 | 9 | 15) && args[1] < args[0], "odd_limb_domain");
        }
        "exactodd" | "exactapi" => {
            harness_require(!args.is_empty(), "exact_shape");
            let divisor = args[0];
            harness_require(divisor > 0, "exact_divisor");
            harness_require(op != "exactodd" || matches!(divisor, 3 | 9 | 15), "odd_divisor");
            let mut rem = 0u128;
            for word in args[1..].iter().rev() {
                rem = ((rem << 64) + *word as u128) % divisor as u128;
            }
            harness_require(rem == 0, "exact_multiple");
        }
        "subscaled" => {
            harness_require(args.len() >= 3, "subscaled_shape");
            let n = args[1] as usize;
            let m = args[2] as usize;
            harness_require(m <= n && n <= args.len() - 3 && m == args.len() - 3 - n, "subscaled_shape");
            let original = &args[3..3+n];
            let rhs = &args[3+n..];
            let mut product = vec![0u64; n+1];
            let mut carry = 0u128;
            for i in 0..m {
                let value = (args[0] as u128) * (rhs[i] as u128) + carry;
                product[i] = value as u64;
                carry = value >> 64;
            }
            product[m] = carry as u64;
            harness_require(product[n] == 0
                && original.iter().rev().cmp(product[..n].iter().rev()) != std::cmp::Ordering::Less,
                "subscaled_domain");
        }
        "divide" => harness_require(!args.is_empty() && args[0] > 0, "divide_domain"),
        "squarebase" | "squarebaselow" => harness_require(!args.is_empty(), "base_square_shape"),
        "workspace" => harness_require(args.len() == 1, "workspace_shape"),
        "row" => {
            harness_require(args.len() >= 3, "row_shape");
            let n = args[1] as usize;
            let m = args[2] as usize;
            harness_require(n <= args.len() - 3 && m == args.len() - 3 - n && m >= n, "row_shape");
        }
        "full4" | "full4same" | "squarefull4" | "low4" | "squarelow4" | "candidate4"
            | "candidate4square" | "shortscratch4" | "full" | "low" | "default" | "same"
            | "shortscratch" | "squarefull" | "squarek" | "squarelow" | "square" => {
            harness_require(args.len() >= 6 && (args.len() - 4) % 2 == 0, "arithmetic_shape");
            harness_require((1..=64).contains(&args[0]), "arithmetic_parameters");
            if op == "squarek" {
                harness_require(args[1] >= 8, "arithmetic_parameters");
            } else if matches!(op, "full4" | "full4same" | "squarefull4" | "shortscratch4" | "full" | "squarefull") {
                harness_require(args[1] >= 24, "arithmetic_parameters");
            } else if matches!(op, "low4" | "squarelow4" | "low" | "squarelow") {
                harness_require(args[1] >= 24 && args[2] >= 24 && args[3] <= 2, "arithmetic_parameters");
            }
        }
        _ => harness_reject("operation"),
    }
}
