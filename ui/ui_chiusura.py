# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from ui.theme import Spinner
from ui.theme import Label
from ui.menu_colors import MenuButton as Button
from ui.theme import TextInput
from ui.theme import Popup
from kivy.app import App
from kivy.clock import Clock
import sqlite3
from datetime import datetime
import storage,auth
from ui.menu_colors import menu_button

class InterfacciaChiusura(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        root=BoxLayout(orientation='vertical',padding=10,spacing=8)
        tabs=BoxLayout(size_hint_y=None,height=45)
        for label,screen in [('Cassa / Vendita','cassa'),('Magazzino','magazzino'),('Chiusura & Storico','chiusura')]:
            b=menu_button(label);b.bind(on_release=lambda _,s=screen:self.vai_a(s));tabs.add_widget(b)
        root.add_widget(tabs)
        actions=BoxLayout(size_hint_y=None,height=45,spacing=5)
        for label,func in [('Cassa',self.apri_gestione_casse),('Cassiere',self.apri_gestione_cassieri),('Backup DB',self.esegui_backup),('Archivio / Ristampa',self._backup_archive_auth),('Chiusura Z',self.esegui_chiusura_z),('Archivio Z',self.archivio_z),('Setup',self.setup)]:
            b=menu_button(label);b.bind(on_release=lambda _,f=func:f());actions.add_widget(b)
        root.add_widget(actions)
        self.info=Label(text='',size_hint_y=None,height=35,color=(0,0,0,1));root.add_widget(self.info)
        self.casse_visibili=Label(text='',size_hint_y=None,height=55,color=(0,0,0,1));root.add_widget(self.casse_visibili)
        scroll=ScrollView()
        self.storico_layout=GridLayout(cols=1,spacing=4,size_hint_y=None)
        self.storico_layout.bind(minimum_height=self.storico_layout.setter('height'))
        scroll.add_widget(self.storico_layout);root.add_widget(scroll)
        foot=BoxLayout(size_hint_y=None,height=45)
        self.lbl_totale=Label(text='',color=(0,0.4,0,1));foot.add_widget(self.lbl_totale)
        b=Button(text='Aggiorna Storico');b.bind(on_release=self.carica_storico);foot.add_widget(b)
        root.add_widget(foot);self.add_widget(root)
        self.carica_storico()

    def on_pre_enter(self,*args):self.carica_storico()
    def vai_a(self,name):self.manager.current=name
    def popup(self,title,fields,action,button='Conferma',on_cancel=None):
        box=BoxLayout(orientation='vertical',padding=12,spacing=8)
        widgets={}
        for key,label,secret,initial in fields:
            box.add_widget(Label(text=label,color=(0,0,0,1),size_hint_y=None,height=24))
            if isinstance(initial, dict) and 'choices' in initial:
                choices=initial['choices']
                field=Spinner(text=initial.get('selected',choices[0] if choices else ''),values=choices,size_hint_y=None,height=42,background_normal='',background_color=(.145,.455,.475,1),color=(1,1,1,1))
            else:
                field=TextInput(text=initial,multiline=False,password=secret,size_hint_y=None,height=38)
            box.add_widget(field);widgets[key]=field
        error=Label(text='',color=(0.8,0,0,1),size_hint_y=None,height=30);box.add_widget(error)
        row=BoxLayout(size_hint_y=None,height=43)
        ok=Button(text=button);cancel=Button(text='Annulla')
        row.add_widget(ok);row.add_widget(cancel);box.add_widget(row)
        p=Popup(title=title,content=box,size_hint=(0.65,min(.9,.28+len(fields)*.13)))
        cancel.bind(on_release=lambda _: (p.dismiss(), Clock.schedule_once(lambda dt: on_cancel(), .08) if on_cancel else None))
        def submit(_):
            try:
                result=action({k:v.text for k,v in widgets.items()})
                if result is not False:
                    p.dismiss()
                    self.carica_storico()
                    if callable(result):
                        Clock.schedule_once(lambda dt: result(), 0.08)
            except (ValueError,sqlite3.Error,KeyError) as exc:error.text=str(exc)[:110]
        ok.bind(on_release=submit);p.open()

    def setup(self):
        if auth.admin_exists():self.ask_admin(self._setup_menu,title='Autorizzazione Setup')
        else:self._set_admin()
    def _setup_menu(self):
        box=BoxLayout(orientation='vertical',padding=12,spacing=10)
        actions=[('Password amministratore',self._set_admin),('Gestione POS (12 pulsanti)',self._pos_menu),('Impostazioni stampa',self._print_settings)]
        for label,func in actions:
            b=menu_button(label,size_hint_y=None,height=52)
            b.bind(on_release=lambda _,f=func: (pop.dismiss(), Clock.schedule_once(lambda dt: f(), 0.08)))
            box.add_widget(b)
        b=Button(text='Chiudi',size_hint_y=None,height=46);box.add_widget(b)
        pop=Popup(title='Setup',content=box,size_hint=(.65,.60));b.bind(on_release=lambda _:pop.dismiss());pop.open()
    def _set_admin(self):
        def save(d):
            if d['pwd']!=d['repeat']:raise ValueError('Le password non coincidono')
            auth.set_admin(d['pwd'])
        self.popup('Setup password amministratore',[('pwd','Nuova password amministratore',True,''),('repeat','Ripeti password',True,'')],lambda d: (save(d), self._setup_menu)[1],'Salva',on_cancel=self._setup_menu)
    def _pos_menu(self):
        palette={'Petrolio':'#267C80','Blu':'#2466A8','Verde':'#34865A','Arancio':'#C87824','Rosso':'#A94747','Viola':'#7654A1','Grigio':'#526374','Giallo':'#E3B747','Turchese':'#268E9A','Rosa':'#AD648B','Nero':'#303B46','Bianco':'#F2F5F7'}
        def choose(d):
            slot=int(d['slot'].split(' - ')[0]);current=next(x for x in storage.get_slots() if x[0]==slot)
            reverse={v:k for k,v in palette.items()}
            def save(x):
                color=palette.get(x['colore'],x['colore'])
                storage.save_slot(slot,x['etichetta'],color,x['stato']=='Attivo')
                app=App.get_running_app()
                if app and hasattr(app,'cassa_screen'):app.cassa_screen.refresh_pos()
            def open_editor():
                self.popup('Configura pulsante '+str(slot),[('etichetta','Etichetta',False,current[1]),('colore','Colore (tavolozza HEX)',False,{'choices':list(palette),'selected':reverse.get(current[2],'Petrolio')}),('stato','Stato',False,{'choices':['Attivo','Disattivato'],'selected':'Attivo' if current[3] else 'Disattivato'})],lambda x: (save(x), self._pos_menu)[1],'Salva',on_cancel=self._pos_menu)
            return open_editor
        self.popup('Gestione POS',[('slot','Seleziona pulsante',False,{'choices':[str(i)+' - '+label for i,label,_,_ in storage.get_slots()]})],choose,'Modifica',on_cancel=self._setup_menu)
    def _print_settings(self):
        import sys
        # In Windows il pulsante apre il dialogo nativo del sistema.
        box=BoxLayout(orientation='vertical',padding=12,spacing=8)
        printer=Label(text='Stampante: '+(storage.get_setting('printer') or '(predefinita di sistema)'),size_hint_y=None,height=45)
        box.add_widget(printer)
        selected=[storage.get_setting('printer') or '']
        if sys.platform=='win32':
            pick=Button(text='Scegli stampante (dialogo Windows)',size_hint_y=None,height=48)
            box.add_widget(pick)
            def choose(_):
                try:
                    from windows_printers import choose_printer
                    value=choose_printer()
                    if value:
                        selected[0]=value
                        printer.text='Stampante: '+value
                except Exception as exc:
                    printer.text='Errore selezione: '+str(exc)[:90]
            pick.bind(on_release=choose)
        else:
            box.add_widget(Label(text='Stampante di sistema (configurazione manuale)',size_hint_y=None,height=25))
            entry=TextInput(text=selected[0],multiline=False,size_hint_y=None,height=42)
            box.add_widget(entry)
        box.add_widget(Label(text='Sequenza di stampa',size_hint_y=None,height=25))
        options=['Intestazione > Articoli > QR','Articoli > Intestazione > QR','Intestazione > QR > Articoli']
        order=Spinner(text=storage.get_setting('print_order',options[0]),values=options,size_hint_y=None,height=45)
        box.add_widget(order)
        box.add_widget(Label(text='Android: RawBT',size_hint_y=None,height=25))
        rawbt=Spinner(text='Si' if storage.get_setting('android_rawbt')=='1' else 'No',values=['No','Si'],size_hint_y=None,height=45)
        box.add_widget(rawbt)
        status=Label(text='',size_hint_y=None,height=25)
        box.add_widget(status)
        row=BoxLayout(size_hint_y=None,height=46)
        save_btn=Button(text='Salva');back=Button(text='Torna a Setup')
        row.add_widget(save_btn);row.add_widget(back);box.add_widget(row)
        pop=Popup(title='Impostazioni stampa',content=box,size_hint=(.72,.78))
        def save(_):
            storage.set_setting('printer',selected[0] if sys.platform=='win32' else entry.text)
            storage.set_setting('print_order',order.text)
            storage.set_setting('android_rawbt','1' if rawbt.text=='Si' else '0')
            status.text='Impostazioni salvate. Puoi continuare.'
        def leave(_):
            pop.dismiss()
            Clock.schedule_once(lambda dt:self._setup_menu(),.08)
        save_btn.bind(on_release=save)
        back.bind(on_release=leave)
        pop.open()
    def ask_admin(self,callback,title='Accesso amministratore'):
        if not auth.admin_exists():
            self.setup();return
        def verify(d):
            if not auth.is_admin(d['pwd']):raise ValueError('Password amministratore errata')
            return callback
        self.popup(title,[('pwd','Password amministratore',True,'')],verify,'Accedi')

    def apri_gestione_casse(self):
        # La lista e visibile senza credenziali; le modifiche richiedono sempre l'admin.
        self._list_casse()
    def _list_casse(self):
        box=BoxLayout(orientation='vertical',padding=10,spacing=6)
        grid=GridLayout(cols=1,size_hint_y=None,spacing=4)
        grid.bind(minimum_height=grid.setter('height'))
        scroll=ScrollView();scroll.add_widget(grid);box.add_widget(scroll)
        def refresh():
            grid.clear_widgets()
            for cid,name in storage.list_casse():
                row=BoxLayout(size_hint_y=None,height=42)
                row.add_widget(Label(text=f'{cid} - {name}',color=(0,0,0,1)))
                b=Button(text='Modifica / Elimina',size_hint_x=.45)
                b.bind(on_release=lambda _,i=cid,n=name:self.ask_admin(lambda:self._edit_cassa(i,n,refresh)))
                row.add_widget(b);grid.add_widget(row)
            if not storage.list_casse():grid.add_widget(Label(text='Nessuna cassa creata',size_hint_y=None,height=40,color=(0,0,0,1)))
        actions=BoxLayout(size_hint_y=None,height=45)
        new=menu_button('Nuova cassa');new.bind(on_release=lambda _:self.ask_admin(lambda:self._edit_cassa(None,'',refresh)))
        actions.add_widget(new)
        open_shift=menu_button('Apertura Cassa')
        open_shift.bind(on_release=lambda _: (p.dismiss(), Clock.schedule_once(lambda dt:self.apri_gestione_turno(),.08)))
        actions.add_widget(open_shift)
        suspend_shift=menu_button('Sospendi / Riprendi')
        suspend_shift.bind(on_release=lambda _: (p.dismiss(), Clock.schedule_once(lambda dt:self._suspend_auth(),.08)))
        actions.add_widget(suspend_shift)
        close_shift=menu_button('Chiusura Cassa')
        close_shift.bind(on_release=lambda _: (p.dismiss(), Clock.schedule_once(lambda dt:self._close_auth(),.08)))
        actions.add_widget(close_shift)
        archive_shift=menu_button('Archivio Chiusure')
        archive_shift.bind(on_release=lambda _: (p.dismiss(), Clock.schedule_once(lambda dt:self.ask_admin(self._archivio_cassa_menu,title='Archivio Chiusure - amministratore'),.08)))
        actions.add_widget(archive_shift)
        close=menu_button('Chiudi');actions.add_widget(close);box.add_widget(actions)
        p=Popup(title='Elenco casse registrate',content=box,size_hint=(.8,.75))
        close.bind(on_release=lambda _:p.dismiss());refresh();p.open()
    def _edit_cassa(self,cid,name,refresh):
        def save(d):
            if d['operation'].strip().upper()=='ELIMINA':
                if cid is None:raise ValueError('Cassa non esistente')
                storage.disable_cassa(cid)
            else:
                storage.save_cassa(d['name'],cid)
                if cid is not None:storage.save_header(cid,d)
            refresh()
        h=storage.get_header(cid) if cid is not None else {}
        fields=[('name','Nome cassa',False,name)]
        if cid is not None:
            fields += [(k,label,False,h.get(k,'')) for k,label in [('negozio','Nome Punto Vendita'),('indirizzo','Indirizzo'),('piva','P.IVA'),('telefono','Telefono'),('qr_testo','Testo destinato al QR-Code')]]
        fields.append(('operation','ELIMINA per disattivare (storico conservato)',False,''))
        self.popup('Gestione cassa',fields,save,'Registra')

    def apri_gestione_cassieri(self):self.ask_admin(self._list_cassieri)
    def _list_cassieri(self):
        box=BoxLayout(orientation='vertical',padding=10,spacing=5)
        grid=GridLayout(cols=1,size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        sc=ScrollView();sc.add_widget(grid);box.add_widget(sc)
        def refresh():
            grid.clear_widgets()
            for cid,nh in storage.list_cassieri():
                row=BoxLayout(size_hint_y=None,height=42)
                row.add_widget(Label(text=f'{auth.cashier_display_name(cid) or "Cassiere"} | ID {cid}',color=(0,0,0,1)))
                b=Button(text='Modifica',size_hint_x=.3);b.bind(on_release=lambda _,i=cid:self._edit_cashier(i,refresh));row.add_widget(b);grid.add_widget(row)
        row=BoxLayout(size_hint_y=None,height=45)
        b=Button(text='Aggiungi cassiere');b.bind(on_release=lambda _:self._edit_cashier(None,refresh));row.add_widget(b)
        done=Button(text='Chiudi');row.add_widget(done);box.add_widget(row)
        p=Popup(title='Gestione cassieri (amministratore)',content=box,size_hint=(.8,.7));done.bind(on_release=lambda _:p.dismiss());refresh();p.open()
    def _edit_cashier(self,cid,refresh):
        def save(d):
            if d['operation'].strip().upper()=='ELIMINA':
                if cid is None:raise ValueError('Cassiere inesistente')
                storage.disable_cassiere(cid);auth.remove_cashier(cid)
            else:
                if not d['name'].strip():raise ValueError('Nome obbligatorio')
                if d['pwd']!=d['repeat']:raise ValueError('Le password non coincidono')
                auth.credential(d['pwd'])
                if not auth.password_available(d['pwd'],exclude_cid=cid):
                    raise ValueError("Password non valida. Sceglierne un'altra.")
                nh=auth.namehash(d['name'])
                storage.save_cassiere(nh,cid)
                if cid is None:
                    cid_new=next(i for i,h in storage.list_cassieri() if h==nh)
                else:cid_new=cid
                auth.set_cashier(cid_new,d['name'],d['pwd'])
            refresh()
        self.popup('Registra cassiere',[('name','Nome cassiere (non recuperabile dal solo hash)',False,''),('pwd','Password (minimo 8 caratteri)',True,''),('repeat','Ripeti password',True,''),('operation','ELIMINA per disattivare',False,'')],save,'Salva')

    def apri_gestione_turno(self):
        def login(d):
            if auth.is_admin(d['pwd']):cid=None
            else:
                cid=auth.cashier_by_password(d['pwd'])
                if cid is None:raise ValueError('Password non riconosciuta')
            self._turn_form(cid)
        self.popup('Autenticazione turno',[('pwd','Password amministratore o cassiere',True,'')],login,'Accedi')
    def _turn_form(self,logged_cid):
        casse=storage.list_casse()
        if not casse:raise ValueError('Creare almeno una cassa')
        cassieri=storage.list_cassieri()
        if not cassieri:raise ValueError('Registrare almeno un cassiere')
        cassa_labels={f'{nome} (Cassa {cid})':cid for cid,nome in casse}
        cassiere_labels={f'{auth.cashier_display_name(cid) or "Cassiere " + str(cid)} (ID {cid})':cid for cid,_ in cassieri}
        if logged_cid is not None and logged_cid not in [cid for cid,_ in cassieri]:
            raise ValueError('Cassiere non attivo')

        def fmt(value):
            if not value:return '---'
            try:return datetime.fromisoformat(value).strftime('%d/%m/%Y    %H:%M:%S')
            except (ValueError,TypeError):return str(value)

        box=BoxLayout(orientation='vertical',padding=14,spacing=9)
        def field(label,values,selected=None):
            box.add_widget(Label(text=label,color=(.12,.20,.26,1),size_hint_y=None,height=27,bold=True))
            sp=Spinner(text=selected or values[0],values=values,size_hint_y=None,height=46,
                       background_normal='',background_color=(.145,.455,.475,1),color=(1,1,1,1))
            box.add_widget(sp)
            return sp
        cassa_spinner=field('CASSA',list(cassa_labels))
        chosen=next((label for label,cid in cassiere_labels.items() if cid==logged_cid),next(iter(cassiere_labels)))
        cassiere_spinner=field('CASSIERE', [chosen] if logged_cid is not None else list(cassiere_labels),chosen)
        status=Label(text='',color=(.10,.22,.30,1),bold=True,size_hint_y=None,height=35)
        box.add_widget(status)
        opening=Label(text='',color=(.10,.22,.30,1),size_hint_y=None,height=40)
        closing=Label(text='',color=(.10,.22,.30,1),size_hint_y=None,height=40)
        box.add_widget(opening);box.add_widget(closing)
        box.add_widget(Label(text='FONDO CASSA RESIDUO (CHF) - obbligatorio in apertura',color=(.1,.2,.3,1),size_hint_y=None,height=27))
        fondo_input=TextInput(text='0.00',multiline=False,size_hint_y=None,height=39,input_filter='float')
        box.add_widget(fondo_input)
        error=Label(text='',color=(.72,.12,.12,1),size_hint_y=None,height=45)
        box.add_widget(error)
        row=BoxLayout(size_hint_y=None,height=49,spacing=8)
        action=Button(text='Apri turno');cancel=Button(text='Esci')
        row.add_widget(action);row.add_widget(cancel);box.add_widget(row)
        popup=Popup(title='Apri / Chiudi turno - Data e ora',content=box,size_hint=(.78,.80))
        cancel.bind(on_release=lambda _:popup.dismiss())

        def refresh(*_):
            cassa=cassa_labels[cassa_spinner.text]
            active=storage.active_turn(cassa)
            last=storage.last_turn(cassa)
            if active:
                status.text='STATO: TURNO APERTO'
                opening.text='DATA E ORA APERTURA:  '+fmt(active[3])
                closing.text='DATA E ORA CHIUSURA:  non ancora effettuata'
                action.text='Chiudi turno'
                owner=next((label for label,cid in cassiere_labels.items() if cid==active[2]),f'Cassiere ID {active[2]}')
                if logged_cid is None and owner in cassiere_labels:cassiere_spinner.text=owner
            else:
                status.text='STATO: CASSA DISPONIBILE'
                opening.text='DATA E ORA APERTURA:  da registrare'
                closing.text='ULTIMA CHIUSURA:  '+fmt(last[4] if last else None)
                action.text='Apri turno'
            error.text=''
        cassa_spinner.bind(text=refresh)

        def submit(_):
            try:
                cassa=cassa_labels[cassa_spinner.text]
                active=storage.active_turn(cassa)
                if active:
                    if logged_cid is not None and active[2]!=logged_cid:
                        raise ValueError('Turno assegnato ad altro cassiere')
                    storage.close_turn(active[0])
                    closed=storage.last_turn(cassa)
                    self.info.text='Turno {} chiuso il {}'.format(active[0],fmt(closed[4]))
                else:
                    cashier=cassiere_labels.get(cassiere_spinner.text) if logged_cid is None else logged_cid
                    if cashier not in [i for i,_ in storage.list_cassieri()]:
                        raise ValueError('Cassiere non valido')
                    tid=storage.open_turn(cassa,cashier,fondo_input.text)
                    storage.set_setting('cassa_operativa_id',str(cassa))
                    started=storage.active_turn(cassa)
                    self.info.text='Turno {} aperto il {}'.format(tid,fmt(started[3]))
                refresh()
                self.carica_storico()
            except (ValueError,sqlite3.Error,KeyError) as exc:
                error.text=str(exc)[:120]
        action.bind(on_release=submit)
        refresh()
        popup.open()

    def carica_storico(self,*args):
        self.storico_layout.clear_widgets()
        self.casse_visibili.text='Casse: '+(', '.join(f'{i} - {n}' for i,n in storage.list_casse()) or 'nessuna')
        for timestamp,cassa,metodo,cent,idv in storage.history():
            self.storico_layout.add_widget(Label(text=f'#{idv}  {timestamp[:19]}  | {cassa} | {metodo} | CHF {cent/100:.2f}',size_hint_y=None,height=34,color=(0,0,0,1)))
        self.lbl_totale.text=f'Incasso giornaliero: CHF {storage.daily_total()/100:.2f}'
    def esegui_backup(self):
        self.ask_admin(self._backup_menu)
    def _do_backup(self):
        path=storage.backup();self.info.text='Backup: '+path
    def esegui_chiusura_z(self):
        self.ask_admin(self._do_z)
    def _z_message(self, message):
        self.info.text = str(message)[:160]

    def _z_view(self, title, text, on_confirm=None, report_id=None, tipo="Z", on_print=None):
        from kivy.uix.scrollview import ScrollView
        box=BoxLayout(orientation='vertical',padding=12,spacing=8)
        scroll=ScrollView()
        from kivy.uix.label import Label as KivyLabel
        label=KivyLabel(text=text,font_size=13,
                        halign='left',valign='top',size_hint=(None,None),
                        color=(0.05,0.12,0.19,1))
        # Kivy non include RobotoMono: usa un font monospaziato di sistema, se disponibile.
        import os, sys
        candidates = ([r'C:\Windows\Fonts\consola.ttf', r'C:\Windows\Fonts\cour.ttf']
                      if sys.platform == 'win32' else
                      ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                       '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'])
        label.font_name = next((f for f in candidates if os.path.isfile(f)), 'Roboto')
        label.texture_update()
        label.size=(max(850,label.texture_size[0]+30),max(500,label.texture_size[1]+20))
        scroll.add_widget(label);box.add_widget(scroll)
        controls=BoxLayout(size_hint_y=None,height=48,spacing=8)
        pop=Popup(title=title,content=box,size_hint=(.94,.90))
        if on_confirm:
            btn=Button(text='CONFERMA CHIUSURA '+('CASSA' if tipo=='CASSA' else 'Z'))
            def confirm(_):
                try:
                    rid=on_confirm()
                    pop.dismiss()
                    self.carica_storico()
                    self._z_view('Chiusura '+tipo+' archiviata N. '+str(rid),(__import__('cassa_report').archived_text(rid) if tipo=='CASSA' else __import__('z_report').archived_text(rid)),report_id=rid,tipo=tipo)
                except Exception as exc:self._z_message('Errore chiusura '+tipo+': '+str(exc))
            btn.bind(on_release=confirm);controls.add_widget(btn)
        if on_print is not None:
            btn=Button(text='STAMPA BACKUP')
            def print_backup(_):
                try:on_print()
                except Exception as exc:self._z_message('Errore stampa backup: '+str(exc))
            btn.bind(on_release=print_backup);controls.add_widget(btn)
        if report_id is not None:
            btn=Button(text='STAMPA / RISTAMPA')
            def print_now(_):
                try:
                    import z_report
                    (__import__('cassa_report').print_report(report_id) if tipo=='CASSA' else z_report.print_z(report_id))
                    self._z_message('Rapporto '+tipo+' inviato alla stampa: '+str(report_id))
                except Exception as exc:self._z_message('Stampa '+tipo+' non completata: '+str(exc))
            btn.bind(on_release=print_now);controls.add_widget(btn)
        close=Button(text='CHIUDI');close.bind(on_release=lambda _:pop.dismiss())
        controls.add_widget(close);box.add_widget(controls);pop.open()

    def _do_z(self):
        import z_report
        choices=[str(i)+' - '+name for i,name in storage.list_casse()]
        if not choices:
            self._z_message('Nessuna cassa registrata');return
        def selected(d):
            cid=int(d['cassa'].split(' - ')[0])
            return lambda:self._z_preview(cid)
        self.popup('Chiusura Z - Seleziona cassa',
                   [('cassa','Cassa da chiudere',False,{'choices':choices})],
                   selected,'ANTEPRIMA Z')

    def _z_preview(self,cid):
        import z_report
        try:
            text=z_report.preview(cid)
            self._z_view('ANTEPRIMA Z - non ancora registrata',text,
                         on_confirm=lambda:z_report.close(cid))
        except Exception as exc:self._z_message('Anteprima Z: '+str(exc))

    def archivio_z(self):
        self.ask_admin(self._archivio_z_menu,title='Accesso archivio Z')

    def _archivio_z_menu(self):
        import z_report
        reports=z_report.archive()
        if not reports:
            self._z_message('Archivio Z vuoto');return
        choices=['{} - {} - {}'.format(rid,ts[:19],name) for rid,ts,name,_ in reports]
        def selected(d):
            rid=int(d['rapporto'].split(' - ')[0])
            return lambda:self._z_view('Archivio Z - Rapporto '+str(rid),z_report.archived_text(rid),report_id=rid)
        self.popup('Archivio Z / Ristampa',
                   [('rapporto','Rapporti Z registrati',False,{'choices':choices})],
                   selected,'VISUALIZZA')

    def _authorize_operator(self, callback, title):
        def check(d):
            if auth.is_admin(d['pwd']):
                return lambda: callback(None)
            cid=auth.cashier_by_password(d['pwd'])
            if cid is None:
                raise ValueError('Password non valida')
            return lambda: callback(cid)
        self.popup(title,[('pwd','Password cassiere o amministratore',True,'')],check,'Accedi')

    def _close_auth(self):
        self._authorize_operator(self._cassa_chiusura_menu,'Chiusura Cassa - Autorizzazione')

    def _suspend_auth(self):
        self._authorize_operator(self._suspend_menu,'Sospensione - Autorizzazione')

    def _suspend_menu(self, cashier_id):
        choices=[]
        for cid,name in storage.list_casse():
            t=storage.active_turn(cid)
            if t and (cashier_id is None or t[2]==cashier_id):
                choices.append('{} - {}'.format(cid,name))
        if not choices:
            self._z_message('Nessun turno autorizzato da sospendere o riprendere');return
        def save(d):
            cid=int(d['cassa'].split(' - ')[0])
            t=storage.active_turn(cid)
            if not t or (cashier_id is not None and t[2]!=cashier_id):
                raise ValueError('Cassa non autorizzata')
            storage.set_suspended(cid,not storage.is_suspended(cid))
            self.carica_storico()
            return lambda: self._z_message('Stato cassa aggiornato')
        self.popup('Sospendi / Riprendi cassa',
            [('cassa','Cassa',False,{'choices':choices})],save,'CAMBIA STATO')

    def _backup_archive_auth(self):
        self.ask_admin(self._backup_menu,title='Archivio backup - Amministratore')

    def _backup_menu(self):
        import cassa_report
        reports=cassa_report.archive()
        if not reports:
            self._z_message('Nessuna chiusura cassa archiviata');return
        box=BoxLayout(orientation='vertical',padding=12,spacing=8)
        for label,fn in [('CONSULTA CHIUSURE GIORNALIERE',self._backup_report_choose),
                         ('TOTALI PER INTERVALLO',self._backup_interval),
                         ('COPIA DATABASE',self._do_backup)]:
            b=menu_button(label);box.add_widget(b)
            b.bind(on_release=lambda _,f=fn:(pop.dismiss(),Clock.schedule_once(lambda dt:f(),.08)))
        pop=Popup(title='Backup DB - Chiusure giornaliere',content=box,size_hint=(.72,.48));pop.open()

    def _backup_report_choose(self):
        import cassa_report
        reports=cassa_report.archive()
        choices=['{} - {} - {}'.format(rid,ts[:19],name) for rid,ts,name,_ in reports]
        if not choices:self._z_message('Archivio vuoto');return
        def show(d):
            rid=int(d['rapporto'].split(' - ')[0])
            return lambda:self._z_view('Chiusura giornaliera '+str(rid),cassa_report.archived_text(rid),report_id=rid,tipo='CASSA')
        self.popup('Archivio chiusure', [('rapporto','Seleziona chiusura',False,{'choices':choices})],show,'ANTEPRIMA')

    def _backup_interval(self):
        from datetime import date
        def selected(d):
            start,end=d['dal'].strip(),d['al'].strip()
            # Formato ISO; la data di chiusura determina l'intervallo.
            a=date.fromisoformat(start);b=date.fromisoformat(end)
            if a>b:raise ValueError('Data iniziale successiva alla finale')
            return lambda:self._backup_interval_view(start,end)
        today=date.today().isoformat()
        self.popup('Totali chiusure per intervallo', [('dal','Dal (AAAA-MM-GG)',False,today),('al','Al (AAAA-MM-GG)',False,today)],selected,'CALCOLA')

    def _backup_interval_view(self,dal,al):
        import json
        from collections import defaultdict
        import cassa_report
        cassa_report.setup()
        with storage.connect() as c:
            rows=c.execute('SELECT id,momento,dati_json FROM rapporti_cassa WHERE substr(momento,1,10) BETWEEN ? AND ? ORDER BY momento,id',(dal,al)).fetchall()
        rep=defaultdict(lambda:[0,0]);methods={m:0 for m in storage.PAYMENT_METHODS}
        totale=0;fondo=0;transactions=0
        lines=['RIEPILOGO CHIUSURE CASSA','Periodo: {} / {}'.format(dal,al),'Rapporti: {}'.format(len(rows)),'-'*55]
        for rid,momento,raw in rows:
            d=json.loads(raw);totale+=d['totale'];transactions+=d['transazioni'];fondo+=d.get('fondo_apertura_centesimi',0)
            lines.append('N. {:06d}  {}  {}  CHF {:.2f}'.format(rid,momento[:10],d.get('cassa',''),d['totale']/100))
            for x in d['reparti']:
                from decimal import Decimal
                rep[x['nome']][0]+=Decimal(x['qta']);rep[x['nome']][1]+=x['centesimi']
            for x in d['pagamenti']:methods[x['nome']]=methods.get(x['nome'],0)+x['centesimi']
        lines+=['-'*55,'TOTALE VENDITE: CHF {:.2f}'.format(totale/100),'TRANSAZIONI: {}'.format(transactions),'FONDI APERTURA (somma, NON ricavo): CHF {:.2f}'.format(fondo/100),'','REPARTI']
        for name,(qty,amount) in sorted(rep.items()):lines.append('{} | {} | CHF {:.2f}'.format(name,qty,amount/100))
        lines+=['','PAGAMENTI']
        for name,amount in sorted(methods.items()):lines.append('{}: CHF {:.2f}'.format(name,amount/100))
        text='\n'.join(lines)
        self._z_view('Totali per intervallo',text,on_print=lambda:self._print_backup_text(text))

    def _print_backup_text(self,text):
        import sys
        if sys.platform!='win32':raise RuntimeError('Stampa disponibile su Windows')
        from windows_print_job import print_text
        return print_text(text,storage.get_setting('printer') or None,'Kristina - Riepilogo chiusure')

    def _cassa_chiusura_menu(self, cashier_id=None):
        import cassa_report
        choices=[str(i)+' - '+name for i,name in storage.list_casse() if storage.active_turn(i) and (cashier_id is None or storage.active_turn(i)[2]==cashier_id)]
        if not choices:
            self._z_message('Nessuna cassa con turno aperto');return
        def selected(d):
            cid=int(d['cassa'].split(' - ')[0])
            return lambda:self._cassa_chiusura_preview(cid)
        self.popup('Chiusura Cassa - Seleziona',
                   [('cassa','Cassa da chiudere',False,{'choices':choices})],
                   selected,'ANTEPRIMA')

    def _cassa_chiusura_preview(self,cid):
        import cassa_report
        try:
            text=cassa_report.preview(cid)
            self._z_view('ANTEPRIMA CHIUSURA CASSA',text,
                         on_confirm=lambda:cassa_report.close(cid),tipo='CASSA')
        except Exception as exc:self._z_message('Anteprima chiusura cassa: '+str(exc))

    def _archivio_cassa_menu(self):
        import cassa_report
        reports=cassa_report.archive()
        if not reports:
            self._z_message('Archivio chiusure cassa vuoto');return
        choices=['{} - {} - {}'.format(rid,ts[:19],name) for rid,ts,name,_ in reports]
        def selected(d):
            rid=int(d['rapporto'].split(' - ')[0])
            return lambda:self._z_view('Archivio chiusura cassa N. '+str(rid),
                    cassa_report.archived_text(rid),report_id=rid,tipo='CASSA')
        self.popup('Archivio chiusure cassa',
                   [('rapporto','Rapporto registrato',False,{'choices':choices})],
                   selected,'VISUALIZZA')
