[app]

# (str) Title of your application
title = OpenHub

# (str) Package name
package.name = openhub

# (str) Package domain (needed for android packaging)
package.domain = org.nexus.openhub

# (str) Source code directory where main.py resides
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,ttf,json,wav,mp3

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
requirements = python3, kivy==2.3.1, kivymd==1.2.0, plyer, pygments, requests, urllib3, certifi, charset-normalizer, idna, python-dotenv

# (str) Supported orientations
orientation = sensor

# (bool) Use screen/window fullscreen mode
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, RECORD_AUDIO, VIBRATE, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, CAMERA

# (int) Target Android API
android.api = 34

# (str) Allow unencrypted local HTTP/WS traffic for Cortex
android.manifest.application_arguments = --uses-cleartext-traffic

# (int) Minimum API your APK will support
android.minapi = 21

# (bool) Accept SDK licenses
android.accept_sdk_license = True

# (str) Android architectures to build for (Pixel 7a is arm64-v8a)
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
