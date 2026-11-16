# -*- coding: utf-8 -*-
import os, json, csv
import storage
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from ui.theme import Label
from ui.menu_colors import MenuButton as Button
from ui.theme import TextInput
from kivy.uix.scrollview import ScrollView
from ui.theme import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock

def importa_magazzino_excel(filepath):
    """Legge il tracciato a sedici colonne. Nessuna scrittura prima della validazione."""
    return storage.import_articles_excel(filepath)

class FileChooserPopup(Popup):
    def __init__(self, callback, mode="open", **kwargs):
        super(FileChooserPopup, self).__init__(**kwargs)
        self.callback = callback
        self.mode = mode
        self.title = "Seleziona file Excel/CSV da Importare" if mode == "open" else "Scegli dove Esportare il file"
        self.size_hint = (0.85, 0.85)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        start_path = "/mnt/c/Users/utente/Desktop" if os.path.exists("/mnt/c/Users/utente/Desktop") else os.path.expanduser("~")
        self.fc = FileChooserListView(filters=["*.xlsx", "*.xlsm"], path=start_path)
        layout.add_widget(self.fc)
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_ok = Button(text="Seleziona", background_normal="", background_color=(0.1, 0.6, 0.3, 1), bold=True)
        btn_ok.bind(on_press=self.conferma)
        btn_cancel = Button(text="Annulla", background_normal="", background_color=(0.8, 0.2, 0.2, 1), bold=True)
        btn_cancel.bind(on_press=self.dismiss)
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)
        self.content = layout

    def conferma(self, *args):
        selection = self.fc.selection
        if selection:
            self.dismiss()
            self.callback(selection[0])
        elif self.mode == "save" and self.fc.path:
            self.callback(os.path.join(self.fc.path, "magazzino_export.csv"))
            self.dismiss()

