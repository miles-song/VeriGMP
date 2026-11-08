use verigmp::fast_words::combine_cross;

fn alias_z0() {
    let mut words = [0u64; 2];
    combine_cross(&mut words, &words, &[], true);
}

fn alias_z2() {
    let mut words = [0u64; 2];
    let z0 = [0u64; 2];
    combine_cross(&mut words, &z0, &words, true);
}

fn main() { alias_z0(); alias_z2(); }
