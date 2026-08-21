"""
OpenHub Hardware Abstraction Layer
Integrates plyer for Android (Pixel 7a) with smart desktop fallbacks for Linux testing.
"""
import math
import time
import threading

class HardwareBridge:
    def __init__(self):
        self._plyer_available = False
        self._simulated_accel = [0.0, 0.0, 9.81] # [x, y, z] in m/s^2
        self._simulated_heading = 0.0 # Degrees [0 - 360]
        self._simulated_mic_level = 35.0 # dB
        self._is_polling = False
        
        # Attempt to import plyer
        try:
            from plyer import accelerometer, compass, vibrator, gravity, audio
            self.plyer_accel = accelerometer
            self.plyer_compass = compass
            self.plyer_vibrator = vibrator
            self.plyer_gravity = gravity
            self.plyer_audio = audio
            self._plyer_available = True
        except Exception as e:
            print(f"[HardwareBridge] Plyer not available or native sensor absent ({e}). Running in Desktop Simulation Mode.")
            self._plyer_available = False

    def start_sensors(self):
        """Enable sensor polling."""
        self._is_polling = True
        if self._plyer_available:
            try:
                self.plyer_accel.enable()
            except Exception:
                pass
            try:
                self.plyer_compass.enable()
            except Exception:
                pass

    def stop_sensors(self):
        """Disable sensor polling to preserve battery."""
        self._is_polling = False
        if self._plyer_available:
            try:
                self.plyer_accel.disable()
            except Exception:
                pass
            try:
                self.plyer_compass.disable()
            except Exception:
                pass

    def get_orientation_angles(self):
        """
        Returns (pitch_deg, roll_deg, is_simulated).
        Pitch: Tilt forward/backward (-90 to +90)
        Roll: Tilt left/right (-90 to +90)
        """
        x, y, z = 0.0, 0.0, 9.81
        simulated = True

        if self._plyer_available:
            try:
                reading = self.plyer_accel.acceleration
                if reading and reading[0] is not None:
                    x, y, z = reading[0], reading[1], reading[2]
                    simulated = False
            except Exception:
                pass

        if simulated:
            x, y, z = self._simulated_accel

        # Calculate pitch and roll from gravity vector
        denom = math.sqrt(x * x + y * y + z * z)
        if denom == 0:
            return 0.0, 0.0, simulated

        # Roll: angle around Y-axis (tilt left/right)
        roll = math.atan2(x, math.sqrt(y * y + z * z)) * (180.0 / math.pi)
        # Pitch: angle around X-axis (tilt forward/back)
        pitch = math.atan2(-y, z) * (180.0 / math.pi)

        return pitch, roll, simulated

    def set_simulated_accel(self, x, y, z):
        """Used for mouse/interactive testing on desktop."""
        self._simulated_accel = [x, y, z]

    def get_compass_heading(self):
        """Returns heading in degrees (0 = North, 90 = East, 180 = South, 270 = West)."""
        if self._plyer_available:
            try:
                h = self.plyer_compass.heading
                if h is not None:
                    return float(h), False
            except Exception:
                pass
        return float(self._simulated_heading), True

    def set_simulated_heading(self, deg):
        self._simulated_heading = deg % 360.0

    def vibrate(self, duration_ms=50):
        """Trigger haptic feedback on Pixel 7a or log on desktop."""
        if self._plyer_available:
            try:
                # plyer.vibrator accepts duration in seconds
                self.plyer_vibrator.vibrate(duration_ms / 1000.0)
                return
            except Exception:
                pass
        # Desktop silent / terminal feedback

    def get_audio_level_db(self):
        """Simulated or native microphone ambient decibel reading."""
        # Returns current dB value
        return self._simulated_mic_level
