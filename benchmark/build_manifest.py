import argparse
import random
from typing import List

from benchmark.adapters import HistoricalBugAdapter, SyntheticMutationAdapter
from benchmark.manifest import BenchmarkCase, write_manifest


def sample_cases(cases: List[BenchmarkCase], limit: int, seed: int) -> List[BenchmarkCase]:
    if limit <= 0 or len(cases) <= limit:
        return cases
    rng = random.Random(seed)
    return rng.sample(cases, k=limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build hybrid benchmark manifest")
    parser.add_argument("--historical-source", required=True, help="JSONL for historical cases")
    parser.add_argument("--synthetic-source", required=True, help="JSONL for synthetic templates")
    parser.add_argument("--output", required=True, help="Output manifest JSONL path")
    parser.add_argument("--historical-ratio", type=float, default=0.7)
    parser.add_argument("--synthetic-ratio", type=float, default=0.3)
    parser.add_argument("--target-count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    if abs((args.historical_ratio + args.synthetic_ratio) - 1.0) > 1e-9:
        raise ValueError("historical-ratio + synthetic-ratio must equal 1.0")

    historical_cases = HistoricalBugAdapter(args.historical_source).build_cases()
    synthetic_cases = SyntheticMutationAdapter(args.synthetic_source).build_cases()

    target_h = int(round(args.target_count * args.historical_ratio))
    target_s = max(0, args.target_count - target_h)

    selected_h = sample_cases(historical_cases, limit=target_h, seed=args.seed)
    selected_s = sample_cases(synthetic_cases, limit=target_s, seed=args.seed + 1)

    combined = selected_h + selected_s
    write_manifest(args.output, combined)
    print(f"Wrote {len(combined)} cases to {args.output}")


if __name__ == "__main__":
    main()
