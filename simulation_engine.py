import random
import time
from datetime import datetime

class Vehicle:
    def __init__(self, vehicle_id):
        self.id = vehicle_id
        self.wait_time = 0
        self.entry_time = datetime.now()

class TrafficLight:
    def __init__(self, cycle_time=30):
        self.cycle_time = cycle_time
        self.state = "GREEN"
        self.last_change = time.time()
    
    def update(self):
        current_time = time.time()
        if current_time - self.last_change > self.cycle_time:
            self.state = "RED" if self.state == "GREEN" else "GREEN"
            self.last_change = current_time
        return self.state

class Zone:
    def __init__(self, name):
        self.name = name
        self.vehicles = []
        self.traffic_light = TrafficLight()
        self.total_vehicles_processed = 0
        self.total_wait_time = 0
        self.congestion = 0
        self.flow_rate = 5
    
    def simulate_step(self, step_time=1):
        light_state = self.traffic_light.update()
        
        # Add new vehicles
        new_vehicles = random.randint(0, 5)
        for _ in range(new_vehicles):
            self.vehicles.append(Vehicle(f"{self.name}-{len(self.vehicles)+1}"))
        
        # Process vehicles during green light
        if light_state == "GREEN" and self.vehicles:
            processed = min(self.flow_rate, len(self.vehicles))
            for _ in range(processed):
                vehicle = self.vehicles.pop(0)
                exit_time = datetime.now()
                wait_seconds = (exit_time - vehicle.entry_time).total_seconds()
                self.total_wait_time += wait_seconds
                self.total_vehicles_processed += 1
        
        # Update metrics
        self.congestion = len(self.vehicles)
        for vehicle in self.vehicles:
            vehicle.wait_time += step_time
        
        return {
            "name": self.name,
            "vehicles_processed": self.total_vehicles_processed,
            "avg_wait_time": self.total_wait_time / self.total_vehicles_processed if self.total_vehicles_processed else 0,
            "congestion": self.congestion
        }