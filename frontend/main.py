# from kivy.config import Config

# # Enable debug outlines
# Config.set("graphics", "debug", "1")

from kivy.app import App
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import BooleanProperty, StringProperty
import requests

from kivy.uix.textinput import TextInput
from kivymd.uix.list import OneLineListItem

class FocusTextInput(TextInput):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.focus = True
        return super().on_touch_down(touch)


class SignupPage(Screen):
    is_login_mode = BooleanProperty(False)
    error_message = StringProperty("")

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
        
        try:
            payload = {
                "username": username,
                "password": password,
                "input_type": input_type
            }
            # FastAPI's default port is 8000
            # response = requests.post("http://127.0.0.1", json=payload, timeout=5)
            response = requests.post(
                "http://127.0.0.1:8000/signup",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
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
            if data["input_type"] == "audio":
                self.manager.current = "audioinput"
            else:
                self.manager.current = "textinput"
        else:
            self.error_message = response.json().get("detail", "Signup failed")


    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode

class AudioInput(Screen):
    pass

class TextInputScreen(Screen):
    def send_message(self):
        message = self.ids.message_input.text.strip()
        try:
            self.ids.chat_list.add_widget(
                OneLineListItem(text=f"You: {message}")
            )
        except Exception as e:
            print("Failed to update chat list:", e)

        if not message:
            return

        try:
            response = requests.post(
                "http://127.0.0.1:8000/message",
                json={"message": message},
                timeout=5
            )

            if response.status_code == 200:
                reply = response.json()["reply"]
                print("Server replied:", reply)
                self.show_reply(reply)

        except Exception:
            print("Failed to send message")

    def show_reply(self, reply):
        print(reply)
        self.response = reply
        try:
            self.ids.chat_list.add_widget(
                OneLineListItem(text=f"Bot: {reply}")
            )
            self.ids.message_input.text = ""
        except Exception as e:
            print("Failed to update chat list:", e)

class ChatApp(MDApp):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SignupPage(name="signuppage"))
        sm.add_widget(AudioInput(name="audioinput"))
        sm.add_widget(TextInputScreen(name="textinput"))
        return sm
        

if __name__ == "__main__":
    ChatApp().run()