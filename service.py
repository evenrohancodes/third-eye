"""
service.py -- Third Eye background service.

Runs as an Android foreground service (started/stopped from main.py). Polls
the Dahua camera's own HTTP API for active login sessions and fires a
high-priority notification with a unique alert sound whenever a new,
non-ignored IP logs in. Keeps a small persistent "Third Eye is watching"
notification while running, as required by Android for foreground services.

Same core logic as the desktop dahua_access_alert.py, adapted to run inside
python-for-android's service process and to use native Android notification
channels (so the alert channel can carry its own bundled sound, independent
of the phone's default notification sound / silent mode settings).
"""

import json
import os
import time
import traceback

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from jnius import autoclass, cast

PythonService = autoclass("org.kivy.android.PythonService")
Context = autoclass("android.content.Context")
NotificationManager = autoclass("android.app.NotificationManager")
NotificationChannel = autoclass("android.app.NotificationChannel")
NotificationBuilder = autoclass("android.app.Notification$Builder")
AudioAttributes = autoclass("android.media.AudioAttributes")
Uri = autoclass("android.net.Uri")
Build = autoclass("android.os.Build")

STATUS_CHANNEL_ID = "thirdeye_status"
ALERT_CHANNEL_ID = "thirdeye_alert"
STATUS_NOTIF_ID = 1
ALERT_NOTIF_ID_BASE = 1000


def get_service():
    service = PythonService.mService
    service.setAutoRestartService(True)
    return service


def ensure_channels(service):
    if Build.VERSION.SDK_INT < 26:
        return  # notification channels only exist on Android 8+

    manager = cast(
        NotificationManager,
        service.getSystemService(Context.NOTIFICATION_SERVICE),
    )

    # Low-importance, silent channel for the persistent "running" notification.
    status_channel = NotificationChannel(
        STATUS_CHANNEL_ID, "Third Eye status", NotificationManager.IMPORTANCE_LOW
    )
    status_channel.setSound(None, None)
    manager.createNotificationChannel(status_channel)

    # High-importance channel with the bundled unique alert sound.
    alert_channel = NotificationChannel(
        ALERT_CHANNEL_ID, "Third Eye alerts", NotificationManager.IMPORTANCE_HIGH
    )
    sound_uri = Uri.parse(
        "android.resource://{}/raw/alert".format(service.getPackageName())
    )
    attrs = (
        AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_NOTIFICATION_EVENT)
        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
        .build()
    )
    alert_channel.setSound(sound_uri, attrs)
    alert_channel.enableVibration(True)
    manager.createNotificationChannel(alert_channel)


def start_foreground(service, text="Watching for camera access..."):
    if Build.VERSION.SDK_INT >= 26:
        builder = NotificationBuilder(service, STATUS_CHANNEL_ID)
    else:
        builder = NotificationBuilder(service)
    builder.setContentTitle("Third Eye")
    builder.setContentText(text)
    builder.setOngoing(True)
    notification = builder.build()
    service.startForeground(STATUS_NOTIF_ID, notification)


def push_alert(service, title, text):
    if Build.VERSION.SDK_INT >= 26:
        builder = NotificationBuilder(service, ALERT_CHANNEL_ID)
    else:
        builder = NotificationBuilder(service)
    builder.setContentTitle(title)
    builder.setContentText(text)
    builder.setAutoCancel(True)
    notification = builder.build()

    manager = cast(
        NotificationManager,
        service.getSystemService(Context.NOTIFICATION_SERVICE),
    )
    notif_id = ALERT_NOTIF_ID_BASE + (int(time.time()) % 10000)
    manager.notify(notif_id, notification)


# ---------------------------------------------------------------- Dahua API
def parse_active_users(text):
    prefix = "users["
    users = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if "=" not in line or not line.startswith(prefix):
            continue
        key, val = line.split("=", 1)
        idx_part, field = key[len(prefix):].split("].", 1)
        idx = int(idx_part)
        users.setdefault(idx, {})[field] = val
    return list(users.values())


def fetch_active_users(base_url, auth, timeout):
    url = "{}/cgi-bin/userManager.cgi?action=getActiveUserInfoAll".format(base_url)
    resp = requests.get(url, auth=auth, timeout=timeout)
    resp.raise_for_status()
    return parse_active_users(resp.text)


def detect_auth(base_url, user, password, timeout):
    test_url = "{}/cgi-bin/magicBox.cgi?action=getSystemInfo".format(base_url)
    for auth in (HTTPDigestAuth(user, password), HTTPBasicAuth(user, password)):
        try:
            resp = requests.get(test_url, auth=auth, timeout=timeout)
            if resp.status_code == 200:
                return auth
        except requests.RequestException:
            continue
    raise RuntimeError("Could not authenticate to the camera with Digest or Basic auth")


def main():
    service = get_service()
    ensure_channels(service)
    start_foreground(service, "Starting...")

    raw_args = os.environ.get("PYTHON_SERVICE_ARGUMENT", "{}")
    cfg = json.loads(raw_args or "{}")

    camera_ip = cfg.get("camera_ip")
    scheme = "https" if cfg.get("https") else "http"
    base_url = "{}://{}".format(scheme, camera_ip)
    user = cfg.get("user", "admin")
    password = cfg.get("password", "")
    ignore = set(cfg.get("ignore", []))
    interval = int(cfg.get("interval", 5))

    seen_sessions = set()
    auth = None

    while True:
        try:
            if auth is None:
                auth = detect_auth(base_url, user, password, timeout=5)
                start_foreground(service, "Watching {}".format(camera_ip))

            active = fetch_active_users(base_url, auth, timeout=5)
            for u in active:
                ip = u.get("ClientAddress", "unknown")
                if ip in ignore or ip == "Local":
                    continue
                key = (ip, u.get("Name", "?"), u.get("LoginTime", "?"))
                if key in seen_sessions:
                    continue
                seen_sessions.add(key)

                title = "Camera {} accessed".format(camera_ip)
                text = "{} from {} at {}".format(
                    u.get("Name", "?"), ip, u.get("LoginTime", "?")
                )
                push_alert(service, title, text)

        except Exception:
            traceback.print_exc()
            start_foreground(service, "Error - retrying...")
            auth = None

        time.sleep(interval)


if __name__ == "__main__":
    main()
