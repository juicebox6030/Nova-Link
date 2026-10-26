from pathlib import Path
import os,sys,traceback
P=Path(__file__).resolve().parent
try:
 target=os.environ.get('ALLOCATION_SCRIPT','build.py');exec(compile((P/target).read_text(),str(P/target),'exec'),{'__file__':str(P/target)})
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
