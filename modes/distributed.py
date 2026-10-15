try:
    from mpi4py import MPI
    MPI_AVAILABLE = True
except ImportError:
    MPI = None
    MPI_AVAILABLE = False

import time
import pickle

def run_distributed(zones, steps, log_callback=None): # Added log_callback
    """Run simulation in distributed mode using MPI"""
    if not MPI_AVAILABLE:
        raise RuntimeError("mpi4py not available. Install with: pip install mpi4py")
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    if size < 2:
        if log_callback:
            log_callback("Warning: Distributed mode requires at least 2 MPI processes")
            log_callback("Running in serial mode instead...\n")
        from . import serial
        return serial.run_serial(zones, steps, log_callback) # Pass log_callback to serial

    if rank == 0:  # Master process
        return _master_process(comm, zones, steps, size, log_callback) # Pass log_callback
    else:          # Worker processes
        _worker_process(comm, rank, log_callback) # Pass log_callback
        return [], None, 0.0 # Workers return empty results and 0 duration

def _master_process(comm, zones, steps, size, log_callback): # Added log_callback
    """Master process coordinates the distributed simulation"""
    results = []
    replay_data = [] # Master collects replay data
    start_time = time.time()
    
    if log_callback:
        log_callback(f"Starting distributed simulation with {size} processes...\n")
    
    # --- Traffic Light Initialization for Central Coordination ---
    # Similar to serial.py/parallel.py, master will manage light phases
    LIGHT_CYCLE_ORDER = ['North', 'South', 'East', 'West']
    current_light_phase_index = LIGHT_CYCLE_ORDER.index('North')
    current_light_timer = 0
    
    # Set initial green/red states and enable manual control for central coordination
    zones_map_initial = {z.name: z for z in zones}
    for zone_name in LIGHT_CYCLE_ORDER:
        zone = zones_map_initial[zone_name]
        if zone.name in [LIGHT_CYCLE_ORDER[current_light_phase_index], LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % 4]]:
            zone.traffic_light.set_state("green")
        else:
            zone.traffic_light.set_state("red")
        zone.traffic_light.manual_control = True # Set to manual control for central coordination

    # Distribute zones among workers
    zones_per_worker = len(zones) // (size - 1)
    remaining_zones = len(zones) % (size - 1)
    
    worker_assignments = {}
    zone_idx = 0
    
    for worker_rank in range(1, size):
        worker_zones_slice = zones_per_worker + (1 if worker_rank <= remaining_zones else 0)
        # Deep copy assigned zones for initial send to ensure independent worker objects
        worker_assignments[worker_rank] = copy.deepcopy(zones[zone_idx:zone_idx + worker_zones_slice])
        zone_idx += worker_zones_slice
        
        # Send initial assignment to worker
        comm.send(worker_assignments[worker_rank], dest=worker_rank, tag=0)
    
    # Main simulation loop
    for step in range(steps):
        # --- TRAFFIC LIGHT COORDINATION (Master) ---
        current_light_timer += 1

        current_green_zone_obj = next(
            (z for z in zones if z.name == LIGHT_CYCLE_ORDER[current_light_phase_index]), None)

        if current_green_zone_obj and current_light_timer > current_green_zone_obj.traffic_light.green_duration:
            for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                              LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % len(LIGHT_CYCLE_ORDER)]]:
                for z in zones:
                    if z.name == zone_name:
                        z.traffic_light.set_state('red')

            current_light_phase_index = (current_light_phase_index + 1) % len(LIGHT_CYCLE_ORDER)

            for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                              LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % len(LIGHT_CYCLE_ORDER)]]:
                for z in zones:
                    if z.name == zone_name:
                        z.traffic_light.set_state('green')

            current_light_timer = 0
        # --- END TRAFFIC LIGHT COORDINATION ---

        step_results = []
        
        # Prepare data for workers: full zone state (deep copy) and current light states
        # Full zone state is sent because workers need to check adjacent zones' capacities
        zones_copy_for_workers = copy.deepcopy(zones)
        current_light_states = {z.name: z.traffic_light.get_state() for z in zones}

        # Send current state and light states to all workers
        for worker_rank in range(1, size):
            # Send a tuple of (full_zones_copy, current_light_states)
            comm.send((zones_copy_for_workers, current_light_states), dest=worker_rank, tag=100 + step)
        
        # Collect results from workers
        for worker_rank in range(1, size):
            worker_results = comm.recv(source=worker_rank, tag=200 + step)
            step_results.extend(worker_results)
        
        # Update master's zone states based on worker results
        # Use a map for efficient updates
        updated_zone_map = {z.name: z for z in zones}
        for result in step_results:
            zone_name = result['zone']
            if zone_name in updated_zone_map:
                updated_zone_map[zone_name] = result['zone_obj']
        
        # Rebuild master's zone list from the updated map, preserving order if needed
        # Assuming original `zones` list order matters, recreate it from map
        zones = [updated_zone_map[z.name] for z in zones] # Update master's zones list
        
        results.append(step_results)
        
        # Capture replay data (similar to serial/parallel)
        current_frame_vehicles = []
        current_frame_lights = {}
        for zone in zones:
            current_frame_lights[zone.name] = zone.traffic_light.get_state()
            for vehicle in zone.vehicles:
                current_frame_vehicles.append(vehicle.get_visual_info())
        replay_data.append({
            'step': step,
            'traffic_lights': current_frame_lights,
            'vehicles': current_frame_vehicles
        })

        if log_callback and (step % 10 == 0 or step == steps - 1): # Log progress
            total_vehicles = sum(len(z.vehicles) for z in zones)
            log_callback(f"Distributed: Step {step + 1}/{steps} completed ({total_vehicles} vehicles active)\n")
    
    # Send termination signal
    for worker_rank in range(1, size):
        comm.send(None, dest=worker_rank, tag=999)
    
    duration = time.time() - start_time
    if log_callback:
        log_callback(f"Distributed simulation completed in {duration:.2f} seconds\n")
    
    # Final replay frame
    final_vehicles = []
    final_lights = {}
    for zone in zones:
        final_lights[zone.name] = zone.traffic_light.get_state()
        for vehicle in zone.vehicles:
            final_vehicles.append(vehicle.get_visual_info())
    replay_data.append({
        'step': steps,
        'traffic_lights': final_lights,
        'vehicles': final_vehicles
    })

    return replay_data, results, duration # Return duration

