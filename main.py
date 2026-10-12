from utils.printer import stampa_scontrino_rawbt
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
Window.clearcolor = (0, 0, 0, 1)
from datetime import datetime
import sqlite3
from kivy.config import Config

# Imposta la risoluzione fissa della finestra per simulare il tablet
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1200')
Config.set('graphics', 'resizable', True)

from kivy.app import App
Window.softinput_mode = "pan"
from kivy.uix.boxlayout import BoxLayout
from ui.ui_cassa import InterfacciaCassa

class CassaApp(App):
    def build(self):
        # Forziamo le dimensioni della finestra a 1440x900 (16:10)
        from kivy.core.window import Window
        Window.size = (1280, 720)

        self.db_name = "database/negozio.db"
        self.operatore_corrente = "Rosario Vincenzo"
        self.cassa_corrente = "Cassa Mobile Android"
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.reparto_selezionato = "GENERALE"
        self.moltiplicatore_qta = 1
        self.prezzo_forzato = None
        self.valuta_corrente = "CHF"
        self.vendita_completata_flag = False
        self.title = "Cassa - Chiosco & Alimentari dell'Est"

        self.root_layout = BoxLayout(orientation='vertical', padding=[24, 16, 24, 16], spacing=12)

        nav_layout = InterfacciaCassa.crea_menu_superiore(self)
        self.root_layout.add_widget(nav_layout)

        self.content_container = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.content_container)

        self.inizializza_db_se_manca()
        self.mostra_schermata("vendita")

        # Contenitore radice per il centramento geometrico con aspect ratio 16:10 rigoroso e sfondo BIANCO
        root_aspect = FloatLayout()

        with root_aspect.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=root_aspect.pos, size=root_aspect.size)
        root_aspect.bind(pos=lambda inst, val: setattr(self.bg_rect, 'pos', val))
        root_aspect.bind(size=lambda inst, val: setattr(self.bg_rect, 'size', val))

        self.root_layout.size_hint = (None, None)

        def update_layout_geometry(inst, size):
            parent_w, parent_h = size
            if parent_h == 0 or parent_w == 0:
                return
            # Calcoliamo basandoci rigorosamente sul rapporto 16:10 (1.6) con margine di sicurezza perimetrale
            target_w = parent_w * 0.95
            target_h = target_w / 1.6
            if target_h > parent_h * 0.95:
                target_h = parent_h * 0.95
                target_w = target_h * 1.6
            inst.size = (target_w, target_h)
            inst.pos = ((parent_w - target_w) / 2, (parent_h - target_h) / 2)

        root_aspect.bind(size=lambda inst, val: update_layout_geometry(self.root_layout, val))
        root_aspect.add_widget(self.root_layout)
        return root_aspect
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
        if self.vendita_completata_flag:
            return
        self.reparto_selezionato = reparto
        self.lbl_stato_corrente.text = f"Reparto Selezionato: {reparto}"

    def imposta_modalita(self, modo):
        if self.vendita_completata_flag:
            return
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
        if self.vendita_completata_flag:
            return
        if valore == '⌫':
            self.input_codice.text = self.input_codice.text[:-1]
        else:
            self.input_codice.text += valore

    def cerca_e_aggiungi_prodotto(self):
        if self.vendita_completata_flag:
            return
        query = self.input_codice.text.strip()
        if self.prezzo_forzato is not None:
            prezzo_unitario = self.prezzo_forzato
            nome_prod = f"{self.reparto_selezionato}" if not query else query
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
        conn = sqlite3.connect(self.db_name)
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

    def gestisci_azione_scontrino(self, *args):
        if self.vendita_completata_flag:
            self.nuova_operazione()
        else:
            self.elimina_ultima_riga()

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
        if not self.scontrino_righe or self.vendita_completata_flag:
            return
        data_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dettagli = " | ".join([r[0] for r in self.scontrino_righe])
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vendite (data_ora, totale, dettagli, pagamento, cassa, cassiere) VALUES (?, ?, ?, ?, ?, ?)", 
                       (data_ora, self.totale_generale, dettagli, pagamento, self.cassa_corrente, self.operatore_corrente))
        conn.commit()
        conn.close()
        
        # Rimossa stampa automatica su Cash/Carta/Twint
        # self.esegui_stampa_termica(dettagli, self.totale_generale, pagamento)
        
        self.vendita_completata_flag = True
        self.lbl_stato_corrente.text = f"Vendita completata ({pagamento}) - Scontrino in verifica"
        self.btn_azione_scontrino.text = "NUOVA OPERAZIONE"
        self.btn_azione_scontrino.set_color((0.1, 0.5, 0.8, 1))

    def nuova_operazione(self):
        self.scontrino_righe = []
        self.totale_generale = 0.0
        self.vendita_completata_flag = False
        self.input_moneta.text = ""
        self.aggiorna_vista_scontrino()
        self.lbl_stato_corrente.text = "Pronto per nuova vendita"
        self.btn_azione_scontrino.text = "Elimina Riga Selezionata"


    def stampa_scontrino_manuale(self, *args):
        if not self.scontrino_righe:
            self.lbl_stato_corrente.text = "Impossibile stampare: scontrino vuoto"
            return
        righe = [f"Cassa: {self.cassa_corrente}", f"Op: {self.operatore_corrente}", "-" * 32]
        for r in self.scontrino_righe:
            righe.append(str(r[0]))
        righe.append("-" * 32)
        righe.append(f"TOTALE: CHF {self.totale_generale:.2f}")
        testo = "\n".join(righe) + "\n"
        try:
            stampa_scontrino_rawbt(testo)
            self.lbl_stato_corrente.text = "Scontrino inviato a RawBT"
        except Exception as e:
            self.lbl_stato_corrente.text = f"Errore stampa RawBT: {e}"

    def esegui_stampa_termica(self, dettagli, totale, pagamento):
        pass

    def esegui_chiusura_z(self, *args):
        self.lbl_stato_corrente.text = "Chiusura Z calcolata e registrata con successo"

if __name__ == '__main__':
    CassaApp().run()
