import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
import sys
import math

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Corrected import: Removed create_vehicles as it's not a direct function in cli.py
from cli import run_simulation, create_zones

# --- Constants for Visualization ---
CANVAS_WIDTH, CANVAS_HEIGHT = 700, 700
CENTER_X, CENTER_Y = CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2
ZONE_SIZE = 100 # Size of zone rectangles
ROAD_WIDTH = 30 # Wider roads for better visual
VEHICLE_RADIUS = 7 # Slightly larger vehicles

# Roundabout specific dimensions
INNER_ROUNDABOUT_RADIUS = 100 # Radius of the inner circle of the roundabout
OUTER_ROUNDABOUT_RADIUS = INNER_ROUNDABOUT_RADIUS + ROAD_WIDTH # Outer edge of the main roundabout road

# Animation parameters
ANIMATION_SUB_STEPS = 15 # Number of intermediate frames for smooth transition for each path segment
ANIMATION_FRAME_DELAY_MS = 30 # Delay between each sub-frame (ms) -> Total time per sim step = 15 * 30 = 450ms

# Coordinates for zones (top-left x, top-left y, bottom-right x, bottom-right y)
ZONE_POSITIONS = {
    "North": (CENTER_X - ZONE_SIZE/2, 50, CENTER_X + ZONE_SIZE/2, 50 + ZONE_SIZE),
    "East":  (CANVAS_WIDTH - 50 - ZONE_SIZE, CENTER_Y - ZONE_SIZE/2, CANVAS_WIDTH - 50, CENTER_Y + ZONE_SIZE/2),
    "South": (CENTER_X - ZONE_SIZE/2, CANVAS_HEIGHT - 50 - ZONE_SIZE, CENTER_X + ZONE_SIZE/2, CANVAS_HEIGHT - 50),
    "West":  (50, CENTER_Y - ZONE_SIZE/2, 50 + ZONE_SIZE, CENTER_Y + ZONE_SIZE/2)
}

# Define key points for paths (junctions between zones and roundabout)
# These are points on the *outer* edge of the roundabout road.
ROUNDABOUT_ENTRY_POINTS = {
    "North": (CENTER_X, CENTER_Y - OUTER_ROUNDABOUT_RADIUS), # Top
    "East":  (CENTER_X + OUTER_ROUNDABOUT_RADIUS, CENTER_Y), # Right
    "South": (CENTER_X, CENTER_Y + OUTER_ROUNDABOUT_RADIUS), # Bottom
    "West":  (CENTER_X - OUTER_ROUNDABOUT_RADIUS, CENTER_Y)  # Left
}

# Angles for roundabout entry points (radians, relative to CENTER_X, CENTER_Y; standard math angles)
# East is 0, North is pi/2, West is pi, South is 3pi/2.
# Tkinter's Y-axis is inverted (increases downwards), so +Y is South.
# When using math.cos and math.sin, standard Cartesian coordinates apply.
# So, if CENTER_Y is higher values for lower visual positions, then to make North appear at top:
# North: Y-axis is negative relative to center if center is higher visually
# North: (CENTER_X, CENTER_Y - R) -> angle should be math.pi / 2
# South: (CENTER_X, CENTER_Y + R) -> angle should be 3 * math.pi / 2 or -math.pi / 2
# East: (CENTER_X + R, CENTER_Y) -> angle should be 0
# West: (CENTER_X - R, CENTER_Y) -> angle should be math.pi
ROUNDABOUT_ANGLES = {
    "East": 0,             # 0 degrees
    "North": math.pi / 2,  # 90 degrees
    "West": math.pi,       # 180 degrees
    "South": 3 * math.pi / 2 # 270 degrees
}

