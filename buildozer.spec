[app]

title = Third Eye
package.name = thirdeye
package.domain = org.thirdeye

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,json
source.include_patterns = assets/*

version = 1.0

requirements = python3,kivy==2.3.0,requests,urllib3,certifi,charset_normalizer,idna,pyjnius

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
android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
