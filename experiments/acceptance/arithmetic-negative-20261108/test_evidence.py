#!/usr/bin/env python3
"""Inject five read-only corruptions; never change a checkout or archive."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('negative_checkpoint_audit', HERE/'check_evidence.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    with contextlib.redirect_stdout(io.StringIO()) as output:
        audit.main()
    assert json.loads(output.getvalue())['status'] == 'pass'
    original_read = Path.read_bytes
    cases = {
        'native_source': audit.ROOT/'native/verified/square_low.rs',
        'public_readme': audit.ROOT/'README.md',
        'frozen_measurement_input': audit.ROOT/'experiments/combination-20261108/measure.py',
        'original_raw_archive': HERE/'frozen-measurements.zip',
        'linked_static_archive': audit.ROOT/'experiments/combination-20261108/evidence/evidence.zip',
    }
    rejected = {}
    for name, target in cases.items():
        hits = []
        def corrupted_read(path):
            data = original_read(path)
            if path.resolve() == target.resolve():
                hits.append(str(path))
                return data+b'corruption fixture'
            return data
        try:
            with patch.object(Path, 'read_bytes', corrupted_read), contextlib.redirect_stdout(io.StringIO()):
                audit.main()
        except AssertionError:
            assert hits, name
            rejected[name] = True
        else:
            raise AssertionError('Corrupted input was accepted: '+name)
    print(json.dumps(dict(status='pass',valid_checkpoint_accepted=True,
        corruptions_rejected=rejected,actual_files_changed=False,
        benchmark_executed=False,binary_executed=False),indent=2))


if __name__ == '__main__':
    main()
