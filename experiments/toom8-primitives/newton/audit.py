"""Audit preserved Newton-interpolation evidence without claiming a fresh proof."""
from pathlib import Path
import hashlib,json,re
import newton_oracle,newton_codegen
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(name):
    p=(HERE/name).resolve()
    if not p.is_relative_to(HERE) or p.is_symlink():raise ValueError('Unsafe archive path')
    return p
def read(name):return json.loads(safe(name).read_text(encoding='utf-8'))
def audit():
    publication=read('publication.json');files=publication['files'];v=read('evidence/verification.json')
    if v['status']!='pass' or v['benchmark_run'] or v['production_modified']:raise ValueError('Wrong acceptance scope')
    for name,item in files.items():
        data=safe(name).read_bytes();text=data.decode('utf-8')
        if hashlib.sha256(data).hexdigest()!=item['published_sha256']:raise ValueError('Archive file hash mismatch: '+name)
        if re.search(r'/mnt/[a-z]/|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|Users[/\\]+\d+',text,re.I):raise ValueError('Private path in archive')
    if files['evidence/verification.json']['original_sha256']!=publication['accepted_gate_original_sha256']:raise ValueError('Gate identity mismatch')
    for name,digest in v['source_sha256'].items():
        if files[name]['original_sha256']!=digest or sha(safe(name))!=files[name]['published_sha256']:raise ValueError('Frozen source changed: '+name)
        if files[name]['transform']!='none' and name not in publication['redacted_provenance_inputs']:raise ValueError('Unexpected source transformation')
    if len(v['source_sha256'])!=89:raise ValueError('Incomplete source inventory')
    commands={c['log']:c for c in v['commands']}
    if len(commands)!=27:raise ValueError('Incomplete command inventory')
    for log,c in commands.items():
        if c['status']!='completed' or 'returncode' not in c:raise ValueError('Incomplete command result')
        if log!='oracle.log' and files['evidence/'+log]['original_sha256']!=c['log_sha256']:raise ValueError('Command log binding mismatch')
    for log,expected in [('library.log',425),('runner-build.log',427),('codegen-build.log',427)]:
        text=safe('evidence/'+log).read_text(encoding='utf-8')
        summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
        if commands[log]['returncode']!=0 or summaries!=[(str(expected),'0')] or 'partial verification' in text or re.search(r'(?im)^error(?:\[|:)|resource limit|timed out',text):raise ValueError('Bad complete proof log: '+log)
    expected_mutants=['even-wrong-rhs','even-wrong-power','even-wrong-odd','even-wrong-conversion','even-wrong-recovery','odd-wrong-divisor4095','odd-wrong-conversion','odd-wrong-recovery']
    if [m['name'] for m in v['mutations']]!=expected_mutants:raise ValueError('Unexpected semantic mutant inventory')
    source=safe('candidate/native/verified/toom8_newton.rs').read_bytes()
    for m in v['mutations']:
        log=m['name']+'.log';text=safe('evidence/'+log).read_text(encoding='utf-8');command=commands[log]
        if not m['semantically_rejected'] or command['returncode']!=1:raise ValueError('Wrong semantic failure exit code')
        summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
        if len(summaries)!=1 or int(summaries[0][1])==0 or '(partial verification with `--verify-*`)' not in text or 'note: verifying module toom8_newton' not in text:raise ValueError('Wrong partial proof scope')
        argv=command['argv'];idx=argv.index('--verify-module')
        if argv[idx+1]!='toom8_newton' or argv.count('--verify-module')!=1:raise ValueError('Wrong mutation module')
        diagnostics=re.findall(r'(?m)^error(?:\[[^\]]*\])?: (.*)$',text)
        failures=[x for x in diagnostics if not x.startswith('aborting due to ')]
        allowed=('assertion failed','postcondition not satisfied','precondition not satisfied','requires not satisfied','invariant not satisfied','loop invariant not satisfied','possible arithmetic underflow/overflow','possible arithmetic overflow','possible arithmetic underflow')
        if not failures or any(not x.startswith(allowed) for x in failures) or re.search(r'(?i)timed out|time limit|resource limit|internal error|panicked at|error\[E\d+\]|could not (?:load|compile)|failed to load',text):raise ValueError('Nonsemantic failure classified as rejection')
        text_source=source.decode();start=text_source.index('fn '+m['function']+'(');end=text_source.index('\n}',start)+2;body=text_source[start:end]
        if body.count(m['before'])!=1:raise ValueError('Mutation anchor mismatch')
        changed=(text_source[:start]+body.replace(m['before'],m['after'])+text_source[end:]).encode()
        if hashlib.sha256(changed).hexdigest()!=m['source_sha256']:raise ValueError('Mutant source mismatch')
        if files['evidence/'+log]['original_sha256']!=m['log_sha256']:raise ValueError('Mutant log mismatch')
    rows,counts=newton_oracle.cases();input_bytes=('\n'.join(row[0] for row in rows)+'\n').encode();output_bytes=('\n'.join(row[1] for row in rows)+'\n').encode()
    oracle=v['oracle']
    if len(rows)!=1087 or {str(k):v for k,v in counts.items()}!=oracle['counts'] or len(rows)!=oracle['cases'] or hashlib.sha256(input_bytes).hexdigest()!=oracle['input_sha256'] or hashlib.sha256(output_bytes).hexdigest()!=oracle['output_sha256']:raise ValueError('Independent integer oracle identity mismatch')
    if commands['oracle.log']['returncode']!=0 or commands['oracle.log']['log_sha256']!=oracle['output_sha256']:raise ValueError('Oracle command mismatch')
    if [x['command'] for x in v['invalid']]!=newton_oracle.invalid():raise ValueError('Invalid input inventory mismatch')
    for i,item in enumerate(v['invalid']):
        log=f'invalid-{i:02}.log'
        if item['returncode']!=101 or commands[log]['returncode']!=101 or 'panicked at' not in safe('evidence/'+log).read_text(encoding='utf-8') or files['evidence/'+log]['original_sha256']!=item['log_sha256']:raise ValueError('Invalid-domain rejection mismatch')
    if sha(safe('evidence/codegen.s'))!=files['evidence/codegen.s']['published_sha256'] or files['evidence/codegen.s']['original_sha256']!=v['artifact_sha256']['codegen.s']:raise ValueError('Codegen identity mismatch')
    if newton_codegen.inspect(safe('evidence/codegen.s').read_text(encoding='utf-8'))!=v['codegen']:raise ValueError('Codegen inspection differs')
    root=read('evidence/root-independent-audit.json')
    if root['status']!='pass' or root['report_sha256']!=publication['accepted_gate_original_sha256'] or files['evidence/root-independent-audit.json']['original_sha256']!=publication['independent_audit_original_sha256']:raise ValueError('Independent audit binding mismatch')
    if root['runtime']!=v['runtime_library_sha256'] or root['artifacts']!=v['artifact_sha256']:raise ValueError('Independent runtime/artifact identities differ')
    for attempt in read('development/index.json')['attempts']:
        report=read(attempt['report'])
        if report['status']!=attempt['reported_status']:raise ValueError('Historical status changed')
        for name,digest in report['source_sha256'].items():
            path=attempt['source_overlays'].get(name,name)
            if files[path]['original_sha256']!=digest or sha(safe(path))!=files[path]['published_sha256']:raise ValueError('Historical source reconstruction failed: '+attempt['name']+'/'+name)
    source_text=source.decode()
    tokens=['toom_words::sub_exact(','toom_words::divide_exact(','wide_odd_division::divide_toom8_odd(','scaled_subtraction::sub_scaled_exact(']
    if [source_text.count(t) for t in tokens]!=[36]*4:raise ValueError('Actual primitive schedule changed')
    phases=re.findall(r'fn (?:even|odd)_phase_\d+\(',source_text)
    if len(phases)!=24 or v['static_schedule']['primitive_calls']!=144 or root['phase_count']!=24:raise ValueError('Actual phase schedule changed')
    if publication['redacted_provenance_inputs']!=['parent-newton-proof.json','parent-wide-odd-gate.json']:raise ValueError('Unexpected transformed input inventory')
    return {'status':'pass','scope':'Historical archive/hash/log/independent-integer/codegen audit; not fresh proof or binary execution',
        'sources':89,'mapped_files':len(files),'positive_counts':[425,427,427],'integer_cases':len(rows),'semantic_mutants':8,'invalid_commands':10,
        'historical_attempts':6,'benchmark_run':False,'complete_toom8':False,'performance_accepted':False,'production_promoted':False}
if __name__=='__main__':print(json.dumps(audit(),indent=2))
