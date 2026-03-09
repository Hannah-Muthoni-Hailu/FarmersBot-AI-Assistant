import os

from kivy.app import App
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import BooleanProperty, StringProperty
from kivy.core.audio import SoundLoader
import requests

from kivy.uix.textinput import TextInput
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.toast import toast
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore

import threading
from camera4kivy import Preview
from plyer import audio
import base64

os.environ['KIVY_AUDIO'] = 'ffpyplayer'

class CameraPopup(ModalView):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.ids.preview.connect_camera(filepath_callback=self.on_photo_saved)

    def do_capture(self):
        self.ids.preview.capture_photo(location='private', name="my_capture")

    def on_photo_saved(self, path):
        self.callback(path)
        self.dismiss()

    def on_dismiss(self):
        self.ids.preview.disconnect_camera()
        return False


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
            "Ainabkoi",
            "Ainamoi",
            "Aldai",
            "Alego Usonga",
            "Athi River",
            "Awendo",
            "Balambala",
            "BANISSA",
            "Baringo Central",
            "Baringo North",
            "Belgut",
            "Bobasi",
            "Bomachoge Borabu",
            "Bomachoge Chache",
            "Bomet Central",
            "Bomet East",
            "Bonchari",
            "Bondo",
            "Borabu",
            "Bumula",
            "Bunyala",
            "Bura",
            "Bureti",
            "Butere",
            "Butula",
            "Buuri",
            "Changamwe",
            "Chepalungu",
            "Cheptais",
            "Cherengany",
            "Chesumei",
            "Chuka",
            "Dadaab",
            "Dagoretti North",
            "Dagoretti South",
            "East Pokot",
            "Eldas",
            "Embakasi Central",
            "Embakasi East",
            "Embakasi North",
            "Embakasi South",
            "Embakasi West",
            "Emgwen",
            "Emuhaya",
            "Endebess",
            "Fafi",
            "Galole",
            "Ganze",
            "Garbatulla",
            "Garissa",
            "Garsen",
            "Gatanga",
            "Gatundu North",
            "Gem",
            "Gilgil",
            "Githunguri",
            "Hamisi",
            "Homa Bay Town",
            "Hulugho",
            "Igambang'ombe",
            "Igembe Central",
            "Igembe North",
            "Igembe South",
            "Ijara",
            "Ikolomani",
            "Imenti Central",
            "Imenti North",
            "Imenti South",
            "Isiolo",
            "Jomvu",
            "Juja",
            "Kabete"
            "Kabondo Kasipul",
            "Kabuchai",
            "Kaiti",
            "Kajiado Central",
            "Kajiado East",
            "Kajiado North",
            "Kajiado West",
            "Kalama",
            "Kaloleni",
            "Kamukunji",
            "Kandara",
            "Kandunyi",
            "Kangemi",
            "Kangundo",
            "Kapsaret",
            "Karachuonyo",
            "Kasarani",
            "Kasipul",
            "Kathiani",
            "Keiyo North",
            "Keiyo South",
            "Kesses",
            "Khwisero",
            "Kiambaa",
            "Kiambu Town",
            "Kibish",
            "Kibra",
            "Kibwezi East",
            "Kibwezi West",
            "Kieni East",
            "Kieni West",
            "Kigumo",
            "Kiharu",
            "Kikuyu",
            "Kilifi North"
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
        toast("Signup process started")
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

        # Check length of password
        if len(password) > 256:
            self.error_message = "Password too long"

        # Ensure that a subcounty has been selected
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
            response = requests.post(
                "https://farmersbot-ai-assistant.onrender.com/signup",
                json=payload,
                timeout=240
            )

            if response.status_code == 200:
                data = response.json()
                app = App.get_running_app()
                app.current_username = username
                app.current_input_type = input_type
                app.current_subcounty = self.selected_subcounty
                # Save authentication token
                if app.auth_token:
                    app.store.put(
                        "auth",
                        token=app.auth_token,
                        username=app.current_username,
                        input_type=app.current_input_type,
                        subcounty=app.current_subcounty,
                    )
                # Conditional Navigation on success
                if input_type == "audio":
                    self.manager.current = "audioinput"
                else:
                    self.manager.current = "textinput"
            else:
                self.error_message = response.json().get("detail", "Signup failed")
        except Exception as e:
            self.error_message = "Cannot connect to server"

    def process_login(self):
        toast("Login process started")
        self.error_message = ""
        card = self.ids.signup_card
        username = card.ids.username_input.text
        password = card.ids.password_input.text

        # Ensure fields aren't empty
        if not username or not password:
            self.error_message = "Username and password are required"
            return
        
        if len(password) > 256:
            self.error_message = "Password too long"

        payload = {
            "username": username,
            "password": password,
        }
        response = requests.post(
            "https://farmersbot-ai-assistant.onrender.com/login",
            json=payload,
            timeout=240
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
            self.error_message = response.text

    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode

class AudioInput(Screen):
    is_recording = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_dir = App.get_running_app().user_data_dir
        self.audio_path = os.path.join(self.data_dir, "voice_note.3gp")

    def start_recording(self):
        try:
            # Prepare the recorder with the file path
            self.is_recording = True
            audio.file_path = self.audio_path
            audio.start()
            toast("Recording started...")
            print("Recording started...")
        except Exception as e:
            toast("Please press the button again.")
            print(f"Error starting record: {e}")

    def stop_recording(self):
        try:
            self.is_recording = False
            audio.stop()
            toast("Recording stopped")
            print(f"Recording saved at: {self.audio_path}")
            self.upload_audio(self.audio_path)
        except Exception as e:
            toast("Please try recording again.")
            print(f"Error stopping record: {e}")

    def upload_audio(self, audio_path):
        try:
            with open(audio_path, 'rb') as f:
                files = {'audio_file': (os.path.basename(audio_path), f, 'audio/3gp')} # Send decoded file for easier transfer
                
                response = requests.post(
                    "https://farmersbot-ai-assistant.onrender.com/audio", 
                    files=files, 
                    timeout=180)
                
                if response.status_code == 200:
                    data = response.json()
                    audio_b64 = data.get("audio")

                    if audio_b64:
                        self.play_response_audio(audio_b64)
                else:
                    toast("Server error. Try again.")
                    print(f"Upload failed: {response.status_code} - {response.text}")
        except Exception as e:
            toast("There was an issue with the server.")
            print(f"Network error: {e}")
        finally:
            Clock.schedule_once(lambda *_: self._set_audio_loading(False), 0)

    def _set_audio_loading(self, is_loading):
        spinner = self.ids.get("audio_spinner")
        if not spinner:
            return
        spinner.active = is_loading
        spinner.opacity = 1 if is_loading else 0

    def play_response_audio(self, audio_b64):
        temp_path = os.path.join(self.data_dir, "response.wav")
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(audio_b64)) # Decode the server audio

        Clock.schedule_once(lambda dt: self._load_and_play(temp_path), 0.1)

    def _load_and_play(self, path):
        abs_path = os.path.abspath(path)
        sound = SoundLoader.load(abs_path)
        if sound:
            # Cleanup function to run when audio ends
            def cleanup(instance):
                try:
                    instance.unload() # Release the file handle
                    os.remove(abs_path)
                    print("Temporary audio cleaned up.")
                except Exception as e:
                    print(f"Cleanup error: {e}")

            sound.bind(on_stop=cleanup)
            sound.play()
        else:
            print(f"CRITICAL: Could not load sound from {abs_path}")
            if os.path.exists(abs_path):
                os.remove(abs_path)

    # Opens the image capture popup
    def capture_image(self):
        popup = CameraPopup(callback=self.handle_camera_data)
        popup.open()

    def handle_camera_data(self, path):
        if not path or not os.path.exists(path):
            toast("Invalid image. Try again!")
            print("Invalid image path")
            return
        
        toast("You response is being generated!")
        threading.Thread(target=self.upload_to_server, args=(path,), daemon=True).start()

    def upload_to_server(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                files = {'imageFile': (os.path.basename(image_path), f, 'image/jpeg')}
                
                print(f"Uploading {image_path}")

                response = requests.post(
                    "https://farmersbot-ai-assistant.onrender.com/image_audio",
                    files=files,
                    timeout=180
                )
                
                if response.status_code == 200:
                    data = response.json()
                    reply_text = data.get("reply")
                    audio_b64 = data.get("audio")

                    if audio_b64:
                        print(reply_text)
                        self.play_response_audio(audio_b64)
                else:
                    toast("An error occured")
                    print(f"Upload failed (Status {response.status_code}): {response.text}")
                    
        except Exception as e:
            toast("An error occured")
            print("Failed to send message: ", str(e))
        finally:
            Clock.schedule_once(lambda *_: self._set_audio_loading(False), 0)

class TextInputScreen(Screen):
    # Sends text input to server
    def send_message(self):
        message = self.ids.message_input.text.strip()
        try:
            self.ids.chat_list.add_widget(self._make_chat_bubble(f"You: {message}", is_user=True))
            Clock.schedule_once(self._scroll_chat_to_bottom, 0)
        except Exception as e:
            print("Failed to update chat list:", e)

        # Check that the input tab is not empty
        if not message:
            toast("Please input a message")
            return

        try:
            toast("Generating a response")
            response = requests.post(
                "https://farmersbot-ai-assistant.onrender.com/message",
                json={"message": message},
                timeout=180
            )

            if response.status_code == 200:
                reply = response.json()["reply"]
                print("Server replied:", reply)
                self.show_reply(reply)
            else:
                error_message = f"Server error: {response.text}"
                print(error_message)
                self.show_reply(error_message)

        except Exception:
            toast("An error was encountered")
            print("Failed to send message: ", str(e))

    # Print reply to screen
    def show_reply(self, reply):
        self.response = reply
        try:
            self.ids.chat_list.add_widget(self._make_chat_bubble(f"Bot: {reply}", is_user=False))
            Clock.schedule_once(self._scroll_chat_to_bottom, 0)
            self.ids.message_input.text = ""
        except Exception as e:
            print("Failed to update chat list:", e)

    def _scroll_chat_to_bottom(self, *args): # Allows the screen to automatically scroll when text buttons flow below the screen
        if "chat_scroll" in self.ids:
            self.ids.chat_scroll.scroll_y = 0

    # Generates the text bubble
    def _make_chat_bubble(self, text, is_user=False):
        row = BoxLayout(
            size_hint_y=None,
            size_hint_x=1,
        )

        bubble = MDCard(
            orientation="vertical",
            size_hint_y=None,
            size_hint_x=None,
            padding=(dp(12), dp(8)),
            radius=[dp(12), dp(12), dp(12), dp(12)],
            md_bg_color=(0.62, 0.62, 0.61, 1) if is_user else (0.46, 0.53, 0.28, 1),
        )

        label = MDLabel(
            text=text,
            halign="left",
            valign="top",
            size_hint_y=None,
        )
        bubble.add_widget(label)

        def _update_text_size(*_):
            max_width = max(self.ids.chat_list.width * 0.8, dp(150))
            label.text_size = (max_width - dp(24), None)
            label.texture_update()
            label.height = label.texture_size[1]
            bubble.width = max_width
            bubble.height = label.height + dp(16)

        self.ids.chat_list.bind(width=_update_text_size)
        _update_text_size()

        if is_user:
            row.add_widget(Widget())
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Widget())

        row.height = bubble.height
        return row

    # Opens the image capture popup
    def capture_image(self):
        popup = CameraPopup(callback=self.handle_camera_data)
        popup.open()

    def handle_camera_data(self, path):
        if not path or not os.path.exists(path):
            toast("Invalid image. Try again!")
            print("Invalid image path")
            return
        
        toast("You response is being generated!")
        threading.Thread(target=self.upload_to_server, args=(path,), daemon=True).start()

    # Send image data to the server
    def upload_to_server(self, image_path):
        # Print a user text box to ensure users know that their image has been sent
        try:
            self.ids.chat_list.add_widget(self._make_chat_bubble(f"You: Image", is_user=True))
            Clock.schedule_once(self._scroll_chat_to_bottom, 0)
        except Exception as e:
            print("Failed to update chat list:", e)

        try:
            with open(image_path, 'rb') as f:
                files = {'imageFile': (os.path.basename(image_path), f, 'image/jpeg')}

                response = requests.post(
                    "https://farmersbot-ai-assistant.onrender.com/image",
                    files=files,
                    timeout=180
                )
                
                if response.status_code == 200:
                    reply = response.json()["reply"]
                    print("Server replied:", reply)
                    Clock.schedule_once(lambda dt: self.show_reply(reply)) # Schedule server reply because there are some concurrent events
                else:
                    print(f"Upload failed (Status {response.status_code}): {response.text}")
                    Clock.schedule_once(lambda dt: self.show_reply(f"Server error: {response.text}"))
                    
        except Exception as e:
            toast("An error was encountered")
            print("Failed to send message: ", str(e))

