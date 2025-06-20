import time
import copy

LIGHT_CYCLE_ORDER = ['North', 'South', 'East', 'West']

def run_serial(zones, steps, log_callback=None):
    """
    Run simulation in serial mode and collect replay data.
    Implements central traffic light coordination for opposite zones.
    """
    results = []
    replay_data = []
    start_time = time.time()

    if log_callback:
        log_callback(f"Starting serial simulation with {len(zones)} zones for {steps} steps...\n")

    current_light_phase_index = LIGHT_CYCLE_ORDER.index('North')
    current_light_timer = 0
    
    # --- Initialize Traffic Lights ---
    # Set initial green/red states and enable manual control for central coordination
    zones_map = {z.name: z for z in zones} # Ensure zones_map is available for initial setup
    for zone_name in LIGHT_CYCLE_ORDER:
        zone = zones_map[zone_name]
        if zone.name in [LIGHT_CYCLE_ORDER[current_light_phase_index], LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % 4]]:
            zone.traffic_light.set_state("green")
        else:
            zone.traffic_light.set_state("red")
        zone.traffic_light.manual_control = True # Ensure manual override is enabled

    for step in range(steps):
        # 🔁 Rebuild zones map every step to stay in sync with any internal zone object changes
        # This is particularly important if Zone objects are modified in place within simulate_step
        zones_map = {z.name: z for z in zones} 

        # --- TRAFFIC LIGHT COORDINATION ---
        # Get the zone object corresponding to the current green phase
        current_green_zone_obj = zones_map[LIGHT_CYCLE_ORDER[current_light_phase_index]]

        # Increment timer for central light coordination
        current_light_timer += 1 

        # Check if the current green phase duration has expired
        if current_light_timer > current_green_zone_obj.traffic_light.green_duration:
            # Transition current green lights to yellow, then to red
            for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                              LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % len(LIGHT_CYCLE_ORDER)]]:
                if zone_name in zones_map: # Safety check
                    zones_map[zone_name].traffic_light.set_state('yellow')
                    # The yellow light transition happens within TrafficLight.update() if not manual,
                    # but here we are manually setting. So we need to ensure the yellow phase is handled.
                    # For simplicity of central control, we'll immediately transition to red after yellow_duration
            
            # Allow for yellow light duration (simulated as immediate transition after green)
            # This is a simplification. In a real-time system, yellow phase would persist for yellow_duration.
            # Given the current setup, we need to advance the overall cycle here.
            # A more advanced light coordination might involve a separate timer for yellow phase,
            # or allowing TrafficLight.update() to run fully if not manual_control.
            # For this central coordination, we effectively "skip" a step for yellow by immediately
            # calculating the next green phase and applying it.
            
            # Advance to next phase
            current_light_phase_index = (current_light_phase_index + 1) % len(LIGHT_CYCLE_ORDER)

            # Turn next phase green
            for zone_name in [LIGHT_CYCLE_ORDER[current_light_phase_index],
                              LIGHT_CYCLE_ORDER[(current_light_phase_index + 2) % len(LIGHT_CYCLE_ORDER)]]:
                if zone_name in zones_map: # Safety check
                    zones_map[zone_name].traffic_light.set_state('green')

            current_light_timer = 0 # Reset timer for the new green phase
        # --- END TRAFFIC LIGHT COORDINATION ---

        # 🎥 Capture visual state before simulating zones
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

        # Simulate each zone step-by-step using the centrally managed light states
        step_results = []
        for zone in zones:
            # Pass the updated zones_map to simulate_step to ensure consistency
            result = zone.simulate_step(zones_map) # Pass the map directly
            step_results.append(result)

        results.append(step_results)

        if log_callback and (step % 5 == 0 or step == steps - 1):
            total_vehicles = sum(len(z.vehicles) for z in zones)
            log_callback(f"Serial: Step {step + 1}/{steps} completed ({total_vehicles} vehicles active)\n")

    duration = time.time() - start_time
    if log_callback:
        log_callback(f"Serial simulation completed in {duration:.4f} seconds\n")

    # Final visual state after simulation
    current_frame_vehicles = []
    current_frame_lights = {}
    for zone in zones:
        current_frame_lights[zone.name] = zone.traffic_light.get_state()
        for vehicle in zone.vehicles:
            current_frame_vehicles.append(vehicle.get_visual_info())
    replay_data.append({
        'step': steps,
        'traffic_lights': current_frame_lights,
    'vehicles': total_vehicles    })

    return replay_data, results, duration # Return duration