"""
OpenHub Camera Bridge
Captures photos on Pixel 7a using native Android ACTION_IMAGE_CAPTURE Intent with PyJNIus,
with desktop fallback for simulation and testing.
"""
import base64
import os
import threading
from kivy.utils import platform
from kivy.clock import Clock

class CameraBridge:
    def __init__(self, on_image_callback=None, on_error_callback=None):
        self.on_image_callback = on_image_callback
        self.on_error_callback = on_error_callback
        self.is_capturing = False

    def capture_photo(self):
        """Starts photo capture."""
        if self.is_capturing:
            return
        self.is_capturing = True

        if platform == 'android':
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                MediaStore = autoclass('android.provider.MediaStore')
                ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
                BitmapCompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')

                activity = PythonActivity.mActivity
                intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)

                class CameraResultListener(PythonJavaClass):
                    __javainterfaces__ = ['org/kivy/android/PythonActivity$ActivityResultListener']
                    __javacontext__ = 'app'

                    def __init__(self, outer):
                        super().__init__()
                        self.outer = outer

                    @java_method('(IILandroid/content/Intent;)V')
                    def onActivityResult(self, requestCode, resultCode, data):
                        if requestCode == 8899 and data:
                            try:
                                extras = data.getExtras()
                                if extras and extras.containsKey("data"):
                                    bmp = extras.get("data")
                                    bos = ByteArrayOutputStream()
                                    bmp.compress(BitmapCompressFormat.JPEG, 85, bos)
                                    b_array = bytes(bos.toByteArray())
                                    b64_str = base64.b64encode(b_array).decode('utf-8')
                                    Clock.schedule_once(lambda dt: self.outer._deliver_image(b64_str), 0)
                                    return
                            except Exception as e:
                                Clock.schedule_once(lambda dt: self.outer._deliver_error(f"Camera parse: {e}"), 0)
                                return
                        Clock.schedule_once(lambda dt: self.outer._deliver_error("Photo capture cancelled"), 0)

                listener = CameraResultListener(self)
                PythonActivity.mActivity.registerActivityResultListener(listener)
                activity.startActivityForResult(intent, 8899)
            except Exception as e:
                self._deliver_error(f"Android camera error: {e}")
        else:
            # Desktop simulation mode: generate a minimal test JPEG
            def _sim():
                mock_jpeg = (
                    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00'
                    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
                    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
                    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
                    b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00'
                    b'\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00'
                    b'\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00'
                    b'\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
                )
                b64_str = base64.b64encode(mock_jpeg).decode('utf-8')
                Clock.schedule_once(lambda dt: self._deliver_image(b64_str), 0.5)
            threading.Thread(target=_sim, daemon=True).start()

    def _deliver_image(self, b64_str):
        self.is_capturing = False
        if self.on_image_callback:
            self.on_image_callback(b64_str)

    def _deliver_error(self, err_msg):
        self.is_capturing = False
        if self.on_error_callback:
            self.on_error_callback(err_msg)