def _worker_process(comm, rank, log_callback): # Added log_callback
    """Worker process handles assigned zones"""
    # Receive initial zone assignment (deep copy was sent from master)
    assigned_zones = comm.recv(source=0, tag=0)
    
    # Create a map for worker's assigned zones for quick lookup
    assigned_zones_map = {z.name: z for z in assigned_zones}

    while True:
        # Receive updated state or termination signal
        data = comm.recv(source=0, tag=MPI.ANY_TAG)
        
        if data is None:  # Termination signal
            break
        
        # Unpack received data: full zone state and light states
        all_zones_from_master, current_light_states = data
        
        # Worker uses a map of all zones for correct inter-zone vehicle transfer logic
        all_zones_map_for_worker = {z.name: z for z in all_zones_from_master}

        worker_results = []
        updated_assigned_zones = [] # To hold the updated zone objects for this worker
        
        for zone_name_in_assignment in assigned_zones_map: # Iterate through the names to ensure correct object retrieval
            # Get the current zone object for this worker from the full map sent by master
            # This ensures the worker operates on the latest state of its assigned zone
            current_zone_obj = all_zones_map_for_worker[zone_name_in_assignment]

            # Apply the centrally determined light state to the zone's traffic light
            if current_zone_obj.name in current_light_states:
                current_zone_obj.traffic_light.set_state(current_light_states[current_zone_obj.name])
                current_zone_obj.traffic_light.manual_control = True # Ensure manual control is on

            # Simulate the step for this assigned zone, passing the comprehensive map
            result = current_zone_obj.simulate_step(all_zones_map_for_worker)
            worker_results.append(result)
            
            # Store the updated zone object for this worker's next iteration
            updated_assigned_zones.append(result['zone_obj'])
        
        # Update worker's local assigned_zones list with the new state
        # This will be used in the next step to identify its zones from the incoming all_zones_from_master
        assigned_zones = updated_assigned_zones 
        assigned_zones_map = {z.name: z for z in assigned_zones} # Rebuild map for consistency

        # Send results back to master
        comm.send(worker_results, dest=0, tag=200 + (comm.Get_tag() - 100)) # Maintain tag for master