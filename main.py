"""
Third Eye -- simple UI to start/stop background monitoring of a Dahua
camera's login activity. Start launches an Android foreground service
(service.py) that keeps polling even while this app is backgrounded; Stop
kills it. New logins pop a high-priority notification with a unique sound.
"""

import json
import os

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import StringProperty

# Must match buildozer.spec: package.domain + "." + package.name + ".Service" + <services= name, capitalized>
SERVICE_CLASS = "org.thirdeye.thirdeye.ServiceThirdeye"

CONFIG_FILENAME = "thirdeye_config.json"


def is_android():
    return "ANDROID_ARGUMENT" in os.environ


def config_path(app):
    return os.path.join(app.user_data_dir, CONFIG_FILENAME)


class ThirdEyeRoot(BoxLayout):
    status_text = StringProperty("Stopped")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=20, spacing=12, **kwargs)

        self.camera_ip = TextInput(hint_text="Camera IP, e.g. 192.168.29.200",
                                    multiline=False, size_hint_y=None, height=48)
        self.user = TextInput(hint_text="Username", text="admin",
                               multiline=False, size_hint_y=None, height=48)
        self.password = TextInput(hint_text="Password", password=True,
                                   multiline=False, size_hint_y=None, height=48)
        self.ignore = TextInput(hint_text="Ignore IPs, comma-separated (e.g. your own phone)",
                                 multiline=False, size_hint_y=None, height=48)
        self.interval = TextInput(hint_text="Poll interval seconds (default 5)",
                                   text="5", multiline=False, size_hint_y=None, height=48)

        self.status_label = Label(text="Status: Stopped", size_hint_y=None, height=40)

        btn_row = BoxLayout(size_hint_y=None, height=56, spacing=12)
        self.start_btn = Button(text="Start", on_release=self.on_start)
        self.stop_btn = Button(text="Stop", on_release=self.on_stop, disabled=True)
        btn_row.add_widget(self.start_btn)
        btn_row.add_widget(self.stop_btn)

        self.add_widget(Label(text="Third Eye", font_size=28, size_hint_y=None, height=48))
        self.add_widget(self.camera_ip)
        self.add_widget(self.user)
        self.add_widget(self.password)
        self.add_widget(self.ignore)
        self.add_widget(self.interval)
        self.add_widget(btn_row)
        self.add_widget(self.status_label)

        self.load_config()

    def load_config(self):
        app = App.get_running_app()
        path = config_path(app)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    cfg = json.load(f)
                self.camera_ip.text = cfg.get("camera_ip", "")
                self.user.text = cfg.get("user", "admin")
                self.ignore.text = ",".join(cfg.get("ignore", []))
                self.interval.text = str(cfg.get("interval", 5))
                # password intentionally not persisted in plain text
            except Exception:
                pass

    def save_config(self, cfg):
        app = App.get_running_app()
        to_save = dict(cfg)
        to_save.pop("password", None)
        with open(config_path(app), "w") as f:
            json.dump(to_save, f)

    def build_cfg(self):
        ignore = [ip.strip() for ip in self.ignore.text.split(",") if ip.strip()]
        try:
            interval = int(self.interval.text or "5")
        except ValueError:
            interval = 5
        return {
            "camera_ip": self.camera_ip.text.strip(),
            "user": self.user.text.strip() or "admin",
            "password": self.password.text,
            "ignore": ignore,
            "interval": interval,
            "https": False,
        }

    def on_start(self, *_):
        cfg = self.build_cfg()
        if not cfg["camera_ip"]:
            self.status_label.text = "Status: enter a camera IP first"
            return
        if not cfg["password"]:
            self.status_label.text = "Status: enter the camera password"
            return

        self.save_config(cfg)

        if is_android():
            self.request_notification_permission()
            self.start_android_service(cfg)
        else:
            self.status_label.text = "Status: service only runs on Android device"
            return

        self.status_label.text = "Status: Running (watching {})".format(cfg["camera_ip"])
        self.start_btn.disabled = True
        self.stop_btn.disabled = False

    def on_stop(self, *_):
        if is_android():
            self.stop_android_service()
        self.status_label.text = "Status: Stopped"
        self.start_btn.disabled = False
        self.stop_btn.disabled = True

    def request_notification_permission(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.POST_NOTIFICATIONS, Permission.INTERNET])
        except Exception:
            pass

    def start_android_service(self, cfg):
        from jnius import autoclass
        service = autoclass(SERVICE_CLASS)
        mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
        argument = json.dumps(cfg)
        service.start(mActivity, argument)

    def stop_android_service(self):
        from jnius import autoclass
        service = autoclass(SERVICE_CLASS)
        mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
        service.stop(mActivity)


class ThirdEyeApp(App):
    def build(self):
        self.title = "Third Eye"
        return ThirdEyeRoot()


if __name__ == "__main__":
    ThirdEyeApp().run()
