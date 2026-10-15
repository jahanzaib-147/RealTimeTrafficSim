import multiprocessing

def run_serial(zones, steps):
    results = []
    for zone in zones:
        for _ in range(steps):
            result = zone.simulate_step()
        results.append(result)
    return results

def run_zone_simulation(args):
    zone, steps = args
    for _ in range(steps):
        result = zone.simulate_step()
    return result

def run_parallel(zones, steps):
    with multiprocessing.Pool() as pool:
        results = pool.map(run_zone_simulation, [(zone, steps) for zone in zones])
    return results

def run_distributed(zones, steps):
    try:
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()
        
        if rank == 0:
            results = []
            # Distribute zones to workers
            for i in range(1, min(size, len(zones) + 1)):
                comm.send((zones[i-1], steps), dest=i, tag=0)
            
            # Process first zone
            if zones:
                results.append(run_zone_simulation((zones, steps)))
            
            # Collect results
            for i in range(1, min(size, len(zones) + 1)):
                if i <= len(zones):
                    results.append(comm.recv(source=i, tag=1))
            return results
        else:
            # Worker processes
            if rank <= len(zones):
                zone, steps = comm.recv(source=0, tag=0)
                result = run_zone_simulation((zone, steps))
                comm.send(result, dest=0, tag=1)
    except ImportError:
        print("⚠️ MPI not available. Falling back to parallel mode.")
        return run_parallel(zones, steps)