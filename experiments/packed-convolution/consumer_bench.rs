//! Same-result consumer benchmark for packed coefficient layouts.
use std::hint::black_box;
use std::time::Instant;
use verigmp::{packed_layout, toom_multiply};

const SEED: u64 = 16_438_731;
const STREAM_SETS: usize = 32;
const REPS: usize = 7;
const MIN_BATCH_NS: u128 = 10_000_000;
const CALIBRATION_TARGET_NS: u128 = 25_000_000;
const PRODUCT_THRESHOLD: usize = 24;
const SHAPES: &[(usize, usize)] = &[
    (0, 7),
    (1, 7),
    (1, 53),
    (2, 17),
    (7, 29),
    (63, 29),
    (64, 29),
    (64, 30),
    (65, 30),
    (257, 17),
    (1024, 7),
    (1024, 17),
    (1024, 29),
    (1024, 53),
];

struct Inputs {
    left: Vec<u64>,
    right: Vec<u64>,
}

struct Workspace {
    packed_left: Vec<u64>,
    packed_right: Vec<u64>,
    product: Vec<u64>,
    scratch: Vec<u64>,
    output: Vec<u64>,
    accumulator: Vec<u128>,
}

impl Workspace {
    fn new(count: usize, slot_words: usize, result_words: usize, direct: bool) -> Self {
        let packed_words = count * slot_words;
        Self {
            packed_left: if direct { Vec::new() } else { vec![0; packed_words] },
            packed_right: if direct { Vec::new() } else { vec![0; packed_words] },
            product: if direct { Vec::new() } else { vec![0; 2 * packed_words] },
            scratch: if direct { Vec::new() } else { vec![0; 12 * packed_words] },
            output: vec![0; 2 * count * result_words],
            accumulator: if direct { vec![0; 2 * count] } else { Vec::new() },
        }
    }
}

fn ceil_log2(n: usize) -> usize {
    if n <= 1 { 0 } else { usize::BITS as usize - (n - 1).leading_zeros() as usize }
}

fn slot_words(count: usize, precision: usize) -> usize {
    let coefficient_words = precision.div_ceil(64);
    if count == 0 {
        return coefficient_words;
    }
    let result_bits = 2 * precision + ceil_log2(count);
    coefficient_words.max(result_bits.div_ceil(64))
}

fn result_precision(count: usize, input_precision: usize) -> usize {
    if count == 0 {
        input_precision
    } else {
        2 * input_precision + ceil_log2(count)
    }
}

fn random_word(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

fn make_inputs(count: usize, precision: usize) -> Vec<Inputs> {
    let coefficient_mask = (1u64 << precision) - 1;
    (0..STREAM_SETS)
        .map(|set| {
            let mut state = SEED
                ^ (count as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15)
                ^ (precision as u64).wrapping_mul(0xd1b5_4a32_d192_ed03)
                ^ (set as u64).wrapping_mul(0x94d0_49bb_1331_11eb);
            if state == 0 {
                state = 1;
            }
            let mut next = || random_word(&mut state) & coefficient_mask;
            let left = (0..count).map(|_| next()).collect();
            let right = (0..count).map(|_| next()).collect();
            Inputs { left, right }
        })
        .collect()
}

fn bulk_zero_pack(dst: &mut [u64], src: &[u64], count: usize, precision: usize, slot: usize) {
    let layout = packed_layout::checked_layout(count, precision, slot)
        .unwrap_or_else(|_| panic!("valid benchmark layout"));
    assert_eq!(src.len(), layout.source_words);
    assert_eq!(dst.len(), layout.packed_words);
    dst.fill(0);
    for coefficient in 0..count {
        let source_start = coefficient * layout.coefficient_limbs;
        let destination_start = coefficient * slot;
        dst[destination_start..destination_start + layout.coefficient_limbs]
            .copy_from_slice(&src[source_start..source_start + layout.coefficient_limbs]);
    }
}

fn packed_composition(work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    packed_layout::pack_coefficients(
        &mut work.packed_left,
        &input.left,
        count,
        precision,
        slot,
    )
    .unwrap_or_else(|_| panic!("packed left conversion"));
    packed_layout::pack_coefficients(
        &mut work.packed_right,
        &input.right,
        count,
        precision,
        slot,
    )
    .unwrap_or_else(|_| panic!("packed right conversion"));
    if !work.packed_left.is_empty() {
        toom_multiply::full(
            &mut work.product,
            &work.packed_left,
            &work.packed_right,
            &mut work.scratch,
            PRODUCT_THRESHOLD,
        );
    }
    packed_layout::extract_coefficients(
        &mut work.output,
        &work.product,
        2 * count,
        result_precision(count, precision),
        slot,
    )
    .unwrap_or_else(|_| panic!("packed result extraction"));
}

fn bulk_zero_composition(work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    bulk_zero_pack(&mut work.packed_left, &input.left, count, precision, slot);
    bulk_zero_pack(&mut work.packed_right, &input.right, count, precision, slot);
    if !work.packed_left.is_empty() {
        toom_multiply::full(
            &mut work.product,
            &work.packed_left,
            &work.packed_right,
            &mut work.scratch,
            PRODUCT_THRESHOLD,
        );
    }
    packed_layout::extract_coefficients(
        &mut work.output,
        &work.product,
        2 * count,
        result_precision(count, precision),
        slot,
    )
    .unwrap_or_else(|_| panic!("packed result extraction"));
}

fn direct_convolution(work: &mut Workspace, input: &Inputs, count: usize, precision: usize) {
    work.accumulator.fill(0);
    for left in 0..count {
        for right in 0..count {
            work.accumulator[left + right] +=
                (input.left[left] as u128) * (input.right[right] as u128);
        }
    }
    let result_words = result_precision(count, precision).div_ceil(64);
    for index in 0..2 * count {
        work.output[index * result_words] = work.accumulator[index] as u64;
        if result_words > 1 {
            work.output[index * result_words + 1] = (work.accumulator[index] >> 64) as u64;
        }
    }
}

fn run_mode(mode: usize, work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    match black_box(mode) {
        0 => packed_composition(work, input, count, precision, slot),
        1 => bulk_zero_composition(work, input, count, precision, slot),
        2 => direct_convolution(work, input, count, precision),
        _ => unreachable!(),
    }
}

fn evict_caches(buffer: &mut [u64]) {
    for index in (0..buffer.len()).step_by(8) {
        buffer[index] = black_box(buffer[index].wrapping_add(0x9e37_79b9_7f4a_7c15));
    }
    black_box(buffer);
}

fn batch(
    mode: usize,
    work: &mut Workspace,
    inputs: &[Inputs],
    count: usize,
    precision: usize,
    slot: usize,
    start_index: usize,
    iterations: u64,
) -> u128 {
    let start = Instant::now();
    for iteration in 0..iterations {
        let input = &inputs[(start_index + iteration as usize) % inputs.len()];
        run_mode(mode, work, black_box(input), count, precision, slot);
        black_box(work.output.as_slice());
    }
    start.elapsed().as_nanos()
}

fn output_line(shape: usize, mode: usize, output: &[u64]) {
    print!("RESULT,{shape},{},", mode_name(mode));
    for (index, word) in output.iter().enumerate() {
        if index > 0 {
            print!(";");
        }
        print!("{word:016x}");
    }
    println!();
}

fn mode_name(mode: usize) -> &'static str {
    ["layout", "bulk_zero", "direct"][mode]
}

