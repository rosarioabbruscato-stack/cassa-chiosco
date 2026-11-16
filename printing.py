# -*- coding: utf-8 -*-
"""Preparazione scontrino gestionale. Stampa di sistema via dialogo, RawBT su Android."""
import json, sys, os, tempfile, subprocess
import storage

def receipt(sale_id):
    sale=storage.sale_details(sale_id)
    if not sale:raise ValueError('Vendita non trovata')
    ident,momento,metodo,totale,ricevuto,resto,items,cid,cassa= sale
    h=storage.get_header(cid)
    head='\n'.join(x for x in (h['negozio'],h['indirizzo'],'P.IVA: '+h['piva'] if h['piva'] else '', 'Tel: '+h['telefono'] if h['telefono'] else '') if x)
    from receipt_layout import format_receipt_lines
    details=format_receipt_lines(ident, momento, cassa, json.loads(items),
                                 totale/100, metodo, ricevuto/100, resto/100)
    qr=h['qr_testo']
    qrblock='QR: '+qr if qr else ''
    sections={'Intestazione':head,'Articoli':'\n'.join(details),'QR':qrblock}
    order=storage.get_setting('print_order','Intestazione > Articoli > QR').split(' > ')
    return '\n\n'.join(sections[x] for x in order if sections.get(x))

def send(sale_id):
    text=receipt(sale_id)
    try:
        from kivy.utils import platform
    except ImportError:
        platform=sys.platform
    if platform=='android':
        if storage.get_setting('android_rawbt')!='1':raise RuntimeError('Abilitare RawBT nel Setup')
        # RawBT: intento testo condiviso, l'utente conferma la stampante nell'app.
        from jnius import autoclass
        Intent=autoclass('android.content.Intent')
        PythonActivity=autoclass('org.kivy.android.PythonActivity')
        intent=Intent(Intent.ACTION_SEND)
        intent.setType('text/plain')
        intent.putExtra(Intent.EXTRA_TEXT,text)
        intent.setPackage('ru.a402d.rawbtprinter')
        PythonActivity.mActivity.startActivity(intent)
        return 'Scontrino inviato a RawBT'
    if sys.platform.startswith('win'):
        from windows_print_job import print_text
        printer = storage.get_setting('printer') or None
        selected = print_text(text, printer)
        return 'Documento inviato alla coda di stampa: ' + selected
    # Per piattaforme desktop non Windows, prepara il documento senza inviarlo.
    fd,path=tempfile.mkstemp(prefix='kristina_scontrino_',suffix='.txt')
    with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(text)
    raise RuntimeError('Scontrino preparato in '+path+'; stampa automatica non configurata')
