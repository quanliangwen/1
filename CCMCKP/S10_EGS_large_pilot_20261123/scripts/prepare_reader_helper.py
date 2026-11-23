from pathlib import Path
import base64,hashlib
R=Path(__file__).resolve().parent
code=(R/'audit_count_helper.cpp').read_bytes()
source='''from pathlib import Path
import base64,hashlib,json,subprocess
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_large_pilot_20261123'
assert Path.cwd().resolve()==B.resolve()
code=base64.b64decode(PAYLOAD)
assert hashlib.sha256(code).hexdigest()==EXPECTED
path=H/'audit_count_helper.cpp'
if path.exists():assert path.read_bytes()==code
else:path.write_bytes(code)
binary=H/'audit_count_helper'
if not binary.exists():
 p=subprocess.run(['g++','-O2','-std=c++17',str(path),'-lgmpxx','-lgmp','-o',str(binary)],capture_output=True)
 assert p.returncode==0,p.stderr.decode()
receipt={'role':'independent read-only postprocessing arithmetic, not a worker/optimizer','source_sha256':hashlib.sha256(code).hexdigest(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
(H/'AUDIT_TOOLCHAIN.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
'''.replace('PAYLOAD',repr(base64.b64encode(code).decode())).replace('EXPECTED',repr(hashlib.sha256(code).hexdigest()))
(R/'prepare_reader_helper_remote.py').write_text(source,encoding='utf-8')
print('Prepared independent reader arithmetic helper')
