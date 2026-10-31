from kivy.app import App
from kivy.core.window import Window
from ui.ui_cassa import InterfacciaCassa

class CassaChioscoApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return InterfacciaCassa()

if __name__ == "__main__":
    CassaChioscoApp().run()
