# -*- coding: utf-8 -*-
"""Rapporti Z gestionali: anteprima, consolidamento atomico, ristampa snapshot."""
import json, hashlib, datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import storage

def setup():
    storage.init_fondo()
    with storage.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS z_rapporti(
          id INTEGER PRIMARY KEY, cassa_id INTEGER NOT NULL REFERENCES casse(id),
          momento TEXT NOT NULL, apertura_periodo TEXT NOT NULL,
          testo TEXT NOT NULL, dati_json TEXT NOT NULL, sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS z_vendite(
          vendita_id INTEGER PRIMARY KEY REFERENCES vendite(id),
          rapporto_id INTEGER NOT NULL REFERENCES z_rapporti(id));
        CREATE TRIGGER IF NOT EXISTS z_rapporti_no_update BEFORE UPDATE ON z_rapporti
          BEGIN SELECT RAISE(ABORT,'Rapporto Z immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS z_rapporti_no_delete BEFORE DELETE ON z_rapporti
          BEGIN SELECT RAISE(ABORT,'Rapporto Z immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS z_vendite_no_update BEFORE UPDATE ON z_vendite
          BEGIN SELECT RAISE(ABORT,'Associazione Z immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS z_vendite_no_delete BEFORE DELETE ON z_vendite
          BEGIN SELECT RAISE(ABORT,'Associazione Z immutabile'); END;
        ''')

def _money(n):return 'CHF {:.2f}'.format(Decimal(n)/100)
def _qty(v):
    try:return Decimal(str(v))
    except (InvalidOperation,TypeError):return Decimal(0)
def _text(data):
    width=54
    lines=[]
    h=data['intestazione']
    lines += [x for x in [h.get('negozio'),h.get('indirizzo'),('P.IVA / UID: '+h['piva']) if h.get('piva') else '',('Tel: '+h['telefono']) if h.get('telefono') else ''] if x]
    lines += ['', 'RESOCONTO VENDITE - CHIUSURA Z', 'Rapporto N. {:06d}  Cassa: {}'.format(data['numero'],data['cassa']),
              'Periodo: {} / {}'.format(data['dal'][:19],data['al'][:19]),
              'Emissione: '+data['emissione'][:19], '-'*width,
              'REPARTI / SETTORI', '{:<29} {:>7} {:>16}'.format('Reparto','Qta','Totale')]
    for d in data['reparti']:
        lines.append('{:<29} {:>7} {:>16}'.format(d['nome'][:29],str(d['qta']),_money(d['centesimi'])))
    lines += ['-'*width,'TOTALE VENDITE {:>36}'.format(_money(data['totale'])),
              'Transazioni: {}'.format(data['transazioni']), '', 'MEZZI DI PAGAMENTO']
    for p in data['pagamenti']:
        lines.append('{:<35} {:>18}'.format(p['nome'][:35],_money(p['centesimi'])))
    lines += ['-'*width, 'TOTALE PAGAMENTI {:>34}'.format(_money(data['pagato'])),
              'DIFFERENZA {:>42}'.format(_money(data['totale']-data['pagato'])),
              '', 'IVA: dati per aliquota non disponibili nelle vendite',
              'Resi / storni / sconti: non registrati',
              'FONDO CASSA INIZIALE {:>30}'.format(_money(data.get('fondo_apertura_centesimi',0))),
              'FONDO + INCASSI CONTANTI {:>27}'.format(_money(data.get('fondo_apertura_centesimi',0)+next((p['centesimi'] for p in data['pagamenti'] if p['nome']=='CASH'),0))),
              'Documento gestionale - verificare requisiti fiscali',
              'Identificativo cassa: {}'.format(data['cassa_id'])]
    return '\n'.join(lines)

def _build(c,cid,number):
    ca=c.execute('SELECT nome FROM casse WHERE id=?',(cid,)).fetchone()
    if not ca:raise ValueError('Cassa inesistente')
    rows=c.execute('''SELECT v.id,v.momento,v.metodo,v.totale_centesimi,v.righe_json
      FROM vendite v JOIN turni t ON t.id=v.turno_id
      LEFT JOIN z_vendite zv ON zv.vendita_id=v.id
      WHERE t.cassa_id=? AND zv.vendita_id IS NULL
        AND NOT EXISTS(SELECT 1 FROM chiusure_z old WHERE old.turno_id=t.id)
      ORDER BY v.id''',(cid,)).fetchall()
    if not rows:raise ValueError('Nessuna vendita non ancora chiusa per questa cassa')
    rep=defaultdict(lambda:[Decimal(0),0]); payments=defaultdict(int, {method:0 for method in storage.PAYMENT_METHODS})
    for sid,ts,method,total,items_json in rows:
        payments[method or 'Non specificato']+=total
        try: items=json.loads(items_json)
        except (ValueError,TypeError):items=[]
        if not isinstance(items,list):items=[]
        for item in items:
            if not isinstance(item,dict):continue
            name=str(item.get('nome') or item.get('reparto') or 'Non categorizzato')
            qty=_qty(item.get('qta',0)); price=_qty(item.get('prezzo',0))
            if qty<=0 or price<0:continue
            rep[name][0]+=qty
            rep[name][1]+=storage.cents(qty*price)
    total=sum(x[3] for x in rows)
    headrow=c.execute('SELECT negozio,indirizzo,piva,telefono,qr_testo FROM intestazioni WHERE cassa_id=?',(cid,)).fetchone()
    header=dict(zip(('negozio','indirizzo','piva','telefono','qr_testo'),headrow or ('','','','','')))
    opening=c.execute('SELECT MIN(t.apertura) FROM turni t JOIN vendite v ON v.turno_id=t.id WHERE v.id IN ({})'.format(','.join('?' for _ in rows)),[r[0] for r in rows]).fetchone()[0]
    data={'numero':number,'cassa_id':cid,'cassa':ca[0],'intestazione':header,
          'dal':opening or rows[0][1], 'al':rows[-1][1], 'emissione':storage.now(),
          'transazioni':len(rows),'totale':total,'pagato':sum(payments.values()),
          'reparti':[{'nome':n,'qta':str(v[0]),'centesimi':v[1]} for n,v in sorted(rep.items())],
          'pagamenti':[{'nome':n,'centesimi':v} for n,v in sorted(payments.items())],
          'vendite_ids':[r[0] for r in rows], 'fondo_apertura_centesimi':sum(storage.fondo_turno(c,r[0]) for r in c.execute('SELECT DISTINCT v.turno_id FROM vendite v WHERE v.id IN ({})'.format(','.join('?' for _ in rows)),[r[0] for r in rows]).fetchall())}
    return data,_text(data)

def preview(cid):
    setup()
    with storage.connect() as c:
        number=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM z_rapporti').fetchone()[0]
        return _build(c,cid,number)[1]

def close(cid):
    setup()
    with storage.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if not storage.verify():raise ValueError('Integrita del registro movimenti non valida')
        number=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM z_rapporti').fetchone()[0]
        data,txt=_build(c,cid,number)
        raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256((raw+'\n'+txt).encode('utf-8')).hexdigest()
        rid=c.execute('INSERT INTO z_rapporti(id,cassa_id,momento,apertura_periodo,testo,dati_json,sha256) VALUES(?,?,?,?,?,?,?)',
            (number,cid,data['emissione'],data['dal'],txt,raw,digest)).lastrowid
        c.executemany('INSERT INTO z_vendite(vendita_id,rapporto_id) VALUES(?,?)',[(x,rid) for x in data['vendite_ids']])
        # Chiusura del turno operativo corrente della cassa.
        c.execute("UPDATE turni SET chiusura=?,stato='CHIUSO' WHERE cassa_id=? AND stato='APERTO'",(storage.now(),cid))
        storage.log(c,'RAPPORTO_Z',rid,{'cassa_id':cid,'totale_centesimi':data['totale'],'vendite':data['transazioni'],'sha256':digest})
    return rid

def archive():
    setup()
    with storage.connect() as c:
        return c.execute('SELECT z.id,z.momento,c.nome,z.sha256 FROM z_rapporti z JOIN casse c ON c.id=z.cassa_id ORDER BY z.id DESC').fetchall()

def archived_text(rid):
    setup()
    with storage.connect() as c:
        row=c.execute('SELECT testo,dati_json,sha256 FROM z_rapporti WHERE id=?',(rid,)).fetchone()
    if not row:raise ValueError('Rapporto Z non trovato')
    txt,raw,digest=row
    if hashlib.sha256((raw+'\n'+txt).encode('utf-8')).hexdigest()!=digest:
        raise ValueError('Integrita del rapporto Z compromessa')
    return txt

def print_z(rid):
    import sys, os
    txt=archived_text(rid)
    if sys.platform.startswith('win'):
        from windows_print_job import print_text
        return print_text(txt,storage.get_setting('printer') or None,'Kristina - Rapporto Z {}'.format(rid))
    try:
        from kivy.utils import platform
    except ImportError:platform=sys.platform
    if platform=='android':
        if storage.get_setting('android_rawbt')!='1':raise RuntimeError('Abilitare RawBT nel Setup')
        from jnius import autoclass
        Intent=autoclass('android.content.Intent'); PythonActivity=autoclass('org.kivy.android.PythonActivity')
        intent=Intent(Intent.ACTION_SEND);intent.setType('text/plain');intent.putExtra(Intent.EXTRA_TEXT,txt)
        intent.setPackage('ru.a402d.rawbtprinter');PythonActivity.mActivity.startActivity(intent)
        return 'RawBT'
    raise RuntimeError('Stampa Z non configurata per questo sistema operativo')
