import os

from kivy.app import App
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import BooleanProperty, StringProperty
from kivy.core.audio import SoundLoader
import requests

from kivy.uix.textinput import TextInput
from kivymd.uix.list import OneLineListItem
from kivymd.uix.label import MDLabel
from kivymd.toast import toast
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore

import time

import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import threading

import pygame

pygame.mixer.init()

class FocusTextInput(TextInput):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.focus = True
        return super().on_touch_down(touch)


class SignupPage(Screen):
    is_login_mode = BooleanProperty(False)
    error_message = StringProperty("")
    selected_subcounty = ""

    def open_subcounty_menu(self):
        subcounties = [
            "Mvita",
            "Kisumu Central",
            "Kitui West",
            "Bumula",
            "Nyakach"
        ]

        menu_items = [
            {
                "text": sc,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=sc: self.set_subcounty(x),
            }
            for sc in subcounties
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.signup_card.ids.subcounty_field,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()

    def set_subcounty(self, subcounty):
        self.selected_subcounty = subcounty
        self.ids.signup_card.ids.subcounty_field.text = subcounty
        self.menu.dismiss()

    def process_signup(self):
        self.error_message = ""
        card = self.ids.signup_card
        username = card.ids.username_input.text
        password = card.ids.password_input.text
        
        # Determine preference based on checkbox active state
        input_type = "audio" if card.ids.audio_check.active else "text"

        # Ensure fields aren't empty
        if not username or not password:
            self.error_message = "Username and password are required"
            return
        
        if len(password) > 256:
            self.error_message = "Password too long"

        if not self.selected_subcounty:
            self.show_error("Please select your subcounty")
            return
        
        try:
            payload = {
                "username": username,
                "password": password,
                "input_type": input_type,
                "subcounty": self.selected_subcounty
            }
            # FastAPI's default port is 8000
            # response = requests.post("http://127.0.0.1", json=payload, timeout=5)
            response = requests.post(
                "http://127.0.0.1:8000/signup",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                app = App.get_running_app()
                app.current_username = username
                app.current_input_type = input_type
                app.current_subcounty = self.selected_subcounty
                # 3. Conditional Navigation on success
                if input_type == "audio":
                    self.manager.current = "audioinput"
                else:
                    self.manager.current = "textinput"
            else:
                self.error_message = response.json().get("detail", "Signup failed")
        except Exception as e:
            self.error_message = "Cannot connect to server"

    def process_login(self):
        self.error_message = ""
        card = self.ids.signup_card
        username = card.ids.username_input.text
        password = card.ids.password_input.text

        response = requests.post(
            "http://127.0.0.1:8000/login",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            app = App.get_running_app()
            app.current_username = username
            app.current_input_type = data.get("input_type")
            app.current_subcounty = data.get("subcounty")
            app.auth_token = data.get("access_token")
            if app.auth_token:
                app.store.put(
                    "auth",
                    token=app.auth_token,
                    username=app.current_username,
                    input_type=app.current_input_type,
                    subcounty=app.current_subcounty,
                )
            if data["input_type"] == "audio":
                self.manager.current = "audioinput"
            else:
                self.manager.current = "textinput"
        else:
            self.error_message = response.json().get("detail", "Signup failed")

    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode

class AudioInput(Screen):
    is_recording = BooleanProperty(False)
    response_audio_path = StringProperty("")
    generated_audio = StringProperty("")
    _recording_thread = None
    _recording_stop = threading.Event()
    _frames = None
    _samplerate = 16000
    _channels = 1
    _response_sound = None
    cam_screen = None

    def build(self):
        pass

    def _record_worker(self):
        self._frames = []
        self._recording_stop.clear()

        def callback(indata, frames, time_info, status):
            if status:
                print("Audio stream status:", status)
            self._frames.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self._samplerate,
                channels=self._channels,
                dtype="int16",
                callback=callback,
            ):
                while not self._recording_stop.is_set():
                    sd.sleep(100)
        except Exception as e:
            print("Failed to start audio stream:", e)

    def _build_audio_path(self):
        backend_data_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "backend",
            "data",
        )
        os.makedirs(backend_data_path, exist_ok=True)
        filename = f"recorded_{int(time.time())}.wav"
        return os.path.join(backend_data_path, filename)

    def _build_response_audio_path(self):
        frontend_data_path = os.path.join(
            os.path.dirname(__file__),
            "data",
        )
        os.makedirs(frontend_data_path, exist_ok=True)
        filename = f"response_{int(time.time())}.wav"
        return os.path.join(frontend_data_path, filename)
    
    def record_audio(self):
        if not self.is_recording:
            self.is_recording = True
            self.ids.record_audio.text = "Stop recording"
            toast("Recording started")
            self._recording_thread = threading.Thread(
                target=self._record_worker,
                daemon=True,
            )
            self._recording_thread.start()
            return

        self._recording_stop.set()
        if self._recording_thread:
            self._recording_thread.join(timeout=2.0)
        self.is_recording = False
        self.ids.record_audio.text = "Record audio"

        if not self._frames:
            print("No audio captured")
            return

        audio_data = np.concatenate(self._frames, axis=0)
        filepath = self._build_audio_path()
        write(filepath, self._samplerate, audio_data)
        print("Saved audio to:", filepath)

        self._set_audio_loading(True)
        threading.Thread(
            target=self._send_audio_request,
            args=(filepath,),
            daemon=True,
        ).start()

    def _send_audio_request(self, filepath):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/audio",
                json={"audio": filepath},
                timeout=30,
            )

            if response.status_code == 200:
                payload = response.json()
                reply = payload.get("reply", "")
                audio_url = payload.get("audio_url")
                print("Server replied:", reply)

                if audio_url:
                    audio_response = requests.get(
                        f"http://127.0.0.1:8000{audio_url}",
                        timeout=30,
                    )
                    if audio_response.status_code == 200:
                        response_path = self._build_response_audio_path()
                        with open(response_path, "wb") as f:
                            f.write(audio_response.content)
                        self.response_audio_path = response_path
                        threading.Thread(target=self.play_response, daemon=True).start()

        except Exception:
            print("Failed to send message")
        finally:
            Clock.schedule_once(lambda *_: self._set_audio_loading(False), 0)

    def _set_audio_loading(self, is_loading):
        spinner = self.ids.get("audio_spinner")
        if not spinner:
            return
        spinner.active = is_loading
        spinner.opacity = 1 if is_loading else 0

    def play_response(self):
        print("Playing Audio")
        if not self.response_audio_path or not os.path.isfile(self.response_audio_path):
            print("No response audio available")
            return
        
        try:
            pygame.mixer.music.load(self.response_audio_path)
            pygame.mixer.music.play()
            # Optional: wait for it to finish so the file isn't locked
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            print(self.response_audio_path)
            if self.response_audio_path and os.path.isfile(self.response_audio_path):
                try:
                    os.remove(self.response_audio_path)
                except Exception as e:
                    print("Failed to delete response audio:", e)

            self.response_audio_path = ""

    def capture_image(self):
        self.cam_screen = Builder.load_string('''
BoxLayout:
    orientation: 'vertical'
    Camera:
        id: cam
        resolution: (640, 480)
        play: True
    MDRaisedButton:
        text: "Capture"
        on_release: app.root.get_screen('audioinput').send_image(cam)
''')
        self.add_widget(self.cam_screen)

    def send_image(self, cam):
        backend_data_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')
        os.makedirs(backend_data_path, exist_ok=True)  # make sure folder exists

        filename = f"captured_{int(time.time())}.png"
        filepath = os.path.join(backend_data_path, filename)

        cam.export_to_png(filepath)
        
        cam.play = False  # stops the live feed
        cam._camera = None  # release low-level camera reference

        # Remove the camera widget from the screen
        if self.cam_screen:
            self.remove_widget(self.cam_screen)
            self.cam_screen = None
        self._set_audio_loading(True)
        threading.Thread(
            target=self._send_image_audio_request,
            args=(filepath,),
            daemon=True,
        ).start()

    def _send_image_audio_request(self, filepath):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/image",
                json={"image": filepath},
                timeout=30
            )
            
            if response.status_code == 200:
                reply = response.json().get("reply", "")
                if not reply:
                    return

                response = requests.post(
                    "http://127.0.0.1:8000/image_audio",
                    json={"text": reply},
                    timeout=30,
                )

                if response.status_code == 200:
                    payload = response.json()
                    audio_url = payload.get("audio_url")

                    if audio_url:
                        audio_response = requests.get(
                            f"http://127.0.0.1:8000{audio_url}",
                            timeout=30,
                        )
                        if audio_response.status_code == 200:
                            response_path = self._build_response_audio_path()
                            with open(response_path, "wb") as f:
                                f.write(audio_response.content)
                            self.response_audio_path = response_path
                            threading.Thread(target=self.play_response, daemon=True).start()
        except Exception:
            print("Failed to generate audio")
        finally:
            Clock.schedule_once(lambda *_: self._set_audio_loading(False), 0)
        

    def image_response(self):
        pass