fn main() {
    println!("SHAPE,shape,count,input_precision,output_precision,slot_words,guard_bits,output_words");
    println!("SAMPLE,shape,phase,mode,repetition,iterations,total_ns");
    println!("RESULT,shape,phase,mode,words_hex_semicolon_separated");
    let mut eviction = vec![0u64; (64 * 1024 * 1024) / 8];

    for (shape, &(count, precision)) in SHAPES.iter().enumerate() {
        let slot = slot_words(count, precision);
        let output_precision = result_precision(count, precision);
        let output_words = output_precision.div_ceil(64);
        let guard_bits = 64 * slot - 2 * precision;
        println!("SHAPE,{shape},{count},{precision},{output_precision},{slot},{guard_bits},{output_words}");
        let inputs = make_inputs(count, precision);
        let mut workspaces: Vec<Workspace> = (0..3)
            .map(|mode| Workspace::new(count, slot, output_words, mode == 2))
            .collect();
        let mut expected_outputs = Vec::with_capacity(inputs.len());

        for input in &inputs {
            run_mode(0, &mut workspaces[0], input, count, precision, slot);
            run_mode(1, &mut workspaces[1], input, count, precision, slot);
            run_mode(2, &mut workspaces[2], input, count, precision, slot);
            assert_eq!(workspaces[0].output, workspaces[2].output, "layout mismatch at shape {shape}");
            assert_eq!(workspaces[1].output, workspaces[2].output, "bulk-zero mismatch at shape {shape}");
            expected_outputs.push(workspaces[2].output.clone());
        }
        for mode in 0..3 {
            run_mode(mode, &mut workspaces[mode], &inputs[0], count, precision, slot);
            output_line(shape, mode, &workspaces[mode].output);
        }

        for (phase_id, phase, ring_len, cold) in [
            (0usize, "reuse", 1usize, false),
            (1usize, "streaming", STREAM_SETS, true),
        ] {
            let ring = &inputs[..ring_len];
            for mode in 0..3 {
                for warm in 0..3 {
                    if cold {
                        evict_caches(&mut eviction);
                    }
                    batch(mode, &mut workspaces[mode], ring, count, precision, slot, warm % ring_len, 1);
                }
            }

            let mut iterations = [1u64; 3];
            for mode in 0..3 {
                loop {
                    if cold {
                        evict_caches(&mut eviction);
                    }
                    let elapsed = batch(
                        mode,
                        &mut workspaces[mode],
                        ring,
                        count,
                        precision,
                        slot,
                        0,
                        iterations[mode],
                    );
                    if elapsed >= CALIBRATION_TARGET_NS {
                        break;
                    }
                    iterations[mode] *= 2;
                }
            }

            for repetition in 0..REPS {
                let rotation = (shape + phase_id + repetition) % 3;
                for offset in 0..3 {
                    let mode = (rotation + offset) % 3;
                    let start_index = (repetition * 11) % ring_len;
                    loop {
                        if cold {
                            evict_caches(&mut eviction);
                        }
                        let elapsed = batch(
                            mode,
                            &mut workspaces[mode],
                            ring,
                            count,
                            precision,
                            slot,
                            start_index,
                            iterations[mode],
                        );
                        if elapsed < MIN_BATCH_NS {
                            println!(
                                "SHORT,{shape},{phase},{},{repetition},{},{}",
                                mode_name(mode),
                                iterations[mode],
                                elapsed,
                            );
                            iterations[mode] *= 2;
                            continue;
                        }
                        let last_input = (start_index + iterations[mode] as usize - 1) % ring_len;
                        assert_eq!(workspaces[mode].output, expected_outputs[last_input],
                            "timed output mismatch at shape {shape}, phase {phase}, mode {}",
                            mode_name(mode));
                        println!(
                            "SAMPLE,{shape},{phase},{},{repetition},{},{}",
                            mode_name(mode),
                            iterations[mode],
                            elapsed,
                        );
                        break;
                    }
                }
            }
        }
    }
}
