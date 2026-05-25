"""
Simulates one day of delivery operations:
  - Reads warehouses, agents, and packages from data.json
  - Assigns each package to the nearest agent (by Euclidean distance)
  - Simulates pickup + delivery, computing total distance per agent
  - Generates and saves a report to report.json
  - BONUS: Random delays, ASCII route visualization, mid-day agent, CSV export
"""

import json
import math
import random
import csv
import time
import os


# ──────────────────────────────────────────────
# 1: JSON Parsing
# ──────────────────────────────────────────────

def load_data(filepath: str) -> dict:
    with open(filepath, "r") as f:
        raw = f.read()
    data = json.loads(raw)

    # Basic validation
    for key in ("warehouses", "agents", "packages"):
        if key not in data:
            raise ValueError(f"Missing required key in JSON: '{key}'")

    print(f"Loaded data: {len(data['warehouses'])} warehouses, "
          f"{len(data['agents'])} agents, {len(data['packages'])} packages.")
    return data


# ──────────────────────────────────────────────
# 2: Distance Utilities
# ──────────────────────────────────────────────

def euclidean(point_a: list, point_b: list) -> float:
    """
    Computes Euclidean distance between two 2D coordinate points.
    Formula: sqrt((x2-x1)^2 + (y2-y1)^2)
    """
    return math.sqrt((point_b[0] - point_a[0]) ** 2 +
                     (point_b[1] - point_a[1]) ** 2)

# ──────────────────────────────────────────────
# 3: Package Assignment
# ──────────────────────────────────────────────

def assign_packages(packages: list, agents: dict, warehouses: dict) -> dict:
    """
    Assigns each package to the nearest available agent(smallest Euclidean distance).
    Returns a dict: { agent_id: [list of package dicts] }
    """
    assignments = {agent: [] for agent in agents}

    for pkg in packages:
        warehouse_pos = warehouses[pkg["warehouse"]]

        # Find the agent closest to this package's warehouse
        nearest_agent = min(
            agents,
            key=lambda a: euclidean(agents[a], warehouse_pos)
        )

        assignments[nearest_agent].append(pkg)
        print(f"  Package {pkg['id']} (warehouse {pkg['warehouse']}) "
              f"  assigned to Agent {nearest_agent}")

    return assignments

# ──────────────────────────────────────────────
# 4: Delivery Simulation
# ──────────────────────────────────────────────

def simulate_deliveries(assignments: dict,
                        agents: dict,
                        warehouses: dict,
                        enable_delays: bool = True) -> dict:
    """
    Simulates each agent:
      1. Traveling from their start → warehouse (pickup)
      2. Traveling from warehouse → package destination (delivery)
    Accumulates total distance and optional random delay per delivery.

    Returns a results dict with distance and delivered package info.
    """
    results = {}

    for agent_id, pkgs in assignments.items():
        current_pos = agents[agent_id][:]  # agent's starting position
        total_distance = 0.0
        delivered = []
        total_delay = 0  # seconds (bonus feature)

        for pkg in pkgs:
            warehouse_pos = warehouses[pkg["warehouse"]]
            destination = pkg["destination"]

            # Leg 1: Agent → Warehouse (pickup)
            leg1 = euclidean(current_pos, warehouse_pos)

            # Leg 2: Warehouse → Destination (delivery)
            leg2 = euclidean(warehouse_pos, destination)

            # BONUS: Random delay between 0–10 minutes
            delay = 0
            if enable_delays:
                delay = random.randint(0, 10)
                total_delay += delay

            trip_distance = leg1 + leg2
            total_distance += trip_distance

            # After delivery, agent is now at the destination
            current_pos = destination

            delivered.append({
                "package_id": pkg["id"],
                "warehouse": pkg["warehouse"],
                "destination": destination,
                "distance": round(trip_distance, 2),
                "delay_min": delay
            })

        efficiency = (total_distance / len(pkgs)) if pkgs else 0.0

        results[agent_id] = {
            "packages_delivered": len(delivered),
            "delivered_details": delivered,
            "total_distance": round(total_distance, 2),
            "efficiency": round(efficiency, 2),   # avg distance per package
            "total_delay_min": total_delay
        }

    return results

# 5: Report Generation

def generate_report(results: dict) -> dict:
    """
    Builds the final report dict:
    
    """
    # Best agent = lowest efficiency score (most distance-efficient)
    active = {a: r for a, r in results.items() if r["packages_delivered"] > 0}
    best_agent = min(active, key=lambda a: active[a]["efficiency"])

    report = {}
    for agent, data in results.items():
        report[agent] = {
            "packages_delivered": data["packages_delivered"],
            "total_distance": data["total_distance"],
            "efficiency": data["efficiency"]
        }

    report["best_agent"] = best_agent
    return report


