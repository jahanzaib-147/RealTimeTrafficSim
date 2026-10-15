import argparse
import time
from simulation_engine import Zone
from processing_modes import run_serial, run_parallel, run_distributed

def main():
    parser = argparse.ArgumentParser(description="Traffic Flow Simulation")
    parser.add_argument("--mode", choices=["serial", "parallel", "distributed"], default="serial", 
                        help="Execution mode")
    parser.add_argument("--steps", type=int, default=100, 
                        help="Simulation steps")
    parser.add_argument("--zones", nargs="+", default=["North", "South", "East", "West"], 
                        help="Zone names")
    args = parser.parse_args()

    # Create zones
    zones = [Zone(name) for name in args.zones]
    
    # Run simulation
    start_time = time.perf_counter()
    
    if args.mode == "serial":
        results = run_serial(zones, args.steps)
    elif args.mode == "parallel":
        results = run_parallel(zones, args.steps)
    elif args.mode == "distributed":
        results = run_distributed([ (zone, args.steps) for zone in zones ])
    
    end_time = time.perf_counter()
    
    # Display results
    print("\nSimulation Results:")
    for result in results:
        print(f"\n{result['name']} Zone:")
        print(f"  Vehicles processed: {result['vehicles_processed']}")
        print(f"  Average wait time: {result['avg_wait_time']:.2f} seconds")
        print(f"  Current congestion: {result['congestion']} vehicles")
    
    print(f"\n⏱️  Execution time: {end_time - start_time:.4f} seconds")
    print(f"🚥 Mode: {args.mode.upper()} | Steps: {args.steps} | Zones: {len(args.zones)}")

if __name__ == "__main__":
    main()