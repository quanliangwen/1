"""Compare C++ with the user's original package at the same evaluation budget.

Python is used only as the comparison oracle. The solver executable is standalone.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import numpy as np


def verify(reference_dir, binary, instance, tmax, seed, budget, mc_samples, qc_timeout, native_cache_first):
    sys.path.insert(0, str(reference_dir))
    os.environ["CCMCKP_SEARCH_ABLATION_POLICY"] = str(reference_dir / "selected_policy.json")
    from src import exp_Result_TabuSearch as original
    from src.functions.func_fast_initialization import Fast_Construct_Procedure

    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        cache = work / "shared_cache"
        if not native_cache_first:
            prepared = original.prepare_instance_resources(instance, 0.99, 5.0, cache, qc_timeout)
        output = work / "native"
        subprocess.run([str(binary), "--instance", str(instance), "--tmax", str(tmax),
                        "--seed", str(seed), "--evaluation-budget", str(budget), "--mc-samples", str(mc_samples),
                        "--quick-check-timeout", str(qc_timeout), "--quick-check-cache-dir", str(cache),
                        "--output-dir", str(output), "--trace", "--inspect"], check=True)
        if native_cache_first:
            prepared = original.prepare_instance_resources(instance, 0.99, 5.0, cache, qc_timeout)
            assert prepared.quick_check_metadata["cache_hit"], "Python could not read C++ QuickCheck cache"
        resources = json.loads((output / "instance_resources.json").read_text())
        assert resources["exact"] == (not prepared.eval_func.reference_mc)
        for key, groups in (("weight", prepared.Aw), ("utility", prepared.Au), ("value", prepared.Av)):
            assert resources[key] == [list(map(int, groups[cid])) for cid in sorted(groups)], key
        assert resources["quick_check_list"] == prepared.quick_check, (
            "QuickCheck mismatch", len(resources["quick_check_list"]), len(prepared.quick_check),
            resources["quick_check_timed_out"], prepared.quick_check_metadata["timed_out"])
        trace, phase = [], "init"
        factor_ids = {id(factor): fid for fid, factor in enumerate(prepared.factors)}

        def evaluate(factors, *params):
            p = float(prepared.eval_func(factors, *params))
            used = getattr(prepared.eval_func, "last_samples_used", 0)
            evaluate.last_samples_used = used
            trace.append((phase, [factor_ids[id(f)] for f in factors], p, used))
            return p

        evaluate.reference_protocol = True
        evaluate.reference_mc = prepared.eval_func.reference_mc
        np.random.seed(seed)
        random.seed(seed)
        cp, metadata = Fast_Construct_Procedure(
            evaluate, prepared.Aw, prepared.Au, prepared.factors, 0.99, tmax, prepared.param,
            run_seed=seed, safe_reserve_seconds=0.0, authoritative_mc_samples=mc_samples,
            quick_check_list=prepared.quick_check, use_cost_risk_seed=True)
        np.random.seed(seed)
        random.seed(seed)
        phase = "search"
        result = original.Data_Driven_Tabu_Search(
            evaluate, cp, prepared.Av, prepared.factors, 0.99, tmax, prepared.param,
            30, mc_samples, prepared.quick_check, time_limit_seconds=600.0, evaluation_budget=budget,
            run_seed=seed, perturbation_policy="nearby_pair", operator_selection_policy="single",
            dual_perturbation_enabled=True)
        with next(output.glob("*_trace.csv")).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        native_trace = [(row["phase"], json.loads(row["solution"]), float(row["probability"]),
                         int(row["samples_used"])) for row in rows if row["event"] == "evaluate"]
        assert len(trace) == len(native_trace), ("trace lengths", len(trace), len(native_trace))
        for index, (python_row, cpp_row) in enumerate(zip(trace, native_trace), 1):
            assert python_row == cpp_row, ("evaluation", index, python_row, cpp_row)
        native_events = [row for row in rows if row["event"] != "evaluate"]
        assert len(native_events) == len(result.convergence_log), (
            "event lengths", len(native_events), len(result.convergence_log))
        for index, (cpp_row, python_row) in enumerate(zip(native_events, result.convergence_log)):
            for key in ("event", "cycle", "evaluation_count"):
                assert cpp_row[key] == str(python_row[key]), ("event", index, key, cpp_row, python_row)
            assert float(cpp_row["cost"]) == python_row["current_cost"], ("event cost", index)
            assert float(cpp_row["probability"]) == python_row["current_probability"], ("event probability", index)
        native = json.loads(next(output.glob("*_run0.json")).read_text())
        assert native["initial_solution"] == cp[0].tolist()
        assert native["initial_cost"] == cp[1]
        assert native["initial_probability"] == cp[2]
        assert native["initialization_source"] == metadata["source"]
        assert native["initialization_repair_count"] == metadata["repair_count"]
        for key in ("solution", "cost", "probability", "evaluation_count", "completed_cycles",
                    "total_class_scans", "total_tabu_moves", "perturbation_count", "pair_exchange_count",
                    "pair_exchange_evaluation_count", "pair_exchange_proposal_count", "stop_reason"):
            assert native[key] == getattr(result, key), (key, native[key], getattr(result, key))
        return {
            "instance": instance.name, "tmax": tmax, "seed": seed,
            "evaluator": prepared.evaluator_name, "mc_samples": mc_samples,
            "quick_check_rows": len(prepared.quick_check),
            "qc_timeout": qc_timeout, "evaluations_matched": len(trace),
            "cache_generated_by": "C++" if native_cache_first else "Python",
            "fresh_mc_evaluations_matched": sum(row[3] > 0 for row in trace),
            "events_matched": len(native_events), "initialization": metadata["source"],
            "initialization_repairs": metadata["repair_count"],
            "pair_exchanges": result.pair_exchange_count, "perturbations": result.perturbation_count,
            "best_cost": native["cost"], "probability": native["probability"],
            "solution": native["solution"],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--tmax", type=float, required=True)
    parser.add_argument("--seed", type=int, default=832273)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--mc-samples", type=int, default=1_000_000)
    parser.add_argument("--qc-timeout", type=float, default=1.0)
    parser.add_argument("--native-cache-first", action="store_true")
    args = parser.parse_args()
    result = verify(args.reference.resolve(), args.binary.resolve(), args.instance.resolve(),
                    args.tmax, args.seed, args.budget, args.mc_samples, args.qc_timeout, args.native_cache_first)
    print(json.dumps(result), flush=True)
