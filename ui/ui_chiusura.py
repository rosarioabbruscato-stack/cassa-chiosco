import sqlite3
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

class SchermataChiusura(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 15
        
        self.inizializza_db()

        # Titolo e Controlli Turno & Gestione Anagrafiche
        top_bar = BoxLayout(size_hint_y=None, height=50, spacing=10)
        top_bar.add_widget(Label(text='Gestione Casse, Cassieri & Chiusura Z', font_size=18, bold=True, color=(0.2, 0.2, 0.2, 1)))
        
        self.btn_nuova_cassa = Button(text='+ Nuova Cassa', size_hint_x=None, width=130, background_color=(0.2, 0.5, 0.8, 1))
        self.btn_nuova_cassa.bind(on_press=self.apri_popup_crea_cassa)
        top_bar.add_widget(self.btn_nuova_cassa)

        self.btn_nuovo_cassiere = Button(text='+ Nuovo Cassiere', size_hint_x=None, width=140, background_color=(0.3, 0.6, 0.3, 1))
        self.btn_nuovo_cassiere.bind(on_press=self.apri_popup_crea_cassiere)
        top_bar.add_widget(self.btn_nuovo_cassiere)

        self.btn_turno = Button(text='Apri Turno (PIN)', size_hint_x=None, width=150, background_color=(0.1, 0.4, 0.7, 1))
        self.btn_turno.bind(on_press=self.apri_popup_turno)
        top_bar.add_widget(self.btn_turno)
        
        self.btn_chiusura_z = Button(text='Chiusura Z (Svizzera)', size_hint_x=None, width=170, background_color=(0.8, 0.2, 0.5, 1))
        self.btn_chiusura_z.bind(on_press=self.esegui_chiusura_z)
        top_bar.add_widget(self.btn_chiusura_z)
        
        self.add_widget(top_bar)
        
        # Area Storico / Report Foglio Z
        self.scroll = ScrollView()
        self.report_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.report_layout.bind(minimum_height=self.report_layout.setter('height'))
        
        self.lbl_report = Label(
            text='Nessuna sessione attiva.\nCrea o seleziona una cassa e un cassiere protetto da PIN per iniziare.',
            font_size=14,
            color=(0.3, 0.3, 0.3, 1),
            halign='center',
            valign='middle'
        )
        self.lbl_report.bind(size=self.lbl_report.setter('text_size'))
        self.report_layout.add_widget(self.lbl_report)
        
        self.scroll.add_widget(self.report_layout)
        self.add_widget(self.scroll)

    def inizializza_db(self):
        conn = sqlite3.connect('database/cassa.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS casse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                pin TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cassieri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                pin TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def apri_popup_crea_cassa(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text='Nome Nuova Cassa:', font_size=14))
        txt_nome = TextInput(text='', multiline=False, size_hint_y=None, height=40)
        content.add_widget(txt_nome)

        content.add_widget(Label(text='PIN Cassa (opzionale):', font_size=14))
        txt_pin = TextInput(text='', password=True, multiline=False, size_hint_y=None, height=40)
        content.add_widget(txt_pin)

        btn_salva = Button(text='Salva Cassa', size_hint_y=None, height=45, background_color=(0.2, 0.6, 0.2, 1))
        popup = Popup(title='Crea Nuova Postazione Cassa', content=content, size_hint=(0.5, 0.5))

        def salva(btn):
            nome = txt_nome.text.strip()
            pin = txt_pin.text.strip()
            if nome:
                try:
                    conn = sqlite3.connect('database/cassa.db')
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO casse (nome, pin) VALUES (?, ?)', (nome, pin))
                    conn.commit()
                    conn.close()
                    popup.dismiss()
                except Exception as e:
                    print(f"Errore creazione cassa: {e}")

        btn_salva.bind(on_press=salva)
        content.add_widget(btn_salva)
        popup.open()

    def apri_popup_crea_cassiere(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text='Nome Nuovo Cassiere:', font_size=14))
        txt_nome = TextInput(text='', multiline=False, size_hint_y=None, height=40)
        content.add_widget(txt_nome)

        content.add_widget(Label(text='PIN Cassiere (richiesto per login):', font_size=14))
        txt_pin = TextInput(text='', password=True, multiline=False, size_hint_y=None, height=40)
        content.add_widget(txt_pin)

        btn_salva = Button(text='Salva Cassiere', size_hint_y=None, height=45, background_color=(0.2, 0.6, 0.2, 1))
        popup = Popup(title='Crea Nuovo Cassiere', content=content, size_hint=(0.5, 0.5))

        def salva(btn):
            nome = txt_nome.text.strip()
            pin = txt_pin.text.strip()
            if nome:
                try:
                    conn = sqlite3.connect('database/cassa.db')
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO cassieri (nome, pin) VALUES (?, ?)', (nome, pin))
                    conn.commit()
                    conn.close()
                    popup.dismiss()
                except Exception as e:
                    print(f"Errore creazione cassiere: {e}")

        btn_salva.bind(on_press=salva)
        content.add_widget(btn_salva)
        popup.open()
        
    def apri_popup_turno(self, instance):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        conn = sqlite3.connect('database/cassa.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome FROM casse')
        casse = cursor.fetchall()
        cursor.execute('SELECT id, nome FROM cassieri')
        cassieri = cursor.fetchall()
        conn.close()
        
        content.add_widget(Label(text='Seleziona Cassa:', font_size=14))
        casse_names = [c[1] for c in casse] if casse else ['Nessuna Cassa Disponibile']
        spin_casse = Spinner(text=casse_names[0], values=casse_names, height=40, size_hint_y=None)
        content.add_widget(spin_casse)
        
        content.add_widget(Label(text='Seleziona Cassiere:', font_size=14))
        cassieri_names = [cas[1] for cas in cassieri] if cassieri else ['Nessun Cassiere Disponibile']
        spin_cassieri = Spinner(text=cassieri_names[0], values=cassieri_names, height=40, size_hint_y=None)
        content.add_widget(spin_cassieri)

        content.add_widget(Label(text='Inserisci PIN Autenticazione:', font_size=14))
        txt_pin_login = TextInput(text='', password=True, multiline=False, size_hint_y=None, height=45)
        content.add_widget(txt_pin_login)
        
        btn_conferma = Button(text='Verifica PIN e Apri Turno', size_hint_y=None, height=45, background_color=(0.2, 0.6, 0.2, 1))
        popup = Popup(title='Apertura Turno con PIN', content=content, size_hint=(0.6, 0.7))
        
        def conferma(btn):
            cassa_selezionata = spin_casse.text
            cassiere_selezionato = spin_cassieri.text
            inserito_pin = txt_pin_login.text.strip()

            conn = sqlite3.connect('database/cassa.db')
            cursor = conn.cursor()
            cursor.execute('SELECT pin FROM cassieri WHERE nome = ?', (cassiere_selezionato,))
            res = cursor.fetchone()
            conn.close()

            db_pin = res[0] if res and res[0] is not None else ''

            if db_pin == '' or db_pin == inserito_pin:
                self.lbl_report.text = f"Turno attivo:\nCassa: {cassa_selezionata}\nCassiere: {cassiere_selezionato}\nStato: Operativo (Autenticato)"
                popup.dismiss()
            else:
                popup.title = 'Apertura Turno - PIN ERRATO!'

        btn_conferma.bind(on_press=conferma)
        content.add_widget(btn_conferma)
        popup.open()

    def esegui_chiusura_z(self, instance):
        conn = sqlite3.connect('database/cassa.db')
        cursor = conn.cursor()
        
        report_text = """=== FOGLIO Z - CHIUSURA DI CASSA (SVIZZERA) ===
Data: 2026-10-11 18:00:00
--------------------------------------------------
[ SUBTOTALI PER CATEGORIA POS ]
- Alimentari: CHF 450.00
- Bevande:    CHF 180.00
- Tabacchi:   CHF 320.00
- Extra:      CHF 55.00

--------------------------------------------------
[ CANALI DI PAGAMENTO ]
- Cash (Contanti): CHF 350.00
- Carta (POS):     CHF 400.00
- Twint:           CHF 200.00
- Altro:           CHF 55.00
--------------------------------------------------
TOTALE GENERALE INCASSATO: CHF 1005.00
=================================================="""
        self.lbl_report.text = report_text
        conn.close()
