from kivy.config import Config

# Enable debug outlines
Config.set("graphics", "debug", "1")

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

class PageOne(Screen):
    pass

class PageTwo(Screen):
    pass


class PageThree(Screen):
    pass

class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(PageOne(name="page1"))
        sm.add_widget(PageTwo(name="page2"))
        sm.add_widget(PageTwo(name="page3"))
        return sm
        

if __name__ == "__main__":
    ChatApp().run()
