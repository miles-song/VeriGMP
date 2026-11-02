"""Audit the append-only gate repair; no proof, compiled runner, or timing."""
from pathlib import Path
import ast,hashlib,json,re,types
A=Path(__file__).resolve().parent;ARCHIVES=A.parent
CACHE={}
def captured(path):
    path=Path(path).resolve()
    if path not in CACHE:CACHE[path]=path.read_bytes()
    return CACHE[path]
def text(path):return captured(path).decode('utf-8')
def sha(path):return hashlib.sha256(captured(path)).hexdigest()
def checked_path(relative):
    path=(ARCHIVES/relative).resolve()
    if not path.is_relative_to(ARCHIVES.resolve()):raise ValueError('Source leaves archive root')
    return path
index=json.loads(text(A/'index.json'));results={}
for relative,identity in index['mapped_files'].items():
    assert sha(A/relative)==identity['published_sha256'],relative
for name,feature in index['features'].items():
    report=json.loads(text(A/name/'evidence/verification.json'))
    assert report['status']=='pass' and not report['benchmark_run'] and not report['production_modified']
    assert set(feature['source_map'])==set(report['source_sha256'])
    for relative,identity in feature['source_map'].items():
        assert identity['original_sha256']==report['source_sha256'][relative]
        assert sha(checked_path(identity['archive_path']))==identity['published_sha256']
        if identity['bytes_exact']:assert identity['published_sha256']==identity['original_sha256']
        else:assert name=='newton' and relative in ['parent-newton-proof.json','parent-wide-odd-gate.json']
    code=text(A/name/feature['checker']);tree=ast.parse(code)
    selected=[node for node in tree.body if
        (isinstance(node,ast.FunctionDef) and node.name in {'fatal_diagnostic','strict_vc'}) or
        (isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FATAL_DIAGNOSTIC' for t in node.targets))]
    env={'re':re};exec(compile(ast.Module(body=selected,type_ignores=[]),'<frozen diagnostic functions>','exec'),env)
    imports=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))]
    assert all('_oracle' not in ast.unparse(node) and '_codegen' not in ast.unparse(node) for node in imports)
    assert "exec(compile(checker_bytes" in code and "exec(compile(inputs[module_name+'.py']" in code and "origin=json.loads(inputs['origin.json'])" in code
    for command in report['commands']:
        assert command['status']=='completed' and 'returncode' in command
        identity=index['mapped_files'].get(name+'/evidence/'+command['log'])
        if command['log']=='oracle.log':assert identity is None
        else:assert identity['original_sha256']==command['log_sha256']
    for logfile,count in zip(['library.log','runner-build.log','codegen-build.log'],feature['verified']):
        diagnostic=text(A/name/'evidence'/logfile);command=next(c for c in report['commands'] if c['log']==logfile)
        assert command['returncode']==0 and re.findall(r'verification results:: (\d+) verified, (\d+) errors',diagnostic)==[(str(count),'0')]
        assert 'partial verification' not in diagnostic and not env['fatal_diagnostic'](diagnostic)
    for mutant in report['mutations']:
        logfile=mutant['name']+'.log';diagnostic=text(A/name/'evidence'/logfile);command=next(c for c in report['commands'] if c['log']==logfile)
        assert index['mapped_files'][name+'/evidence/'+logfile]['original_sha256']==mutant['log_sha256']
        assert env['strict_vc'](diagnostic,command['returncode'])
        for suffix in report['appended_failure_fixtures_rejected']:assert not env['strict_vc'](diagnostic+'\n'+suffix+'\n',command['returncode'])
    stem='wide_odd' if name=='wide-odd' else 'newton'
    oracle_path=checked_path(feature['source_map'][stem+'_oracle.py']['archive_path'])
    oracle=types.ModuleType('frozen_oracle');oracle.__file__=str(oracle_path)
    exec(compile(captured(oracle_path),str(oracle_path),'exec'),oracle.__dict__)
    rows,counts=oracle.cases();commands='\n'.join(x[0] for x in rows)+'\n'
    expected='\n'.join(x[1] if isinstance(x[1],str) else ' '.join(map(str,x[1])) for x in rows)+'\n'
    assert len(rows)==feature['integer_cases']==report['oracle']['cases']
    assert hashlib.sha256(commands.encode()).hexdigest()==report['oracle']['input_sha256']
    assert hashlib.sha256(expected.encode()).hexdigest()==report['oracle']['output_sha256']
    invalid=oracle.invalid();assert len(invalid)==feature['invalid_cases']
    for case in report['invalid']:
        assert case['command'] in invalid and case['returncode']==101
    inspector_path=checked_path(feature['source_map'][stem+'_codegen.py']['archive_path'])
    inspector=types.ModuleType('frozen_inspector');inspector.__file__=str(inspector_path)
    exec(compile(captured(inspector_path),str(inspector_path),'exec'),inspector.__dict__)
    assert inspector.inspect(text(A/name/'evidence/codegen.s'))==report['codegen']
    results[name]={'sources':len(feature['source_map']),'verified':feature['verified'],'integer_cases':len(rows),
        'semantic_mutants':len(report['mutations']),'mixed_fatal_rejections':len(report['mutations'])*len(report['appended_failure_fixtures_rejected'])}
    if 'history' in feature:
        history=A/name/'history/feature6';old=json.loads(text(history/'verification.json'));status=json.loads(text(history/'status.json'))
        assert status['status']=='superseded_metadata_claim_requires_fresh_gate'
        assert index['mapped_files'][name+'/history/feature6/verification.json']['original_sha256']==status['preserved_report_sha256']
        for relative,digest in old['source_sha256'].items():
            if relative==feature['checker']:assert sha(history/relative)==digest
            else:assert digest==report['source_sha256'][relative]
print(json.dumps({'status':'pass','scope':'Saved evidence, reconstructed source identity and independent integer regeneration; no fresh proof or compiled runner execution','features':results,'mapped_files':len(index['mapped_files']),'benchmark_run':False,'production_promoted':False}))
