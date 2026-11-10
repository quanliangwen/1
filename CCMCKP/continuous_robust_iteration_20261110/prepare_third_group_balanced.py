from pathlib import Path
H=Path(__file__).resolve().parent
old=(H/'replay_third_group_repair.py').read_text(encoding='utf8')
needle="queue=sorted(pairs.values(),key=lambda r:(r['cost'],r['center'],r['pair'],r['delta']))[:reg['max_pair_centers']];histograms={};done=set();records=[];accepted=[];visited=0;generated=0"
replacement="""raw_members={tuple(r['selection']):r for r in data['candidate_shortlist']}
buckets=[sorted((r for r in pairs.values() if r['pair'] in raw_members and raw_members[r['pair']]['certificate']['lower']>=level),key=lambda r:(r['cost'],r['center'],r['pair'],r['delta'])) for level in [.99,.99025,.991,.992,.995]]
queue=[];queued=set()
while any(buckets) and len(queue)<reg['max_pair_centers']:
 for bucket in buckets:
  while bucket and (bucket[0]['center'],bucket[0]['pair'],bucket[0]['delta']) in queued:bucket.pop(0)
  if bucket and len(queue)<reg['max_pair_centers']:
   item=bucket.pop(0);queued.add((item['center'],item['pair'],item['delta']));queue.append(item)
histograms={};done=set();records=[];accepted=[];visited=0;generated=0"""
assert old.count(needle)==1
new=old.replace("research/third_group_repair_replay","research/third_group_repair_balanced_replay").replace(needle,replacement)
out=H/'replay_third_group_repair_balanced.py'
if out.exists():raise RuntimeError('No balanced replay source overwrite')
out.write_text(new,encoding='utf8')
reg=(H/'register_third_group_replay.py').read_text(encoding='utf8').replace("research/third_group_repair_replay","research/third_group_repair_balanced_replay").replace("'replay_third_group_repair.py'","'replay_third_group_repair_balanced.py'").replace("'register_third_group_replay.py'","'register_third_group_balanced.py'")
needle="D.mkdir(exist_ok=True)"
replacement="""negative=H/'research/third_group_repair_replay/INDEPENDENT_REPLAY_AUDIT.json';negative_data=json.load(open(negative))
if not negative_data['passed'] or negative_data['checked']!=120 or negative_data['accepted_new_raw']!=0 or negative_data['integer_refuted']!=120:raise RuntimeError('Actual complete first negative replay required')
inputs.extend([negative,H/'research/third_group_repair_replay/REPLAY_RESULT.json.gz',H/'prepare_third_group_balanced.py'])
D.mkdir(exist_ok=True)"""
assert reg.count(needle)==1
reg=reg.replace(needle,replacement).replace("'single third-group robust-CDF repair from own saved two-group checks below own saved center cost; layers are proposals, no new acceptance gate'","'balanced round-robin of own RAW-qualified pair centers at lower levels .99/.99025/.991/.992/.995; same proposal kernel and12second budget; respond to first40cheapest replay all120raw-refuted; no true probability/target/cache feedback'")
out=H/'register_third_group_balanced.py'
if out.exists():raise RuntimeError('No balanced registration driver overwrite')
out.write_text(reg,encoding='utf8')
print('Prepared distinct balanced replay sources; original replay/source/result unchanged; no search/MC launched')
