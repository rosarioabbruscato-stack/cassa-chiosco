from kivy.app import App
from kivy.core.window import Window
from ui.ui_cassa import InterfacciaCassa

class CassaChioscoApp(App):
    def build(self):
        # Inizializzato in modo sicuro all avvio del contesto grafico
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return InterfacciaCassa()

if __name__ == "__main__":
    CassaChioscoApp().run()
