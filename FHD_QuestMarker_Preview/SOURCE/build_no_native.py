from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dat_codec import parse_txt,dat_build,decode_tree,dat_unwrap
root=Path(__file__).resolve().parent.parent
for name,output in [('Main','CFG/Main.dat'),('Lang','CFG/Rus/Lang.dat'),('Lang_Eng','CFG/Eng/Lang.dat')]:
    data=dat_build(parse_txt((root/'SOURCE'/'CFG'/(name+'.txt')).read_text(encoding='utf8')))
    (root/output).parent.mkdir(parents=True,exist_ok=True)
    (root/output).write_bytes(data)
    decode_tree(dat_unwrap(data))
print('Built and verified native-free BlockPar DAT files')
