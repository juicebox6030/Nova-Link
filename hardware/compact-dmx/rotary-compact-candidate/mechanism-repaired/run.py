import os,traceback
from pathlib import Path
p=Path(os.environ['NOVA_ROTARY_CANDIDATE'])/'build.py'
try:exec(compile(p.read_text(),str(p),'exec'))
except Exception:traceback.print_exc();raise
