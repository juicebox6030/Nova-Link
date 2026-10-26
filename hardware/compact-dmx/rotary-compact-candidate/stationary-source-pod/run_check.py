from pathlib import Path
import sys,os,traceback
P=Path(__file__).resolve().parent
try:exec(compile((P/'check.py').read_text(),str(P/'check.py'),'exec'),{'__file__':str(P/'check.py')})
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
