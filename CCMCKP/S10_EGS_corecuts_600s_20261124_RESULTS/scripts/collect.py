from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
R=Path(__file__).resolve().parent
p=subprocess.run([sys.executable,'-X','utf8','E:/codex/S10_EGS_OA_20261123/remote.py',str(R/'collect_remote.py')],capture_output=True,check=True)
receipt=json.loads(p.stdout);(R/'COLLECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz'
subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60:/home/junhao/quan/parallel_test_solver/CCMKCP/work/egs_corecuts_600s_20261124/COMPACT_EVIDENCE_FULL.tar.gz',str(archive)],check=True)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
with tarfile.open(archive) as tar:
    assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in tar.getmembers())
    tar.extractall(R/'evidence',filter='data')
print(json.dumps(receipt))
