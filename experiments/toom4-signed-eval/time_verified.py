from pathlib import Path
import hashlib
import json
import subprocess
import sys

STAGE = Path(__file__).resolve().parent
EVIDENCE = STAGE / 'evidence'
report_path = EVIDENCE / 'verification.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

arguments = sys.argv[1:]
tag = arguments[arguments.index('--tag') + 1]
binding_path = EVIDENCE / (tag + '-binding.json')
if binding_path.exists():
    raise RuntimeError('Refusing to overwrite measurement binding')
binding = {'status': 'running', 'verification_report_sha256': sha(report_path)}
binding_path.write_text(json.dumps(binding, indent=2) + '\n')
try:
    verification = json.loads(report_path.read_text())
    if verification['status'] != 'pass' or not verification.get('identity_checks_before_after'):
        raise RuntimeError('Snapshot verification did not pass')
    identities = {STAGE / p: h for p, h in verification['source_sha256'].items()}
    identities.update({Path(p): h for p, h in verification['toolchain_file_sha256'].items()})
    identities.update({Path(p): h for p, h in verification['runtime_library_sha256'].items()})
    identities.update({EVIDENCE / p: h for p, h in verification['artifact_sha256'].items()})
    identities[report_path] = binding['verification_report_sha256']
    identities[STAGE / 'measure_interpolation.py'] = sha(STAGE / 'measure_interpolation.py')
    identities[Path(__file__)] = sha(Path(__file__))
    binding['measurement_script_sha256'] = identities[STAGE / 'measure_interpolation.py']
    binding['measurement_binding_script_sha256'] = identities[Path(__file__)]
    for name, data in verification['libraries'].items():
        identities[EVIDENCE / ('lib' + name + '.rlib')] = data['rlib_sha256']
        identities[EVIDENCE / (name + '.vir')] = data['vir_sha256']
    if any(sha(p) != h for p, h in identities.items()):
        raise RuntimeError('Verified source, tool, or artifact changed before timing')
    result = subprocess.run([sys.executable, STAGE / 'measure_interpolation.py', *arguments])
    if result.returncode:
        raise RuntimeError('Measurement failed')
    if any(sha(p) != h for p, h in identities.items()):
        raise RuntimeError('Verified source, tool, or artifact changed during timing')
    measurements = EVIDENCE / tag / 'measurements.json'
    measured = json.loads(measurements.read_text())
    if measured['status'] != 'pass':
        raise RuntimeError('Measurement did not produce a passing record')
    binding.update(status='pass', measurements_sha256=sha(measurements),
                   raw_sha256=sha(EVIDENCE / tag / 'benchmark.csv'),
                   source_tool_artifact_checks_before_after=True,
                   samples=measured['samples'],
                   minimum_observed_batch_ns=measured['minimum_observed_batch_ns'])
except Exception as error:
    binding.update(status='error', error=f'{type(error).__name__}: {error}')
finally:
    binding_path.write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps(binding, indent=2))
raise SystemExit(binding['status'] != 'pass')