class TextInputScreen(Screen):
    cam_screen = None
    chat_padding = dp(20)

    def send_message(self):
        message = self.ids.message_input.text.strip()
        try:
            self.ids.chat_list.add_widget(self._make_chat_label(f"You: {message}"))
            Clock.schedule_once(self._scroll_chat_to_bottom, 0)
        except Exception as e:
            print("Failed to update chat list:", e)

        if not message:
            return

        try:
            response = requests.post(
                "http://127.0.0.1:8000/message",
                json={"message": message},
                timeout=30
            )

            if response.status_code == 200:
                reply = response.json()["reply"]
                print("Server replied:", reply)
                self.show_reply(reply)

        except Exception:
            print("Failed to send message")

    def show_reply(self, reply):
        self.response = reply
        try:
            self.ids.chat_list.add_widget(self._make_chat_label(f"Bot: {reply}"))
            Clock.schedule_once(self._scroll_chat_to_bottom, 0)
            self.ids.message_input.text = ""
        except Exception as e:
            print("Failed to update chat list:", e)

    def capture_image(self):
        self.cam_screen = Builder.load_string('''
BoxLayout:
    orientation: 'vertical'
    Camera:
        id: cam
        resolution: (640, 480)
        play: True
    MDRaisedButton:
        text: "Capture"
        on_release: app.root.get_screen('textinput').send_image(cam)
''')
        self.add_widget(self.cam_screen)

    def send_image(self, cam):
        backend_data_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')
        os.makedirs(backend_data_path, exist_ok=True)  # make sure folder exists

        filename = f"captured_{int(time.time())}.png"
        filepath = os.path.join(backend_data_path, filename)

        cam.export_to_png(filepath)
        
        cam.play = False  # stops the live feed
        cam._camera = None  # release low-level camera reference

        # Remove the camera widget from the screen
        if self.cam_screen:
            self.remove_widget(self.cam_screen)
            self.cam_screen = None

        try:
            response = requests.post(
                "http://127.0.0.1:8000/image",
                json={"image": filepath},
                timeout=30
            )
            
            if response.status_code == 200:
                print("Responded")
                reply = response.json()["reply"]
                print("Server replied:", reply)
                self.show_reply(reply)

        except Exception:
            print("Failed to send message")

    def _scroll_chat_to_bottom(self, *args):
        if "chat_scroll" in self.ids:
            self.ids.chat_scroll.scroll_y = 0

    def _make_chat_label(self, text):
        label = MDLabel(
            text=text,
            halign="left",
            valign="top",
            size_hint_y=None,
        )

        def _update_text_size(*_):
            width = max(self.ids.chat_list.width - self.chat_padding, dp(100))
            label.text_size = (width, None)
            label.texture_update()
            label.height = label.texture_size[1] + dp(10)

        self.ids.chat_list.bind(width=_update_text_size)
        _update_text_size()
        return label