def save_report(report: dict, filepath: str):
    """Saves the report dict to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n Report saved to: {filepath}")



# BONUS 1: ASCII Route Visualization

def visualize_routes_ascii(agents: dict,
                           warehouses: dict,
                           assignments: dict,
                           grid_size: int = 20):
    """
    Renders a simple ASCII grid showing agents (A), warehouses (W),
    and package destinations (D) scaled to fit the grid.
    """
    print("\n" + "═" * 50)
    print("  ASCII ROUTE MAP  (scaled to grid)")
    print("═" * 50)

    # Collect all coordinates to find bounds (warehouses, agents, destinations)
    dest_points = [pkg["destination"] for pkgs in assignments.values() for pkg in pkgs]
    all_points = (
        list(agents.values()) +
        list(warehouses.values()) +
        dest_points
    )
    max_x = max(p[0] for p in all_points) or 1
    max_y = max(p[1] for p in all_points) or 1

    def scale(coord):
        """Scale real coordinates to grid indices."""
        x = round((coord[0] / max_x) * (grid_size - 1))
        y = round((coord[1] / max_y) * (grid_size - 1))
        return x, y

    # Build empty grid
    grid = [["·" for _ in range(grid_size)] for _ in range(grid_size)]

    # Place warehouses
    for wid, pos in warehouses.items():
        x, y = scale(pos)
        grid[grid_size - 1 - y][x] = wid[0]  # 'W'

    # Place destinations
    for agent_id, pkgs in assignments.items():
        for pkg in pkgs:
            x, y = scale(pkg["destination"])
            x = min(x, grid_size - 1)
            y = min(y, grid_size - 1)
            grid[grid_size - 1 - y][x] = "D"

    # Place agents (drawn last so they appear on top)
    for aid, pos in agents.items():
        x, y = scale(pos)
        grid[grid_size - 1 - y][x] = aid[0]  # 'A'

    # Print grid with Y-axis labels
    for row_idx, row in enumerate(grid):
        print(" ".join(row))

    print("\nLegend:  A=Agent  W=Warehouse  D=Destination  ·=empty")
    print("═" * 50)



# BONUS 2: Mid-Day Agent Joining

def add_midday_agent(agents: dict,
                     new_agent_id: str,
                     position: list) -> dict:
    """
    Simulates a new agent joining mid-day.
    Adds the agent to the agents dict and returns updated dict.
    """
    agents[new_agent_id] = position
    print(f"\n[+] Mid-day join: Agent {new_agent_id} at position {position}")
    return agents


# BONUS 3: Export Top Performer to CSV

def export_top_performer_csv(results: dict, report: dict, filepath: str):
    """
    Exports the best agent's detailed delivery log to a CSV file.
    """
    best = report["best_agent"]
    details = results[best]["delivered_details"]

    with open(filepath, "w", newline="") as csvfile:
        fieldnames = ["package_id", "warehouse",
                      "destination", "distance", "delay_min"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in details:
            row["destination"] = str(row["destination"])  # serialize list
            writer.writerow(row)

    print(f"Top performer ({best}) exported to: {filepath}")




def main():
    print("\n" + "╔" + "═"*46 + "╗")
    print("FastBox Logistics Simulator")
    print("╚" + "═"*46 + "╝\n")

    random.seed(42)  # Reproducible delays

    # ── Step 1: Load data ──
    data = load_data("data.json")
    warehouses = data["warehouses"]
    agents = data["agents"]
    packages = data["packages"]

    # ── BONUS: Add a mid-day agent ──
    agents = add_midday_agent(agents, "A4", [45, 10])
    # A4 joins but has no packages pre-assigned (they arrive after morning rush)

    # ── Step 2: Assign packages ──
    print("\n Assigning packages to nearest agents...")
    assignments = assign_packages(packages, agents, warehouses)

    # ── BONUS: ASCII visualization ──
    visualize_routes_ascii(agents, warehouses, assignments)

    # ── Step 3: Simulate deliveries ──
    print("\n Simulating deliveries (with random delays)...")
    results = simulate_deliveries(assignments, agents, warehouses, enable_delays=True)

    # ── Print simulation details ──
    print("\n── Simulation Summary ─────────────────────────")
    for agent_id, data in results.items():
        print(f"\n  Agent {agent_id}:")
        if data["packages_delivered"] == 0:
            print("    No packages assigned today.")
            continue
        for d in data["delivered_details"]:
            delay_str = f" (delayed {d['delay_min']} min)" if d["delay_min"] else ""
            print(f"     {d['package_id']} from {d['warehouse']} "
                  f" {d['destination']}  |  dist: {d['distance']:.2f}{delay_str}")
        print(f"    Total distance : {data['total_distance']} km")
        print(f"    Efficiency     : {data['efficiency']} km/package")
        print(f"    Total delay    : {data['total_delay_min']} min")

    # ── Step 4: Generate report ──
    report = generate_report(results)

    print("\n── Final Report ────")
    print(json.dumps(report, indent=2))

    # ── Step 5: Save report ──
    save_report(report, "report.json")

    # ── BONUS: Export CSV ──
    export_top_performer_csv(results, report, "top_performer.csv")

    # ── Sanity check ──
    total_delivered = sum(
        r["packages_delivered"] for r in results.values()
    )
    print(f"\n Packages delivered: {total_delivered} / {len(packages)}")
    if total_delivered == len(packages):
        print(" All packages accounted for!\n")
    else:
        print(" Warning: Package count mismatch!\n")


if __name__ == "__main__":
    main()
