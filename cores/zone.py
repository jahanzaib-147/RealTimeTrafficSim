import random
from .trafficlight import TrafficLight

class Zone:
    def __init__(self, name, capacity=50):
        self.name = name
        self.vehicles = []
        self.capacity = capacity
        self.adjacent_zones = []
        self.traffic_light = TrafficLight(name)
        self.congestion_history = []
        self.total_processed_vehicles = 0
        self.total_wait_time = 0
        self.vehicles_that_finished = 0
        self.vehicles_exited_zone = 0

    def add_vehicle(self, vehicle):
        if len(self.vehicles) < self.capacity:
            self.vehicles.append(vehicle)
            vehicle.current_zone = self
            vehicle.reset_wait_time()
            return True
        return False

    def remove_vehicle(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            return True
        return False

    def set_adjacent_zones(self, zones):
        self.adjacent_zones = zones

    def calculate_congestion(self):
        return len(self.vehicles) / self.capacity if self.capacity > 0 else 0

    def simulate_step(self, all_zones_map):
        vehicles_to_remove = []
        vehicles_moved_out_this_step = 0

        if not self.traffic_light.manual_control:
            self.traffic_light.update()

        current_vehicles_in_zone = self.vehicles.copy()
        random.shuffle(current_vehicles_in_zone)

        for vehicle in current_vehicles_in_zone:
            vehicle.increment_total_travel_time()
            vehicle.has_moved_in_step = False

            # ✅ Check if vehicle has reached destination
            if vehicle.current_zone.name == vehicle.destination.name:
                print(f"[🎯] Vehicle {vehicle.id} reached destination: {vehicle.destination.name}")
                vehicles_to_remove.append(vehicle)
                self.total_processed_vehicles += 1
                self.vehicles_that_finished += 1
                self.total_wait_time += vehicle.wait_time
                continue

            can_move_through_light = (
                self.traffic_light.get_state() == "green" or 
                (self.traffic_light.get_state() == "yellow" and self.traffic_light.get_time_to_change() > 0)
            )

            if can_move_through_light:
                if self.try_move_vehicle_on_route(vehicle, all_zones_map):
                    vehicles_to_remove.append(vehicle)
                    vehicles_moved_out_this_step += 1
                    vehicle.has_moved_in_step = True
                    self.vehicles_exited_zone += 1
                else:
                    vehicle.increment_wait_time()
            else:
                vehicle.increment_wait_time()

        for vehicle in vehicles_to_remove:
            if vehicle in self.vehicles:
                self.remove_vehicle(vehicle)

        congestion = self.calculate_congestion()
        self.congestion_history.append(congestion)

        if not self.traffic_light.manual_control:
            self.traffic_light.adjust_for_congestion(congestion)

        current_avg_wait_time = (
            sum(v.wait_time for v in self.vehicles) / len(self.vehicles)
            if self.vehicles else 0
        )

        recommendation = self.get_recommendation(congestion)

        return {
            'zone': self.name,
            'congestion': f"{congestion*100:.1f}%",
            'recommendation': recommendation,
            'vehicle_count': len(self.vehicles),
            'vehicles_moved_out': vehicles_moved_out_this_step,
            'total_processed_vehicles_in_zone': self.total_processed_vehicles,
            'avg_wait_time_current_zone': current_avg_wait_time,
            'traffic_light_state': self.traffic_light.get_state(),
            'zone_obj': self
        }

    def try_move_vehicle_on_route(self, vehicle, all_zones_map):
        target_zone = vehicle.get_next_zone_in_route()

        if target_zone and target_zone in self.adjacent_zones:
            actual_target_zone = all_zones_map.get(target_zone.name)

            if actual_target_zone and actual_target_zone.add_vehicle(vehicle):
                print(f"[✓] Vehicle {vehicle.id} moved from {self.name} to {actual_target_zone.name} (dest: {vehicle.destination.name})")
                vehicle.advance_route()
                return True

        return False

    def get_recommendation(self, congestion):
        if congestion > 0.9:
            return "CRITICAL: Activate emergency protocols, reroute traffic"
        elif congestion > 0.7:
            return "HIGH: Adjust traffic signals, extend green lights"
        elif congestion > 0.5:
            return "MODERATE: Monitor closely, prepare adjustments"
        else:
            return "LOW: Normal operations"

    def get_average_final_wait_time(self):
        if self.vehicles_that_finished > 0:
            return self.total_wait_time / self.vehicles_that_finished
        return 0
