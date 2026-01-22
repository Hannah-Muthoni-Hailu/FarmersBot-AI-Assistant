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

class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SignupPage(name="signuppage"))
        return sm
        

if __name__ == "__main__":
    ChatApp().run()


'''
# sm.add_widget(PageTwo(name="page2"))
# sm.add_widget(PageTwo(name="page3"))

        Label:
            text: "Hello, Kivy!"
            font_size: 32

        Button:
            text: "Next"
            on_press: root.manager.current = "page2"
<PageTwo>:
    BoxLayout:
        orientation: "vertical"
        padding: 40
        spacing: 20

        Label:
            text: "Hello, Kivy!"
            font_size: 32

        Button:
            text: "Next"
            on_press: root.manager.current = "page3"

<PageThree>:
    BoxLayout:
        orientation: "vertical"
        padding: 40
        spacing: 20

        Label:
            text: "Hello, Kivy!"
            font_size: 32

        Button:
            text: "Next"
'''