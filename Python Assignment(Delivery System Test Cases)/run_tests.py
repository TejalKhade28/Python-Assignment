import json
import math
import random
import csv
import os
import glob



def euclidean(a, b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)


def load_data(filepath):
    with open(filepath) as f:
        data = json.load(f)
    for key in ("warehouses", "agents", "packages"):
        if key not in data:
            raise ValueError(f"Missing key '{key}' in {filepath}")
    return data


def assign_packages(packages, agents, warehouses):
    assignments = {a: [] for a in agents}
    for pkg in packages:
        wh_pos = warehouses[pkg["warehouse"]]
        nearest = min(agents, key=lambda a: euclidean(agents[a], wh_pos))
        assignments[nearest].append(pkg)
    return assignments


def simulate_deliveries(assignments, agents, warehouses, seed=42):
    random.seed(seed)
    results = {}
    for agent_id, pkgs in assignments.items():
        pos = agents[agent_id][:]
        total_dist = 0.0
        delivered = []
        total_delay = 0

        for pkg in pkgs:
            wh_pos  = warehouses[pkg["warehouse"]]
            dst     = pkg["destination"]
            leg1    = euclidean(pos, wh_pos)
            leg2    = euclidean(wh_pos, dst)
            delay   = random.randint(0, 10)
            total_delay += delay
            total_dist  += leg1 + leg2
            pos = dst
            delivered.append({
                "package_id": pkg["id"],
                "warehouse":  pkg["warehouse"],
                "destination": dst,
                "distance":   round(leg1+leg2, 2),
                "delay_min":  delay
            })

        eff = round(total_dist / len(pkgs), 2) if pkgs else 0.0
        results[agent_id] = {
            "packages_delivered": len(delivered),
            "delivered_details":  delivered,
            "total_distance":     round(total_dist, 2),
            "efficiency":         eff,
            "total_delay_min":    total_delay
        }
    return results


def generate_report(results):
    active = {a: r for a, r in results.items() if r["packages_delivered"] > 0}
    best   = min(active, key=lambda a: active[a]["efficiency"]) if active else "N/A"
    report = {}
    for a, d in results.items():
        report[a] = {
            "packages_delivered": d["packages_delivered"],
            "total_distance":     d["total_distance"],
            "efficiency":         d["efficiency"]
        }
    report["best_agent"] = best
    return report


def validate(results, packages):
    """Sanity checks on a test result."""
    issues = []
    total_delivered = sum(r["packages_delivered"] for r in results.values())
    if total_delivered != len(packages):
        issues.append(
            f"Package count mismatch: delivered {total_delivered}, expected {len(packages)}"
        )
    for agent, data in results.items():
        if data["total_distance"] < 0:
            issues.append(f"{agent} has negative distance")
        if data["packages_delivered"] > 0 and data["efficiency"] <= 0:
            issues.append(f"{agent} has zero/negative efficiency despite deliveries")
    return issues



def run_test(filepath, output_dir, case_num):
    label = f"Test Case {case_num}"
    print(f"\n{'─'*55}")
    print(f"  {label}  ←  {os.path.basename(filepath)}")
    print(f"{'─'*55}")

    data       = load_data(filepath)
    warehouses = data["warehouses"]
    agents     = data["agents"]
    packages   = data["packages"]

    print(f"  Warehouses: {len(warehouses)}  |  Agents: {len(agents)}  |  Packages: {len(packages)}")

    assignments = assign_packages(packages, agents, warehouses)

    # Show assignment summary
    for a, pkgs in assignments.items():
        ids = [p["id"] for p in pkgs]
        print(f"  {a} → {ids if ids else '(no packages)'}")

    results = simulate_deliveries(assignments, agents, warehouses, seed=case_num)
    report  = generate_report(results)
    issues  = validate(results, packages)

    # Per-agent summary
    print()
    for a, d in results.items():
        if d["packages_delivered"] == 0:
            print(f"  {a}: — idle —")
        else:
            print(f"  {a}: {d['packages_delivered']} pkgs | "
                  f"dist={d['total_distance']} | eff={d['efficiency']} | "
                  f"delay={d['total_delay_min']}min")

    print(f"\n {report['best_agent']}")
    if issues:
        print(f"{'; '.join(issues)}")
    else:
        print(f"Validation : PASSED ({len(packages)}/{len(packages)} packages delivered)")

    # Save individual report
    out_path = os.path.join(output_dir, f"report_{case_num}.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    return {
        "case":           case_num,
        "file":           os.path.basename(filepath),
        "warehouses":     len(warehouses),
        "agents":         len(agents),
        "packages":       len(packages),
        "best_agent":     report["best_agent"],
        "validation":     "PASSED" if not issues else "FAILED: " + "; ".join(issues),
        "report_file":    os.path.basename(out_path)
    }


# ── Summary CSV ──────────────

def save_summary_csv(rows, filepath):
    if not rows:
        return
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n Summary CSV saved → {filepath}")


# ── Main ───────

def main():
    
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Find all test_case_N.json files in current directory
    test_files = sorted(glob.glob("test_case_*.json"))

    if not test_files:
        print("\n[!] No test_case_N.json files found in current directory.")
        print("    Place files named test_case_1.json … test_case_10.json here and rerun.")
        return

    print(f"\n  Found {len(test_files)} test file(s): {[os.path.basename(f) for f in test_files]}")

    summary_rows = []
    passed = 0

    for tf in test_files:
        # Extract case number from filename
        base = os.path.splitext(os.path.basename(tf))[0]  # e.g. "test_case_1"
        try:
            case_num = int(base.split("_")[-1])
        except ValueError:
            case_num = base

        row = run_test(tf, output_dir, case_num)
        summary_rows.append(row)
        if row["validation"] == "PASSED":
            passed += 1

    # Overall summary
    print(f"\n{'═'*55}")
    print(f"  OVERALL RESULTS: {passed}/{len(test_files)} test cases PASSED")
    print(f"{'═'*55}")
    for r in summary_rows:
        status = "✓" if r["validation"] == "PASSED" else "✗"
        print(f"  {status}  Case {r['case']:>2}  |  "
              f"{r['packages']} pkgs  |  best={r['best_agent']}  |  {r['validation']}")

    save_summary_csv(summary_rows, os.path.join(output_dir, "summary.csv"))
    print(f"\n  Individual reports saved to: ./{output_dir}/report_N.json\n")


if __name__ == "__main__":
    main()
