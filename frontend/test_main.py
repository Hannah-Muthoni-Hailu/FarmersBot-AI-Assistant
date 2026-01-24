import unittest
from main import ChatApp
from kivy.lang import Builder
from kivy.graphics import Color
from kivy.graphics import RoundedRectangle

class TestChatApp(unittest.TestCase):
    def setUp(self):
        Builder.load_file('chat.kv') 
        self.app = ChatApp()
        self.sm = self.app.build()

    def test_signup_page_exists(self):
        self.assertTrue(self.sm.has_screen("signuppage"))

    def test_top_bar(self):
        signup_page = self.sm.get_screen('signuppage')

        self.assertIn('top_bar', signup_page.ids)

        # Check if the top_bar has the correct height
        self.assertEqual(signup_page.ids.top_bar.height, 50)

    def test_signup_card(self):
        signup_page = self.sm.get_screen('signuppage')

        # 1. Test Existence: Check if the card ID exists
        self.assertIn('signup_card', signup_page.ids)
        card = signup_page.ids.signup_card

        # Test card height and width
        self.assertEqual(card.height, 400)
        self.assertEqual(card.width, 400)

        # Test card colour
        card_colors = [instr for instr in card.canvas.before.children 
                       if isinstance(instr, Color)]
        
        self.assertTrue(len(card_colors) > 0, "No Color instruction found in card canvas")
        
        # Get the RGBA values from the first Color instruction
        actual_rgba = card_colors[0].rgba
        expected_rgba = [96/255, 119/255, 68/255, 1]
        
        # Use almostEqual for floats to avoid precision issues
        for actual, expected in zip(actual_rgba, expected_rgba):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_text_input_exists_in_card(self):
        signup_page = self.sm.get_screen('signuppage')
        card = signup_page.ids.signup_card
        
        # Check if the username exists within the card's scope
        self.assertIn('username_input', card.ids)
        
        # Check the default text value or input properties
        username_input_widget = card.ids.username_input
        self.assertEqual(username_input_widget.multiline, False)

        # Check if the passsword entry exists within the card's scope
        self.assertIn('password_input', card.ids)
        
        # Check the default text value or input properties
        password_input_widget = card.ids.password_input
        self.assertEqual(password_input_widget.multiline, False)

    def test_send_button_properties(self):
        signup_page = self.sm.get_screen('signuppage')
        card = signup_page.ids.signup_card
        
        # 1. Existence check
        self.assertIn('send_button', card.ids)
        btn = card.ids.send_button
        
        # 2. Color check
        btn_colors = [instr for instr in btn.canvas.before.children 
                       if isinstance(instr, Color)]
        
        self.assertTrue(len(btn_colors) > 0, "No Color instruction found in btn canvas")
        
        # Get the RGBA values from the first Color instruction
            
        # 3. Roundness check
        has_round = any(isinstance(ins, RoundedRectangle) for ins in btn.canvas.before.children)
        self.assertTrue(has_round, "Button should have rounded corners")

    def test_toggle_signup_login_mode(self):
        signup_page = self.sm.get_screen("signuppage")
        card = signup_page.ids.signup_card
        toggle_btn = card.ids.toggle_mode_button

        # 1. Initial state: signup mode
        self.assertFalse(signup_page.is_login_mode)
        self.assertIn("Login here", toggle_btn.text)

        # 2. Simulate button press
        toggle_btn.dispatch("on_release")

        # 3. Assert mode changed
        self.assertTrue(signup_page.is_login_mode)
        self.assertIn("Signup here", toggle_btn.text)

        # 4. Toggle back
        toggle_btn.dispatch("on_release")

        self.assertFalse(signup_page.is_login_mode)
        self.assertIn("Login here", toggle_btn.text)

    def test_audioinput_page_exists(self):
        self.assertTrue(self.sm.has_screen("audioinput"))

    def test_audiopage_properties(self):
        audio_page = self.sm.get_screen("audioinput")

        # Test the audio page has a button for recording audio
        self.assertIn('record_audio', audio_page.ids)

        # Test the audio page has a button for capturing images
        self.assertIn('capture', audio_page.ids)

    def test_audioinput_page_exists(self):
        self.assertTrue(self.sm.has_screen("textinput"))

    def test_textpage_properties(self):
        text_page = self.sm.get_screen("textinput")

        # Test the text page has a text input panel
        self.assertIn('input_panel', text_page.ids)

        # Test the input panel has a send button and image capturing button
        self.assertIn('message_input', text_page.ids)
        self.assertIn('send', text_page.ids)
        self.assertIn('capture', text_page.ids)
    

if __name__ == "__main__":
    unittest.main()