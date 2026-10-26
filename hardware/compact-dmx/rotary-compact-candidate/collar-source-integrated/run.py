from pathlib import Path
import traceback
p=Path(__file__).resolve().parent
try:exec(compile((p/'build.py').read_text(),str(p/'build.py'),'exec'),{'__file__':str(p/'build.py'),'__name__':'__main__'})
except BaseException:
 traceback.print_exc()
 raise
