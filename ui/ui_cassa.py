# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from ui.theme import Label
from ui.theme import TextInput
from ui.theme import Button
from ui.theme import Spinner
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle
from receipt_layout import row, WIDTH
import os, sys
import storage

class InterfacciaCassa(Screen):
    def __init__(self, **kwargs):
        super(InterfacciaCassa, self).__init__(**kwargs)
        
        self.carrello = []
        self.totale = 0.0
        self.item_corrente = None
        self.pagamento_completato = False
        self.last_sale_id = None
        #self._focus_idle = 0
        self._barcode_editing = False

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        root = BoxLayout(orientation="vertical", spacing=0)

        top_tabs = BoxLayout(size_hint_y=None, height=45, spacing=2)
        btn_tab_cassa = Button(text="Cassa / Vendita", background_normal="", background_color=(0.15, 0.1, 0.4, 1), bold=True)
        btn_tab_mag = Button(text="Magazzino", background_normal="", background_color=(0.25, 0.25, 0.25, 1), bold=True)
        btn_tab_mag.bind(on_press=lambda x: self.vai_a_schermata("magazzino"))
        btn_tab_storico = Button(text="Chiusura & Storico", background_normal="", background_color=(0.25, 0.25, 0.25, 1), bold=True)
        btn_tab_storico.bind(on_press=lambda x: self.vai_a_schermata("chiusura"))
        
        top_tabs.add_widget(btn_tab_cassa)
        top_tabs.add_widget(btn_tab_mag)
        top_tabs.add_widget(btn_tab_storico)
        root.add_widget(top_tabs)

        main_content = BoxLayout(orientation="horizontal", padding=12, spacing=12)
        
        left_box = BoxLayout(orientation="vertical", spacing=10, size_hint_x=1.1)
        
        # Abilitato markup=True per gestire il grassetto [b]...[/b]
        self.lbl_scontrino = Label(text="Scontrino Vuoto", color=(0.1,0.1,0.1,1), size_hint_y=0.45, halign="left", valign="top", markup=True, font_name=("C:/Windows/Fonts/consola.ttf" if sys.platform == "win32" and os.path.exists("C:/Windows/Fonts/consola.ttf") else "Roboto"))
        self.lbl_scontrino.bind(size=self.lbl_scontrino.setter("text_size"))
        left_box.add_widget(self.lbl_scontrino)
        
        actions_box = BoxLayout(size_hint_y=None, height=45, spacing=6)
        btn_elimina = Button(text="ELIMINA RIGA", background_normal="", background_color=(0.9, 0.2, 0.2, 1), bold=True)
        btn_elimina.bind(on_press=self.elimina_ultima_riga)
        btn_stampa = Button(text="STAMPA", background_normal="", background_color=(0.9, 0.2, 0.2, 1), bold=True)
        btn_stampa.bind(on_press=self.stampa_scontrino)
        actions_box.add_widget(btn_elimina)
        actions_box.add_widget(btn_stampa)
        left_box.add_widget(actions_box)

        self.lbl_totale = Label(text="TOTALE: CHF 0.00", bold=True, font_size=20, color=(0,0,0,1), size_hint_y=None, height=40)
        left_box.add_widget(self.lbl_totale)
        
        self.lbl_resto = Label(text="Resto: -", color=(0, 0.6, 0.2, 1), bold=True, size_hint_y=None, height=25)
        left_box.add_widget(self.lbl_resto)

        pay_input_box = BoxLayout(size_hint_y=None, height=40, spacing=6)
        pay_input_box.add_widget(Label(text="Importo Ricevuto:", color=(0.1,0.1,0.1,1), size_hint_x=0.6))
        self.txt_importo = TextInput(hint_text="Contanti", multiline=False)
        pay_input_box.add_widget(self.txt_importo)
        left_box.add_widget(pay_input_box)

        self.cassa_choices={}
        self.cassa_selector=Spinner(text='Seleziona cassa',values=[],size_hint_y=None,height=40)
        # Scelta della postazione rimane possibile in presenza di piu casse,
        # ma il suo nome e mostrato nella label sottostante.
        self.cassa_status=Label(text='CASSA NON APERTA',bold=True,color=(.75,.10,.10,1),size_hint_y=None,height=35)
        left_box.add_widget(self.cassa_status)
        self.cassa_selector.bind(text=lambda *_:self.update_cassa_status())
        self._blink_visible=True
        #Clock.schedule_interval(self._blink_status,0.65)
        left_box.add_widget(Label(text="Seleziona Pagamento:", color=(0.1,0.1,0.1,1), size_hint_y=None, height=20))
        pay_buttons = BoxLayout(size_hint_y=None, height=50, spacing=6)
        btn_carta = Button(text="CARTA", background_normal="", background_color=(0.15, 0.5, 0.9, 1), bold=True)
        btn_carta.bind(on_press=lambda x: self.gestisci_pagamento("CARTA"))
        btn_twint = Button(text="TWINT", background_normal="", background_color=(0.2, 0.75, 0.85, 1), bold=True, color=(0,0,0,1))
        btn_twint.bind(on_press=lambda x: self.gestisci_pagamento("TWINT"))
        btn_cash = Button(text="CASH", background_normal="", background_color=(1, 0.75, 0.1, 1), bold=True, color=(0,0,0,1))
        btn_cash.bind(on_press=lambda x: self.gestisci_pagamento("CASH"))
        pay_buttons.add_widget(btn_carta)
        pay_buttons.add_widget(btn_twint)
        pay_buttons.add_widget(btn_cash)
        left_box.add_widget(pay_buttons)

        main_content.add_widget(left_box)

        right_box = BoxLayout(orientation="vertical", spacing=10, size_hint_x=1.3)
        self.txt_input = TextInput(hint_text="Scrivi qui Q.tà o Prezzo", multiline=False, size_hint_y=None, height=42)
        input_row = BoxLayout(orientation="horizontal", spacing=6, size_hint_y=None, height=42)
        input_row.add_widget(self.txt_input)
        self.txt_barcode = TextInput(hint_text="Bar Code", multiline=False, size_hint_x=1)
        input_row.add_widget(self.txt_barcode)
        self.btn_barcode = Button(text='CONFERMA', size_hint_x=None, width=105,
            background_normal='', background_color=(0.15,0.55,0.36,1),
            bold=True, disabled=True, color=(1,1,1,1))
        self.btn_barcode.bind(on_press=self.leggi_barcode)
        input_row.add_widget(self.btn_barcode)
        right_box.add_widget(input_row)
        #self.txt_input.bind(text=lambda *_: self._mark_activity())
        self.txt_barcode.bind(text=self._barcode_changed)
        self.txt_barcode.bind(on_text_validate=self.leggi_barcode)
        #Clock.schedule_interval(self._focus_barcode_idle, 1)

        self.lbl_stato_attivo = Label(text="Sequenza: 1) Reparto -> 2) Q.tà -> 3) Prezzo", color=(0.1, 0.4, 0.8, 1), bold=True, size_hint_y=None, height=22)
        right_box.add_widget(self.lbl_stato_attivo)

        right_box.add_widget(Label(text="Reparti Dinamici (12 Slot Configurabili)", color=(0.3,0.3,0.3,1), size_hint_y=None, height=20))

        reparti_grid = GridLayout(cols=4, spacing=5, size_hint_y=None, height=130)
        self.pos_buttons={}
        for idx in range(1,13):
            btn=Button(text='Reparto '+str(idx),bold=True)
            btn.bind(on_press=lambda instance,v=idx:self.seleziona_reparto(v))
            self.pos_buttons[idx]=btn
            reparti_grid.add_widget(btn)
        self.refresh_pos()
        right_box.add_widget(reparti_grid)

        bottom_pad_box = BoxLayout(orientation="horizontal", spacing=6)
        numpad_grid = GridLayout(cols=3, spacing=5, size_hint_x=2.2)
        for t in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ",", "⌫"]:
            btn = Button(text=str(t), background_normal="", background_color=(0.92, 0.92, 0.92, 1), color=(0.1,0.1,0.1,1), bold=True, font_size=28)
            btn.bind(on_press=lambda instance, val=t: self.premi_tasto(val))
            numpad_grid.add_widget(btn)
        bottom_pad_box.add_widget(numpad_grid)

        func_grid = BoxLayout(orientation="vertical", spacing=5, size_hint_x=1)
        btn_qta = Button(text="Q.tà", background_normal="", background_color=(1, 0.55, 0.1, 1), bold=True, font_size=28)
        btn_qta.bind(on_press=lambda x: self.imposta_quantita())
        btn_prezzo = Button(text="Prezzo", background_normal="", background_color=(0.15, 0.5, 0.9, 1), bold=True, font_size=28)
        btn_prezzo.bind(on_press=lambda x: self.imposta_prezzo())
        btn_conferma = Button(text="CONFERMA", background_normal="", background_color=(0.1, 0.65, 0.3, 1), bold=True, font_size=28)
        btn_conferma.bind(on_press=lambda x: self.conferma_fine_ordine())
        
        func_grid.add_widget(btn_qta)
        func_grid.add_widget(btn_prezzo)
        func_grid.add_widget(btn_conferma)
        bottom_pad_box.add_widget(func_grid)

        right_box.add_widget(bottom_pad_box)
        main_content.add_widget(right_box)

        root.add_widget(main_content)
        self.add_widget(root)

    @staticmethod
    def _ean_valid(code):
        if not (code.isascii() and code.isdigit() and len(code) in (8,13)):
            return False
        digits=[int(x) for x in code]
        checksum=sum(d*(3 if i%2==0 else 1) for i,d in enumerate(reversed(digits[:-1])))
        return (10-checksum%10)%10 == digits[-1]

    def _barcode_changed(self, instance, value):
        #self._mark_activity()
        self.btn_barcode.disabled=not self._ean_valid(value.strip())
    """
    def _mark_activity(self):
        self._focus_idle = 0
    
    def _focus_barcode_idle(self, dt):
        if self.manager and self.manager.current != self.name: return
        self._focus_idle += dt
        if self._focus_idle >= 5 and not self.txt_barcode.focus:
            self.txt_barcode.focus = True
    """
    def leggi_barcode(self, *args):
        code=self.txt_barcode.text.strip()
        #self._focus_idle=0
        if not self._ean_valid(code):
            self.lbl_stato_attivo.text='EAN-8 / EAN-13 non valido.'
            return
        self.txt_barcode.text=''
        if self.pagamento_completato:
            self.lbl_stato_attivo.text='Concludi prima lo scontrino precedente.'
            return
        if self.item_corrente is not None and self.item_corrente.get('qta',0)==0:
            self.carrello.remove(self.item_corrente)
            self.item_corrente=None
        art=storage.article_by_barcode(code)
        if not art:
            self.lbl_stato_attivo.text='Codice a barre non presente in magazzino.'
            return
        if float(art.get('giac',0))<1:
            self.lbl_stato_attivo.text='Articolo esaurito.'
            return
        price=float(art.get('prezzo',0))
        if price<=0:
            self.lbl_stato_attivo.text='Prezzo articolo non valido.'
            return
        item={'nome':art.get('nome','Articolo'),'barcode':code,'prezzo':price,'qta':1}
        self.carrello.append(item)
        self.item_corrente=item
        self.aggiorna_scontrino()
        self.lbl_stato_attivo.text='Articolo EAN inserito: Q.ta 1 modificabile con Q.ta.'
        self.txt_input.text='1'
        self.txt_barcode.focus=True

    def on_pre_enter(self,*args):
        self.refresh_pos()
        self.refresh_casse()
        self.update_cassa_status()

    def _blink_status(self,dt):
        self._blink_visible=not self._blink_visible
        if hasattr(self,'cassa_status'):
            self.cassa_status.opacity=1 if self._status_open or self._blink_visible else .12

    def update_cassa_status(self):
        cid=self.cassa_choices.get(self.cassa_selector.text)
        turn=storage.active_turn(cid) if cid else None
        suspended=storage.is_suspended(cid) if cid and turn else False
        self._status_open=bool(turn and not suspended)
        self.cassa_status.text=(self.cassa_selector.text.split(' (ID ')[0] if self._status_open else 'CASSA SOSPESA' if suspended else 'CASSA NON APERTA')
        self.cassa_status.color=(.07,.43,.20,1) if self._status_open else (.75,.10,.10,1)
        self.cassa_status.opacity=1

    def refresh_casse(self):
        self.cassa_choices={"{} (ID {})".format(name,cid):cid for cid,name in storage.list_casse()}
        values=list(self.cassa_choices)
        self.cassa_selector.values=values
        if self.cassa_selector.text not in values:
            aperte=[v for v,cid in self.cassa_choices.items() if storage.active_turn(cid)]
            self.cassa_selector.text=next((v for v,cid in self.cassa_choices.items() if str(cid)==storage.get_setting('cassa_operativa_id') and storage.active_turn(cid)),None) or (aperte[0] if len(aperte)==1 else values[0] if len(values)==1 else 'Seleziona cassa')
        self.update_cassa_status()

    def refresh_pos(self):
        self.pos_active = {}
        for idx, label, hexcolor, active in storage.get_slots():
            btn = self.pos_buttons[idx]
            color_code = str(hexcolor or '').strip().upper()
            enabled = bool(active) and color_code != '#267C80'
            self.pos_active[idx] = enabled
            btn.text = str(label) if enabled else 'NON ATTIVO'
            try:
                rgb = tuple(int(color_code[i:i+2], 16)/255 for i in (1, 3, 5))
                if len(color_code) != 7:
                    raise ValueError('Colore non valido')
            except (ValueError, TypeError):
                rgb = (.15, .49, .50)
            btn.background_normal = ''
            btn.background_color = (*rgb, 1)
            luminance = .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
            btn.color = (.07, .12, .16, 1) if luminance > .60 else (1, 1, 1, 1)
            btn.disabled = not enabled

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def vai_a_schermata(self, nome_schermata):
        if self.manager:
            self.manager.current = nome_schermata
        else:
            app = App.get_running_app()
            if app and hasattr(app, "root") and app.root:
                app.root.current = nome_schermata

    def premi_tasto(self, val, *args):
        current = self.txt_input.text
        if val == "⌫":
            self.txt_input.text = current[:-1]
        else:
            self.txt_input.text = current + str(val)

    def seleziona_reparto(self, reparto_id):
        # Controllo lato logica, indipendente dallo stato grafico del pulsante.
        slot = next((r for r in storage.get_slots() if r[0] == reparto_id), None)
        if slot is None or not bool(slot[3]) or str(slot[2]).strip().upper() == '#267C80':
            self.lbl_stato_attivo.text = 'Reparto NON ATTIVO'
            return
        if self.pagamento_completato:
            self.lbl_stato_attivo.text = "Ordine completato. Premi CONFERMA per il nuovo cliente."
            return

        self.item_corrente = {
            "nome": next((r[1] for r in storage.get_slots() if r[0]==reparto_id), f"Reparto {reparto_id}"),
            "prezzo": 0.0,
            "qta": 0
        }
        self.carrello.append(self.item_corrente)
        self.aggiorna_scontrino()
        
        self.txt_input.text = "0"
        self.lbl_stato_attivo.text = f"Reparto {reparto_id} inserito. Ora scrivi Q.tà e premi Q.tà"

    def imposta_quantita(self):
        if self.item_corrente is None:
            self.lbl_stato_attivo.text = "ATTENZIONE: Seleziona prima un Reparto!"
            return

        txt_val = self.txt_input.text.strip()
        try:
            val = int(txt_val) if txt_val else 0

            if val <= 0:
                self.carrello.remove(self.item_corrente)
                self.item_corrente = None
                self.txt_input.text = ""
                self.aggiorna_scontrino()
                return

            self.item_corrente["qta"] = val
            self.aggiorna_scontrino()
            
            self.txt_input.text = ""
            self.lbl_stato_attivo.text = f"Q.tà impostata a {self.item_corrente['qta']}. Ora scrivi il Prezzo e premi Prezzo"
        except ValueError:
            self.lbl_stato_attivo.text = "Quantità non valida"

    def imposta_prezzo(self):
        if self.item_corrente is not None and self.item_corrente.get('barcode'):
            self.lbl_stato_attivo.text='Prezzo EAN da magazzino: non modificabile in vendita.'
            return
        if self.item_corrente is None:
            self.lbl_stato_attivo.text = "ATTENZIONE: Seleziona prima un Reparto!"
            return

        txt_val = self.txt_input.text.strip()
        try:
            val = float(txt_val.replace(",", ".")) if txt_val else 0.0
            if val > 0:
                self.item_corrente["prezzo"] = val
                self.aggiorna_scontrino()
                
                self.lbl_stato_attivo.text = f"Registrato: {self.item_corrente['qta']}x {self.item_corrente['nome']} @ CHF {val:.2f}"
                self.item_corrente = None
                self.txt_input.text = ""
            else:
                self.lbl_stato_attivo.text = "Inserisci un prezzo maggiore di zero"
        except ValueError:
            self.lbl_stato_attivo.text = "Prezzo non valido"

    def conferma_input(self):
        pass

    def conferma_fine_ordine(self, *args):
        if self.carrello and not self.pagamento_completato:
            self.lbl_stato_attivo.text='Ordine non pagato: elimina le righe oppure completa il pagamento.'
            return
        print("[CASSA] Ordine chiuso. Pronto per il prossimo cliente.")
        self.carrello = []
        self.totale = 0.0
        self.item_corrente = None
        self.pagamento_completato = False
        self.last_sale_id = None
        self.txt_importo.text = ""
        self.lbl_resto.text = "Resto: -"
        self.txt_input.text = ""
        self.lbl_stato_attivo.text = "Sequenza: 1) Reparto -> 2) Q.tà -> 3) Prezzo"
        self.aggiorna_scontrino()

    def aggiorna_scontrino(self):
        self.totale = 0.0
        righe = ['[b]' + row('DESCRIZIONE', 'QTA', 'UNIT.', 'TOTALE', header=True) + '[/b]']
        for i, item in enumerate(self.carrello):
            subtot = item['prezzo'] * item['qta']
            self.totale += subtot
            colore = '102B44' if i % 2 else '111111'
            riga = row(str(item.get('nome', 'Articolo')), item['qta'], item['prezzo'], subtot)
            righe.append('[color=#' + colore + ']' + riga + '[/color]')
        if not self.carrello:
            righe = ['Scontrino Vuoto']
        self.lbl_scontrino.text = '\n'.join(righe)
        self.lbl_totale.text = f'TOTALE: CHF {self.totale:.2f}'

    def elimina_ultima_riga(self, *args):
        if not self.pagamento_completato and self.carrello:
            self.carrello.pop()
            self.item_corrente = None
            self.aggiorna_scontrino()

    def stampa_scontrino(self, *args):
        if not self.pagamento_completato or not self.last_sale_id:
            self.lbl_stato_attivo.text='Stampa disponibile dopo la registrazione del pagamento.'
            return
        try:
            import printing
            self.lbl_stato_attivo.text=printing.send(self.last_sale_id)
        except Exception as exc:
            self.lbl_stato_attivo.text='Stampa non completata: '+str(exc)[:110]

    def gestisci_pagamento(self, tipo):
        import storage
        if self.pagamento_completato:
            self.lbl_resto.text = 'Pagamento gia registrato: premi CONFERMA per nuovo cliente.'
            return
        if not self.carrello or any(x['qta'] <= 0 or x['prezzo'] <= 0 for x in self.carrello):
            self.lbl_resto.text = 'Completa prima tutte le righe dello scontrino.'
            return
        cid=self.cassa_choices.get(self.cassa_selector.text)
        if cid is None:
            self.lbl_resto.text='Seleziona la cassa operativa.'
            return
        turn=storage.active_turn(cid)
        if not turn:
            self.lbl_resto.text = 'Aprire prima un turno da Chiusura & Storico.'
            return
        try:
            importo = float(self.txt_importo.text.replace(',', '.')) if self.txt_importo.text.strip() else self.totale
            if tipo != 'CASH':
                importo = self.totale
            if storage.cents(importo) < storage.cents(self.totale):
                self.lbl_resto.text = 'Importo insufficiente!'
                return
            import copy
            self.last_sale_id = storage.sale(turn[0], tipo, copy.deepcopy(self.carrello), self.totale, importo)
            self.lbl_resto.text = f'Resto: CHF {(storage.cents(importo)-storage.cents(self.totale))/100:.2f} ({tipo})'
            self.pagamento_completato = True
        except Exception as exc:
            self.lbl_resto.text = 'Pagamento NON registrato: ' + str(exc)[:90]
