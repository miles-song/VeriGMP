"""Build a reproducible, isolated matrix from pinned production and archive inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def policy_arithmetic(base, cutoff):
    text = base.decode().replace('\r\n', '\n')
    for expected in ['use crate::{fast_multiply,toom_low,square_low,pow2};',
            'else { toom_low::modular(dst,a,b,scratch,top,192,128,2); }',
            '    square_low::low(dst,a,scratch,192,64,1);']:
        if text.count(expected) != 1:
            raise ValueError('Unexpected pinned production entry: ' + expected)
    text = text.replace('use crate::{fast_multiply,toom_low,square_low,pow2};',
        'use crate::{fast_multiply,toom_low,square_low,toom4_low,toom4_square_low,pow2};')
    text = text.replace('else { toom_low::modular(dst,a,b,scratch,top,192,128,2); }',
        f'else if a.len()<{cutoff} {{ toom_low::modular(dst,a,b,scratch,top,192,128,2); }}\n'
        '    else { toom4_low::modular(dst,a,b,scratch,top,256,128,2); }')
    text = text.replace('    square_low::low(dst,a,scratch,192,64,1);',
        f'    if a.len()<{cutoff} {{ square_low::low(dst,a,scratch,192,64,1); }}\n'
        '    else { toom4_square_low::low(dst,a,scratch,256,64,1); }')
    return text.encode()


def prepare(output):
    policy = json.loads((HERE / 'policy.json').read_text())
    if output.exists():
        raise ValueError('Refusing to overwrite existing stage')
    base = policy['base_commit']
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', base, 'native', 'scripts'],
        cwd=REPO, text=True).splitlines()
    baseline = {p: subprocess.check_output(['git', 'show', base + ':' + p], cwd=REPO) for p in paths}
    sources = {}

    def archive(name, relative):
        path = REPO / 'experiments' / name / 'overlay/candidate' / relative
        data = path.read_bytes()
        sources[path.relative_to(REPO).as_posix()] = sha(data)
        return data

    modules = {
        'toom4': 'specs/toom4.rs', 'toom4_blocks': 'specs/toom4_blocks.rs',
        'toom4_evaluate': 'verified/toom4_evaluate.rs',
        'toom4_interpolate': 'verified/toom4_interpolate.rs',
        'toom4_multiply': 'verified/toom4_multiply.rs',
        'toom4_square': 'verified/toom4_square.rs',
        'toom4_low': 'verified/toom4_low.rs',
        'toom4_square_low': 'verified/toom4_square_low.rs',
        'odd_division_spec': 'specs/odd_division.rs',
        'odd_division': 'verified/odd_division.rs',
        'scaled_subtraction': 'verified/scaled_subtraction.rs',
        'signed_evaluation_spec': 'specs/signed_evaluation.rs',
        'signed_evaluation': 'verified/signed_evaluation.rs',
    }
    additions = {}
    for module, relative in modules.items():
        origin = ('toom4-entry' if module.startswith('toom4') else
            'odd-division' if module.startswith('odd') else
            'toom4-fusion' if module == 'scaled_subtraction' else 'toom4-signed-eval')
        additions['native/' + relative] = archive(origin, 'native/' + relative)
    helper_declarations = ''.join(f'#[path="{p}"] pub mod {m};\n' for m, p in modules.items())
    runner = archive('toom4-signed-eval', 'native/toom4_runner.rs').decode().replace('\r\n', '\n')
    runner = runner.replace('toom4_candidate::', 'arithmetic::')
    runner = runner.replace('#[path="verified/toom4_candidate.rs"] mod toom4_candidate;\n', '')
    codegen = archive('toom4-signed-eval', 'native/toom4_codegen.rs').decode().replace('\r\n', '\n')
    codegen = codegen.replace('toom4_candidate::', 'arithmetic::')
    codegen = codegen.replace('#[path="verified/toom4_candidate.rs"] mod toom4_candidate;\n', '')
    codegen = codegen.replace('toom_words::divide_exact(dst,', 'odd_division::divide_exact_odd(dst,')
    manifest = {'base_commit': base, 'archive_input_sha256': sources, 'variants': {},
        'policy_sha256': sha((HERE / 'policy.json').read_bytes()),
        'script_sha256': sha(Path(__file__).read_bytes()),
        'status': 'prepared_not_verified_not_measured'}
    for name in policy['modes'][:-1]:
        data = dict(baseline)
        if name != 'baseline':
            features = policy['features'][name]
            data.update(additions)
            data['native/lib.rs'] += ('\n' + helper_declarations).encode()
            data['native/verified/arithmetic.rs'] = policy_arithmetic(
                baseline['native/verified/arithmetic.rs'], policy['dispatch']['toom4_min_limbs'])
            data['native/toom4_runner.rs'] = runner.encode()
            data['native/toom4_codegen.rs'] = codegen.encode()
            if 'fusion' in features:
                data['native/verified/toom4_interpolate.rs'] = archive('toom4-fusion',
                    'native/verified/toom4_interpolate.rs')
            if 'signed' in features:
                data['native/verified/toom4_evaluate.rs'] = archive('toom4-signed-eval',
                    'native/verified/toom4_evaluate.rs')
            if 'odd' in features:
                text = data['native/verified/toom4_interpolate.rs'].decode().replace('\r\n', '\n')
                for variable, divisor in [('pmh', 3), ('scratch', 9), ('ph', 15)]:
                    text = text.replace(f'toom_words::divide_exact({variable},{divisor})',
                        f'crate::odd_division::divide_exact_odd({variable},{divisor})')
                data['native/verified/toom4_interpolate.rs'] = text.encode()
        for relative, raw in data.items():
            path = output / name / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        manifest['variants'][name] = {p: sha(raw) for p, raw in data.items()}
    manifest['archive_input_sha256'] = sources
    infrastructure = {}
    for path in HERE.glob('*'):
        if path.is_file():
            (output / path.name).write_bytes(path.read_bytes())
            infrastructure[path.name] = sha(path.read_bytes())
    manifest['infrastructure_sha256'] = infrastructure
    (output / 'preparation.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'status': manifest['status'], 'variants': list(manifest['variants']),
        'output': str(output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output.resolve())
