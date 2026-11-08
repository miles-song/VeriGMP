//! Experiment-only packed-layout crossover benchmark.
use std::fs::File;
use std::hint::black_box;
use std::io::{BufWriter, Write};
use std::time::Instant;
use verigmp::{packed_layout, toom_multiply};

const SEED: u64 = 16_438_731;
const STREAM_SETS: usize = 32;
const REPS: usize = 7;
const MIN_BATCH_NS: u128 = 10_000_000;
const CALIBRATION_TARGET_NS: u128 = 25_000_000;
const PRODUCT_THRESHOLD: usize = 24;
const PRECISIONS: &[usize] = &[7, 17, 29, 30, 53];
const MODES: &[&str] = &["layout", "bulk_zero"];

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
}

impl Workspace {
    fn new(count: usize, slot_words: usize, result_words: usize) -> Self {
        let packed_words = count * slot_words;
        Self {
            packed_left: vec![0; packed_words],
            packed_right: vec![0; packed_words],
            product: vec![0; 2 * packed_words],
            scratch: vec![0; 12 * packed_words],
            output: vec![0; 2 * count * result_words],
        }
    }
}

fn counts() -> Vec<usize> {
    let mut values: Vec<usize> = (1..=35)
        .chain(60..=69)
        .chain(125..=131)
        .chain(253..=259)
        .chain(509..=515)
        .chain(1019..=1024)
        .collect();
    values.sort_unstable();
    values.dedup();
    values
}

fn selected(n: usize, split: &str) -> bool {
    match split {
        "discovery" => (1..=35).contains(&n) || (125..=131).contains(&n) || (509..=515).contains(&n),
        "confirmation" => (60..=69).contains(&n) || (253..=259).contains(&n) || (1019..=1024).contains(&n),
        _ => panic!("split must be discovery or confirmation"),
    }
}

fn ceil_log2(n: usize) -> usize {
    if n <= 1 { 0 } else { usize::BITS as usize - (n - 1).leading_zeros() as usize }
}

fn slot_words(count: usize, precision: usize) -> usize {
    let q = 2 * precision + ceil_log2(count);
    ((precision + 63) / 64).max((q + 63) / 64)
}