class SettingsPage(Screen):
    error_message = StringProperty("")
    selected_subcounty = ""

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        card = self.ids.settings_card
        card.ids.username_input.text = app.current_username or ""
        card.ids.password_input.text = ""
        self.selected_subcounty = app.current_subcounty or ""
        card.ids.subcounty_field.text = self.selected_subcounty or "Select subcounty"

        if app.current_input_type == "audio":
            card.ids.audio_check.active = True
            card.ids.text_check.active = False
        else:
            card.ids.audio_check.active = False
            card.ids.text_check.active = True

    # Allows users to exist settings page
    def go_back(self):
        app = App.get_running_app()
        self.manager.current = "textinput" if app.current_input_type == "text" else "audioinput"

    def open_subcounty_menu(self):
        subcounties = [
            "Ainabkoi",
            "Ainamoi",
            "Aldai",
            "Alego Usonga",
            "Athi River",
            "Awendo",
            "Balambala",
            "BANISSA",
            "Baringo Central",
            "Baringo North",
            "Belgut",
            "Bobasi",
            "Bomachoge Borabu",
            "Bomachoge Chache",
            "Bomet Central",
            "Bomet East",
            "Bonchari",
            "Bondo",
            "Borabu",
            "Bumula",
            "Bunyala",
            "Bura",
            "Bureti",
            "Butere",
            "Butula",
            "Buuri",
            "Changamwe",
            "Chepalungu",
            "Cheptais",
            "Cherengany",
            "Chesumei",
            "Chuka",
            "Dadaab",
            "Dagoretti North",
            "Dagoretti South",
            "East Pokot",
            "Eldas",
            "Embakasi Central",
            "Embakasi East",
            "Embakasi North",
            "Embakasi South",
            "Embakasi West",
            "Emgwen",
            "Emuhaya",
            "Endebess",
            "Fafi",
            "Galole",
            "Ganze",
            "Garbatulla",
            "Garissa",
            "Garsen",
            "Gatanga",
            "Gatundu North",
            "Gem",
            "Gilgil",
            "Githunguri",
            "Hamisi",
            "Homa Bay Town",
            "Hulugho",
            "Igambang'ombe",
            "Igembe Central",
            "Igembe North",
            "Igembe South",
            "Ijara",
            "Ikolomani",
            "Imenti Central",
            "Imenti North",
            "Imenti South",
            "Isiolo",
            "Jomvu",
            "Juja",
            "Kabete"
            "Kabondo Kasipul",
            "Kabuchai",
            "Kaiti",
            "Kajiado Central",
            "Kajiado East",
            "Kajiado North",
            "Kajiado West",
            "Kalama",
            "Kaloleni",
            "Kamukunji",
            "Kandara",
            "Kandunyi",
            "Kangemi",
            "Kangundo",
            "Kapsaret",
            "Karachuonyo",
            "Kasarani",
            "Kasipul",
            "Kathiani",
            "Keiyo North",
            "Keiyo South",
            "Kesses",
            "Khwisero",
            "Kiambaa",
            "Kiambu Town",
            "Kibish",
            "Kibra",
            "Kibwezi East",
            "Kibwezi West",
            "Kieni East",
            "Kieni West",
            "Kigumo",
            "Kiharu",
            "Kikuyu",
            "Kilifi North"
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
        self.ids.settings_card.ids.subcounty_field.text = subcounty
        self.menu.dismiss()

    def save_settings(self):
        self.error_message = ""
        app = App.get_running_app()
        current_username = app.current_username
        if not current_username:
            self.error_message = "No user is logged in"
            return

        card = self.ids.settings_card
        new_username = card.ids.username_input.text.strip()
        new_password = card.ids.password_input.text.strip()
        input_type = "audio" if card.ids.audio_check.active else "text"
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
                "https://farmersbot-ai-assistant.onrender.com/update_profile",
                json=payload,
                timeout=180
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
