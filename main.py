from datetime import datetime
import os
import sqlite3

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window

# --- CONFIGURAZIONE DATABASE ---
DB_NAME = "negozio.db"

class CassaApp(App):
    def build(self):
        self.operatore_corrente = "Rosario Vincenzo"
        self.cassa_corrente = "Cassa Mobile Android"
        self.scontrino_righe = []
        self.totale_generale = 0.0
        
        self.title = "Cassa - Chiosco & Alimentari dell'Est"
        
        # Layout principale
        self.root_layout = BoxLayout(orientation='vertical')
        
        # Barra superiore di navigazione
        nav_layout = BoxLayout(size_hint_y=None, height=50)
        btn_vendita = Button(text="Cassa", background_color=(0.37, 0.24, 0.77, 1))
        btn_vendita.bind(on_press=lambda x: self.mostra_schermata("vendita"))
        btn_magazzino = Button(text="Magazzino & Listino")
        btn_magazzino.bind(on_press=lambda x: self.mostra_schermata("magazzino"))
        btn_storico = Button(text="Storico Vendite")
        btn_storico.bind(on_press=lambda x: self.mostra_schermata("storico"))
        
        nav_layout.add_widget(btn_vendita)
        nav_layout.add_widget(btn_magazzino)
        nav_layout.add_widget(btn_storico)
        self.root_layout.add_widget(nav_layout)
        
        # Contenitore dinamico centrale
        self.content_container = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.content_container)
        
        self.mostra_schermata("vendita")
        return self.root_layout

    def mostra_schermata(self, nome):
        self.content_container.clear_widgets()
        if nome == "vendita":
            self.content_container.add_widget(self.crea_schermata_vendita())
        elif nome == "magazzino":
            self.content_container.add_widget(self.crea_schermata_magazzino())
        elif nome == "storico":
            self.content_container.add_widget(self.crea_schermata_storico())

    def crea_schermata_vendita(self):
        layout = BoxLayout(orientation='horizontal', padding=15, spacing=15)
        
        # Sezione Sinistra: Scontrino e Totali (Occupa il 40% dello schermo)
        left_box = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.40)
        
        # Scontrino inserito in un ScrollView per evitare il taglio del testo se lungo
        scroll_scontrino = ScrollView(size_hint_y=0.45)
        self.scontrino_label = Label(
            text="Scontrino Vuoto", 
            font_size='14sp', 
            halign='left', 
            valign='top',
            size_hint_y=None
        )
        self.scontrino_label.bind(width=lambda *x: setattr(self.scontrino_label, 'text_size', (self.scontrino_label.width, None)))
        self.scontrino_label.bind(texture_size=lambda *x: setattr(self.scontrino_label, 'height', self.scontrino_label.texture_size[1]))
        scroll_scontrino.add_widget(self.scontrino_label)
        left_box.add_widget(scroll_scontrino)
        
        # Totale e Resto
        tot_box = BoxLayout(orientation='vertical', size_hint_y=0.20, padding=5, spacing=5)
        self.lbl_totale = Label(text="TOTALE: CHF 0.00", font_size='22sp', bold=True, halign='right')
        self.lbl_resto = Label(text="RESTO: CHF 0.00", font_size='16sp', color=(1, 0.3, 0.3, 1), halign='right')
        tot_box.add_widget(self.lbl_totale)
        tot_box.add_widget(self.lbl_resto)
        left_box.add_widget(tot_box)
        
        # Moneta ricevuta
        moneta_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=5)
        moneta_box.add_widget(Label(text="Moneta CHF:", size_hint_x=0.4, font_size='14sp'))
        self.input_moneta = TextInput(text="", multiline=False, font_size='16sp', input_filter='float')
        self.input_moneta.bind(text=self.aggiorna_resto)
        moneta_box.add_widget(self.input_moneta)
        left_box.add_widget(moneta_box)
        
        # Pulsanti Pagamento ben visibili in basso a sinistra
        pay_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=55, spacing=8)
        btn_carta = Button(text="CARTA", background_color=(0.1, 0.4, 0.7, 1), font_size='15sp', bold=True)
        btn_carta.bind(on_press=lambda x: self.completa_vendita("CARTA"))
        btn_twint = Button(text="TWINT", background_color=(0.1, 0.6, 0.2, 1), font_size='15sp', bold=True)
        btn_twint.bind(on_press=lambda x: self.completa_vendita("TWINT"))
        btn_cash = Button(text="CASH", background_color=(0.9, 0.6, 0.1, 1), font_size='15sp', bold=True)
        btn_cash.bind(on_press=lambda x: self.completa_vendita("CASH"))
        pay_box.add_widget(btn_carta)
        pay_box.add_widget(btn_twint)
        pay_box.add_widget(btn_cash)
        left_box.add_widget(pay_box)
        
        layout.add_widget(left_box)
        
        # Sezione Destra: Tastierino e Ricerca Barcode (Occupa il 60% dello schermo)
        right_box = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.60)
        
        self.input_codice = TextInput(
            text="", 
            hint_text="Digita Barcode o Nome Prodotto", 
            multiline=False, 
            size_hint_y=None, 
            height=50, 
            font_size='18sp'
        )
        right_box.add_widget(self.input_codice)
        
        # Tastierino Numerico proporzionato
        grid_tasti = GridLayout(cols=4, spacing=6)
        tasti = ['1', '2', '3', 'QTA', '4', '5', '6', 'PREZZO', '7', '8', '9', 'C', '0', ',', '⌫', 'CERCA / AGGIUNGI']
        for t in tasti:
            btn = Button(text=t, font_size='16sp', bold=True)
            btn.bind(on_press=lambda instance, val=t: self.premi_tasto(val))
            grid_tasti.add_widget(btn)
        right_box.add_widget(grid_tasti)
        
        layout.add_widget(right_box)
        return layout

    def premi_tasto(self, valore):
        if valore == '⌫':
            self.input_codice.text = self.input_codice.text[:-1]
        elif valore == 'C':
            self.input_codice.text = ""
        elif valore == 'CERCA / AGGIUNGI':
            self.cerca_e_aggiungi_prodotto()
        else:
            self.input_codice.text += valore

    def cerca_e_aggiungi_prodotto(self):
        query = self.input_codice.text.strip()
        if not query:
            return
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome, prezzo FROM prodotti WHERE barcode = ? OR nome LIKE ?", (query, f"%{query}%"))
        risultato = cursor.fetchone()
        conn.close()
        
        if risultato:
            nome_prod, prezzo = risultato
            riga = f"{nome_prod[:18]:<18} CHF {prezzo:.2f}"
            self.scontrino_righe.append(riga)
            self.totale_generale += float(prezzo)
        else:
            try:
                importo = float(query.replace(',', '.'))
                riga = f"Articolo libero{'':<11} CHF {importo:.2f}"
                self.scontrino_righe.append(riga)
                self.totale_generale += importo
            except:
                pass
                
        self.aggiorna_vista_scontrino()
        self.input_codice.text = ""

    def aggiorna_vista_scontrino(self):
        testo = f"Cassa: {self.cassa_corrente}\nOp: {self.operatore_corrente}\n" + "-"*32 + "\n"
        testo += "\n".join(self.scontrino_righe)
        self.scontrino_label.text = testo
        self.lbl_totale.text = f"TOTALE: CHF {self.totale_generale:.2f}"
        self.aggiorna_resto()

    def aggiorna_resto(self, *args):
        try:
            moneta = float(self.input_moneta.text.replace(',', '.'))
            resto = max(0.0, moneta - self.totale_generale)
            self.lbl_resto.text = f"RESTO: CHF {resto:.2f}"
        except:
            self.lbl_resto.text = "RESTO: CHF 0.00"

    def completa_vendita(self, pagamento):
        if not self.scontrino_righe:
            return
        data_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dettagli = " | ".join(self.scontrino_righe)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vendite (data_ora, totale, dettagli, pagamento, cassa, cassiere) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data_ora, self.totale_generale, dettagli, pagamento, self.cassa_corrente, self.operatore_corrente))
        conn.commit()
        conn.close()
        
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.input_moneta.text = ""
        self.aggiorna_vista_scontrino()

    def crea_schermata_magazzino(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Listino Prodotti Caricati nel Database", font_size='18sp', size_hint_y=None, height=40))
        
        scroll = ScrollView()
        box_prodotti = BoxLayout(orientation='vertical', size_hint_y=None)
        box_prodotti.bind(minimum_height=box_prodotti.setter('height'))
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, nome, prezzo, giacenza FROM prodotti ORDER BY nome ASC")
        rows = cursor.fetchall()
        conn.close()
        
        for b, n, p, g in rows:
            lbl = Label(text=f"[{b}] {n} - CHF {p:.2f} (Giac: {g})", size_hint_y=None, height=35, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            box_prodotti.add_widget(lbl)
            
        scroll.add_widget(box_prodotti)
        layout.add_widget(scroll)
        return layout

    def crea_schermata_storico(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Ultime Vendite Registrate", font_size='18sp', size_hint_y=None, height=40))
        
        scroll = ScrollView()
        box_vendite = BoxLayout(orientation='vertical', size_hint_y=None)
        box_vendite.bind(minimum_height=box_vendite.setter('height'))
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_ora, totale, pagamento, cassiere FROM vendite ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        
        for v_id, data, tot, pag, op in rows:
            lbl = Label(text=f"#{v_id} | {data} | CHF {tot:.2f} ({pag}) [{op}]", size_hint_y=None, height=35, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            box_vendite.add_widget(lbl)
            
        scroll.add_widget(box_vendite)
        layout.add_widget(scroll)
        return layout

if __name__ == '__main__':
    CassaApp().run()
