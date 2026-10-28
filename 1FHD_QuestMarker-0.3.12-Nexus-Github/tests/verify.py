#!/usr/bin/env python3
"""Source-only rebuild and supplied native/overlay tests. Optional real EXE check."""
from pathlib import Path
import argparse,hashlib,json,os,platform,re,shutil,subprocess,sys,tempfile,zlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'SOURCE/lib'))
from build import build,hashes,load
from dat_codec import decode as dat_decode,encode as dat_encode
from gi_codec import decode as gi_decode,encode as gi_encode
from gai_codec import decode as gai_decode,encode as gai_encode
TARGET_SHA='e43a4b15503c705eebe2d8ce5778c2a2fb090db515a3fd86d319e5c5aa692ebf'
def walk(block,prefix=''):
    for e in block['entries']:
        name=prefix+e['name'];yield name,e
        if e['kind']=='block':yield from walk(e['value'],name+'.')
def verify(exe=None):
    checks=[];runs=[]
    def check(condition,label):
        assert condition,label;checks.append(label)
    def run(label,command,env=None):
        result=subprocess.run([str(x) for x in command],capture_output=True,text=True,env=env)
        assert result.returncode==0,label+'\n'+result.stdout+result.stderr
        runs.append({'test':label,'status':'passed','stdout':result.stdout.strip()})
    with tempfile.TemporaryDirectory() as folder:
        clean=Path(folder)
        shutil.copytree(ROOT/'SOURCE',clean/'SOURCE',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.o','*.coff'))
        shutil.copyfile(ROOT/'build.py',clean/'build.py')
        check(not any(p.suffix.lower() in ['.dat','.gi','.gai','.dll','.exe'] for p in (clean/'SOURCE').rglob('*') if p.is_file()),'Source-only inputs contain no compiled configs, images, DLL or game EXE')
        files=build(clean)
        expected=load(ROOT/'original-file-sha256.json')
        check(hashes(files)==expected,'All fourteen rebuilt runtime SHA-256 hashes equal original upload')
        check(len(files)==14,'Exactly fourteen runtime files')
        for name,data in files.items():
            out=clean/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
        nodes={};local_paths=[];texts=[]
        for name,data in files.items():
            if name.endswith('.dat'):
                fmt='cachedata' if name.endswith('CacheData.dat') else 'blockpar';d=dat_decode(data,fmt)
                check(dat_encode(d)==data,'DAT roundtrip: '+name)
                for path,e in walk(d['root']):
                    nodes[path]=e
                    if e['kind']=='parameter':texts.append((path,e['value']))
            elif name.endswith('.gi'):check(gi_encode(gi_decode(data))==data,'Typed GI roundtrip: '+name)
            elif name.endswith('.gai'):
                d=gai_decode(data);check(gai_encode(d)==data,'Typed GAI roundtrip, including sequence table')
                check(len(d['frames'])==20 and len(d['sequences'])==1,'Twenty GI animation frames and one sequence retained')
        prefix='Mods/FHD_MODS/FHD_QuestMarker_Preview/'
        for path,text in texts:
            if text.startswith('Mods\\FHD_MODS\\FHD_QuestMarker_Preview\\'):
                target=text.replace('\\','/').removeprefix(prefix)
                check(target in files,'Local runtime path resolves: '+target);local_paths.append(target)
        definitions=(clean/'SOURCE/Native/quest_marker.def').read_text();exports=set(re.findall(r'^\s*(FHD\w+)=',definitions,re.M))
        bindings=[e['value'] for path,e in nodes.items() if path.startswith('Data.ScriptLibs.FHDQuestNative.') and path.rsplit('.',1)[-1]!='Path' and e['kind']=='parameter']
        check(all(b.split(',')[-1] in exports for b in bindings),'Configured native export bindings exist in DLL definition')
        check(files['ModuleInfo.txt'].decode('cp1251')==(ROOT/'SOURCE/ModuleInfo.txt').read_bytes().decode('utf-8'),'CP1251 metadata and exact original line endings retained')
        run('Overlay merge with vanilla Galaxy fixture and both FHD_Trade load orders',[sys.executable,clean/'SOURCE/verify_overlay.py',clean,clean/'SOURCE/fixtures/vanilla_galaxy.json',clean/'SOURCE/fixtures/trade_overlay.json'])
        route_binary=clean/'route-test'
        run('Compile route planner fixture',['gcc','-std=c11','-O2',clean/'SOURCE/Native/test_route.c','-lm','-o',route_binary])
        run('Route planning oracle: 5000 cases, geometry and fuel models',[route_binary])
        env=os.environ.copy();env['FHD_TEST_EMULATE']='1'
        run('Freestanding i386 Delphi ABI and synthetic native route/UI fixture',['bash',clean/'SOURCE/Native/test_native.sh'],env)
        if exe is not None:
            exe=Path(exe).resolve()
            check(hashlib.sha256(exe.read_bytes()).hexdigest()==TARGET_SHA,'Attached target EXE has exact documented SHA-256')
            run('PE exports, relocations and target EXE function guards',[sys.executable,clean/'SOURCE/verify_release.py',exe])
            run('Actual EXE/DLL bytes with synthetic Windows APIs: callbacks, seven hooks and rejection guards',[sys.executable,clean/'SOURCE/verify_exe_integration.py',exe])
    authored=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in ['.git','dist','Native','__pycache__'] and (x!='Native' or p.relative_to(ROOT).parts[0]=='Native') for x in p.relative_to(ROOT).parts)]
    check(len(authored)<=100,'Source package stays within 100-file limit')
    return {'status':'passed','checks_passed':len(checks),'checks':checks,'test_runs':runs,
        'runtime_sha256':hashes(files),'local_paths_checked':len(local_paths),'native_export_bindings_checked':len(bindings),
        'actual_target_exe_bytes_tested':exe is not None,'target_exe_sha256':TARGET_SHA,'target_exe_in_source_or_install_archive':False,
        'live_windows_game_executed':False,'environment':{'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION,
            'gcc':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],'ld':subprocess.check_output(['ld','--version'],text=True).splitlines()[0]},
        'limits':['Windows APIs and game objects are emulation fixtures; no interactive game session was run.','Travel-time accuracy, live UI behavior and saves still require in-game verification.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',type=Path);p.add_argument('--report',type=Path);args=p.parse_args();report=verify(args.exe)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'checks':report['checks_passed'],'test_runs':len(report['test_runs']),'actual_target_exe_bytes_tested':report['actual_target_exe_bytes_tested']},indent=2))
