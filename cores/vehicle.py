# vehicle.py (with fix applied)
import random

class Vehicle:
    def __init__(self, id, origin, destination):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.current_zone = origin
        self.route = []
        self.route_index = 0  # Track the current position in the route
        self.wait_time = 0
        self.total_travel_time = 0
        self.has_moved_in_step = False
        self.color = f"#{random.randint(0, 0xFFFFFF):06x}"

    def __repr__(self):
        return (f"Vehicle(id={self.id}, current='{self.current_zone.name}', "
                f"dest='{self.destination.name}', wait={self.wait_time}, "
                f"total_time={self.total_travel_time})")

    def reset_wait_time(self):
        self.wait_time = 0

    def increment_wait_time(self):
        self.wait_time += 1

    def increment_total_travel_time(self):
        self.total_travel_time += 1

    def set_route(self, route_zones):
        self.route = route_zones
        self.route_index = 0

    def advance_route(self):
        if self.route_index + 1 < len(self.route):
            self.route_index += 1
            self.current_zone = self.route[self.route_index]  # ✅ FIX: update zone after move

    def get_next_zone_in_route(self):
        if self.route_index + 1 < len(self.route):
            return self.route[self.route_index + 1]
        return None

    def get_visual_info(self):
        return {
            'id': self.id,
            'current_zone': self.current_zone.name,
            'destination': self.destination.name,
            'color': self.color
        }
