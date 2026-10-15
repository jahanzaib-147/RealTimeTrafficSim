import argparse
import time
import random
import sys
import os
from collections import deque # New import for efficient queue in BFS

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Import classes from cores
from cores.zone import Zone
from cores.vehicle import Vehicle

def create_zones(zone_names):
    """
    Creates Zone objects with random capacities and establishes adjacency relationships.
    Generates a configuration output string.
    """
    zones = []
    for name in zone_names:
        if 'downtown' in name.lower() or 'center' in name.lower():
            capacity = random.randint(80, 120)
        elif 'airport' in name.lower():
            capacity = random.randint(100, 150)
        elif 'mall' in name.lower():
            capacity = random.randint(60, 100)
        else:
            capacity = random.randint(40, 80)
        
        zones.append(Zone(name, capacity))

    for i, zone in enumerate(zones):
        adjacent_candidates = [z for j, z in enumerate(zones) if i != j]
        # Ensure at least 2 connections, up to 60% of other zones
        num_connections = min(len(adjacent_candidates), max(2, len(adjacent_candidates) * 6 // 10))
        adjacent = random.sample(adjacent_candidates, num_connections)
        zone.set_adjacent_zones(adjacent)

    zone_config_output = "\n--- Zone Configuration ---\n"
    for zone in zones:
        adj_names = [adj.name for adj in zone.adjacent_zones]
        zone_config_output += f"Zone: {zone.name} (Capacity: {zone.capacity}) | Adjacent: {', '.join(adj_names)}\n"
    zone_config_output += "--------------------------"

    return zones, zone_config_output

def populate_vehicles(zones, vehicle_count):
    """Creates vehicles, assigns them origin/destination zones, and finds a valid routeEnsures vehicles have correct origin-to-destination paths """
    def find_route_bfs(start_zone, end_zone):
        visited = set()
        queue = deque([(start_zone, [start_zone])])

        while queue:
            current_zone, path = queue.popleft()
            if current_zone == end_zone:
                return path

            visited.add(current_zone)

            for neighbor in current_zone.adjacent_zones:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    vehicles_output = f"\nCreating {vehicle_count} vehicles across {len(zones)} zones...\n"
    vehicles_created = 0
    max_attempts = vehicle_count * 5
    attempts = 0

    while vehicles_created < vehicle_count and attempts < max_attempts:
        origin = random.choice(zones)
        destination_candidates = [z for z in zones if z != origin]
        if not destination_candidates:
            attempts += 1
            continue

        destination = random.choice(destination_candidates)
        path = find_route_bfs(origin, destination)

        # ✅ Check if path exists and ends at correct destination
        if path and path[-1] == destination and len(origin.vehicles) < origin.capacity:
            vehicle = Vehicle(vehicles_created, origin, destination)
            vehicle.set_route(path)
            if origin.add_vehicle(vehicle):
                vehicles_output += f"[🛣️] Vehicle {vehicle.id} route: {[z.name for z in path]} → {destination.name}\n"
                vehicles_created += 1

        attempts += 1

    total_placed = 0
    for zone in zones:
        count = len(zone.vehicles)
        total_placed += count
        vehicles_output += f"   {zone.name} (cap: {zone.capacity}): {count} vehicles\n"

    vehicles_output += f"\nTotal vehicles placed: {total_placed}/{vehicle_count}"
    return total_placed, vehicles_output


def get_mode_handler(mode):
    """Dynamically imports and returns the simulation function for the specified mode."""
    try:
        if mode == "serial":
            from modes.serial import run_serial
            return run_serial
        elif mode == "parallel":
            from modes.parallel import run_parallel
            return run_parallel
        elif mode == "distributed":
            from modes.distributed import run_distributed
            return run_distributed
    except ImportError as e:
        error_msg = f"Mode '{mode}' disabled due to import error: {str(e)}\n"
        if mode == "distributed":
            error_msg += "For distributed mode, ensure mpi4py is installed and MPI is configured.\n"
        raise RuntimeError(error_msg)

def get_performance_report(mode, duration, zones, results, initial_vehicle_count):
    """Generates a detailed performance report for the simulation."""
    report = [f"\n{' PERFORMANCE REPORT '.center(70, '=')}"]
    report.append(f"Execution Mode: {mode.upper()}")
    report.append(f"Total Simulation Time: {duration:.4f} seconds")
    report.append(f"Simulation Steps: {len(results)}")
    report.append(f"Zones Simulated: {len(zones)}")

    total_processed_globally = sum(z.total_processed_vehicles for z in zones)
    total_remaining = sum(len(z.vehicles) for z in zones)
    total_capacity = sum(z.capacity for z in zones)

    report.append(f"Initial Vehicles: {initial_vehicle_count}")
    report.append(f"Vehicles Processed (Reached Destination): {total_processed_globally}")
    report.append(f"Vehicles Remaining in System: {total_remaining}")
    report.append(f"Total System Capacity: {total_capacity}")
    if total_capacity > 0:
        report.append(f"System Utilization (at end): {(total_remaining/total_capacity)*100:.1f}%")

    if duration > 0:
        throughput = total_processed_globally / duration
        report.append(f"Processing Throughput: {throughput:.2f} vehicles/second")

    all_congestion = []
    # all_final_wait_times = [] # Old: This was an average of zone averages
    total_wait_time_overall = 0 # New: Accumulate total wait time from all finished vehicles
    total_finished_vehicles_overall = 0 # New: Accumulate total finished vehicles count

    for zone in zones:
        if hasattr(zone, 'congestion_history') and zone.congestion_history:
            all_congestion.extend(zone.congestion_history)

        # Accumulate global wait time and finished vehicles count directly
        total_wait_time_overall += zone.total_wait_time
        total_finished_vehicles_overall += zone.vehicles_that_finished

    if all_congestion:
        non_zero_congestion = [c for c in all_congestion if c > 0]
        if non_zero_congestion:
            peak_congestion = max(non_zero_congestion)
            avg_congestion = sum(non_zero_congestion) / len(non_zero_congestion)
            report.append(f"Peak Congestion: {peak_congestion*100:.1f}%")
            report.append(f"Average Congestion: {avg_congestion*100:.1f}%")
        else:
            report.append("Peak Congestion: N/A (no congestion)")
            report.append("Average Congestion: N/A (no congestion)")
    else:
        report.append("Congestion data not available.")

    # Calculate true overall average wait time
    if total_finished_vehicles_overall > 0:
        overall_avg_wait = total_wait_time_overall / total_finished_vehicles_overall
        report.append(f"Overall Average Wait Time (all finished vehicles): {overall_avg_wait:.2f} steps")
    else:
        report.append("Overall Average Wait Time: N/A (no vehicles finished)")

    report.append(f"{'='*70}")
    return "\n".join(report)

def get_stakeholder_report(results, final_zones):
    """Generates a summary report for stakeholders, highlighting key traffic conditions."""
    if not results:
        return "No results to display."

    report = [f"\n{' TRAFFIC MANAGEMENT REPORT '.center(70, '=')}"]
    num_steps = len(results)
    steps_to_show = {0, num_steps // 2, num_steps - 1} if num_steps > 1 else {0} # Show start, middle, end

    for idx in sorted(steps_to_show):
        if idx < num_steps:
            report.append(f"\n   STEP {idx + 1}:")
            step_result = results[idx]
            step_result.sort(key=lambda x: x['zone']) # Sort by zone name for consistent output

            for z in step_result:
                status = "NORMAL"
                if "CRITICAL" in z['recommendation']:
                    status = "CRITICAL"
                elif "HIGH" in z['recommendation']:
                    status = "HIGH"
                elif "MODERATE" in z['recommendation']:
                    status = "MODERATE"

                moved = f" (moved: {z.get('vehicles_moved_out', 0)})"
                light = f"Light: {z.get('traffic_light_state', 'N/A')}"

                report.append(f"     [{status}] {z['zone']}: {z['congestion']} ({z.get('vehicle_count', 0)} vehicles, {light}{moved})")

                if z['recommendation'] != "LOW: Normal operations":
                    report.append(f"       WARNING: {z['recommendation']}")

                if 'avg_wait_time_current_zone' in z:
                    report.append(f"       Avg. Wait Time (current): {z['avg_wait_time_current_zone']:.2f} steps")
                if 'vehicles_exited_zone' in z['zone_obj'].__dict__: # Access the direct count from the zone object
                     report.append(f"       Vehicles Exited Zone: {z['zone_obj'].vehicles_exited_zone}")


    report.append(f"{'='*70}")
    return "\n".join(report)

def run_simulation(zone_names, vehicles, steps, mode, seed=None, log_callback=None):
    """
    Sets up and runs the traffic simulation in the specified mode (serial, parallel, or distributed).
    Returns replay data, simulation results, final zone states, initial vehicle count, and duration.
    """
    if log_callback:
        log_callback("Smart City Traffic Simulation\n")
        log_callback(f"Mode: {mode.upper()}\n")
        log_callback(f"Zones: {', '.join(zone_names)}\n")
        log_callback(f"Vehicles: {vehicles}\n")
        log_callback(f"Steps: {steps}\n")
        log_callback("=" * 70 + "\n")

    if seed:
        random.seed(seed)
        if log_callback:
            log_callback(f"Using random seed: {seed}\n")

    zones, zone_config_output = create_zones(zone_names)
    if log_callback:
        log_callback(zone_config_output + "\n")

    initial_vehicle_count, vehicles_output = populate_vehicles(zones, vehicles)
    if log_callback:
        log_callback(vehicles_output + "\n")

    try:
        handler = get_mode_handler(mode)
    except RuntimeError as e:
        if log_callback:
            log_callback(str(e) + "\n")
        return [], None, None, None, 0.0 # Return 0.0 for duration on error

    if log_callback:
        log_callback(f"\nStarting {mode} simulation...\n")

    # The handler functions (run_serial, run_parallel, run_distributed) should return duration as well
    replay_data, results, duration = handler(zones, steps, log_callback) # Now expects duration from handler

    if results is not None:
        if log_callback:
            log_callback(f"\nSimulation completed!\n")
        return replay_data, results, zones, initial_vehicle_count, duration
    else:
        # This branch is primarily for worker processes in distributed mode
        if log_callback:
            log_callback(f"Worker process completed task (no master output).\n")
        return [], None, None, None, 0.0 # Ensure duration is returned as 0.0 for worker processes
def main_cli():
    """Main function for the command-line interface."""
    parser = argparse.ArgumentParser(description="Smart City Traffic Flow Simulation")
    parser.add_argument("--zones", nargs="+", default=["North", "West", "East", "South"], help="Zone names")
    parser.add_argument("--vehicles", type=int, default=200, help="Number of vehicles")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps")
    parser.add_argument("--mode", choices=["serial", "parallel", "distributed"], default="serial", help="Mode")
    parser.add_argument("--seed", type=int, help="Random seed")

    args = parser.parse_args()

    def print_to_console(message):
        print(message, end='')

    # run_simulation now returns duration directly
    replay_data, results, final_zones, initial_vehicle_count, duration = run_simulation(
        args.zones, args.vehicles, args.steps, args.mode, args.seed, print_to_console
    )

    if results is not None: # Only print reports if simulation successfully ran (not a worker process)
        print(get_performance_report(args.mode, duration, final_zones, results, initial_vehicle_count))
        print(get_stakeholder_report(results, final_zones))

if __name__ == "__main__":
    main_cli()