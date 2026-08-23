"""
OpenHub Voice Input & Speech-to-Text Bridge
Uses Android Native SpeechRecognizer via PyJNIus on mobile, with graceful simulation fallback.
"""
import threading
from kivy.utils import platform
from kivy.clock import Clock

class VoiceBridge:
    def __init__(self, on_result_callback=None, on_error_callback=None):
        self.on_result_callback = on_result_callback
        self.on_error_callback = on_error_callback
        self.is_listening = False

    def start_listening(self):
        """Starts voice recognition."""
        if self.is_listening:
            return
        self.is_listening = True

        if platform == 'android':
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                RecognizerIntent = autoclass('android.speech.RecognizerIntent')

                activity = PythonActivity.mActivity
                intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                )
                intent.putExtra(
                    RecognizerIntent.EXTRA_PROMPT,
                    "Speak to OpenHub Agent..."
                )

                # Custom Activity Result Listener for Kivy
                class SpeechResultListener(PythonJavaClass):
                    __javainterfaces__ = ['org/kivy/android/PythonActivity$ActivityResultListener']
                    __javacontext__ = 'app'

                    def __init__(self, outer):
                        super().__init__()
                        self.outer = outer

                    @java_method('(IILandroid/content/Intent;)V')
                    def onActivityResult(self, requestCode, resultCode, data):
                        if requestCode == 7788 and data:
                            try:
                                matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                                if matches and matches.size() > 0:
                                    text = matches.get(0)
                                    Clock.schedule_once(lambda dt: self.outer._deliver_result(text), 0)
                                    return
                            except Exception as e:
                                Clock.schedule_once(lambda dt: self.outer._deliver_error(f"Voice parse error: {e}"), 0)
                        Clock.schedule_once(lambda dt: self.outer._deliver_error("No speech recognized"), 0)

                listener = SpeechResultListener(self)
                PythonActivity.mActivity.registerActivityResultListener(listener)
                activity.startActivityForResult(intent, 7788)
            except Exception as e:
                self._deliver_error(f"Android speech init failed: {e}")
        else:
            # Desktop simulation mode
            print("[VoiceBridge] Desktop mode: Voice recognition simulated.")
            Clock.schedule_once(lambda dt: self._deliver_result("Build a countdown timer with alarm sound"), 1.2)

    def _deliver_result(self, text):
        self.is_listening = False
        if self.on_result_callback:
            self.on_result_callback(text)

    def _deliver_error(self, err_msg):
        self.is_listening = False
        if self.on_error_callback:
            self.on_error_callback(err_msg)
