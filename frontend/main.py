from kivy.config import Config

# Enable debug outlines
Config.set("graphics", "debug", "1")

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import BooleanProperty

class SignupPage(Screen):
    is_login_mode = BooleanProperty(False)

    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode

class AudioInput(Screen):
    pass

class TextInputScreen(Screen):
    pass

class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SignupPage(name="signuppage"))
        sm.add_widget(AudioInput(name="audioinput"))
        sm.add_widget(TextInputScreen(name="textinput"))
        return sm
        

if __name__ == "__main__":
    ChatApp().run()