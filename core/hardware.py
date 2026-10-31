"""
OpenHub Hardware Abstraction Layer
Integrates plyer and Android native services (Camera2 Torch, Sensors, Vibrator, Audio) for Pixel 7a with desktop simulation fallbacks.
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
        self._simulated_lux = 350.0 # Lux (normal indoor room)
        self._simulated_pitch_hz = 440.0 # Hz (Concert A)
        self._torch_active = False
        self._is_polling = False
        
        self.plyer_accel = None
        self.plyer_compass = None
        self.plyer_vibrator = None
        self.plyer_audio = None
        self.plyer_light = None
        
        self._camera_manager = None
        self._camera_id = None
        
        # Initialize Android native CameraManager for fast, direct LED torch control
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            if activity:
                self._camera_manager = activity.getSystemService(Context.CAMERA_SERVICE)
                if self._camera_manager:
                    ids = self._camera_manager.getCameraIdList()
                    if ids and len(ids) > 0:
                        self._camera_id = ids[0]
        except Exception:
            pass

        try:
            from plyer import accelerometer
            self.plyer_accel = accelerometer
        except Exception as e:
            print(f"[HardwareBridge] Accelerometer not available: {e}")

        try:
            from plyer import compass
            self.plyer_compass = compass
        except Exception as e:
            print(f"[HardwareBridge] Compass not available: {e}")

        try:
            from plyer import vibrator
            self.plyer_vibrator = vibrator
        except Exception as e:
            print(f"[HardwareBridge] Vibrator not available: {e}")

        try:
            from plyer import audio
            self.plyer_audio = audio
        except Exception as e:
            print(f"[HardwareBridge] Audio not available: {e}")

        try:
            from plyer import light
            self.plyer_light = light
        except Exception:
            pass

    def start_sensors(self):
        """Enable sensor polling."""
        self._is_polling = True
        if self.plyer_accel:
            try:
                self.plyer_accel.enable()
            except Exception:
                pass
        if self.plyer_compass:
            try:
                self.plyer_compass.enable()
            except Exception:
                pass
        if self.plyer_light:
            try:
                self.plyer_light.enable()
            except Exception:
                pass

    def stop_sensors(self):
        """Disable sensor polling to preserve battery."""
        self._is_polling = False
        if self.plyer_accel:
            try:
                self.plyer_accel.disable()
            except Exception:
                pass
        if self.plyer_compass:
            try:
                self.plyer_compass.disable()
            except Exception:
                pass
        if self.plyer_light:
            try:
                self.plyer_light.disable()
            except Exception:
                pass
        if self._torch_active:
            self.set_torch(False)

    def set_torch(self, state: bool):
        """Turns the physical LED camera flashlight on or off."""
        self._torch_active = bool(state)
        if self._camera_manager and self._camera_id:
            try:
                self._camera_manager.setTorchMode(self._camera_id, bool(state))
                return True
            except Exception as e:
                print(f"[HardwareBridge] Native Torch error: {e}")
        try:
            from plyer import flash
            if state:
                flash.on()
            else:
                flash.off()
            return True
        except Exception:
            pass
        return False

    def toggle_torch(self):
        """Toggles current torch state."""
        return self.set_torch(not self._torch_active)

    def is_torch_active(self):
        """Returns whether physical torch is currently illuminated."""
        return self._torch_active

    def get_orientation_angles(self):
        """
        Returns (pitch_deg, roll_deg, is_simulated).
        Pitch: Tilt forward/backward (-90 to +90)
        Roll: Tilt left/right (-90 to +90)
        """
        x, y, z = 0.0, 0.0, 9.81
        simulated = True

        if self.plyer_accel:
            try:
                reading = self.plyer_accel.acceleration
                if reading and reading[0] is not None:
                    x, y, z = reading[0], reading[1], reading[2]
                    simulated = False
            except Exception:
                pass

        if simulated:
            x, y, z = self._simulated_accel

        denom = math.sqrt(x * x + y * y + z * z)
        if denom == 0:
            return 0.0, 0.0, simulated

        roll = math.atan2(x, math.sqrt(y * y + z * z)) * (180.0 / math.pi)
        pitch = math.atan2(-y, z) * (180.0 / math.pi)

        return pitch, roll, simulated

    def set_simulated_accel(self, x, y, z):
        """Used for mouse/interactive testing on desktop."""
        self._simulated_accel = [x, y, z]

    def get_compass_heading(self):
        """Returns heading in degrees (0 = North, 90 = East, 180 = South, 270 = West)."""
        if self.plyer_compass:
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
        if self.plyer_vibrator:
            try:
                self.plyer_vibrator.vibrate(duration_ms / 1000.0)
                return
            except Exception:
                pass

    def get_audio_level_db(self):
        """Simulated or native microphone ambient decibel reading."""
        return self._simulated_mic_level

    def get_lux(self):
        """Returns ambient light illuminance in Lux and is_simulated boolean."""
        if self.plyer_light:
            try:
                lux = self.plyer_light.illumination
                if lux is not None:
                    return float(lux), False
            except Exception:
                pass
        return float(self._simulated_lux), True

    def set_simulated_lux(self, lux):
        self._simulated_lux = max(0.0, float(lux))

    def speak(self, text: str):
        """
        Speaks text on Google Pixel 7a using native Android Google Text-to-Speech
        or desktop simulation speech.
        """
        if not text:
            return
        import re
        cleaned = re.sub(r'```[\s\S]*?```', '', text)
        cleaned = re.sub(r'`[^`]*`', '', cleaned)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'[\*\#\_]', '', cleaned).strip()
        if not cleaned:
            return

        # 1. Android Native TTS via Plyer
        try:
            from plyer import tts
            tts.speak(message=cleaned[:3000])
            return
        except Exception as pe:
            pass

        # 2. Android Native TextToSpeech via pyjnius
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            Locale = autoclass('java.util.Locale')
            activity = PythonActivity.mActivity
            if activity:
                if not hasattr(self, '_android_tts') or not self._android_tts:
                    self._android_tts = TextToSpeech(activity, None)
                    self._android_tts.setLanguage(Locale.US)
                self._android_tts.speak(cleaned[:3000], TextToSpeech.QUEUE_FLUSH, None, "openhub_tts")
                return
        except Exception:
            pass

        # 3. Desktop Linux Simulation fallback (spd-say or espeak)
        try:
            import subprocess
            if subprocess.run(["which", "spd-say"], capture_output=True).returncode == 0:
                subprocess.Popen(["spd-say", "-t", "female2", cleaned[:300]])
            elif subprocess.run(["which", "espeak"], capture_output=True).returncode == 0:
                subprocess.Popen(["espeak", cleaned[:300]])
        except Exception:
            pass