fn result_precision(count: usize, precision: usize) -> usize {
    2 * precision + ceil_log2(count)
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

fn compose_layout(work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    packed_layout::pack_coefficients(
        &mut work.packed_left, &input.left, count, precision, slot,
    ).unwrap_or_else(|_| panic!("packed left conversion"));
    packed_layout::pack_coefficients(
        &mut work.packed_right, &input.right, count, precision, slot,
    ).unwrap_or_else(|_| panic!("packed right conversion"));
    toom_multiply::full(
        &mut work.product, &work.packed_left, &work.packed_right,
        &mut work.scratch, PRODUCT_THRESHOLD,
    );
    packed_layout::extract_coefficients(
        &mut work.output, &work.product, 2 * count,
        result_precision(count, precision), slot,
    ).unwrap_or_else(|_| panic!("packed result extraction"));
}

fn compose_bulk_zero(work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    bulk_zero_pack(&mut work.packed_left, &input.left, count, precision, slot);
    bulk_zero_pack(&mut work.packed_right, &input.right, count, precision, slot);
    toom_multiply::full(
        &mut work.product, &work.packed_left, &work.packed_right,
        &mut work.scratch, PRODUCT_THRESHOLD,
    );
    packed_layout::extract_coefficients(
        &mut work.output, &work.product, 2 * count,
        result_precision(count, precision), slot,
    ).unwrap_or_else(|_| panic!("packed result extraction"));
}

fn run_mode(mode: usize, work: &mut Workspace, input: &Inputs, count: usize, precision: usize, slot: usize) {
    match black_box(mode) {
        0 => compose_layout(work, input, count, precision, slot),
        1 => compose_bulk_zero(work, input, count, precision, slot),
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
    mode: usize, work: &mut Workspace, inputs: &[Inputs], count: usize,
    precision: usize, slot: usize, start_index: usize, iterations: u64,
) -> u128 {
    let start = Instant::now();
    for iteration in 0..iterations {
        let input = &inputs[(start_index + iteration as usize) % inputs.len()];
        run_mode(mode, work, black_box(input), count, precision, slot);
        black_box(work.output.as_slice());
    }
    start.elapsed().as_nanos()
}

fn write_u32(out: &mut impl Write, value: u32) {
    out.write_all(&value.to_le_bytes()).expect("write result header");
}

fn write_u64(out: &mut impl Write, value: u64) {
    out.write_all(&value.to_le_bytes()).expect("write result header");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(args.len(), 3, "usage: crossover-bench <discovery|confirmation> <results.bin>");
    let split = args[1].as_str();
    assert!(split == "discovery" || split == "confirmation");
    let result_file = File::create(&args[2]).expect("create result dump");
    let mut result_dump = BufWriter::new(result_file);
    result_dump.write_all(b"PCROSS01").expect("write result magic");

    println!("SHAPE,shape,count,input_precision,output_precision,slot_words,required_guard_bits,guard_margin_bits");
    println!("SAMPLE,shape,phase,mode,repetition,iterations,total_ns");
    println!("SHORT,shape,phase,mode,repetition,iterations,total_ns");
    let mut eviction = vec![0u64; (64 * 1024 * 1024) / 8];
    let count_values = counts();
    let mut shape_index = 0usize;

    for &precision in PRECISIONS {
        for &count in &count_values {
            let current_shape = shape_index;
            shape_index += 1;
            if !selected(count, split) {
                continue;
            }
            let slot = slot_words(count, precision);
            let output_precision = result_precision(count, precision);
            let output_words = (output_precision + 63) / 64;
            let required_guard_bits = ceil_log2(count);
            let guard_margin_bits = 64 * slot - output_precision;
            println!(
                "SHAPE,{current_shape},{count},{precision},{output_precision},{slot},{required_guard_bits},{guard_margin_bits}"
            );

            let inputs = make_inputs(count, precision);
            let mut workspaces = [
                Workspace::new(count, slot, output_words),
                Workspace::new(count, slot, output_words),
            ];
            let mut expected_outputs = Vec::with_capacity(inputs.len());
            let mut saved_outputs: [Vec<Vec<u64>>; 2] = [
                Vec::with_capacity(inputs.len()),
                Vec::with_capacity(inputs.len()),
            ];

            for input in &inputs {
                compose_layout(&mut workspaces[0], input, count, precision, slot);
                let expected = workspaces[0].output.clone();
                expected_outputs.push(expected);
                saved_outputs[0].push(workspaces[0].output.clone());
                compose_bulk_zero(&mut workspaces[1], input, count, precision, slot);
                assert_eq!(
                    workspaces[1].output, workspaces[0].output,
                    "cross-path mismatch at shape {current_shape}"
                );
                saved_outputs[1].push(workspaces[1].output.clone());
            }

            for (phase_id, phase, ring_len, cold) in [
                (0usize, "reuse", 1usize, false),
                (1usize, "streaming", STREAM_SETS, true),
            ] {
                let ring = &inputs[..ring_len];
                for mode in 0..2 {
                    for warm in 0..3 {
                        if cold {
                            evict_caches(&mut eviction);
                        }
                        batch(mode, &mut workspaces[mode], ring, count, precision, slot, warm % ring_len, 1);
                    }
                }

                let mut iterations = [1u64; 2];
                for mode in 0..2 {
                    loop {
                        if cold {
                            evict_caches(&mut eviction);
                        }
                        let elapsed = batch(
                            mode, &mut workspaces[mode], ring, count, precision,
                            slot, 0, iterations[mode],
                        );
                        if elapsed >= CALIBRATION_TARGET_NS {
                            break;
                        }
                        iterations[mode] *= 2;
                    }
                }

                for repetition in 0..REPS {
                    let rotation = (current_shape + phase_id + repetition) % 2;
                    for offset in 0..2 {
                        let mode = (rotation + offset) % 2;
                        let start_index = (repetition * 11) % ring_len;
                        loop {
                            if cold {
                                evict_caches(&mut eviction);
                            }
                            let elapsed = batch(
                                mode, &mut workspaces[mode], ring, count, precision,
                                slot, start_index, iterations[mode],
                            );
                            if elapsed < MIN_BATCH_NS {
                                println!(
                                    "SHORT,{current_shape},{phase},{},{repetition},{},{}",
                                    MODES[mode], iterations[mode], elapsed,
                                );
                                iterations[mode] *= 2;
                                continue;
                            }
                            let last_input = (start_index + iterations[mode] as usize - 1) % ring_len;
                            assert_eq!(
                                workspaces[mode].output, expected_outputs[last_input],
                                "timed output mismatch at shape {current_shape}, phase {phase}, mode {}",
                                MODES[mode]
                            );
                            println!(
                                "SAMPLE,{current_shape},{phase},{},{repetition},{},{}",
                                MODES[mode], iterations[mode], elapsed,
                            );
                            break;
                        }
                    }
                }
            }

            for input_index in 0..STREAM_SETS {
                for mode in 0..2 {
                    write_u32(&mut result_dump, current_shape as u32);
                    write_u32(&mut result_dump, input_index as u32);
                    result_dump.write_all(&[mode as u8]).expect("write result mode");
                    write_u64(&mut result_dump, saved_outputs[mode][input_index].len() as u64);
                    for word in &saved_outputs[mode][input_index] {
                        write_u64(&mut result_dump, *word);
                    }
                }
            }
            result_dump.flush().expect("flush shape results");
        }
    }
}