class TrafficSimulationGUI:
    def __init__(self, master):
        self.master = master
        master.title("Smart City Traffic Simulation")

        self.simulation_thread = None
        self.stop_event = threading.Event()
        self.animation_running = False
        self.replay_data = []
        self.current_replay_frame_index = -1 # Start at -1, first frame will be index 0
        self.vehicle_canvas_objects = {} # Stores {vehicle_id: canvas_item_id}
        self.vehicle_animation_states = {} # Stores {vehicle_id: {'path': [(x,y), ...], 'current_path_segment': 0, 'interp_progress': 0.0, 'current_x': x, 'current_y': y}}
        
        # Mapping for actual zone objects (not just names) for easier lookup
        self.zone_name_to_obj = {} 

        self.zones_config = ["North", "West", "East", "South"] # Match your LIGHT_CYCLE_ORDER in parallel/serial
        
        self.setup_gui()
        self.initialize_simulation_parameters()
        self.draw_fixed_scene() # Draw initial empty scene

    def setup_gui(self):
        # --- Parameters Frame ---
        param_frame = ttk.LabelFrame(self.master, text="Simulation Parameters")
        param_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(param_frame, text="Simulation Mode:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.mode_var = tk.StringVar(value="serial")
        ttk.Radiobutton(param_frame, text="Serial", variable=self.mode_var, value="serial").grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ttk.Radiobutton(param_frame, text="Parallel", variable=self.mode_var, value="parallel").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        # ttk.Radiobutton(param_frame, text="Distributed", variable=self.mode_var, value="distributed", state=tk.DISABLED).grid(row=0, column=3, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Number of Steps:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.steps_entry = ttk.Entry(param_frame, width=10)
        self.steps_entry.insert(0, "100")
        self.steps_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Number of Vehicles:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.vehicles_entry = ttk.Entry(param_frame, width=10)
        self.vehicles_entry.insert(0, "50") # Increase for more visual traffic
        self.vehicles_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # --- Controls Frame ---
        control_frame = ttk.LabelFrame(self.master, text="Controls")
        control_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.start_button = ttk.Button(control_frame, text="Start Simulation", command=self.start_simulation)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(control_frame, text="Stop Simulation", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.reset_button = ttk.Button(control_frame, text="Reset Simulation", command=self.reset_simulation)
        self.reset_button.grid(row=0, column=2, padx=5, pady=5)

        # --- Console Log ---
        log_frame = ttk.LabelFrame(self.master, text="Simulation Log")
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.log_text = scrolledtext.ScrolledText(log_frame, width=50, height=10, state='disabled')
        self.log_text.pack(expand=True, fill="both")

        # --- Canvas for Visualization (Roundabout Layout) ---
        self.canvas = tk.Canvas(self.master, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", borderwidth=2, relief="sunken")
        self.canvas.grid(row=0, column=1, rowspan=3, padx=10, pady=10)

        # --- Performance Report ---
        report_frame = ttk.LabelFrame(self.master, text="Performance Report")
        report_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.report_labels = {}
        report_data = {
            "Total Simulation Time:": "N/A",
            "Vehicles Processed (Reached Destination):": "N/A",
            "Vehicles Remaining in System:": "N/A",
            "Processing Throughput (vehicles/second):": "N/A",
            "Overall Average Wait Time (steps):": "N/A",
            "Congestion Data (Avg %):": "N/A"
        }
        for i, (key, value) in enumerate(report_data.items()):
            ttk.Label(report_frame, text=key).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            label = ttk.Label(report_frame, text=value)
            label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.report_labels[key] = label

        # Configure row/column weights for resizing
        self.master.grid_rowconfigure(2, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

    def initialize_simulation_parameters(self):
        # Create zones and store references by name
        zones_list, _ = create_zones(self.zones_config)
        self.zone_name_to_obj = {z.name: z for z in zones_list}

    def log_message(self, message):
        """Thread-safe logging to the GUI console."""
        self.master.after(0, self._insert_log, message)

    def _insert_log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message)
        self.log_text.yview(tk.END)
        self.log_text.config(state='disabled')

    def start_simulation(self):
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.log_message("Simulation already running.\n")
            return

        self.reset_gui_for_new_sim()
        self.stop_event.clear()

        try:
            steps = int(self.steps_entry.get())
            vehicles_count = int(self.vehicles_entry.get())
        except ValueError:
            self.log_message("Please enter valid numbers for steps and vehicles.\n")
            return

        mode = self.mode_var.get()
        self.log_message(f"Starting simulation in {mode.upper()} mode...\n")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.simulation_thread = threading.Thread(
            target=self._run_simulation_threaded,
            args=(steps, vehicles_count, mode)
        )
        self.simulation_thread.start()

    def _run_simulation_threaded(self, steps, vehicles_count, mode):
        try:
            # run_simulation from cli.py should return:
            # replay_data, results, final_zones, initial_vehicle_count, duration
            zones_for_simulation = list(self.zone_name_to_obj.values())
            replay_data, results, final_zones, initial_vehicle_count, duration = run_simulation(
                self.zones_config, vehicles_count, steps, mode, seed=None, log_callback=self.log_message
            )

            if self.stop_event.is_set():
                self.log_message("Simulation stopped by user.\n")
                self.master.after(0, self.enable_controls)
                return

            self.replay_data = replay_data
            self.current_replay_frame_index = -1 # Reset for animation loop
            self.master.after(0, self.update_performance_report, results, final_zones, initial_vehicle_count, duration)
            self.master.after(0, self.start_animation)

        except Exception as e:
            self.log_message(f"Simulation error: {e}\n")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            self.master.after(0, self.enable_controls)

    def stop_simulation(self):
        self.stop_event.set()
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.log_message("Sending stop signal to simulation...\n")
        self.stop_animation()
        self.enable_controls()

    def reset_simulation(self):
        self.stop_simulation()
        self.reset_gui_for_new_sim()
        self.log_message("Simulation GUI reset.\n")

    def reset_gui_for_new_sim(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        self.canvas.delete("all")
        self.replay_data = []
        self.current_replay_frame_index = -1
        self.stop_animation()

        for key in self.report_labels:
            self.report_labels[key].config(text="N/A")

        self.initialize_simulation_parameters() # Re-initialize zones
        self.draw_fixed_scene() # Redraw the empty scene (roads, zones)
        self.vehicle_canvas_objects = {} # Clear vehicle visual IDs
        self.vehicle_animation_states = {} # Clear animation states

        self.enable_controls()

    def enable_controls(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_performance_report(self, raw_results, final_zones, initial_vehicle_count, duration):
        if not raw_results:
            self.log_message("No results available for performance report.\n")
            return

        total_processed_vehicles = sum(z.vehicles_that_finished for z in final_zones) if final_zones else 0
        vehicles_remaining = sum(len(z.vehicles) for z in final_zones) if final_zones else 0

        processing_throughput = total_processed_vehicles / duration if duration > 0 else 0.0

        total_wait_time_all_zones = sum(z.total_wait_time for z in final_zones) if final_zones else 0
        total_finished_all_zones = sum(z.vehicles_that_finished for z in final_zones) if final_zones else 0
        overall_avg_wait_time = total_wait_time_all_zones / total_finished_all_zones if total_finished_all_zones > 0 else 0.0

        all_congestion_values = []
        for step_results in raw_results:
            for zone_result in step_results:
                try:
                    congestion_str = zone_result.get('congestion', '0.0%').replace('%', '')
                    all_congestion_values.append(float(congestion_str) / 100)
                except ValueError:
                    pass
        avg_congestion = sum(all_congestion_values) / len(all_congestion_values) if all_congestion_values else 0.0

        self.report_labels["Total Simulation Time:"].config(text=f"{duration:.4f} seconds")
        self.report_labels["Vehicles Processed (Reached Destination):"].config(text=f"{total_processed_vehicles}")
        self.report_labels["Vehicles Remaining in System:"].config(text=f"{vehicles_remaining}")
        self.report_labels["Processing Throughput (vehicles/second):"].config(text=f"{processing_throughput:.2f}")
        self.report_labels["Overall Average Wait Time (steps):"].config(text=f"{overall_avg_wait_time:.2f}")
        self.report_labels["Congestion Data (Avg %):"].config(text=f"{avg_congestion*100:.2f}%")


    def draw_fixed_scene(self):
        """Draws the static elements of the roundabout (zones, roads, center)."""
        self.canvas.delete("all")

        # Draw central roundabout circle
        self.canvas.create_oval(
            CENTER_X - INNER_ROUNDABOUT_RADIUS, CENTER_Y - INNER_ROUNDABOUT_RADIUS,
            CENTER_X + INNER_ROUNDABOUT_RADIUS, CENTER_Y + INNER_ROUNDABOUT_RADIUS,
            outline="gray", width=2, fill="#e0e0e0" # Lighter gray
        )
        self.canvas.create_text(CENTER_X, CENTER_Y, text="Roundabout", font=("Arial", 10, "bold"))

        # Draw Roads (using the OUTTER_ROUNDABOUT_RADIUS for the main circular path)
        # Main circular road around the roundabout
        self.canvas.create_oval(
            CENTER_X - OUTER_ROUNDABOUT_RADIUS, CENTER_Y - OUTER_ROUNDABOUT_RADIUS,
            CENTER_X + OUTER_ROUNDABOUT_RADIUS, CENTER_Y + OUTER_ROUNDABOUT_RADIUS,
            outline="gray", width=ROAD_WIDTH, tags="roundabout_road_outer"
        )
        
        # Straight connections from zones to roundabout
        for name, coords in ZONE_POSITIONS.items():
            start_x, start_y = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2 # Zone center
            end_x, end_y = ROUNDABOUT_ENTRY_POINTS[name] # Point on outer roundabout circle
            self.canvas.create_line(start_x, start_y, end_x, end_y, 
                                    fill="gray", width=ROAD_WIDTH, capstyle=tk.ROUND, tags=f"road_{name}_straight")

        # Draw Zones and their details (lights, counts)
        for name, coords in ZONE_POSITIONS.items():
            self.canvas.create_rectangle(coords, outline="blue", width=2, fill="#e6e6fa", tags=f"zone_{name}") # Lavender
            self.canvas.create_text(
                (coords[0] + coords[2]) / 2,
                (coords[1] + coords[3]) / 2,
                text=name, font=("Arial", 12, "bold"), tags=f"zone_text_{name}"
            )
            # Position for traffic light and vehicle count near zone entrance to roundabout
            light_x, light_y = 0,0
            count_x, count_y = 0,0
            
            # Place lights and counts strategically
            if name == "North":
                light_x, light_y = CENTER_X - ROAD_WIDTH/2 - 10, ZONE_POSITIONS["North"][3] + ROAD_WIDTH/2
                count_x, count_y = CENTER_X, ZONE_POSITIONS["North"][3] + 15
            elif name == "South":
                light_x, light_y = CENTER_X + ROAD_WIDTH/2 + 10, ZONE_POSITIONS["South"][1] - ROAD_WIDTH/2
                count_x, count_y = CENTER_X, ZONE_POSITIONS["South"][1] - 15
            elif name == "East":
                light_x, light_y = ZONE_POSITIONS["East"][0] - ROAD_WIDTH/2, CENTER_Y - ROAD_WIDTH/2 - 10
                count_x, count_y = ZONE_POSITIONS["East"][0] - 15, CENTER_Y
            elif name == "West":
                light_x, light_y = ZONE_POSITIONS["West"][2] + ROAD_WIDTH/2, CENTER_Y + ROAD_WIDTH/2 + 10
                count_x, count_y = ZONE_POSITIONS["West"][2] + 15, CENTER_Y
            
            self.canvas.create_oval(light_x-7, light_y-7, light_x+7, light_y+7,
                                    fill="gray", outline="black", tags=f"light_{name}")
            self.canvas.create_text(count_x, count_y, text="V: 0", font=("Arial", 10), tags=f"count_{name}")


    def start_animation(self):
        self.stop_animation() # Stop any previous animation
        self.animation_running = True
        self.current_replay_frame_index = -1 # Reset to load the first frame on next animate_frame_interpolated call
        self.vehicle_animation_states = {} # Clear any old animation states
        self.animate_frame_interpolated()

    def stop_animation(self):
        self.animation_running = False
        if hasattr(self, '_animation_job_id'):
            self.master.after_cancel(self._animation_job_id)
            del self._animation_job_id

    def generate_path(self, start_zone_name, dest_zone_name):
        """
        Generates a simplified path (list of points) for a vehicle from start_zone to dest_zone.
        Path: start_zone_center -> entry_point_to_roundabout -> arc_points -> exit_point_from_roundabout -> dest_zone_center
        """
        path = []

        # 1. Start at the center of the current zone
        start_coords = ZONE_POSITIONS[start_zone_name]
        start_point = ((start_coords[0] + start_coords[2]) / 2, (start_coords[1] + start_coords[3]) / 2)
        path.append(start_point)

        if start_zone_name == dest_zone_name:
            # If staying in the same zone (e.g., waiting), just stay at the zone center
            path.append(start_point)
            return path

        # 2. Move to the entry point of the roundabout from the start zone
        entry_to_roundabout = ROUNDABOUT_ENTRY_POINTS[start_zone_name]
        path.append(entry_to_roundabout)

        # 3. Travel along the roundabout arc
        start_angle_rad = ROUNDABOUT_ANGLES[start_zone_name]
        end_angle_rad = ROUNDABOUT_ANGLES[dest_zone_name]

        num_arc_points = ANIMATION_SUB_STEPS # Use same as sub-steps for smooth arc

        # Determine direction of travel around roundabout (counter-clockwise is typical for right-hand traffic)
        # Angles in math.atan2 are counter-clockwise from positive X-axis.
        # To ensure consistent counter-clockwise progression (e.g. N -> W -> S -> E)
        # If the end angle is "before" the start angle in counter-clockwise sense, add 2*pi to wrap around.
        if end_angle_rad < start_angle_rad:
            end_angle_rad += 2 * math.pi
        
        # Generate arc points
        for i in range(1, num_arc_points + 1): # Start from 1 as start_point is already added
            t = i / num_arc_points
            current_angle_rad = start_angle_rad + (end_angle_rad - start_angle_rad) * t
            
            # Map math coordinates to Tkinter coordinates (y-axis inverted)
            arc_x = CENTER_X + OUTER_ROUNDABOUT_RADIUS * math.cos(current_angle_rad)
            arc_y = CENTER_Y + OUTER_ROUNDABOUT_RADIUS * math.sin(current_angle_rad)
            path.append((arc_x, arc_y))

        # 4. Move from the exit point of the roundabout to the center of the destination zone
        exit_from_roundabout = ROUNDABOUT_ENTRY_POINTS[dest_zone_name] # Same point as entry for now
        # Check if exit_from_roundabout is the last point in the path to avoid duplicates
        if not path or path[-1] != exit_from_roundabout:
             path.append(exit_from_roundabout)

        dest_coords = ZONE_POSITIONS[dest_zone_name]
        dest_point = ((dest_coords[0] + dest_coords[2]) / 2, (dest_coords[1] + dest_coords[3]) / 2)
        # Check if dest_point is the last point in the path to avoid duplicates
        if not path or path[-1] != dest_point:
            path.append(dest_point)
        
        return path

    def animate_frame_interpolated(self):
        if not self.animation_running or not self.replay_data:
            return

        # Check if we need to advance to a new simulation step
        # This happens when all interpolation sub-steps for the current sim step are done,
        # or at the very beginning of the animation.
        
        # A flag to indicate if all active vehicles have completed their current path segment
        all_vehicles_finished_segment = True
        if self.vehicle_animation_states: # Only check if there are vehicles to animate
            for veh_id, anim_state in self.vehicle_animation_states.items():
                # A segment is considered finished if interp_progress is 1.0 AND current_path_segment is at last point of path
                # OR interp_progress is 1.0 AND current_path_segment is not at last point, meaning it's ready for next segment
                if anim_state['current_path_segment'] < len(anim_state['path']) -1 or anim_state['interp_progress'] < 1.0:
                    all_vehicles_finished_segment = False
                    break
        
        if self.current_replay_frame_index == -1 or all_vehicles_finished_segment:
            # Advance to the next simulation frame
            self.current_replay_frame_index += 1
            if self.current_replay_frame_index >= len(self.replay_data):
                self.stop_animation()
                self.log_message("Animation complete.\n")
                self.master.title(f"Smart City Traffic Simulation - Animation Finished")
                return
            
            # Process new simulation frame data
            current_frame_data = self.replay_data[self.current_replay_frame_index]
            self.master.title(f"Smart City Traffic Simulation - Step: {current_frame_data['step']}/{self.steps_entry.get()}")

            # Update traffic light states
            for zone_name, light_state in current_frame_data['traffic_lights'].items():
                color = "green" if light_state == "green" else "red"
                self.canvas.itemconfig(f"light_{zone_name}", fill=color)

            # Update vehicle counts
            zone_vehicle_counts = {name: 0 for name in self.zones_config}
            vehicles_in_current_frame = {v['id']: v for v in current_frame_data['vehicles']}

            # Update vehicle animation states and canvas objects
            vehicles_present_in_frame_ids = set(vehicles_in_current_frame.keys())
            
            # --- Handle existing vehicles and new vehicles ---
            for veh_id, vehicle_info in vehicles_in_current_frame.items():
                zone_vehicle_counts[vehicle_info['current_zone']] += 1
                
                # Check if vehicle is new or if its current_zone/destination has changed
                needs_new_path = False
                if veh_id not in self.vehicle_animation_states:
                    needs_new_path = True
                else:
                    # Vehicle exists. Check if its conceptual path needs to change
                    # A robust way would be to store prev_current_zone and prev_destination in anim_state
                    # and compare with current_vehicle_info.
                    # For now, if the path segment is finished, we always compute new path based on new data.
                    anim_state = self.vehicle_animation_states[veh_id]
                    if anim_state['current_path_segment'] >= len(anim_state['path']) - 1 and anim_state['interp_progress'] >= 1.0:
                        needs_new_path = True # It finished its last path, so get a new one

                if needs_new_path:
                    path = self.generate_path(vehicle_info['current_zone'], vehicle_info['destination'])
                    current_pos = path[0] if path else (0,0) # Start at first point of path
                    
                    self.vehicle_animation_states[veh_id] = {
                        'path': path,
                        'current_path_segment': 0,
                        'interp_progress': 0.0,
                        'current_x': current_pos[0],
                        'current_y': current_pos[1]
                    }
                    
                    if veh_id not in self.vehicle_canvas_objects:
                        canvas_item_id = self.canvas.create_oval(
                            current_pos[0] - VEHICLE_RADIUS, current_pos[1] - VEHICLE_RADIUS,
                            current_pos[0] + VEHICLE_RADIUS, current_pos[1] + VEHICLE_RADIUS,
                            fill=vehicle_info['color'], outline="black", tags=f"vehicle_{veh_id}"
                        )
                        self.vehicle_canvas_objects[veh_id] = canvas_item_id
                    else:
                        # If the canvas object already exists (e.g. from a previous simulation run)
                        # just update its position and color
                        self.canvas.coords(self.vehicle_canvas_objects[veh_id],
                                           current_pos[0] - VEHICLE_RADIUS, current_pos[1] - VEHICLE_RADIUS,
                                           current_pos[0] + VEHICLE_RADIUS, current_pos[1] + VEHICLE_RADIUS)
                        self.canvas.itemconfig(self.vehicle_canvas_objects[veh_id], fill=vehicle_info['color'])

                # Ensure vehicle is visible and has correct color
                if veh_id in self.vehicle_canvas_objects:
                    self.canvas.tag_raise(self.vehicle_canvas_objects[veh_id])
                    self.canvas.itemconfig(self.vehicle_canvas_objects[veh_id], fill=vehicle_info['color'])

            # --- Remove vehicles that are no longer in the current frame ---
            vehicles_to_remove = [veh_id for veh_id in self.vehicle_animation_states if veh_id not in vehicles_present_in_frame_ids]
            for veh_id in vehicles_to_remove:
                if veh_id in self.vehicle_canvas_objects:
                    self.canvas.delete(self.vehicle_canvas_objects[veh_id])
                    del self.vehicle_canvas_objects[veh_id]
                del self.vehicle_animation_states[veh_id]

            # Update vehicle counts display
            for zone_name, count in zone_vehicle_counts.items():
                self.canvas.itemconfig(f"count_{zone_name}", text=f"V: {count}")
            
        # --- Interpolate movement for current sub-frame ---
        for veh_id, anim_state in self.vehicle_animation_states.items():
            path = anim_state['path']
            current_segment_idx = anim_state['current_path_segment']
            interp_progress = anim_state['interp_progress']

            if not path or current_segment_idx >= len(path) - 1:
                # Vehicle has reached the end of its current path or path is empty
                # Its position should be at the last point of the path
                if path:
                    anim_state['current_x'], anim_state['current_y'] = path[-1]
                continue

            start_point = path[current_segment_idx]
            end_point = path[current_segment_idx + 1]

            # Interpolate between start_point and end_point
            new_x = start_point[0] + (end_point[0] - start_point[0]) * interp_progress
            new_y = start_point[1] + (end_point[1] - start_point[1]) * interp_progress

            self.canvas.coords(self.vehicle_canvas_objects[veh_id],
                               new_x - VEHICLE_RADIUS, new_y - VEHICLE_RADIUS,
                               new_x + VEHICLE_RADIUS, new_y + VEHICLE_RADIUS)

            # Update interpolation progress for the next sub-frame
            anim_state['interp_progress'] += (1.0 / ANIMATION_SUB_STEPS)
            
            # If interpolation for this segment is complete, move to the next segment
            if anim_state['interp_progress'] >= 1.0:
                anim_state['interp_progress'] = 0.0 # Reset progress for next segment
                anim_state['current_path_segment'] += 1
                if anim_state['current_path_segment'] < len(path):
                    # Set current_x, current_y to the start of the next segment to avoid drift
                    anim_state['current_x'], anim_state['current_y'] = path[anim_state['current_path_segment']]
                else:
                    # Vehicle completed this entire path for this simulation step. Snap to final point.
                    anim_state['current_x'], anim_state['current_y'] = path[-1]
                    # Keep segment index at or beyond end to indicate completion of current path
                    # This will trigger new path calculation on next sim step if needed.
                    anim_state['current_path_segment'] = len(path) - 1


        # Schedule next animation frame
        self._animation_job_id = self.master.after(ANIMATION_FRAME_DELAY_MS, self.animate_frame_interpolated)


# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficSimulationGUI(root)
    root.mainloop()

