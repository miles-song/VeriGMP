from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time

STAGE=Path(__file__).resolve().parent;OUT=STAGE/'evidence'
TARGET=OUT/'confirmation-window.json';BOOT=Path('/proc/sys/kernel/random/boot_id')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sample():
    result={}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():continue
        try:
            text=(directory/'stat').read_text();start=text.index('(');end=text.rindex(')');fields=text[end+2:].split()
            result[int(directory.name)]={'name':text[start+1:end],'ticks':int(fields[11])+int(fields[12]),'last_cpu':int(fields[36])}
        except (OSError,ValueError,IndexError):pass
    return result
if TARGET.exists():raise RuntimeError('Refusing to overwrite a declared confirmation window')
for tag in ['default1','default2']:
    if (OUT/(tag+'-binding.json')).exists() or (OUT/tag).exists():raise RuntimeError('Confirmation tag already exists')
report={'status':'running','benchmark_started':False,'policy':'Exactly two predeclared default runs; no result-based retry',
    'tags':['default1','default2'],'cpu':0,'startup_settle_seconds':10,'idle_probe_seconds':1,
    'max_other_process_cpu_percent':10,'measurement_controller_sha256':sha(Path(__file__)),
    'boot_id':BOOT.read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
TARGET.write_text(json.dumps(report,indent=2)+'\n')
try:
    time.sleep(10)
    a=sample();start=time.monotonic();time.sleep(1);b=sample();duration=time.monotonic()-start
    delta=[]
    for pid,item in b.items():
        if pid not in a or pid==os.getpid():continue
        cpu=100*(item['ticks']-a[pid]['ticks'])/os.sysconf('SC_CLK_TCK')/duration
        if cpu>0:delta.append({'pid':pid,'name':item['name'],'last_cpu':item['last_cpu'],'cpu_percent':cpu})
    report['preflight_process_cpu']=delta
    if any(row['cpu_percent']>report['max_other_process_cpu_percent'] for row in delta):
        raise RuntimeError('Measurement window busy; no benchmark started')
    if BOOT.read_text().strip()!=report['boot_id']:raise RuntimeError('Boot changed before measurement')
    report['benchmark_started']=True;TARGET.write_text(json.dumps(report,indent=2)+'\n')
    report['bindings']={}
    for tag in report['tags']:
        result=subprocess.run([sys.executable,STAGE/'time_verified.py','--tag',tag,'--cpu','0'])
        path=OUT/(tag+'-binding.json');binding=json.loads(path.read_text())
        if result.returncode or binding['status']!='pass':raise RuntimeError('Confirmation failed: '+tag)
        report['bindings'][tag]={'sha256':sha(path),'raw_sha256':binding['raw_sha256']}
    if BOOT.read_text().strip()!=report['boot_id']:raise RuntimeError('Boot changed during confirmation')
    if sha(Path(__file__))!=report['measurement_controller_sha256']:raise RuntimeError('Controller changed during confirmation')
    report.update(status='pass',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Same continuous WSL session, same pinned artifacts and two complete four-mode registered matrices')
except Exception as error:report.update(status='error',error=f'{type(error).__name__}: {error}')
finally:TARGET.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(report['status']!='pass')
