import os
os.environ['KIVY_WINDOW'] = 'x11'
os.environ['KIVY_GL_BACKEND'] = 'gl'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.config import Config
import os
import sqlite3
from datetime import datetime

Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1200')
Config.set('graphics', 'resizable', True)
Window.clearcolor = (0, 0, 0, 1)
Window.softinput_mode = "pan"

from ui.ui_cassa import InterfacciaCassa
from kivy.uix.boxlayout import BoxLayout

class CassaApp(App):
    def build(self):
        from kivy.utils import platform
        if platform == 'android':
            self.db_name = os.path.join(self.user_data_dir, "negozio.db")
        else:
            os.makedirs("database", exist_ok=True)
            self.db_name = "database/negozio.db"
        self.operatore_corrente = "Rosario Vincenzo"
        self.cassa_corrente = "Cassa Mobile Android"
        self.valuta_corrente = "CHF"
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.reparto_selezionato = "GENERALE"
        self.moltiplicatore_qta = 1
        self.vendita_completata_flag = False
        
        self.root_layout = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(InterfacciaCassa.crea_menu_superiore(self))
        self.content_container = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.content_container)
        
        self.inizializza_db_se_manca()
        self.mostra_schermata("vendita")
        return self.root_layout
    def inizializza_db_se_manca(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS prodotti (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, nome TEXT, prezzo REAL, giacenza REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS vendite (id INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, totale REAL, dettagli TEXT, pagamento TEXT, cassa TEXT, cassiere TEXT)")
        conn.commit()
        conn.close()

    def mostra_schermata(self, nome):
        self.content_container.clear_widgets()
        if nome == "vendita":
            self.content_container.add_widget(InterfacciaCassa.crea_schermata_vendita(self))
        elif nome == "magazzino":
            self.content_container.add_widget(InterfacciaCassa.crea_schermata_magazzino(self))
        elif nome == "storico":
            self.content_container.add_widget(InterfacciaCassa.crea_schermata_storico(self))

    def seleziona_reparto(self, reparto):
        if self.vendita_completata_flag: return
        self.reparto_selezionato = reparto
        if hasattr(self, 'lbl_stato_corrente'):
            self.lbl_stato_corrente.text = f"Reparto Selezionato: {reparto}"

    def imposta_modalita(self, modo):
        if self.vendita_completata_flag: return
        valore = self.input_codice.text.strip() if hasattr(self, 'input_codice') and self.input_codice else ""
        if modo == "QTA":
            try:
                self.moltiplicatore_qta = int(valore) if valore else 1
                if hasattr(self, 'lbl_stato_corrente'):
                    self.lbl_stato_corrente.text = f"Quantità impostata a: {self.moltiplicatore_qta}"
            except:
                self.moltiplicatore_qta = 1
            if hasattr(self, 'input_codice') and self.input_codice:
                self.input_codice.text = ""

    def gestisci_azione_scontrino(self, instance):
        if hasattr(self, 'scontrino_righe') and self.scontrino_righe:
            self.scontrino_righe.pop()
            if hasattr(self, 'aggiorna_vista_scontrino'):
                self.aggiorna_vista_scontrino()
        if hasattr(self, 'lbl_stato_corrente'):
            self.lbl_stato_corrente.text = "Azione scontrino eseguita"

    def aggiorna_resto(self, instance, value):
        try:
            versato = float(value.strip()) if value.strip() else 0.0
            totale = getattr(self, 'totale_generale', 0.0)
            resto = versato - totale
            if hasattr(self, 'lbl_resto'):
                self.lbl_resto.text = f"RESTO: {self.valuta_corrente} {resto:.2f}"
        except ValueError:
            if hasattr(self, 'lbl_resto'):
                self.lbl_resto.text = "RESTO: --"

if __name__ == "__main__":
    try:
        CassaApp().run()
    except Exception as e:
        import traceback
        with open("cassa_crash.txt", "w") as f:
            traceback.print_exc(file=f)
        raise
