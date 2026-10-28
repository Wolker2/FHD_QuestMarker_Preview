#!/usr/bin/env python3
"""Build QuestMarker Preview 0.3.12 from supplied C and lossless asset sources."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'SOURCE/lib'))
from dat_codec import encode as dat_encode
from gi_codec import encode as gi_encode
from gai_codec import encode as gai_encode
PREFIX='Mods/FHD_MODS/FHD_QuestMarker_Preview/'
def load(path):return json.loads(Path(path).read_text('utf-8'))
def hashes(files):return {n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}
def build(root=ROOT):
    source=Path(root).resolve()/'SOURCE';files={}
    for name,target in [('Main','Main.dat'),('Lang','Rus/Lang.dat'),('CacheData','CacheData.dat')]:
        files['CFG/'+target]=dat_encode(load(source/'CFG'/(name+'.json')))
    for name,asset in load(source/'Assets/graphics.json')['files'].items():
        files[name]=gai_encode(asset) if name.endswith('.gai') else gi_encode(asset)
    files['ModuleInfo.txt']=(source/'ModuleInfo.txt').read_bytes().decode('utf-8').encode('cp1251')
    with tempfile.TemporaryDirectory() as folder:
        target=Path(folder)/'FHDQuestMarker.dll'
        result=subprocess.run(['bash',str(source/'Native/build.sh'),str(target)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        files['Native/FHDQuestMarker.dll']=target.read_bytes()
    return files
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-original',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'dist/FHD_QuestMarker-0.3.12-install.zip');a=p.parse_args();files=build()
    if a.verify_original:
        actual=hashes(files);expected=load(ROOT/'original-file-sha256.json')
        changed=sorted(n for n in actual.keys()|expected.keys() if actual.get(n)!=expected.get(n))
        if changed:raise SystemExit('Original-byte verification failed: '+', '.join(changed))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(PREFIX+name,(2026,1,1,0,0,0));info.external_attr=0o644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    print(json.dumps({'runtime_files':len(files),'original_bytes_verified':a.verify_original,'output':str(a.output)},indent=2))
if __name__=='__main__':main()
