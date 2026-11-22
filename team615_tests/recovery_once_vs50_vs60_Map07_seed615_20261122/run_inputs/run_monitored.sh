set -euo pipefail
stage="$1"
shared=/home/junhao/quan/parallel_test_solver/match
sealed="$shared/solver_study/framework_screen_20261016/best87_independent_20261025/P407_P398_semifinal_three_maps_20261110"
sdk_python="$shared/.venv/bin/python"
mkdir "$stage/RUN_ONCE_CLAIM"
test ! -e "$stage/START.json"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export DISPLAY=:7100 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg ALSOFT_DRIVERS=null
mkdir "$stage/solution"
"$sdk_python" -m zipfile -e "$stage/candidate_snapshot.zip" "$stage/solution"
cd "$stage"
echo "START Map07 recovery_once seed615"
"$sdk_python" -B stage_run.py "$sealed" "$stage/solution" Map07 > "$stage/run.log" 2>&1 &
sdk_pid=$!
printf '%s\n' "$sdk_pid" > "$stage/SDK_PID"
wait "$sdk_pid"
echo "COMPLETE Map07 recovery_once seed615"
