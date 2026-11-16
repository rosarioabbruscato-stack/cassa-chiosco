# -*- coding: utf-8 -*-
# pip install --upgrade pip command
# pip install kivy
# pip install cryptography
#pip install openpyxl 
from kivy.app import App
import storage
import z_report
import cassa_report
from kivy.uix.screenmanager import ScreenManager
from ui.ui_cassa import InterfacciaCassa
from ui.ui_magazzino import InterfacciaMagazzino
from ui.ui_chiusura import InterfacciaChiusura

class CassaApp(App):
    def build(self):
        storage.init()
        storage.init_settings()
        storage.init_articles()
        z_report.setup()
        cassa_report.setup()
        storage.migrate_legacy()
        self.sm = ScreenManager()
        
        self.cassa_screen = InterfacciaCassa(name="cassa")
        self.mag_screen = InterfacciaMagazzino(name="magazzino")
        self.chiusura_screen = InterfacciaChiusura(name="chiusura")
        
        self.sm.add_widget(self.cassa_screen)
        self.sm.add_widget(self.mag_screen)
        self.sm.add_widget(self.chiusura_screen)
        
        return self.sm

if __name__ == "__main__":
    CassaApp().run()
