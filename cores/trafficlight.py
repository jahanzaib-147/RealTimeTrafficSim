class TrafficLight:
    def __init__(self, zone_name):
        self.zone_name = zone_name
        self.state = "red"  # Start with red for safety
        self.timer = 0
        self.green_duration = 20
        self.yellow_duration = 3  # New: Duration for yellow light
        self.red_duration = 20
        self.min_green = 10
        self.max_green = 60
        self.min_red = 10
        self.max_red = 60
        self.manual_control = False

    def update(self):
        """
        Updates the traffic light's state based on its timer and defined durations.
        Introduces a 'yellow' state for more realistic transitions.
        """
        self.timer += 1
        if self.manual_control:
            return

        if self.state == "green" and self.timer >= self.green_duration:
            self.state = "yellow"  # Transition from green to yellow
            self.timer = 0
        elif self.state == "yellow" and self.timer >= self.yellow_duration: # New state transition
            self.state = "red"     # Transition from yellow to red
            self.timer = 0
        elif self.state == "red" and self.timer >= self.red_duration:
            self.state = "green"   # Transition from red to green
            self.timer = 0

    def adjust_for_congestion(self, congestion):
        """
        Adjusts green and red light durations based on congestion levels.
        This logic aims to mitigate congestion by extending green lights or reducing red lights.
        """
        # Original logic remains the same, but adding a check to ensure yellow duration isn't affected by this.
        # This function primarily influences green/red durations.
        if congestion > 0.8:
            self.green_duration = min(self.max_green, self.green_duration + 10)
            self.red_duration = max(self.min_red, self.red_duration - 5)
        elif congestion > 0.6:
            self.green_duration = min(self.max_green, self.green_duration + 5)
            self.red_duration = max(self.min_red, self.red_duration - 3)
        elif congestion < 0.2:
            self.green_duration = max(self.min_green, self.green_duration - 5)
            self.red_duration = min(self.max_red, self.red_duration + 5)
        elif congestion < 0.4:
            self.green_duration = max(self.min_green, self.green_duration - 3)
            self.red_duration = min(self.max_red, self.red_duration + 3)
        
        # Ensure durations stay within min/max bounds
        self.green_duration = max(self.min_green, min(self.green_duration, self.max_green))
        self.red_duration = max(self.min_red, min(self.red_duration, self.max_red))

    def get_state(self):
        """Returns the current state of the traffic light."""
        return self.state

    def set_state(self, new_state):
        """Sets the state of the traffic light and resets the timer."""
        self.state = new_state
        self.timer = 0

    def get_time_to_change(self):
        """Returns the remaining time until the light changes state."""
        if self.state == "green":
            return self.green_duration - self.timer
        elif self.state == "yellow": # New: Time remaining for yellow light
            return self.yellow_duration - self.timer
        else: # red
            return self.red_duration - self.timer

    def __repr__(self):
        return f"TrafficLight(zone='{self.zone_name}', state='{self.state}', timer={self.timer})"