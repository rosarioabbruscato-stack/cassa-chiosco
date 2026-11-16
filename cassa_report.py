# -*- coding: utf-8 -*-
"""Chiusura di un singolo turno cassa, distinta dalla chiusura giornaliera Z."""
import json, hashlib, sys
from collections import defaultdict
from decimal import Decimal
import storage, z_report

def setup():
    storage.init_fondo()
    with storage.connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS rapporti_cassa(
          id INTEGER PRIMARY KEY, turno_id INTEGER NOT NULL UNIQUE REFERENCES turni(id),
          cassa_id INTEGER NOT NULL REFERENCES casse(id), momento TEXT NOT NULL,
          testo TEXT NOT NULL, dati_json TEXT NOT NULL, sha256 TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS rapporti_cassa_no_update BEFORE UPDATE ON rapporti_cassa
          BEGIN SELECT RAISE(ABORT,'Rapporto chiusura cassa immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS rapporti_cassa_no_delete BEFORE DELETE ON rapporti_cassa
          BEGIN SELECT RAISE(ABORT,'Rapporto chiusura cassa immutabile'); END;
        """)

def _build(c,cid,number):
    t=c.execute("SELECT id,apertura FROM turni WHERE cassa_id=? AND stato='APERTO'",(cid,)).fetchone()
    if not t:raise ValueError('Nessun turno aperto per questa cassa')
    tid,opening=t
    name=c.execute('SELECT nome FROM casse WHERE id=?',(cid,)).fetchone()[0]
    rows=c.execute('SELECT id,momento,metodo,totale_centesimi,righe_json FROM vendite WHERE turno_id=? ORDER BY id',(tid,)).fetchall()
    rep=defaultdict(lambda:[Decimal(0),0]);payments=defaultdict(int, {method:0 for method in storage.PAYMENT_METHODS})
    for sale_id,ts,method,total,raw in rows:
        payments[method or 'Non specificato']+=total
        try:items=json.loads(raw)
        except (ValueError,TypeError):items=[]
        if not isinstance(items,list):items=[]
        for item in items:
            if not isinstance(item,dict):continue
            name_rep=str(item.get('reparto') or item.get('nome') or 'Non categorizzato')
            qty=z_report._qty(item.get('qta',0));price=z_report._qty(item.get('prezzo',0))
            if qty<=0 or price<0:continue
            rep[name_rep][0]+=qty
            rep[name_rep][1]+=storage.cents(qty*price)
    h=c.execute('SELECT negozio,indirizzo,piva,telefono,qr_testo FROM intestazioni WHERE cassa_id=?',(cid,)).fetchone()
    header=dict(zip(('negozio','indirizzo','piva','telefono','qr_testo'),h or ('','','','','')))
    data={'numero':number,'turno_id':tid,'cassa_id':cid,'cassa':name,'intestazione':header,
          'dal':opening,'al':storage.now(),'emissione':storage.now(),
          'transazioni':len(rows),'totale':sum(r[3] for r in rows),
          'pagato':sum(payments.values()),
          'reparti':[{'nome':n,'qta':str(v[0]),'centesimi':v[1]} for n,v in sorted(rep.items())],
          'pagamenti':[{'nome':n,'centesimi':v} for n,v in sorted(payments.items())],
          'vendite_ids':[r[0] for r in rows], 'fondo_apertura_centesimi':storage.fondo_turno(c,tid)}
    text=z_report._text(data).replace('RESOCONTO VENDITE - CHIUSURA Z','RESOCONTO VENDITE - CHIUSURA CASSA').replace('Rapporto N.', 'Chiusura turno N.')
    return data,text

def preview(cid):
    setup()
    with storage.connect() as c:
        number=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM rapporti_cassa').fetchone()[0]
        return _build(c,cid,number)[1]

def close(cid):
    setup()
    with storage.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if not storage.verify():raise ValueError('Integrita registro movimenti non valida')
        number=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM rapporti_cassa').fetchone()[0]
        data,txt=_build(c,cid,number)
        raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256((raw+'\n'+txt).encode('utf-8')).hexdigest()
        rid=c.execute('INSERT INTO rapporti_cassa(id,turno_id,cassa_id,momento,testo,dati_json,sha256) VALUES(?,?,?,?,?,?,?)',
                      (number,data['turno_id'],cid,data['emissione'],txt,raw,digest)).lastrowid
        if c.execute("UPDATE turni SET chiusura=?,stato='CHIUSO' WHERE id=? AND stato='APERTO'",(data['emissione'],data['turno_id'])).rowcount!=1:
            raise ValueError('Turno gia chiuso')
        storage.log(c,'CHIUSURA_CASSA',rid,{'turno_id':data['turno_id'],'cassa_id':cid,'totale_centesimi':data['totale'],'sha256':digest})
    return rid

def archive():
    setup()
    with storage.connect() as c:
        return c.execute('SELECT r.id,r.momento,c.nome,r.sha256 FROM rapporti_cassa r JOIN casse c ON c.id=r.cassa_id ORDER BY r.id DESC').fetchall()

def archived_text(rid):
    setup()
    with storage.connect() as c:
        row=c.execute('SELECT testo,dati_json,sha256 FROM rapporti_cassa WHERE id=?',(rid,)).fetchone()
    if not row:raise ValueError('Rapporto chiusura cassa non trovato')
    txt,raw,digest=row
    if hashlib.sha256((raw+'\n'+txt).encode('utf-8')).hexdigest()!=digest:
        raise ValueError('Integrita rapporto chiusura cassa compromessa')
    return txt

def print_report(rid):
    txt=archived_text(rid)
    if sys.platform=='win32':
        from windows_print_job import print_text
        return print_text(txt,storage.get_setting('printer') or None,'Kristina - Chiusura Cassa {}'.format(rid))
    from kivy.utils import platform
    if platform=='android':
        if storage.get_setting('android_rawbt')!='1':raise RuntimeError('Abilitare RawBT nel Setup')
        from jnius import autoclass
        Intent=autoclass('android.content.Intent');PythonActivity=autoclass('org.kivy.android.PythonActivity')
        intent=Intent(Intent.ACTION_SEND);intent.setType('text/plain');intent.putExtra(Intent.EXTRA_TEXT,txt)
        intent.setPackage('ru.a402d.rawbtprinter');PythonActivity.mActivity.startActivity(intent)
        return 'RawBT'
    raise RuntimeError('Stampa non configurata per questo sistema')
