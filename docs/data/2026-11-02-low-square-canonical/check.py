#!/usr/bin/env python3
"""Audit preserved CI evidence; does not rerun Verus or benchmarks."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMMIT = 'e22a4dd00a28681fd27d68e2a78fa304cf17563e'
RUN = 41331997725
DIGEST = '58861fd92d0966ce059d51bf75dc1b87622846dad8c822f75b4aa295bf5c23f3'
LOW_MUTANTS = {'omit_low_cross_row', 'truncate_retained_row', 'drop_low_row_carry',
               'omit_odd_diagonal', 'drop_odd_output'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def audit():
    archive = HERE / 'github-artifact.zip'
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == DIGEST, 'ZIP digest')
    run = json.loads((HERE / 'github-run.json').read_text())
    require(run['headSha'] == COMMIT and run['status'] == 'completed'
            and run['conclusion'] == 'success', 'CI identity/status')
    require(run['url'].endswith('/' + str(RUN)), 'CI URL')
    artifacts = json.loads((HERE / 'github-artifact.json').read_text())['artifacts']
    artifact = next(a for a in artifacts if a['id'] == 13093204658)
    require(artifact['digest'] == 'sha256:' + DIGEST
            and artifact['workflow_run']['head_sha'] == COMMIT
            and artifact['workflow_run']['id'] == RUN
            and artifact['size_in_bytes'] == archive.stat().st_size, 'Artifact binding')
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, 'ZIP CRC')
        report = json.loads(z.read('verification.json'))
        require(report['status'] == 'pass' and report['git'] == {
            'head': COMMIT, 'tracked_status': '', 'invoking_ci_commit': COMMIT},
            'Snapshot identity')
        for name, digest in report['source_hashes_lf'].items():
            data = subprocess.check_output(['git', '-C', str(ROOT), 'show', COMMIT + ':' + name])
            require(hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest() == digest,
                    'Committed input mismatch: ' + name)
            require(hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                    == digest, 'Current input mismatch: ' + name)
        require(len(report['source_hashes_lf']) == 107, 'Input count')
        require(report['library']['verified_items'] == 234, 'Library proof count')
        for name in ('library.log', 'toom/proof.log'):
            log = z.read(name).decode()
            require(re.search(r'verification results:: 234 verified, 0 errors', log)
                    and 'partial verification' not in log, 'Full positive proof: ' + name)
        for name in ('limbs', 'pow2', 'multiply', 'fast_multiply', 'toom'):
            require(report[name]['status'] == 'pass', 'Module: ' + name)
        toom = report['toom']
        require(toom['oracle']['cases'] == 11292
                and toom['oracle']['direct_low_square_cases'] == 1440
                and toom['oracle']['direct_low_square_seed'] == 20261103
                and toom['invalid_commands_rejected'] == 12, 'Oracle coverage')
        require(len(toom['mutations']) == 21 and LOW_MUTANTS <= {
            m['name'] for m in toom['mutations']}, 'Mutation coverage')
        for mutant in toom['mutations']:
            log = z.read('toom/' + mutant['name'] + '.log').decode()
            require(mutant['rejected_by_semantic_proof']
                    and re.search(r'verification results:: \d+ verified, [1-9]\d* errors', log)
                    and any(d in log for d in ('postcondition not satisfied', 'assertion failed',
                        'invariant not satisfied', 'requires not satisfied', 'precondition not satisfied'))
                    and not re.search(r'(?i)timed out|resource limit|unexpected token|error\[E[0-9]+\]|failed to (?:load|resolve)', log),
                    'Semantic rejection: ' + mutant['name'])
        require(hashlib.sha256(z.read('toom/toom-codegen.s')).hexdigest()
                == toom['codegen']['assembly_sha256'], 'Assembly identity')
        frozen = json.loads((HERE.parent / '2026-11-02-low-square-cutoff9/metadata.json').read_text())
        for name, digest in frozen['candidate_core_sha256_lf'].items():
            require(report['source_hashes_lf'][name] == digest, 'Frozen core binding: ' + name)
        return {'status': 'pass', 'accepted_code_commit': COMMIT, 'ci_run': RUN,
                'source_files_checked': 107, 'library_verified_items': 234,
                'toom_oracle_cases': 11292, 'direct_low_square_cases': 1440,
                'semantic_mutants': 21, 'new_low_square_mutants': 5,
                'artifact_sha256': DIGEST,
                'scope': 'Preserved evidence integrity; no new proof or performance run'}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
