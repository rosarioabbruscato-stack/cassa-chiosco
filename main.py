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

DB_NAME = "negozio.db"

class CassaApp(App):
    def build(self):
        self.operatore_corrente = "Rosario Vincenzo"
        self.cassa_corrente = "Cassa Mobile Android"
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.reparto_selezionato = "GENERALE"
        self.moltiplicatore_qta = 1
        self.prezzo_forzato = None
        self.valuta_corrente = "CHF"
        self.title = "Cassa - Chiosco & Alimentari dell'Est"
        
        self.root_layout = BoxLayout(orientation='vertical')
        
        nav_layout = BoxLayout(size_hint_y=None, height=55, padding=5, spacing=5)
        btn_vendita = Button(text="Cassa / Vendita", background_color=(0.28, 0.08, 0.58, 1), bold=True)
        btn_vendita.bind(on_press=lambda x: self.mostra_schermata("vendita"))
        btn_magazzino = Button(text="Magazzino", background_color=(0.8, 0.8, 0.8, 1), color=(0,0,0,1), bold=True)
        btn_magazzino.bind(on_press=lambda x: self.mostra_schermata("magazzino"))
        btn_storico = Button(text="Chiusura & Storico", background_color=(0.8, 0.8, 0.8, 1), color=(0,0,0,1), bold=True)
        btn_storico.bind(on_press=lambda x: self.mostra_schermata("storico"))
        
        nav_layout.add_widget(btn_vendita)
        nav_layout.add_widget(btn_magazzino)
        nav_layout.add_widget(btn_storico)
        self.root_layout.add_widget(nav_layout)
        
        self.content_container = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.content_container)
        
        self.inizializza_db_se_manca()
        self.mostra_schermata("vendita")
        return self.root_layout

    def inizializza_db_se_manca(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS prodotti (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, nome TEXT, prezzo REAL, giacenza REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS vendite (id INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, totale REAL, dettagli TEXT, pagamento TEXT, cassa TEXT, cassiere TEXT)")
        conn.commit()
        conn.close()

    def mostra_schermata(self, nome):
        self.content_container.clear_widgets()
        if nome == "vendita":
            self.content_container.add_widget(self.crea_schermata_vendita())
        elif nome == "magazzino":
            self.content_container.add_widget(self.crea_schermata_magazzino())
        elif nome == "storico":
            self.content_container.add_widget(self.crea_schermata_storico())

    def crea_schermata_vendita(self):
        layout = BoxLayout(orientation='horizontal', padding=10, spacing=10)
        
        left_box = BoxLayout(orientation='vertical', spacing=6, size_hint_x=0.42)
        top_scontrino_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=35, spacing=5)
        top_scontrino_bar.add_widget(Label(text="Scontrino Corrente", font_size='12sp', bold=True, halign='left'))
        
        self.btn_valuta = Button(text=f"Valuta: {self.valuta_corrente}", size_hint_x_none=None, width=100, background_color=(0.2, 0.4, 0.6, 1), bold=True, font_size='12sp')
        self.btn_valuta.bind(on_press=self.cambia_valuta)
        top_scontrino_bar.add_widget(self.btn_valuta)
        left_box.add_widget(top_scontrino_bar)
        
        scroll_scontrino = ScrollView(size_hint_y=0.42)
        self.scontrino_label = Label(text="Scontrino Vuoto", font_size='13sp', halign='left', valign='top', size_hint_y=None)
        self.scontrino_label.bind(width=lambda *x: setattr(self.scontrino_label, 'text_size', (self.scontrino_label.width, None)))
        self.scontrino_label.bind(texture_size=lambda *x: setattr(self.scontrino_label, 'height', self.scontrino_label.texture_size[1]))
        scroll_scontrino.add_widget(self.scontrino_label)
        left_box.add_widget(scroll_scontrino)
        
        btn_elimina_riga = Button(text="Elimina Riga Selezionata", size_hint_y=None, height=38, background_color=(0.85, 0.3, 0.3, 1), bold=True, font_size='13sp')
        btn_elimina_riga.bind(on_press=self.elimina_ultima_riga)
        left_box.add_widget(btn_elimina_riga)
        
        tot_box = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=2, spacing=2)
        self.lbl_totale = Label(text=f"TOTALE: {self.valuta_corrente} 0.00", font_size='20sp', bold=True, halign='right')
        self.lbl_resto = Label(text="Resto: -", font_size='15sp', color=(0.1, 0.7, 0.3, 1), halign='right', bold=True)
        tot_box.add_widget(self.lbl_totale)
        tot_box.add_widget(self.lbl_resto)
        left_box.add_widget(tot_box)
        
        moneta_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        moneta_box.add_widget(Label(text="Importo Ricevuto:", size_hint_x=0.5, font_size='12sp'))
        self.input_moneta = TextInput(text="", multiline=False, font_size='14sp', input_filter='float', hint_text="Contanti")
        self.input_moneta.bind(text=self.aggiorna_resto)
        moneta_box.add_widget(self.input_moneta)
        left_box.add_widget(moneta_box)
        
        left_box.add_widget(Label(text="Seleziona Pagamento:", size_hint_y=None, height=18, font_size='11sp'))
        pay_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=5)
        btn_carta = Button(text="CARTA", background_color=(0.05, 0.35, 0.85, 1), font_size='13sp', bold=True)
        btn_carta.bind(on_press=lambda x: self.completa_vendita("CARTA"))
        btn_twint = Button(text="TWINT", background_color=(0.2, 0.7, 0.85, 1), font_size='13sp', bold=True, color=(0,0,0,1))
        btn_twint.bind(on_press=lambda x: self.completa_vendita("TWINT"))
        btn_cash = Button(text="CASH", background_color=(0.95, 0.65, 0.2, 1), font_size='13sp', bold=True, color=(0,0,0,1))
        btn_cash.bind(on_press=lambda x: self.completa_vendita("CASH"))
        pay_box.add_widget(btn_carta)
        pay_box.add_widget(btn_twint)
        pay_box.add_widget(btn_cash)
        left_box.add_widget(pay_box)
        layout.add_widget(left_box)
        
        right_box = BoxLayout(orientation='vertical', spacing=6, size_hint_x=0.58)
        self.input_codice = TextInput(text="", hint_text="Input / Tastierino / Barcode", multiline=False, size_hint_y=None, height=40, font_size='15sp')
        right_box.add_widget(self.input_codice)
        
        self.lbl_stato_corrente = Label(text="Pronto: Clicca un Reparto, inserisci quantità/prezzo e conferma", size_hint_y=None, height=22, font_size='11sp', color=(0.2, 0.6, 1, 1), bold=True)
        right_box.add_widget(self.lbl_stato_corrente)
        
        lbl_seq_guida = Label(text="Reparti Rapidi (Sequenza: Clicca Reparto -> Numero -> Q.tà -> Numero -> Prezzo/Conferma)", size_hint_y=None, height=20, font_size='10sp', color=(0.3, 0.3, 0.3, 1))
        right_box.add_widget(lbl_seq_guida)
        
        reparti_grid = GridLayout(cols=4, spacing=4, size_hint_y=None, height=90)
        reparti = ["ALIMENTARI", "BIBITE", "CUCINA", "LOTTO", "LOTTO VINCITE", "NON ALIMENTARI", "SIGARETTE"]
        colori_reparti = {
            "ALIMENTARI": (0.98, 0.72, 0.35, 1), "BIBITE": (0.98, 0.85, 0.35, 1),
            "CUCINA": (0.98, 0.95, 0.5, 1), "LOTTO": (0.65, 0.45, 0.8, 1),
            "LOTTO VINCITE": (0.45, 0.75, 0.95, 1), "NON ALIMENTARI": (0.95, 0.45, 0.6, 1),
            "SIGARETTE": (0.35, 0.7, 0.65, 1)
        }
        for rep in reparti:
            b = Button(text=rep, font_size='10sp', bold=True, color=(0,0,0,1), background_color=colori_reparti.get(rep, (0.5, 0.5, 0.5, 1)))
            b.bind(on_press=lambda instance, r=rep: self.seleziona_reparto(r))
            reparti_grid.add_widget(b)
        reparti_grid.add_widget(Button(text="", disabled=True, background_color=(0,0,0,0)))
        right_box.add_widget(reparti_grid)
        
        tastierino_layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=200)
        grid_tasti = GridLayout(cols=3, spacing=4, size_hint_x=0.72)
        for t in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ',', '⌫']:
            btn = Button(text=t, font_size='16sp', bold=True, background_color=(0.98, 0.98, 0.98, 1), color=(0.1, 0.1, 0.1, 1))
            btn.bind(on_press=lambda instance, val=t: self.premi_tasto(val))
            grid_tasti.add_widget(btn)
        tastierino_layout.add_widget(grid_tasti)
        
        col_azioni = BoxLayout(orientation='vertical', spacing=4, size_hint_x=0.28)
        btn_qta = Button(text="Q.tà", background_color=(0.0, 0.55, 0.4, 1), font_size='13sp', bold=True)
        btn_qta.bind(on_press=lambda x: self.imposta_modalita("QTA"))
        btn_prezzo = Button(text="Prezzo", background_color=(0.1, 0.45, 0.85, 1), font_size='13sp', bold=True)
        btn_prezzo.bind(on_press=lambda x: self.imposta_modalita("PREZZO"))
        btn_conferma = Button(text="CONFERMA", background_color=(0.15, 0.55, 0.22, 1), font_size='12sp', bold=True)
        btn_conferma.bind(on_press=lambda x: self.cerca_e_aggiungi_prodotto())
        
        col_azioni.add_widget(btn_qta)
        col_azioni.add_widget(btn_prezzo)
        col_azioni.add_widget(btn_conferma)
        tastierino_layout.add_widget(col_azioni)
        right_box.add_widget(tastierino_layout)
        layout.add_widget(right_box)
        return layout

    def cambia_valuta(self, *args):
        self.valuta_corrente = "EUR" if self.valuta_corrente == "CHF" else "CHF"
        self.btn_valuta.text = f"Valuta: {self.valuta_corrente}"
        self.aggiorna_vista_scontrino()

    def seleziona_reparto(self, reparto):
        self.reparto_selezionato = reparto
        self.lbl_stato_corrente.text = f"Reparto Selezionato: {reparto}"

    def imposta_modalita(self, modo):
        valore = self.input_codice.text.strip()
        if modo == "QTA":
            try:
                self.moltiplicatore_qta = int(valore) if valore else 1
                self.lbl_stato_corrente.text = f"Quantità impostata a: {self.moltiplicatore_qta}"
            except:
                self.moltiplicatore_qta = 1
            self.input_codice.text = ""
        elif modo == "PREZZO":
            try:
                self.prezzo_forzato = float(valore.replace(',', '.')) if valore else None
                self.lbl_stato_corrente.text = f"Prezzo forzato a: {self.valuta_corrente} {self.prezzo_forzato:.2f}"
            except:
                self.prezzo_forzato = None
            self.input_codice.text = ""

    def premi_tasto(self, valore):
        if valore == '⌫':
            self.input_codice.text = self.input_codice.text[:-1]
        else:
            self.input_codice.text += valore

    def cerca_e_aggiungi_prodotto(self):
        query = self.input_codice.text.strip()
        if self.prezzo_forzato is not None:
            prezzo_unitario = self.prezzo_forzato
            nome_prod = f"Reparto {self.reparto_selezionato}" if not query else query
            totale_riga = prezzo_unitario * self.moltiplicatore_qta
            riga = f"{self.moltiplicatore_qta}x {nome_prod[:14]:<14} {self.valuta_corrente} {totale_riga:.2f}"
            self.scontrino_righe.append((riga, totale_riga))
            self.totale_generale += totale_riga
            self.prezzo_forzato = None
            self.moltiplicatore_qta = 1
            self.aggiorna_vista_scontrino()
            self.input_codice.text = ""
            return
        if not query:
            return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, prezzo FROM prodotti WHERE barcode = ? OR nome LIKE ?", (query, f"%{query}%"))
        risultato = cursor.fetchone()
        conn.close()
        if risultato:
            nome_prod, prezzo = risultato
            totale_riga = prezzo * self.moltiplicatore_qta
            riga = f"{self.moltiplicatore_qta}x {nome_prod[:14]:<14} {self.valuta_corrente} {totale_riga:.2f}"
            self.scontrino_righe.append((riga, totale_riga))
            self.totale_generale += totale_riga
        else:
            try:
                importo = float(query.replace(',', '.'))
                totale_riga = importo * self.moltiplicatore_qta
                riga = f"{self.moltiplicatore_qta}x Articolo Libero{'':<4} {self.valuta_corrente} {totale_riga:.2f}"
                self.scontrino_righe.append((riga, totale_riga))
                self.totale_generale += totale_riga
            except:
                pass
        self.moltiplicatore_qta = 1
        self.aggiorna_vista_scontrino()
        self.input_codice.text = ""

    def elimina_ultima_riga(self, *args):
        if self.scontrino_righe:
            riga, prezzo = self.scontrino_righe.pop()
            self.totale_generale -= prezzo
            if self.totale_generale < 0:
                self.totale_generale = 0.0
            self.aggiorna_vista_scontrino()

    def aggiorna_vista_scontrino(self):
        testo = f"Cassa: {self.cassa_corrente}\nOp: {self.operatore_corrente}\n" + "-"*28 + "\n"
        testo += "\n".join([r[0] for r in self.scontrino_righe])
        self.scontrino_label.text = testo
        self.lbl_totale.text = f"TOTALE: {self.valuta_corrente} {self.totale_generale:.2f}"
        self.aggiorna_resto()

    def aggiorna_resto(self, *args):
        try:
            moneta = float(self.input_moneta.text.replace(',', '.'))
            resto = max(0.0, moneta - self.totale_generale)
            self.lbl_resto.text = f"Resto: {self.valuta_corrente} {resto:.2f}"
        except:
            self.lbl_resto.text = "Resto: -"

    def completa_vendita(self, pagamento):
        if not self.scontrino_righe:
            return
        data_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dettagli = " | ".join([r[0] for r in self.scontrino_righe])
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vendite (data_ora, totale, dettagli, pagamento, cassa, cassiere) VALUES (?, ?, ?, ?, ?, ?)", 
                       (data_ora, self.totale_generale, dettagli, pagamento, self.cassa_corrente, self.operatore_corrente))
        conn.commit()
        conn.close()
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.aggiorna_vista_scontrino()
        self.lbl_stato_corrente.text = f"Vendita completata ({pagamento}) con successo!"

    def crea_schermata_magazzino(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Listino Prodotti Magazzino", font_size='18sp', size_hint_y=None, height=40))
        scroll = ScrollView()
        box_prodotti = BoxLayout(orientation='vertical', size_hint_y=None)
        box_prodotti.bind(minimum_height=box_prodotti.setter('height'))
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, nome, prezzo, giacenza FROM prodotti ORDER BY nome ASC")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            box_prodotti.add_widget(Label(text="Nessun prodotto in magazzino.", size_hint_y=None, height=40))
        for b, n, p, g in rows:
            lbl = Label(text=f"[{b}] {n} - {self.valuta_corrente} {p:.2f} (Giac: {g})", size_hint_y=None, height=35, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            box_prodotti.add_widget(lbl)
        scroll.add_widget(box_prodotti)
        layout.add_widget(scroll)
        return layout

    def crea_schermata_storico(self):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text="Chiusura & Storico Vendite", font_size='18sp', size_hint_y=None, height=40))
        scroll = ScrollView()
        box_vendite = BoxLayout(orientation='vertical', size_hint_y=None)
        box_vendite.bind(minimum_height=box_vendite.setter('height'))
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_ora, totale, pagamento, cassiere FROM vendite ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            box_vendite.add_widget(Label(text="Nessuna vendita registrata.", size_hint_y=None, height=40))
        for v_id, data, tot, pag, op in rows:
            lbl = Label(text=f"#{v_id} | {data} | {self.valuta_corrente} {tot:.2f} ({pag}) [{op}]", size_hint_y=None, height=35, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            box_vendite.add_widget(lbl)
        scroll.add_widget(box_vendite)
        layout.add_widget(scroll)
        return layout

if __name__ == '__main__':
    CassaApp().run()
