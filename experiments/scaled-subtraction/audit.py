"""Validate published evidence and recompute every recorded performance row."""
from pathlib import Path
import csv,hashlib,json,re,statistics

HERE=Path(__file__).resolve().parent
BASE='e22a4dd00a28681fd27d68e2a78fa304cf17563e'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def safe(root,relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Path leaves archive')
    return path

def audit():
    index=json.loads((HERE/'index.json').read_text())
    if index['baseline_commit']!=BASE or index['production_files_changed']:raise ValueError('Wrong baseline/promotion')
    result={'status':'pass','baseline_commit':BASE,'runs':{},'source_identity_scope':'Historical raw source and CSV hashes; report host paths are publication-only redactions'}
    for variant,summary in index['variants'].items():
        root=safe(HERE,variant);publication=json.loads((root/'publication.json').read_text())
        files=publication['files']
        for relative,entry in files.items():
            path=safe(root,relative)
            if sha(path)!=entry['published_sha256']:raise ValueError('Archive bytes changed: '+relative)
            if entry['transform']=='none' and entry['original_sha256']!=entry['published_sha256']:raise ValueError('Invalid identity projection')
            if re.search(r'sat-counting|VeriCount|/mnt/e/|(?<![0-9a-zA-Z])[A-Za-z]:[\\/]|Users[/\\]+23247',path.read_text()):raise ValueError('Local path in public archive')
        verification=json.loads((root/'evidence/verification.json').read_text())
        if verification['status']!='pass' or not verification['identity_checks_before_after']:raise ValueError('Incomplete historical gate')
        if files['evidence/verification.json']['original_sha256']!=publication['historical_verification_original_sha256']:raise ValueError('Historical gate identity mismatch')
        if verification['libraries']['candidate']['verified']!=summary['library_proof_items']:raise ValueError('Proof count mismatch')
        if verification['oracle']['cases']!=summary['oracle_cases'] or len(verification['mutations'])!=summary['semantic_mutants']:raise ValueError('Coverage mismatch')
        if not all(m['semantically_rejected'] for m in verification['mutations']):raise ValueError('Undetected mutant')
        for relative,h in verification['source_sha256'].items():
            if relative.startswith('candidate/'):
                overlay=root/'overlay'/relative.removeprefix('candidate/')
                if overlay.exists() and sha(overlay)!=h:raise ValueError('Overlay source mismatch')
            elif '/' not in relative and sha(root/relative)!=h:raise ValueError('Historical checker mismatch')
        shapes={(op,n,t) for op in [0,1] for n,t in [(1,1),(1,64),(2,1),*[(n,63) for n in [23,24,25,63,64,65,127,128,129,191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]]]}
        for tag in ['default1','default2']:
            binding=json.loads((root/'evidence'/f'{tag}-binding.json').read_text())
            measured=json.loads((root/'evidence'/tag/'measurements.json').read_text())
            raw=root/'evidence'/tag/'benchmark.csv'
            if binding['status']!='pass' or measured['status']!='pass':raise ValueError('Failed measurement')
            if not binding['source_tool_artifact_checks_before_after']:raise ValueError('Missing before/after identity checks')
            if measured['verified_library_identities']!=verification['libraries']:raise ValueError('Measurement library mismatch')
            if measured['benchmark_binary_sha256']!=verification['benchmark_binary_sha256']:raise ValueError('Measurement binary mismatch')
            if measured['benchmark_source_sha256']!=verification['benchmark_source_sha256'] or measured['benchmark_source_sha256']!=sha(root/'compare.rs'):raise ValueError('Measurement driver mismatch')
            if binding['verification_report_sha256']!=publication['historical_verification_original_sha256']:raise ValueError('Unbound historical source')
            if binding['measurements_sha256']!=files[f'evidence/{tag}/measurements.json']['original_sha256']:raise ValueError('Unbound historical report')
            if binding['raw_sha256']!=sha(raw):raise ValueError('Unbound raw CSV')
            rows=list(csv.DictReader(raw.open(newline='')));groups={}
            for row in rows:
                key=tuple(int(row[k]) for k in ['operation','limbs','top','mode'])
                groups.setdefault(key,[]).append(row)
            if set(groups)!={(*s,m) for s in shapes for m in range(3)}:raise ValueError('Incomplete shapes')
            medians={}
            for key,values in groups.items():
                if len(values)!=7 or {int(r['repetition']) for r in values}!=set(range(7)):raise ValueError('Incomplete repetitions')
                if any(int(r['ns'])<10_000_000 or int(r['iterations'])<=0 for r in values):raise ValueError('Short measurement batch')
                medians[key]=statistics.median(int(r['ns'])/int(r['iterations']) for r in values)
            if len(measured['measurements'])!=52 or {(r['operation'],r['limbs'],r['top']) for r in measured['measurements']}!=shapes:raise ValueError('Incomplete report')
            for item in measured['measurements']:
                key=(item['operation'],item['limbs'],item['top'])
                for field,mode in [('baseline_ns',0),('candidate_ns',1),('gmp_ns',2)]:
                    if item[field]!=medians[(*key,mode)]:raise ValueError('Median mismatch')
                if item['candidate_over_baseline']!=medians[(*key,1)]/medians[(*key,0)]:raise ValueError('Baseline ratio mismatch')
                if item['candidate_over_gmp']!=medians[(*key,1)]/medians[(*key,2)]:raise ValueError('GMP ratio mismatch')
            regressions=sum(r['candidate_over_baseline']>1 for r in measured['measurements'])
            primary=sum(r['candidate_over_gmp']>1 for r in measured['measurements'] if r['limbs'] in [256,512,1024,2048,4096] and r['top']==63)
            key_fails=sum(r['candidate_over_gmp']>1.2 for r in measured['measurements'])
            if (regressions,primary,key_fails)!=(summary['regressions_vs_baseline'][tag],summary['primary_gmp_failures'][tag],summary['key_gmp_failures'][tag]):raise ValueError('Summary omits failures')
            result['runs'][variant+'/'+tag]={'samples':len(rows),'minimum_actual_ns':min(int(r['ns']) for r in rows),'observed_regressions':regressions,'primary_gmp_failures':primary,'key_gmp_failures':key_fails,'raw_sha256':sha(raw),'registered_gmp_target_status':'target_not_met' if primary or key_fails else 'candidate_library_target_observed'}
    return result

if __name__=='__main__':print(json.dumps(audit(),indent=2))
