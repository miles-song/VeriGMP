"""Audit saved evaluation evidence; do not claim a new proof or runner execution."""
from pathlib import Path
import ast,hashlib,json,re,types
HERE=Path(__file__).resolve().parent
CACHE={}

def safe(name):
    p=(HERE/name).resolve()
    if not p.is_relative_to(HERE):raise ValueError('Unsafe archive path')
    return p

def captured(name):
    p=safe(name)
    if p not in CACHE:CACHE[p]=p.read_bytes()
    return CACHE[p]

def text(name):return captured(name).decode('utf-8')
def sha(name):return hashlib.sha256(captured(name)).hexdigest()
def read(name):return json.loads(text(name))

def load_module(name):
    module=types.ModuleType(name);module.__file__=str(safe(name+'.py'))
    exec(compile(captured(name+'.py'),module.__file__,'exec'),module.__dict__)
    return module

def audit():
    publication=read('publication.json');files=publication['files'];v=read('evidence/verification.json')
    assert v['status']=='pass' and not v['benchmark_run'] and not v['production_modified']
    for name,item in files.items():
        assert sha(name)==item['published_sha256'],name
        assert not re.search(r'/mnt/[a-z]/|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|Users[/\\]+\d+',text(name),re.I),name
    assert files['evidence/verification.json']['original_sha256']==publication['accepted_gate_original_sha256']
    assert len(v['source_sha256'])==87
    for name,digest in v['source_sha256'].items():
        assert sha(name)==digest and files[name]['transform']=='none',name
    checker=text('check_evaluation.py');tree=ast.parse(checker)
    selected=[node for node in tree.body if
        isinstance(node,ast.FunctionDef) and node.name in {'fatal_diagnostic','strict_vc'} or
        isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FATAL_DIAGNOSTIC' for t in node.targets)]
    env={'re':re};exec(compile(ast.Module(body=selected,type_ignores=[]),'<captured diagnostic functions>','exec'),env)
    imports=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))]
    assert all('_oracle' not in ast.unparse(node) and '_codegen' not in ast.unparse(node) for node in imports)
    assert 'exec(compile(checker_bytes' in checker and "exec(compile(inputs[module_name+'.py']" in checker
    assert "origin=json.loads(inputs['origin.json'])" in checker
    assert v['executed_snapshot_binding']['origin']=='captured bytes parsed'
    commands={c['log']:c for c in v['commands']}
    assert len(commands)==len(v['commands'])==37
    for log,c in commands.items():
        assert c['status']=='completed' and 'returncode' in c
        if log!='oracle.log':assert files['evidence/'+log]['original_sha256']==c['log_sha256']
    for log,expected in [('library.log',447),('runner-build.log',72),('codegen-build.log',72)]:
        diagnostic=text('evidence/'+log)
        assert commands[log]['returncode']==0
        assert re.findall(r'verification results:: (\d+) verified, (\d+) errors',diagnostic)==[(str(expected),'0')]
        assert 'partial verification' not in diagnostic and not env['fatal_diagnostic'](diagnostic)
        assert not re.search(r'(?im)^error(?:\[|:)',diagnostic)
    expected_mutants=['ignore-negative','ignore-incoming','wrong-radix','wrong-carry-bias','omit-high-input','zero-loop-carry','drop-top-word','skip-magnitude-conversion','wrong-sign','wrong-point-eight','ignore-caller-sign','overwrite-tmp']
    assert [m['name'] for m in v['mutations']]==expected_mutants
    source=text('candidate/native/verified/toom8_evaluation.rs')
    expected_fatals=['solver returned unknown','rlimit','failed to typecheck','failed to load metadata','could not compile crate','internal compiler error','verification timed out','out of memory','segmentation fault']
    assert v['appended_failure_fixtures_rejected']==expected_fatals
    for m in v['mutations']:
        log=m['name']+'.log';diagnostic=text('evidence/'+log);command=commands[log]
        assert m['semantically_rejected'] and env['strict_vc'](diagnostic,command['returncode'])
        argv=command['argv'];idx=argv.index('--verify-module')
        assert argv[idx+1]=='toom8_evaluation' and argv.count('--verify-module')==1
        assert source.count(m['before'])==1
        assert hashlib.sha256(source.replace(m['before'],m['after']).encode()).hexdigest()==m['source_sha256']
        assert files['evidence/'+log]['original_sha256']==m['log_sha256']
        for suffix in expected_fatals:assert not env['strict_vc'](diagnostic+'\n'+suffix+'\n',command['returncode'])
    oracle=load_module('evaluation_oracle');rows,counts=oracle.cases()
    input_bytes=('\n'.join(row[0] for row in rows)+'\n').encode()
    output_bytes=('\n'.join(row[1] for row in rows)+'\n').encode()
    assert len(rows)==v['oracle']['cases']==14156 and counts==v['oracle']['counts']
    assert hashlib.sha256(input_bytes).hexdigest()==v['oracle']['input_sha256']
    assert hashlib.sha256(output_bytes).hexdigest()==v['oracle']['output_sha256']
    assert commands['oracle.log']['returncode']==0 and commands['oracle.log']['log_sha256']==v['oracle']['output_sha256']
    assert [x['command'] for x in v['invalid']]==oracle.invalid() and len(v['invalid'])==16
    for i,item in enumerate(v['invalid']):
        log=f'invalid-{i:02}.log'
        assert item['returncode']==commands[log]['returncode']==101 and 'panicked at' in text('evidence/'+log)
        assert files['evidence/'+log]['original_sha256']==item['log_sha256']
    assert files['evidence/codegen.s']['original_sha256']==v['artifact_sha256']['codegen.s']
    assert load_module('evaluation_codegen').inspect(text('evidence/codegen.s'))==v['codegen']
    root=read('evidence/root-independent-audit.json')
    assert root['status']=='pass' and root['report_sha256']==publication['accepted_gate_original_sha256']
    assert files['evidence/root-independent-audit.json']['original_sha256']==publication['independent_audit_original_sha256']
    assert root['checker_only_changed']==['check_evaluation.py'] and root['captured_checker_modules_origin_execution_reviewed']
    assert root['independent_replayed_cases']==14156 and root['invalid_replayed']==16
    assert root['input_sha256']==v['oracle']['input_sha256'] and root['output_sha256']==v['oracle']['output_sha256']
    prior=read('evidence/prior-independent-mathematical-audit.json')
    assert prior['status']=='pass' and prior['report_sha256']==root['old_report_sha256']
    history=read('development/index.json');assert history['accepted_gate']=='evaluation-feature3' and len(history['attempts'])==14
    for attempt in history['attempts']:
        report=read(attempt['report']);assert report['status']==attempt['reported_status']
        for name,digest in report['source_sha256'].items():
            assert sha(attempt['source_overlays'].get(name,name))==digest,(attempt['name'],name)
    return {'status':'pass','scope':'Saved source/hash/log/independent-integer/codegen audit; no fresh proof or compiled runner execution',
        'sources':87,'mapped_files':len(files),'positive_counts':[447,72,72],'integer_cases':len(rows),'semantic_mutants':12,
        'mixed_fatal_rejections':108,'invalid_commands':16,'historical_attempts':14,'benchmark_run':False,
        'complete_toom8':False,'performance_accepted':False,'production_promoted':False}

if __name__=='__main__':print(json.dumps(audit(),indent=2))