class SettingsPage(Screen):
    error_message = StringProperty("")
    selected_subcounty = ""

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.ids.settings_username.text = app.current_username or ""
        self.ids.settings_password.text = ""
        self.selected_subcounty = app.current_subcounty or ""
        self.ids.settings_subcounty.text = self.selected_subcounty or "Select subcounty"

        if app.current_input_type == "audio":
            self.ids.settings_audio.active = True
            self.ids.settings_text.active = False
        else:
            self.ids.settings_audio.active = False
            self.ids.settings_text.active = True

    def open_subcounty_menu(self):
        subcounties = [
            "Mvita",
            "Kisumu Central",
            "Kitui West",
            "Bumula",
            "Nyakach"
        ]

        menu_items = [
            {
                "text": sc,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=sc: self.set_subcounty(x),
            }
            for sc in subcounties
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.settings_subcounty,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()

    def set_subcounty(self, subcounty):
        self.selected_subcounty = subcounty
        self.ids.settings_subcounty.text = subcounty
        self.menu.dismiss()

    def save_settings(self):
        self.error_message = ""
        app = App.get_running_app()
        current_username = app.current_username
        if not current_username:
            self.error_message = "No user is logged in"
            return

        new_username = self.ids.settings_username.text.strip()
        new_password = self.ids.settings_password.text.strip()
        input_type = "audio" if self.ids.settings_audio.active else "text"
        subcounty = self.selected_subcounty

        payload = {
            "current_username": current_username,
            "new_username": new_username if new_username else None,
            "new_password": new_password if new_password else None,
            "input_type": input_type,
            "subcounty": subcounty if subcounty else None,
        }

        try:
            response = requests.post(
                "http://127.0.0.1:8000/update_profile",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                app.current_username = data.get("username", current_username)
                app.current_input_type = data.get("input_type", input_type)
                app.current_subcounty = data.get("subcounty", subcounty)
                self.manager.current = "audioinput" if app.current_input_type == "audio" else "textinput"
            else:
                self.error_message = response.json().get("detail", "Update failed")
        except Exception:
            self.error_message = "Cannot connect to server"

class ChatApp(MDApp):
    current_username = ""
    current_input_type = ""
    current_subcounty = ""
    auth_token = ""

    def build(self):
        self.store = JsonStore("auth.json")
        sm = ScreenManager()
        sm.add_widget(SignupPage(name="signuppage"))
        sm.add_widget(TextInputScreen(name="textinput"))
        sm.add_widget(AudioInput(name="audioinput"))
        sm.add_widget(SettingsPage(name="settings"))
        return sm

    def on_start(self):
        if self.store.exists("auth"):
            data = self.store.get("auth")
            self.auth_token = data.get("token", "")
            self.current_username = data.get("username", "")
            self.current_input_type = data.get("input_type", "")
            self.current_subcounty = data.get("subcounty", "")
            if self.current_input_type == "audio":
                self.root.current = "audioinput"
            elif self.current_input_type == "text":
                self.root.current = "textinput"
        

if __name__ == "__main__":
    ChatApp().run()
