[app]

title = Third Eye
package.name = thirdeye
package.domain = org.thirdeye

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,json
source.include_patterns = assets/*

version = 1.0

# Pin python3 to 3.11 -- newer python-for-android defaults to 3.14, whose
# changed C API breaks Kivy 2.3.0's Cython-generated bindings. hostpython3
# must be pinned to the same version, since p4a requires host and target
# Python versions to match.
requirements = hostpython3==3.11.6,python3==3.11.6,kivy==2.3.0,requests,urllib3,certifi,charset_normalizer,idna,pyjnius

# Bundle the alert sound into the APK's res/raw so a native NotificationChannel
# can reference it as android.resource://<package>/raw/alert
android.add_resources = assets/alert.wav:raw:alert

# service_name:entry_point.py:foreground
services = thirdeye:service.py:foreground

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,POST_NOTIFICATIONS,WAKE_LOCK,RECEIVE_BOOT_COMPLETED

android.minapi = 24
android.api = 33
android.ndk_api = 24
# Pin an older NDK -- newer NDKs (e.g. r28c) ship stricter/changed OpenGL ES
# headers that don't match the GL function pointer types Kivy 2.3.0's
# generated cgl_gl.c expects, causing a fatal "incompatible function pointer
# types" compile error on glShaderSource et al.
android.ndk = 25b
# Single arch for now to keep first CI build fast; add armeabi-v7a later for older devices if needed
android.archs = arm64-v8a

android.allow_backup = True

# Accept Android SDK licenses non-interactively (required for CI builds)
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
