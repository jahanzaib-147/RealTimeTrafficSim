import multiprocessing as mp
import time
import copy

LIGHT_CYCLE_ORDER = ['North', 'South', 'East', 'West']

def simulate_zone_wrapper(args):
    """
    Simulates one zone step in a worker process.
    """
    zone_index, zone_obj_copy, all_zones_map_for_worker, current_light_states = args

    # Apply current light state
    if zone_obj_copy.name in current_light_states:
        zone_obj_copy.traffic_light.set_state(current_light_states[zone_obj_copy.name])
        zone_obj_copy.traffic_light.manual_control = True

    result = zone_obj_copy.simulate_step(all_zones_map_for_worker)
    return zone_index, zone_obj_copy, result

def run_parallel(zones, steps, log_callback=None):
    results = []
    replay_data = []
    start_time = time.time()

    if log_callback:
        log_callback(f"Starting parallel simulation with {len(zones)} zones for {steps} steps...\n")

    num_processes = max(1, min(mp.cpu_count(), len(zones)))
    current_light_phase_index = LIGHT_CYCLE_ORDER.index('North')
    current_light_timer = 0

    # Initial light setup
    zones_map_initial = {z.name: z for z in zones}
    for zone_name in LIGHT_CYCLE_ORDER:
        zone = zones_map_initial[zone_name]
        if zone.name in [LIGHT_CYCLE_ORDER[current_light_phase_index], LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % 4]]:
            zone.traffic_light.set_state("green")
        else:
            zone.traffic_light.set_state("red")
        zone.traffic_light.manual_control = True

    with mp.Pool(processes=num_processes) as pool:
        for step in range(steps):
            current_light_timer += 1

            # Traffic light coordination logic
            current_green_zone_obj = next(
                (z for z in zones if z.name == LIGHT_CYCLE_ORDER[current_light_phase_index]), None)

            if current_green_zone_obj and current_light_timer > current_green_zone_obj.traffic_light.green_duration:
                for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                                  LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % 4]]:
                    for z in zones:
                        if z.name == zone_name:
                            z.traffic_light.set_state("red")

                current_light_phase_index = (current_light_phase_index + 1) % len(LIGHT_CYCLE_ORDER)

                for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                                  LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % 4]]:
                    for z in zones:
                        if z.name == zone_name:
                            z.traffic_light.set_state("green")

                current_light_timer = 0

            # Prepare for parallel simulation
            current_light_states = {z.name: z.traffic_light.get_state() for z in zones}
            zones_copy = copy.deepcopy(zones)
            zones_map_copy = {z.name: z for z in zones_copy}

            args_list = [(i, zone_obj, zones_map_copy, current_light_states)
                         for i, zone_obj in enumerate(zones_copy)]

            # Parallel execution
            parallel_raw_results = pool.map(simulate_zone_wrapper, args_list)

            # === Merge results from workers into original zones ===
            updated_zone_map = {z.name: z for z in zones}
            step_results = []

            for _, updated_zone_obj, result_dict in parallel_raw_results:
                original_zone = updated_zone_map.get(updated_zone_obj.name)
                if original_zone:
                    original_zone.vehicles = updated_zone_obj.vehicles
                    original_zone.total_processed_vehicles = updated_zone_obj.total_processed_vehicles
                    original_zone.total_wait_time = updated_zone_obj.total_wait_time
                    original_zone.vehicles_that_finished = updated_zone_obj.vehicles_that_finished
                    original_zone.vehicles_exited_zone = updated_zone_obj.vehicles_exited_zone
                    original_zone.congestion_history = updated_zone_obj.congestion_history
                    original_zone.traffic_light.set_state(updated_zone_obj.traffic_light.get_state())
                step_results.append(result_dict)

            results.append(step_results)

            # === Capture replay data ===
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

            if log_callback and (step % 5 == 0 or step == steps - 1):
                total_vehicles = sum(len(z.vehicles) for z in zones)
                log_callback(f"Parallel: Step {step + 1}/{steps} completed ({total_vehicles} vehicles active)\n")

    duration = time.time() - start_time
    if log_callback:
        log_callback(f"Parallel simulation completed in {duration:.4f} seconds\n")

    # Final state
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

    return replay_data, results, duration