class InterfacciaMagazzino(Screen):
    def __init__(self, **kwargs):
        super(InterfacciaMagazzino, self).__init__(**kwargs)
        self.articoli = self.carica_dati()
        self.articolo_selezionato_idx = None
        self.vista_attuale = "elenco"
        self._solo_scorte_basse = False
        self.pagina_corrente = 0
        self.elementi_per_pagina = 40

        with self.canvas.before:
            Color(0.92, 0.92, 0.92, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        root = BoxLayout(orientation="vertical", spacing=0, padding=0, size_hint=(1, 1))

        top_tabs = BoxLayout(size_hint_y=None, height=45, spacing=2)
        btn_cassa = Button(text="Cassa / Vendita", background_normal="", background_color=(0.25, 0.25, 0.25, 1), bold=True)
        btn_cassa.bind(on_press=lambda x: self.vai_a("cassa"))
        btn_mag = Button(text="Magazzino", background_normal="", background_color=(0.15, 0.1, 0.4, 1), bold=True)
        btn_st = Button(text="Chiusura & Storico", background_normal="", background_color=(0.25, 0.25, 0.25, 1), bold=True)
        btn_st.bind(on_press=lambda x: self.vai_a("chiusura"))
        top_tabs.add_widget(btn_cassa)
        top_tabs.add_widget(btn_mag)
        top_tabs.add_widget(btn_st)
        root.add_widget(top_tabs)

        odoo_bar = BoxLayout(size_hint_y=None, height=50, padding=8, spacing=10)
        odoo_bar.add_widget(Label(text="Gestione Magazzino (Stile Odoo)", color=(0.1,0.1,0.1,1), bold=True, font_size=18, halign="left"))

        self.btn_elenco = Button(text="Elenco", size_hint_x=None, width=110, background_normal="", background_color=(0.1, 0.4, 0.6, 1), bold=True)
        self.btn_elenco.bind(on_press=lambda x: self.cambia_vista("elenco"))

        self.btn_griglia = Button(text="Vista Griglia", size_hint_x=None, width=100, background_normal="", background_color=(0.2, 0.2, 0.2, 1), bold=True)
        self.btn_griglia.bind(on_press=lambda x: self.cambia_vista("griglia"))

        btn_esp = Button(text="Esporta Excel", size_hint_x=None, width=110, background_normal="", background_color=(0.1, 0.6, 0.3, 1), bold=True)
        btn_esp.bind(on_press=lambda x: self.apri_selettore_salvataggio())
        btn_imp = Button(text="Importa Excel", size_hint_x=None, width=110, background_normal="", background_color=(0.85, 0.89, 0.94, 1), color=(0, 0, 0, 1), bold=True)
        btn_imp.bind(on_press=lambda x: self.apri_selettore_apertura())
        btn_allerta = Button(text="⚠ Allerta", size_hint_x=None, width=110, background_normal="", background_color=(0.6, 0.1, 0.1, 1), bold=True)
        btn_allerta.bind(on_press=self.filtra_scorte_basse)

        odoo_bar.add_widget(self.btn_elenco)
        odoo_bar.add_widget(self.btn_griglia)
        odoo_bar.add_widget(btn_esp)
        odoo_bar.add_widget(btn_imp)
        odoo_bar.add_widget(btn_allerta)
        root.add_widget(odoo_bar)

        filter_bar = BoxLayout(size_hint_y=None, height=45, padding=5, spacing=8)
        self.txt_cerca = TextInput(hint_text="Cerca per nome o codice...", multiline=False, size_hint_x=0.45)
        self.txt_cerca.bind(text=self.cerca_articoli)
        btn_raggruppa = Button(text="Raggruppa per...", size_hint_x=0.2, background_normal="", background_color=(0.3, 0.3, 0.3, 1))
        btn_sel = Button(text="Sel. Tutti", size_hint_x=0.175, background_normal="", background_color=(0.2, 0.5, 0.2, 1), bold=True)
        btn_sel.bind(on_press=self.seleziona_tutti)
        btn_des = Button(text="Deselez.", size_hint_x=0.175, background_normal="", background_color=(0.5, 0.2, 0.2, 1), bold=True)
        btn_des.bind(on_press=self.deseleziona_tutti)

        filter_bar.add_widget(self.txt_cerca)
        filter_bar.add_widget(btn_raggruppa)
        filter_bar.add_widget(btn_sel)
        filter_bar.add_widget(btn_des)
        root.add_widget(filter_bar)

        main_split = BoxLayout(orientation="horizontal", padding=8, spacing=12, size_hint=(1, 1))
        left_layout = BoxLayout(orientation="vertical", spacing=5, size_hint_x=0.67)

        header_list_row = BoxLayout(size_hint_y=None, height=30, spacing=5)
        self.btn_master_chk = Button(text="[    ]", size_hint_x=None, width=40, background_normal="", background_color=(0.85, 0.85, 0.85, 1), color=(0,0,0,1), bold=True)
        self.btn_master_chk.bind(on_press=self.toggle_master_seleziona)
        self.lbl_stato_lista = Label(text="Elenco / Griglia Prodotti (Paginato)", color=(0.1,0.1,0.1,1), bold=True, halign="left", font_size=13)
        self.lbl_stato_lista.bind(size=self.lbl_stato_lista.setter("text_size"))
        header_list_row.add_widget(self.btn_master_chk)
        header_list_row.add_widget(self.lbl_stato_lista)
        left_layout.add_widget(header_list_row)

        self.scroll_list = ScrollView(size_hint_y=1)
        self.list_content = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None)
        self.list_content.bind(minimum_height=self.list_content.setter("height"))
        self.scroll_list.add_widget(self.list_content)
        left_layout.add_widget(self.scroll_list)

        page_bar = BoxLayout(size_hint_y=None, height=40, spacing=8)
        btn_prev = Button(text="« Prec.", background_normal="", background_color=(0.3, 0.3, 0.3, 1), bold=True)
        btn_prev.bind(on_press=self.pagina_precedente)
        self.lbl_pagina = Label(text="Pag. 1", color=(0.1,0.1,0.1,1), bold=True, font_size=15)
        btn_next = Button(text="Succ. »", background_normal="", background_color=(0.3, 0.3, 0.3, 1), bold=True)
        btn_next.bind(on_press=self.pagina_successiva)

        page_bar.add_widget(btn_prev)
        page_bar.add_widget(self.lbl_pagina)
        page_bar.add_widget(btn_next)
        left_layout.add_widget(page_bar)
        main_split.add_widget(left_layout)

        right_layout = BoxLayout(orientation="vertical", spacing=6, size_hint_x=0.33, padding=6)
        right_layout.add_widget(Label(text="Anagrafica & Scheda Articolo", color=(0.1,0.1,0.1,1), bold=True, font_size=13, size_hint_y=None, height=25))

        row_nome_foto = BoxLayout(size_hint_y=None, height=115, spacing=8)
        box_campi_nome = BoxLayout(orientation="vertical", spacing=2)
        box_campi_nome.add_widget(Label(text="Nome Prodotto:", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_nome = TextInput(hint_text="Nome prodotto", multiline=False, font_size=15)
        box_campi_nome.add_widget(self.txt_nome)
        row_nome_foto.add_widget(box_campi_nome)

        box_foto = BoxLayout(orientation="vertical", size_hint_x=None, width=110)
        box_foto.add_widget(Label(text="Foto", color=(0.1,0.1,0.1,1), font_size=10, size_hint_y=None, height=16))
        from kivy.uix.image import Image
        from kivy.uix.behaviors import ButtonBehavior
        
        class ClickableImage(ButtonBehavior, Image):
            pass

        self.img_dettaglio = ClickableImage(source="", allow_stretch=True, keep_ratio=True, mipmap=True)
        self.img_dettaglio.bind(on_release=self.apri_foto_ingrandita)
        box_foto.add_widget(self.img_dettaglio)

        # Pulsanti rapidi Cambia / Rimuovi foto
        btn_box_foto = BoxLayout(size_hint_y=None, height=24, spacing=2)
        btn_cambia = Button(text="Cambia", font_size=9, background_normal="", background_color=(0.1,0.4,0.6,1))
        btn_cambia.bind(on_press=self.seleziona_nuova_foto)
        btn_rimuovi = Button(text="Rimuovi", font_size=9, background_normal="", background_color=(0.6,0.1,0.1,1))
        btn_rimuovi.bind(on_press=self.rimuovi_foto_articolo)
        
        btn_box_foto.add_widget(btn_cambia)
        btn_box_foto.add_widget(btn_rimuovi)
        box_foto.add_widget(btn_box_foto)
        
        row_nome_foto.add_widget(box_foto)
        right_layout.add_widget(row_nome_foto)

        box_bc = BoxLayout(orientation="vertical", spacing=2, size_hint_y=None, height=55)
        box_bc.add_widget(Label(text="Codice a Barre:", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_barcode = TextInput(hint_text="Codice a barre", multiline=False, font_size=15)
        box_bc.add_widget(self.txt_barcode)
        right_layout.add_widget(box_bc)

        box_prezzogiac = BoxLayout(size_hint_y=None, height=55, spacing=8)
        box_p = BoxLayout(orientation="vertical", spacing=2)
        box_p.add_widget(Label(text="Prezzo (€):", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_prezzo = TextInput(hint_text="0.00", multiline=False, font_size=15)
        box_p.add_widget(self.txt_prezzo)
        box_prezzogiac.add_widget(box_p)

        box_g = BoxLayout(orientation="vertical", spacing=2)
        box_g.add_widget(Label(text="Giacenza:", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_giacenza = TextInput(hint_text="0", multiline=False, font_size=15)
        box_g.add_widget(self.txt_giacenza)
        box_prezzogiac.add_widget(box_g)
        right_layout.add_widget(box_prezzogiac)

        box_lotto = BoxLayout(orientation="vertical", spacing=2, size_hint_y=None, height=55)
        box_lotto.add_widget(Label(text="Riferimento Interno / Lotto:", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_lotto = TextInput(hint_text="Rif. interno", multiline=False, font_size=15)
        box_lotto.add_widget(self.txt_lotto)
        right_layout.add_widget(box_lotto)

        box_cat = BoxLayout(orientation="vertical", spacing=2, size_hint_y=None, height=55)
        box_cat.add_widget(Label(text="Magazzino / Categoria:", color=(0.1,0.1,0.1,1), font_size=11, halign="left", size_hint_y=None, height=18))
        self.txt_cat = TextInput(hint_text="Categoria", multiline=False, font_size=15)
        box_cat.add_widget(self.txt_cat)

        # Campi Scadenza e Allerta Scadenza affiancati
        box_scad_allerta = BoxLayout(size_hint_y=None, height=55, spacing=8)
        
        box_scad = BoxLayout(orientation="vertical", size_hint_y=None, height=55, spacing=2, size_hint_x=0.5)
        box_scad.add_widget(Label(text="Scadenza (AAAA-MM-GG):", color=(0.1,0.1,0.1,1), font_size=12, size_hint_y=None, height=20, halign="left"))
        self.txt_scad = TextInput(hint_text="AAAA-MM-GG", multiline=False, font_size=15)
        box_scad.add_widget(self.txt_scad)
        box_scad_allerta.add_widget(box_scad)
        
        box_allerta = BoxLayout(orientation="vertical", size_hint_y=None, height=55, spacing=2, size_hint_x=0.5)
        box_allerta.add_widget(Label(text="Allerta Scadenza:", color=(0.1,0.1,0.1,1), font_size=12, size_hint_y=None, height=20, halign="left"))
        self.txt_allerta = TextInput(hint_text="Soglia / Note allerta", multiline=False, font_size=15)
        box_allerta.add_widget(self.txt_allerta)
        box_scad_allerta.add_widget(box_allerta)
        
        right_layout.add_widget(box_scad_allerta)
    
        right_layout.add_widget(box_cat)

        box_azioni_form = BoxLayout(size_hint_y=None, height=45, spacing=8)
        btn_salva = Button(text="Salva Modifiche", background_normal="", background_color=(0.1, 0.5, 0.2, 1), bold=True)
        btn_salva.bind(on_press=self.salva_articolo_corrente)
        btn_elimina = Button(text="Elimina", background_normal="", background_color=(0.7, 0.1, 0.1, 1), bold=True)
        btn_elimina.bind(on_press=self.elimina_articolo_corrente)
        box_azioni_form.add_widget(btn_salva)
        box_azioni_form.add_widget(btn_elimina)
        right_layout.add_widget(box_azioni_form)

        right_layout.add_widget(Label(text="", size_hint_y=1))
        main_split.add_widget(right_layout)
        root.add_widget(main_split)
        self.add_widget(root)
        self.aggiorna_vista_lista()

    def on_pre_enter(self, *args):
        # Rilegge le giacenze scaricate dalle vendite, senza riutilizzare la cache.
        self.articoli = self.carica_dati()
        self._solo_scorte_basse = False
        self.articolo_selezionato_idx = None
        self.aggiorna_vista_lista()

    def carica_dati(self):
        return storage.load_inventory()

    def salva_dati(self):
        import storage
        storage.save_inventory(self.articoli)

    def _update_bg(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def vai_a(self, screen_name):
        if self.manager:
            self.manager.current = screen_name

    def cambia_vista(self, vista):
        self.vista_attuale = vista
        self.pagina_corrente = 0
        self.aggiorna_vista_lista()

    def pagina_precedente(self, *args):
        if self.pagina_corrente > 0:
            self.pagina_corrente -= 1
            self.aggiorna_vista_lista()

    def pagina_successiva(self, *args):
        filtro = self.txt_cerca.text.lower().strip()
        filtrati = [a for a in self.articoli if filtro in a["nome"].lower() or filtro in a["barcode"]] if filtro else self.articoli
        if getattr(self, "_solo_scorte_basse", False): filtrati = [a for a in filtrati if float(a.get("giac",0)) <= 2]
        if (self.pagina_corrente + 1) * self.elementi_per_pagina < len(filtrati):
            self.pagina_corrente += 1
            self.aggiorna_vista_lista()

    def cerca_articoli(self, instance, value):
        self.pagina_corrente = 0
        self.aggiorna_vista_lista()

    def seleziona_tutti(self, *args):
        for a in self.articoli: a["selezionato"] = True
        self.aggiorna_vista_lista()

    def deseleziona_tutti(self, *args):
        for a in self.articoli: a["selezionato"] = False
        self.aggiorna_vista_lista()

    def toggle_master_seleziona(self, *args):
        tutti = all(a.get("selezionato", False) for a in self.articoli) if self.articoli else False
        for a in self.articoli: a["selezionato"] = not tutti
        self.aggiorna_vista_lista()

    def filtra_scorte_basse(self, *args):
        self.txt_cerca.text = ""
        self._solo_scorte_basse = not self._solo_scorte_basse
        self.pagina_corrente = 0
        self.aggiorna_vista_lista()

    def aggiorna_vista_lista(self):
        self.list_content.clear_widgets()
        filtro = self.txt_cerca.text.lower().strip()
        filtrati = [a for a in self.articoli if filtro in a["nome"].lower() or filtro in a["barcode"]] if filtro else self.articoli
        if getattr(self, "_solo_scorte_basse", False): filtrati = [a for a in filtrati if float(a.get("giac",0)) <= 2]
        tot_pagine = max(1, (len(filtrati) + self.elementi_per_pagina - 1) // self.elementi_per_pagina)
        if self.pagina_corrente >= tot_pagine: self.pagina_corrente = tot_pagine - 1
        if self.pagina_corrente < 0: self.pagina_corrente = 0
        self.lbl_pagina.text = f"Pag. {self.pagina_corrente + 1} / {tot_pagine}"
        
        pagina = filtrati[self.pagina_corrente * self.elementi_per_pagina : (self.pagina_corrente + 1) * self.elementi_per_pagina]
        if self.vista_attuale == "elenco":
            self.list_content.cols = 1
            for art in pagina:
                ri = self.articoli.index(art)
                row = BoxLayout(size_hint_y=None, height=40, spacing=5, padding=3)
                
                chk = Button(text="[X]" if art.get("selezionato") else "[  ]", size_hint_x=None, width=40, background_normal="", background_color=(0.9,0.9,0.9,1), color=(0,0,0,1))
                chk.article_index = ri
                chk.bind(on_press=lambda btn: self.toggle_seleziona_articolo(btn.article_index))
                row.add_widget(chk)

                info = Button(font_size=15, text=f"{art['nome']} | Barcode: {art['barcode']} | Prezzo: €{art['prezzo']:.2f} | Giac: {art['giac']}", background_normal="", background_color=(1,1,1,1), color=(0.1,0.1,0.1,1), halign="left")
                info.article_index = ri
                info.bind(on_press=lambda btn: self.seleziona_articolo(btn.article_index))
                row.add_widget(info)
                
                self.list_content.add_widget(row)
        else:
            from kivy.uix.image import AsyncImage
            grid = GridLayout(cols=4, spacing=8, size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for art in pagina:
                ri = self.articoli.index(art)
                box = BoxLayout(orientation="vertical", size_hint_y=None, height=160, padding=4, spacing=2)
                with box.canvas.before:
                    Color(1,1,1,1)
                    Rectangle(size=box.size, pos=box.pos)
                
                # Miniatura foto ottimizzata per la griglia
                fp = art.get("foto", "")
                if fp and os.path.exists(fp):
                    # Usiamo mipmap=True per una resa fluida e veloce anche con ridimensionamenti rapidi
                    img = AsyncImage(source=fp, size_hint_y=None, height=70, mipmap=True, allow_stretch=True)
                else:
                    img = AsyncImage(source="", size_hint_y=None, height=70)
                box.add_widget(img)

                box.add_widget(Label(text=art["nome"][:20], color=(0,0,0,1), bold=True, font_size=11, size_hint_y=None, height=18))
                box.add_widget(Label(text=f"€{art['prezzo']:.2f} (Giac: {art['giac']})", color=(0.2,0.2,0.2,1), font_size=10, size_hint_y=None, height=16))
                
                btn = Button(text="Seleziona", background_normal="", background_color=(0.1,0.4,0.6,1), font_size=10, size_hint_y=None, height=25)
                btn.bind(on_press=lambda x, r=ri: self.seleziona_articolo(r))
                box.add_widget(btn)
                grid.add_widget(box)
            self.list_content.add_widget(grid)
        self.list_content.height = max(400, len(pagina) * 45 if self.vista_attuale == "elenco" else ((len(pagina)//4 + 1) * 170))

    def toggle_seleziona_articolo(self, ri):
        self.articoli[ri]["selezionato"] = not self.articoli[ri].get("selezionato", False)
        self.aggiorna_vista_lista()

    def seleziona_articolo(self, ri):
        self.articolo_selezionato_idx = ri
        art = self.articoli[ri]
        self.txt_nome.text = str(art.get("nome", ""))
        self.txt_barcode.text = str(art.get("barcode", ""))
        self.txt_prezzo.text = str(art.get("prezzo", 0.0))
        self.txt_giacenza.text = str(art.get("giac", 0.0))
        self.txt_lotto.text = str(art.get("lotto", ""))
        self.txt_cat.text = str(art.get("cat", ""))
        self.txt_scad.text = str(art.get("scad", ""))
        self.txt_allerta.text = str(art.get("allerta", ""))
        if hasattr(self, 'img_dettaglio'):
            fp = art.get("foto", "")
            if fp and os.path.exists(fp):
                self.img_dettaglio.source = fp
            else:
                self.img_dettaglio.source = ""
        # Aggiorniamo anche la foto se il widget immagine è presente
        if hasattr(self, 'img_anteprima') and self.img_anteprima:
            foto_path = art.get("foto", "")
            if foto_path and os.path.exists(foto_path):
                self.img_anteprima.source = foto_path
            else:
                self.img_anteprima.source = ""
        print(f"Articolo selezionato index {ri}: {art.get('nome')}")

    def salva_articolo_corrente(self, *args):
        if self.articolo_selezionato_idx is not None and 0 <= self.articolo_selezionato_idx < len(self.articoli):
            art = self.articoli[self.articolo_selezionato_idx]
            art["nome"] = self.txt_nome.text.strip()
            art["barcode"] = self.txt_barcode.text.strip()
            try: art["prezzo"] = float(self.txt_prezzo.text.strip())
            except: pass
            try: art["giac"] = float(self.txt_giacenza.text.strip())
            except: pass
            art["lotto"] = self.txt_lotto.text.strip()
            art["cat"] = self.txt_cat.text.strip()
            art["scad"] = self.txt_scad.text.strip()
            art["allerta"] = self.txt_allerta.text.strip()
            try:
                self.salva_dati()
            except ValueError as exc:
                print('Salvataggio non riuscito:',exc)
                return
            self.aggiorna_vista_lista()
            print("Articolo salvato.")

    def elimina_articolo_corrente(self, *args):
        if self.articolo_selezionato_idx is not None and 0 <= self.articolo_selezionato_idx < len(self.articoli):
            from ui.theme import Popup
            from kivy.uix.boxlayout import BoxLayout
            from ui.theme import Label
            from ui.menu_colors import MenuButton as Button
            
            content = BoxLayout(orientation='vertical', padding=15, spacing=15)
            content.add_widget(Label(text="VUOI ELIMINARE QUESTO ARTICOLO?", font_size=16, bold=True, color=(1,1,1,1)))
            
            btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
            btn_si = Button(text="SÌ, ELIMINA", background_normal="", background_color=(0.8, 0.2, 0.2, 1), bold=True)
            btn_no = Button(text="ANNULLA", background_normal="", background_color=(0.3, 0.3, 0.3, 1), bold=True)
            
            popup = Popup(title="Conferma Eliminazione", content=content, size_hint=(None, None), size=(400, 200))
            
            def conferma_elimina(instance):
                self.articoli.pop(self.articolo_selezionato_idx)
                self.articolo_selezionato_idx = None
                self.salva_dati()
                self.aggiorna_vista_lista()
                # Pulisci i campi a destra
                self.txt_nome.text = ""
                self.txt_barcode.text = ""
                self.txt_prezzo.text = ""
                self.txt_giacenza.text = ""
                self.txt_lotto.text = ""
                self.txt_cat.text = ""
                if hasattr(self, 'txt_scad'): self.txt_scad.text = ""
                if hasattr(self, 'txt_allerta'): self.txt_allerta.text = ""
                if hasattr(self, 'btn_foto_form'): 
                    self.btn_foto_form.background_normal = ""
                    self.btn_foto_form.text = "[□ Foto]"
                print("Articolo eliminato con conferma.")
                popup.dismiss()
                
            btn_si.bind(on_press=conferma_elimina)
            btn_no.bind(on_press=popup.dismiss)
            
            btn_layout.add_widget(btn_si)
            btn_layout.add_widget(btn_no)
            content.add_widget(btn_layout)
            popup.open()

    def apri_selettore_apertura(self):
        """Apre il dialogo nativo di Windows, non il FileChooser di Kivy.

        Il callback e' programmato al frame successivo per consentire a Kivy
        di terminare la gestione del tocco prima del dialogo modale.
        """
        Clock.schedule_once(self._seleziona_excel_windows, 0)

    def _seleziona_excel_windows(self, _dt):
        import sys
        if sys.platform != 'win32':
            self._messaggio_importazione(
                'Selezione Excel',
                'Il selettore nativo e disponibile nella versione Windows.')
            return

        root = None
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            root.update_idletasks()
            path = filedialog.askopenfilename(
                parent=root,
                title='Kristin_Cassa - Seleziona file Excel',
                initialdir=os.path.expanduser('~'),
                filetypes=[('Cartelle di lavoro Excel', '*.xlsx *.xlsm'),
                           ('Tutti i file', '*.*')]
            )
        except Exception as exc:
            self._messaggio_importazione('Selezione file Excel',
                                         'Impossibile aprire la finestra Windows:\n' + str(exc))
            return
        finally:
            if root is not None:
                root.destroy()

        if path:
            # Il dialogo e chiuso: torna a Kivy e mostra anteprima/conferma.
            Clock.schedule_once(lambda _dt: self.esegui_importazione(path), 0)

    def esegui_importazione(self, path):
        """Solo lettura/anteprima: nessuna scrittura finche non si preme IMPORTA."""
        try:
            anteprima = storage.preview_articles_excel(path)
        except Exception as exc:
            self._messaggio_importazione('Errore lettura Excel', str(exc))
            return
        testo = ('File: ' + os.path.basename(path) + '\n'
                 + 'Righe da importare: ' + str(anteprima['totale']) + '\n'
                 + 'Codici a barre presenti: ' + str(anteprima['barcode']) + '\n'
                 + 'Fotografie incorporate: ' + str(anteprima['immagini']) + '\n\n'
                 + 'Anteprima prodotti:\n' + '\n'.join(anteprima['nomi'])
                 + '\n\nConfermi l\'importazione nella tabella Articoli?')
        layout = BoxLayout(orientation='vertical', padding=12, spacing=12)
        scroll = ScrollView()
        label = Label(text=testo, color=(0,0,0,1), size_hint_y=None,
                      halign='left', valign='top', font_size=15)
        label.bind(width=lambda inst,w: setattr(inst,'text_size',(w-12,None)))
        label.bind(texture_size=lambda inst,size: setattr(inst,'height',max(140,size[1]+20)))
        scroll.add_widget(label)
        layout.add_widget(scroll)
        buttons = BoxLayout(size_hint_y=None,height=54,spacing=12)
        popup = Popup(title='Importa Excel - Conferma',content=layout,size_hint=(0.78,0.78))
        btn_ok = Button(text='IMPORTA',background_normal='',
                        background_color=(0.16,0.52,0.31,1),color=(1,1,1,1),bold=True)
        btn_no = Button(text='ANNULLA',background_normal='',
                        background_color=(0.65,0.22,0.22,1),color=(1,1,1,1),bold=True)
        btn_no.bind(on_release=popup.dismiss)
        def conferma(*_):
            btn_ok.disabled = True
            try:
                risultato = storage.import_articles_excel(path)
                self.articoli = self.carica_dati()
                self.aggiorna_vista_lista()
                popup.dismiss()
                self._messaggio_importazione('Importazione completata',
                    'Nuovi articoli: {}\nArticoli aggiornati: {}\nFotografie: {}'.format(
                    risultato['nuovi'],risultato['aggiornati'],risultato['immagini']))
            except Exception as exc:
                popup.dismiss()
                self._messaggio_importazione('Importazione non eseguita',str(exc))
        btn_ok.bind(on_release=conferma)
        buttons.add_widget(btn_no); buttons.add_widget(btn_ok)
        layout.add_widget(buttons)
        popup.open()

    def _messaggio_importazione(self, titolo, testo):
        layout = BoxLayout(orientation='vertical',padding=12,spacing=12)
        lbl = Label(text=testo,color=(0,0,0,1),halign='center',valign='middle')
        lbl.bind(size=lambda inst,size: setattr(inst,'text_size',size))
        layout.add_widget(lbl)
        btn = Button(text='CHIUDI',size_hint_y=None,height=48,
                     background_normal='',background_color=(0.22,0.45,0.65,1),
                     color=(1,1,1,1))
        popup = Popup(title=titolo,content=layout,size_hint=(0.7,0.45))
        btn.bind(on_release=popup.dismiss)
        layout.add_widget(btn)
        popup.open()

    def apri_selettore_salvataggio(self):
        from ui.theme import Popup
        from kivy.uix.boxlayout import BoxLayout
        from ui.theme import Label
        from ui.theme import TextInput
        from ui.menu_colors import MenuButton as Button
        
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        content.add_widget(Label(text="INSERISCI IL NOME DEL FILE DA ESPORTARE:", font_size=15, bold=True, color=(1,1,1,1)))
        
        txt_nome_file = TextInput(text="magazzino_export.csv", multiline=False, font_size=15, size_hint_y=None, height=40)
        content.add_widget(txt_nome_file)
        
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_conferma = Button(text="CONFERMA", background_normal="", background_color=(0.1, 0.6, 0.3, 1), bold=True)
        btn_annulla = Button(text="ANNULLA", background_normal="", background_color=(0.3, 0.3, 0.3, 1), bold=True)
        
        popup = Popup(title="Nome File Esportazione", content=content, size_hint=(None, None), size=(450, 220))
        
        def procedi_salvataggio(instance):
            nome_file = txt_nome_file.text.strip()
            if not nome_file:
                nome_file = "magazzino_export.csv"
            if not nome_file.endswith(".csv"):
                nome_file += ".csv"
            popup.dismiss()
            FileChooserPopup(callback=lambda path: self.esegui_esportazione_con_nome(path, nome_file), mode="save").open()
            
        btn_conferma.bind(on_press=procedi_salvataggio)
        btn_annulla.bind(on_press=popup.dismiss)
        
        btn_layout.add_widget(btn_conferma)
        btn_layout.add_widget(btn_annulla)
        content.add_widget(btn_layout)
        popup.open()

    def esegui_esportazione_con_nome(self, dir_path, nome_file):
        import os
        if os.path.isdir(dir_path):
            path = os.path.join(dir_path, nome_file)
        else:
            base_dir = os.path.dirname(dir_path)
            path = os.path.join(base_dir, nome_file) if base_dir else nome_file
        self.esegui_esportazione(path)

    def esegui_esportazione(self, path):
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Nome", "Codice a barre", "Categoria", "Lotto", "Scadenza", "Prezzo", "Giacenza", "Foto"])
                for a in self.articoli:
                    w.writerow([a.get("nome", ""), a.get("barcode", ""), a.get("cat", ""), a.get("lotto", ""), a.get("scad", ""), a.get("prezzo", 0.0), a.get("giac", 0.0), a.get("foto", "")])
            print("Esportazione completata:", path)
        except Exception as e:
            print("Errore esportazione:", e)


    def apri_foto_ingrandita(self, *args):
        if not self.img_dettaglio.source or not os.path.exists(self.img_dettaglio.source):
            return
        
        from ui.theme import Popup
        from kivy.uix.boxlayout import BoxLayout
        from ui.menu_colors import MenuButton as Button
        from kivy.uix.image import Image
        
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        img_big = Image(source=self.img_dettaglio.source, fit_mode='contain', mipmap=True)
        content.add_widget(img_big)
        
        btn_chiudi = Button(text="Chiudi", size_hint_y=None, height=40, background_normal="", background_color=(0.2,0.2,0.2,1))
        popup = Popup(title="Anteprima Ingrandita Articolo", content=content, size_hint=(0.8, 0.8))
        btn_chiudi.bind(on_press=popup.dismiss)
        content.add_widget(btn_chiudi)
        popup.open()


    def seleziona_nuova_foto(self, *args):
        if self.articolo_selezionato_idx is None:
            return
        # Apriamo un selettore file semplice o riusciamo a puntare a un file immagine
        from kivy.uix.filechooser import FileChooserListView
        from ui.theme import Popup
        from kivy.uix.boxlayout import BoxLayout
        
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        filechooser = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg', '*.webp'], path=os.getcwd())
        content.add_widget(filechooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_ok = Button(text="Seleziona", background_color=(0.1,0.6,0.3,1))
        btn_annulla = Button(text="Annulla", background_color=(0.5,0.5,0.5,1))
        
        popup = Popup(title="Seleziona Immagine Prodotto", content=content, size_hint=(0.8, 0.8))
        
        def conferma_scelta(btn):
            sel = filechooser.selection
            if sel:
                path_foto = sel[0]
                if self.articolo_selezionato_idx is not None and 0 <= self.articolo_selezionato_idx < len(self.articoli):
                    self.articoli[self.articolo_selezionato_idx]["foto"] = path_foto
                    self.img_dettaglio.source = path_foto
                    self.aggiorna_vista_lista()
            popup.dismiss()
            
        btn_ok.bind(on_press=conferma_scelta)
        btn_annulla.bind(on_press=popup.dismiss)
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_annulla)
        content.add_widget(btn_layout)
        popup.open()

    def rimuovi_foto_articolo(self, *args):
        if self.articolo_selezionato_idx is not None and 0 <= self.articolo_selezionato_idx < len(self.articoli):
            self.articoli[self.articolo_selezionato_idx]["foto"] = ""
            self.img_dettaglio.source = ""
            self.aggiorna_vista_lista()
