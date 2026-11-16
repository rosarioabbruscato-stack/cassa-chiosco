# -*- coding: utf-8 -*-
"""Archivio SQLite centralizzato e giornale append-only applicativo."""
import os, sqlite3, json, hashlib, datetime, shutil
from decimal import Decimal, ROUND_HALF_UP
ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, 'Kristina_DB.sqlite3')
BACKUPS = os.path.join(ROOT, 'backup')
PAYMENT_METHODS = ('CASH', 'CARTA', 'TWINT')

def now(): return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def connect():
    c = sqlite3.connect(DB, timeout=15)
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=15000')
    return c

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS casse(id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE, attiva INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sospensioni_cassa(cassa_id INTEGER PRIMARY KEY REFERENCES casse(id), sospesa INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS cassieri(id INTEGER PRIMARY KEY, nome_hash TEXT NOT NULL UNIQUE, attivo INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS turni(id INTEGER PRIMARY KEY, cassa_id INTEGER NOT NULL REFERENCES casse(id), cassiere_id INTEGER NOT NULL REFERENCES cassieri(id), apertura TEXT NOT NULL, chiusura TEXT, stato TEXT NOT NULL CHECK(stato IN ('APERTO','CHIUSO')));
        CREATE UNIQUE INDEX IF NOT EXISTS turno_cassa_aperto ON turni(cassa_id) WHERE stato='APERTO';
        CREATE TABLE IF NOT EXISTS vendite(id INTEGER PRIMARY KEY, turno_id INTEGER NOT NULL REFERENCES turni(id), momento TEXT NOT NULL, metodo TEXT NOT NULL, totale_centesimi INTEGER NOT NULL CHECK(totale_centesimi>0), ricevuto_centesimi INTEGER NOT NULL, resto_centesimi INTEGER NOT NULL, righe_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS movimenti(id INTEGER PRIMARY KEY, momento TEXT NOT NULL, tipo TEXT NOT NULL, riferimento TEXT NOT NULL, dettagli TEXT NOT NULL, hash_precedente TEXT NOT NULL, hash_corrente TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chiusure_z(id INTEGER PRIMARY KEY, turno_id INTEGER NOT NULL UNIQUE REFERENCES turni(id), momento TEXT NOT NULL, totale_centesimi INTEGER NOT NULL, vendite INTEGER NOT NULL);
        CREATE TRIGGER IF NOT EXISTS movimenti_no_update BEFORE UPDATE ON movimenti BEGIN SELECT RAISE(ABORT,'Registro immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS movimenti_no_delete BEFORE DELETE ON movimenti BEGIN SELECT RAISE(ABORT,'Registro immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS vendite_no_update BEFORE UPDATE ON vendite BEGIN SELECT RAISE(ABORT,'Vendita immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS vendite_no_delete BEFORE DELETE ON vendite BEGIN SELECT RAISE(ABORT,'Vendita immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS chiusure_no_update BEFORE UPDATE ON chiusure_z BEGIN SELECT RAISE(ABORT,'Chiusura immutabile'); END;
        CREATE TRIGGER IF NOT EXISTS chiusure_no_delete BEFORE DELETE ON chiusure_z BEGIN SELECT RAISE(ABORT,'Chiusura immutabile'); END;
        ''')

def migrate_legacy():
    """Progetto nuovo: nessuna migrazione da archivi precedenti."""
    return

def cents(v): return int((Decimal(str(v))*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
def log(c, tipo, ref, dettagli):
    prev = c.execute('SELECT hash_corrente FROM movimenti ORDER BY id DESC LIMIT 1').fetchone()
    previous = prev[0] if prev else '0'*64
    timestamp = now()
    payload = json.dumps([timestamp,tipo,str(ref),dettagli,previous],ensure_ascii=False,sort_keys=True,separators=(',',':'))
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    c.execute('INSERT INTO movimenti(momento,tipo,riferimento,dettagli,hash_precedente,hash_corrente) VALUES(?,?,?,?,?,?)',(timestamp,tipo,str(ref),json.dumps(dettagli,ensure_ascii=False,sort_keys=True,separators=(',',':')),previous,digest))

def verify():
    with connect() as c:
        prev='0'*64
        for ts,typ,ref,detail,p,h in c.execute('SELECT momento,tipo,riferimento,dettagli,hash_precedente,hash_corrente FROM movimenti ORDER BY id'):
            d=json.loads(detail)
            payload=json.dumps([ts,typ,ref,d,prev],ensure_ascii=False,sort_keys=True,separators=(',',':'))
            if p!=prev or hashlib.sha256(payload.encode()).hexdigest()!=h: return False
            prev=h
    return True

def list_casse(active_only=True):
    with connect() as c: return c.execute('SELECT id,nome FROM casse WHERE attiva=1 ORDER BY nome' if active_only else 'SELECT id,nome FROM casse ORDER BY nome').fetchall()
def save_cassa(name, cid=None):
    name=name.strip()
    if not name: raise ValueError('Nome cassa obbligatorio')
    with connect() as c:
        if cid:
            c.execute('UPDATE casse SET nome=?,attiva=1 WHERE id=?',(name,cid)); ref=cid; typ='CASSA_MODIFICATA'
        else:
            ref=c.execute('INSERT INTO casse(nome) VALUES(?)',(name,)).lastrowid; typ='CASSA_CREATA'
        log(c,typ,ref,{'nome':name})
def disable_cassa(cid):
    with connect() as c:
        if c.execute("SELECT 1 FROM turni WHERE cassa_id=? AND stato='APERTO'",(cid,)).fetchone(): raise ValueError('Cassa con turno aperto')
        c.execute('UPDATE casse SET attiva=0 WHERE id=?',(cid,)); log(c,'CASSA_DISATTIVATA',cid,{})
def save_cassiere(namehash, cid=None):
    with connect() as c:
        if cid:
            c.execute('UPDATE cassieri SET nome_hash=?,attivo=1 WHERE id=?',(namehash,cid)); typ='CASSIERE_MODIFICATO'; ref=cid
        else:
            ref=c.execute('INSERT INTO cassieri(nome_hash) VALUES(?)',(namehash,)).lastrowid; typ='CASSIERE_CREATO'
        log(c,typ,ref,{})
def disable_cassiere(cid):
    with connect() as c:
        if c.execute("SELECT 1 FROM turni WHERE cassiere_id=? AND stato='APERTO'",(cid,)).fetchone(): raise ValueError('Cassiere con turno aperto')
        c.execute('UPDATE cassieri SET attivo=0 WHERE id=?',(cid,));log(c,'CASSIERE_DISATTIVATO',cid,{})
def list_cassieri():
    with connect() as c: return c.execute('SELECT id,nome_hash FROM cassieri WHERE attivo=1 ORDER BY id').fetchall()
def active_turn(cassa_id=None):
    with connect() as c:
        sql="SELECT t.id,t.cassa_id,t.cassiere_id,t.apertura FROM turni t WHERE t.stato='APERTO'"
        return c.execute(sql+(' AND t.cassa_id=?' if cassa_id else ' ORDER BY t.id DESC LIMIT 1'),(cassa_id,) if cassa_id else ()).fetchone()
def last_turn(cassa_id):
    """Ultimo turno registrato, inclusi apertura e chiusura persistenti."""
    with connect() as c:
        return c.execute('SELECT id,cassa_id,cassiere_id,apertura,chiusura,stato FROM turni WHERE cassa_id=? ORDER BY id DESC LIMIT 1',(cassa_id,)).fetchone()

def init_fondo():
    with connect() as c:
        cols=[r[1] for r in c.execute('PRAGMA table_info(turni)')]
        if 'fondo_apertura_centesimi' not in cols:
            c.execute('ALTER TABLE turni ADD COLUMN fondo_apertura_centesimi INTEGER NOT NULL DEFAULT 0')

def fondo_turno(c,tid):
    return c.execute('SELECT fondo_apertura_centesimi FROM turni WHERE id=?',(tid,)).fetchone()[0]

def open_turn(cassa_id,cassiere_id,fondo=0):
    init_fondo()
    fondo_c=cents(fondo)
    if fondo_c<0:raise ValueError('Il fondo cassa non puo essere negativo')
    with connect() as c:
        if not c.execute('SELECT 1 FROM casse WHERE id=? AND attiva=1',(cassa_id,)).fetchone(): raise ValueError('Cassa non attiva')
        if not c.execute('SELECT 1 FROM cassieri WHERE id=? AND attivo=1',(cassiere_id,)).fetchone(): raise ValueError('Cassiere non attivo')
        ref=c.execute("INSERT INTO turni(cassa_id,cassiere_id,apertura,stato,fondo_apertura_centesimi) VALUES(?,?,?,'APERTO',?)",(cassa_id,cassiere_id,now(),fondo_c)).lastrowid
        c.execute('INSERT OR REPLACE INTO sospensioni_cassa(cassa_id,sospesa) VALUES(?,0)',(cassa_id,))
        log(c,'APERTURA_TURNO',ref,{'cassa_id':cassa_id,'cassiere_id':cassiere_id,'fondo_apertura_centesimi':fondo_c})
        return ref
def close_turn(tid):
    with connect() as c:
        if c.execute("UPDATE turni SET chiusura=?,stato='CHIUSO' WHERE id=? AND stato='APERTO'",(now(),tid)).rowcount!=1: raise ValueError('Turno non aperto')
        c.execute('UPDATE sospensioni_cassa SET sospesa=0 WHERE cassa_id=(SELECT cassa_id FROM turni WHERE id=?)',(tid,))
        log(c,'CHIUSURA_TURNO',tid,{})
def sale(tid, method, items, total, received):
    total_c=cents(total); received_c=cents(received)
    if total_c<=0 or received_c<total_c: raise ValueError('Pagamento non valido')
    with connect() as c:
        if not c.execute("SELECT 1 FROM turni WHERE id=? AND stato='APERTO'",(tid,)).fetchone(): raise ValueError('Aprire un turno prima della vendita')
        if c.execute('SELECT sospesa FROM sospensioni_cassa WHERE cassa_id=(SELECT cassa_id FROM turni WHERE id=?)',(tid,)).fetchone() == (1,): raise ValueError('Cassa sospesa')
        # Controllo e scarico delle giacenze nella medesima transazione della vendita.
        needs={}
        for item in items:
            bc=str(item.get('barcode') or '').strip()
            if bc:
                qty=int(item.get('qta',0))
                if qty<=0: raise ValueError('Quantita articolo non valida')
                needs[bc]=needs.get(bc,0)+qty
        for bc,qty in needs.items():
            art=c.execute('SELECT id,giacenza FROM Articoli WHERE barcode=?',(bc,)).fetchone()
            if not art or art[1]<qty: raise ValueError('Articolo assente o giacenza insufficiente: '+bc)
            c.execute('UPDATE Articoli SET giacenza=giacenza-? WHERE id=?',(qty,art[0]))
            c.execute('INSERT INTO Movimenti_Magazzino(articolo_id,momento,tipo,quantita,causale) VALUES(?,?,?,?,?)',
                      (art[0],now(),'SCARICO',-qty,'VENDITA'))
        ref=c.execute('INSERT INTO vendite(turno_id,momento,metodo,totale_centesimi,ricevuto_centesimi,resto_centesimi,righe_json) VALUES(?,?,?,?,?,?,?)',(tid,now(),method,total_c,received_c,received_c-total_c,json.dumps(items,ensure_ascii=False))).lastrowid
        for idx,item in enumerate(items,1):
            bc=str(item.get('barcode') or '').strip()
            art_id=c.execute('SELECT id FROM Articoli WHERE barcode=?',(bc,)).fetchone() if bc else None
            c.execute('INSERT INTO Dettagli_Vendita(vendita_id,riga,articolo_id,descrizione,quantita,prezzo_centesimi) VALUES(?,?,?,?,?,?)',
                      (ref,idx,art_id[0] if art_id else None,str(item.get('nome','')),int(item['qta']),cents(item['prezzo'])))
        c.execute('INSERT INTO Pagamenti(vendita_id,metodo,importo_centesimi) VALUES(?,?,?)',(ref,method,total_c))
        c.execute("UPDATE Movimenti_Magazzino SET vendita_id=? WHERE vendita_id IS NULL AND causale='VENDITA' AND articolo_id IN (SELECT articolo_id FROM Dettagli_Vendita WHERE vendita_id=?)",(ref,ref))
        log(c,'VENDITA',ref,{'turno_id':tid,'metodo':method,'totale_centesimi':total_c,'righe':items})
        return ref
def history():
    with connect() as c: return c.execute('SELECT v.momento,c.nome,v.metodo,v.totale_centesimi,v.id FROM vendite v JOIN turni t ON t.id=v.turno_id JOIN casse c ON c.id=t.cassa_id ORDER BY v.id DESC LIMIT 300').fetchall()
def daily_total():
    with connect() as c: return c.execute("SELECT COALESCE(SUM(totale_centesimi),0) FROM vendite WHERE substr(momento,1,10)=?",(datetime.date.today().isoformat(),)).fetchone()[0]
def z_close(tid):
    with connect() as c:
        if not c.execute("SELECT 1 FROM turni WHERE id=? AND stato='APERTO'",(tid,)).fetchone(): raise ValueError('Turno non aperto')
        total,count=c.execute('SELECT COALESCE(SUM(totale_centesimi),0),COUNT(*) FROM vendite WHERE turno_id=?',(tid,)).fetchone()
        c.execute('INSERT INTO chiusure_z(turno_id,momento,totale_centesimi,vendite) VALUES(?,?,?,?)',(tid,now(),total,count))
        c.execute("UPDATE turni SET chiusura=?,stato='CHIUSO' WHERE id=?",(now(),tid))
        log(c,'CHIUSURA_Z',tid,{'totale_centesimi':total,'vendite':count})
        return total,count
def init_articles():
    """Schema relazionale: niente magazzino JSON, niente dati iniziali."""
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS Reparti(id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS Articoli(
            id INTEGER PRIMARY KEY, barcode TEXT UNIQUE, nome TEXT NOT NULL,
            prezzo_centesimi INTEGER NOT NULL CHECK(prezzo_centesimi>=0),
            giacenza REAL NOT NULL DEFAULT 0 CHECK(giacenza>=0),
            reparto_id INTEGER REFERENCES Reparti(id), lotto TEXT NOT NULL DEFAULT '',
            scadenza TEXT NOT NULL DEFAULT '', foto TEXT NOT NULL DEFAULT '',
            allerta TEXT NOT NULL DEFAULT '', colore TEXT NOT NULL DEFAULT '#333333',
            posizione TEXT NOT NULL DEFAULT 'Reparto 1');
        CREATE TABLE IF NOT EXISTS Movimenti_Magazzino(
            id INTEGER PRIMARY KEY, articolo_id INTEGER NOT NULL REFERENCES Articoli(id),
            momento TEXT NOT NULL, tipo TEXT NOT NULL CHECK(tipo IN ('CARICO','SCARICO','RETTIFICA')),
            quantita REAL NOT NULL, causale TEXT NOT NULL,
            vendita_id INTEGER REFERENCES vendite(id));
        CREATE TABLE IF NOT EXISTS Dettagli_Vendita(
            vendita_id INTEGER NOT NULL REFERENCES vendite(id),riga INTEGER NOT NULL,
            articolo_id INTEGER REFERENCES Articoli(id),descrizione TEXT NOT NULL,
            quantita REAL NOT NULL CHECK(quantita>0),prezzo_centesimi INTEGER NOT NULL,
            PRIMARY KEY(vendita_id,riga));
        CREATE TABLE IF NOT EXISTS Pagamenti(
            id INTEGER PRIMARY KEY,vendita_id INTEGER NOT NULL REFERENCES vendite(id),
            metodo TEXT NOT NULL CHECK(metodo IN ('CASH','CARTA','TWINT')),
            importo_centesimi INTEGER NOT NULL CHECK(importo_centesimi>=0));
        CREATE INDEX IF NOT EXISTS idx_articoli_reparto ON Articoli(reparto_id);
        CREATE INDEX IF NOT EXISTS idx_movimenti_articolo ON Movimenti_Magazzino(articolo_id);
        """)

def _ensure_photo_column():
    with connect() as c:
        columns = {r[1] for r in c.execute('PRAGMA table_info(Articoli)')}
        if 'foto_blob' not in columns:
            c.execute('ALTER TABLE Articoli ADD COLUMN foto_blob BLOB')

def _photo_from_blob(article_id, blob):
    """Materializza una copia di visualizzazione; l'originale resta nel DB."""
    if not blob:
        return ''
    directory = os.path.join(ROOT, 'cache_foto')
    os.makedirs(directory, exist_ok=True)
    signature = hashlib.sha256(blob).hexdigest()[:20]
    if blob.startswith(b'\xff\xd8\xff'):
        extension = '.jpg'
    elif blob.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = '.png'
    elif blob[:4] == b'GIF8':
        extension = '.gif'
    else:
        extension = '.img'
    path = os.path.join(directory, '{}_{}{}'.format(article_id, signature, extension))
    if not os.path.isfile(path) or os.path.getsize(path) != len(blob):
        temporary = path + '.tmp'
        with open(temporary, 'wb') as handle:
            handle.write(blob)
        os.replace(temporary, path)
    return path

def _article_dict(r):
    return {'id':r[0],'barcode':r[1] or '', 'nome':r[2], 'prezzo':r[3]/100,
            'giac':r[4], 'cat':r[5] or 'Generale', 'lotto':r[6],
            'scad':r[7], 'foto':(_photo_from_blob(r[0], r[12]) if len(r)>12 and r[12] else (r[8] or '')), 'allerta':r[9],
            'colore':r[10], 'pos':r[11], 'selezionato':False}

_ARTICLE_QUERY="SELECT a.id,a.barcode,a.nome,a.prezzo_centesimi,a.giacenza,r.nome,a.lotto,a.scadenza,a.foto,a.allerta,a.colore,a.posizione,a.foto_blob FROM Articoli a LEFT JOIN Reparti r ON a.reparto_id=r.id"

def article_by_barcode(code):
    _ensure_photo_column()
    with connect() as c:
        r=c.execute(_ARTICLE_QUERY+' WHERE a.barcode=?',(str(code).strip(),)).fetchone()
        return _article_dict(r) if r else None

def load_inventory():
    _ensure_photo_column()
    with connect() as c:
        return [_article_dict(r) for r in c.execute(_ARTICLE_QUERY+' ORDER BY a.nome,a.id')]

def save_inventory(items):
    """Salva righe senza cancellare gli ID referenziati dalle vendite."""
    with connect() as c:
        ids=set()
        codes=set()
        for art in items:
            name=str(art.get('nome','')).strip()
            if not name: raise ValueError('Nome articolo obbligatorio')
            code=str(art.get('barcode','')).strip() or None
            if code and code in codes: raise ValueError('Barcode duplicato: '+code)
            if code: codes.add(code)
            giac=float(art.get('giac',0));prezzo=cents(art.get('prezzo',0))
            if giac<0 or prezzo<0: raise ValueError('Giacenza o prezzo negativo')
            reparto=str(art.get('cat') or 'Generale').strip()
            c.execute('INSERT OR IGNORE INTO Reparti(nome) VALUES(?)',(reparto,))
            rid=c.execute('SELECT id FROM Reparti WHERE nome=?',(reparto,)).fetchone()[0]
            aid=art.get('id')
            old=c.execute('SELECT giacenza FROM Articoli WHERE id=?',(aid,)).fetchone() if aid else None
            values=(code,name,prezzo,giac,rid,str(art.get('lotto','')),
                    str(art.get('scad','')),str(art.get('foto','')),
                    str(art.get('allerta','')),str(art.get('colore','#333333')),
                    str(art.get('pos','Reparto 1')))
            if old:
                c.execute("""UPDATE Articoli SET barcode=?,nome=?,prezzo_centesimi=?,giacenza=?,
                    reparto_id=?,lotto=?,scadenza=?,foto=?,allerta=?,colore=?,posizione=? WHERE id=?""",values+(aid,))
            else:
                # Durante importazioni successive un barcode identifica sempre lo stesso articolo.
                found=c.execute('SELECT id,giacenza FROM Articoli WHERE barcode=?',(code,)).fetchone() if code else None
                if found:
                    aid=found[0];old=(found[1],)
                    c.execute("""UPDATE Articoli SET barcode=?,nome=?,prezzo_centesimi=?,giacenza=?,
                        reparto_id=?,lotto=?,scadenza=?,foto=?,allerta=?,colore=?,posizione=? WHERE id=?""",values+(aid,))
                else:
                    aid=c.execute("""INSERT INTO Articoli(barcode,nome,prezzo_centesimi,giacenza,reparto_id,
                        lotto,scadenza,foto,allerta,colore,posizione) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",values).lastrowid
            ids.add(aid)
            if old is None or old[0]!=giac:
                delta=giac-(old[0] if old else 0)
                c.execute('INSERT INTO Movimenti_Magazzino(articolo_id,momento,tipo,quantita,causale) VALUES(?,?,?,?,?)',
                          (aid,now(),'CARICO' if delta>0 else 'RETTIFICA',delta,'INVENTARIO'))
        for (aid,) in c.execute('SELECT id FROM Articoli').fetchall():
            if aid not in ids:
                # Conserva la storia: eliminazione consentita solo per articoli mai venduti.
                if c.execute('SELECT 1 FROM Dettagli_Vendita WHERE articolo_id=?',(aid,)).fetchone():
                    raise ValueError('Impossibile eliminare articolo con vendite: '+str(aid))
                c.execute('DELETE FROM Movimenti_Magazzino WHERE articolo_id=?',(aid,))
                c.execute('DELETE FROM Articoli WHERE id=?',(aid,))
        log(c,'MAGAZZINO_SALVATO','articoli',{'articoli':len(items)})

def backup():
    if not verify(): raise ValueError('Integrita registro movimenti compromessa')
    os.makedirs(BACKUPS,exist_ok=True)
    path=os.path.join(BACKUPS,'Kristina_DB_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.sqlite3')
    with connect() as src, sqlite3.connect(path) as dst: src.backup(dst)
    return path


# Configurazioni aggiuntive (migrazione non distruttiva).
def init_settings():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS impostazioni (chiave TEXT PRIMARY KEY, valore TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS intestazioni (cassa_id INTEGER PRIMARY KEY REFERENCES casse(id), negozio TEXT NOT NULL DEFAULT '', indirizzo TEXT NOT NULL DEFAULT '', piva TEXT NOT NULL DEFAULT '', telefono TEXT NOT NULL DEFAULT '', qr_testo TEXT NOT NULL DEFAULT '')")
        c.execute("CREATE TABLE IF NOT EXISTS pos_slots (slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 1 AND 12), etichetta TEXT NOT NULL, colore TEXT NOT NULL, attivo INTEGER NOT NULL)")
        for i in range(1,13):
            c.execute('INSERT OR IGNORE INTO pos_slots VALUES(?,?,?,?)',(i,'Reparto '+str(i),'#267C80',1 if i<12 else 0))

def get_header(cid):
    with connect() as c:
        row=c.execute('SELECT negozio,indirizzo,piva,telefono,qr_testo FROM intestazioni WHERE cassa_id=?',(cid,)).fetchone()
    return dict(zip(('negozio','indirizzo','piva','telefono','qr_testo'),row or ('','','','','')))

def save_header(cid,data):
    fields=('negozio','indirizzo','piva','telefono','qr_testo')
    values=[str(data.get(k,'')).strip() for k in fields]
    with connect() as c:
        if not c.execute('SELECT 1 FROM casse WHERE id=?',(cid,)).fetchone():raise ValueError('Cassa non trovata')
        c.execute('INSERT INTO intestazioni VALUES(?,?,?,?,?,?) ON CONFLICT(cassa_id) DO UPDATE SET negozio=excluded.negozio,indirizzo=excluded.indirizzo,piva=excluded.piva,telefono=excluded.telefono,qr_testo=excluded.qr_testo',(cid,*values))
        log(c,'INTESTAZIONE_CASSA',cid,dict(zip(fields,values)))

def get_slots():
    with connect() as c:return c.execute('SELECT slot,etichetta,colore,attivo FROM pos_slots ORDER BY slot').fetchall()

def save_slot(slot,label,color,active):
    import re
    slot=int(slot)
    if not 1<=slot<=12:raise ValueError('Slot non valido')
    if not label.strip():raise ValueError('Etichetta obbligatoria')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Colore HEX non valido')
    with connect() as c:
        c.execute('UPDATE pos_slots SET etichetta=?,colore=?,attivo=? WHERE slot=?',(label.strip(),color.upper(),int(bool(active)),slot))
        log(c,'CONFIGURAZIONE_POS',slot,{'etichetta':label.strip(),'colore':color.upper(),'attivo':bool(active)})

def get_setting(key,default=''):
    with connect() as c:
        r=c.execute('SELECT valore FROM impostazioni WHERE chiave=?',(key,)).fetchone()
    return r[0] if r else default

def set_setting(key,value):
    with connect() as c:
        c.execute('INSERT INTO impostazioni VALUES(?,?) ON CONFLICT(chiave) DO UPDATE SET valore=excluded.valore',(key,str(value)))
        log(c,'IMPOSTAZIONE',key,{'valore':str(value)})

def sale_details(sale_id):
    with connect() as c:
        return c.execute('SELECT v.id,v.momento,v.metodo,v.totale_centesimi,v.ricevuto_centesimi,v.resto_centesimi,v.righe_json,t.cassa_id,c.nome FROM vendite v JOIN turni t ON t.id=v.turno_id JOIN casse c ON c.id=t.cassa_id WHERE v.id=?',(sale_id,)).fetchone()


def init_suspensions():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS sospensioni_cassa(cassa_id INTEGER PRIMARY KEY REFERENCES casse(id), sospesa INTEGER NOT NULL DEFAULT 0)")

def is_suspended(cid):
    init_suspensions()
    with connect() as c:
        row=c.execute('SELECT sospesa FROM sospensioni_cassa WHERE cassa_id=?',(cid,)).fetchone()
        return bool(row and row[0])

def set_suspended(cid, suspended):
    init_suspensions()
    with connect() as c:
        if not c.execute("SELECT 1 FROM turni WHERE cassa_id=? AND stato='APERTO'",(cid,)).fetchone():
            raise ValueError('Nessun turno aperto sulla cassa')
        c.execute('INSERT OR REPLACE INTO sospensioni_cassa(cassa_id,sospesa) VALUES(?,?)',(cid,int(bool(suspended))))
        log(c,'SOSPENSIONE_CASSA' if suspended else 'RIPRESA_CASSA',cid,{'sospesa':bool(suspended)})


def preview_articles_excel(filepath):
    """Anteprima rigorosamente in sola lettura, senza modificare SQLite."""
    from openpyxl import load_workbook
    headers=['Foto','Preferito','Nome','Riferimento interno','Prezzo di vendita',
             'Costo','Quantità giacenza fisica','Quantità prevista','Unità',
             'Decorazione eccezione attività','Codice a barre','Data di scadenza',
             'Data pubblicazione','Etichette','Magazzino','Prodotti']
    def norm(v):return ' '.join(str(v or '').strip().casefold().split())
    wb=load_workbook(filepath,read_only=False,data_only=True)
    try:
        ws=wb.active
        found=[norm(ws.cell(1,i).value) for i in range(1,17)]
        if found!=[norm(h) for h in headers]:
            raise ValueError('Le 16 intestazioni Excel non corrispondono al tracciato concordato.')
        count=barcodes=0;names=[]
        # Conta le immagini tramite gli stessi collegamenti OOXML usati nell'importazione.
        # ws._images puo' risultare vuoto se Pillow non e' disponibile.
        images=len(_embedded_excel_photos(filepath))
        for row in ws.iter_rows(min_row=2,max_col=16,values_only=True):
            if not any(v is not None and str(v).strip() for v in row):continue
            count+=1
            if row[10] is not None and str(row[10]).strip():barcodes+=1
            if len(names)<8:names.append(str(row[2] or '(senza nome)'))
        if not count:raise ValueError('Nessun articolo trovato nel file Excel')
        if count>8:names.append('... e altri {} articoli'.format(count-8))
        return {'totale':count,'barcode':barcodes,'immagini':images,'nomi':names}
    finally:wb.close()

def _embedded_excel_photos(filepath):
    """Legge foto e righe direttamente dai disegni OOXML, senza Pillow."""
    import posixpath
    import zipfile
    from xml.etree import ElementTree as ET
    ns = {'x':'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
          'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
          'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
          'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
    found = {}
    with zipfile.ZipFile(filepath) as archive:
        names = set(archive.namelist())
        for drawing in sorted(n for n in names if n.startswith('xl/drawings/drawing') and n.endswith('.xml')):
            relfile = posixpath.join(posixpath.dirname(drawing), '_rels', posixpath.basename(drawing) + '.rels')
            if relfile not in names:
                continue
            relroot = ET.fromstring(archive.read(relfile))
            rels = {e.attrib['Id']:e.attrib.get('Target','') for e in relroot.findall('p:Relationship',ns)
                    if e.attrib.get('Type','').endswith('/image')}
            root = ET.fromstring(archive.read(drawing))
            for anchor in root:
                cell = anchor.find('x:from',ns)
                if cell is None:continue
                r = cell.find('x:row',ns)
                col = cell.find('x:col',ns)
                if r is None or col is None or int(col.text) != 0:continue
                row = int(r.text)+1
                if row < 2:continue
                blip = anchor.find('.//a:blip',ns)
                if blip is None:continue
                rid = blip.attrib.get('{'+ns['r']+'}embed')
                target = rels.get(rid)
                if not target:continue
                if target.startswith('/'):
                    media = target.lstrip('/')
                else:
                    media = posixpath.normpath(posixpath.join(posixpath.dirname(drawing),target))
                if media not in names:raise ValueError('Immagine Excel non trovata: '+media)
                if row in found:raise ValueError('Riga {}: più fotografie incorporate'.format(row))
                found[row] = archive.read(media)
    return found

def import_articles_excel(filepath):
    """Importa il tracciato a 16 colonne, atomicamente, senza modificare la GUI."""
    import re
    from datetime import date, datetime
    from decimal import Decimal, InvalidOperation
    from openpyxl import load_workbook
    from openpyxl.utils.datetime import from_excel

    headers = ['Foto', 'Preferito', 'Nome', 'Riferimento interno',
               'Prezzo di vendita', 'Costo', 'Quantità giacenza fisica',
               'Quantità prevista', 'Unità', 'Decorazione eccezione attività',
               'Codice a barre', 'Data di scadenza', 'Data pubblicazione',
               'Etichette', 'Magazzino', 'Prodotti']
    def norm(x):
        return ' '.join(str(x if x is not None else '').strip().casefold().split())
    def txt(x):
        return '' if x is None else str(x).strip()
    def num(x, label, row):
        if x is None or txt(x)=='': return Decimal('0')
        if isinstance(x,bool): raise ValueError(f'Riga {row}: {label} non numerico')
        v=txt(x).replace('\u00a0','').replace(' ','').replace('CHF','').replace('€','')
        if ',' in v and '.' in v:
            v=v.replace('.','').replace(',','.') if v.rfind(',')>v.rfind('.') else v.replace(',','')
        elif ',' in v: v=v.replace(',','.')
        try: result=Decimal(v)
        except InvalidOperation: raise ValueError(f'Riga {row}: {label} non numerico: {x}')
        if not result.is_finite() or result<0: raise ValueError(f'Riga {row}: {label} negativo o non valido')
        return result
    def date_str(x, wb):
        if x is None:return ''
        if isinstance(x,datetime):return x.date().isoformat()
        if isinstance(x,date):return x.isoformat()
        if isinstance(x,(float,int)) and x>0:
            try:return from_excel(x,wb.epoch).date().isoformat()
            except (ValueError,OverflowError,TypeError):pass
        return txt(x)
    def code_of(cell,row):
        x=cell.value
        if x is None or txt(x)=='':return None
        if isinstance(x,bool):raise ValueError(f'Riga {row}: barcode non valido')
        if isinstance(x,(int,float)):
            if int(x)!=x:raise ValueError(f'Riga {row}: barcode numerico non intero')
            code=str(int(x))
            fmt=txt(cell.number_format)
            if re.fullmatch(r'0+',fmt):code=code.zfill(len(fmt))
        else:code=txt(x)
        if not re.fullmatch(r'[0-9]+',code):raise ValueError(f'Riga {row}: barcode non numerico: {code}')
        return code
    wb=load_workbook(filepath,data_only=True)
    try:
        ws=wb.active
        actual=[norm(c.value) for c in ws[1]]
        expected=[norm(h) for h in headers]
        if actual[:16]!=expected:
            missing=[h for h in headers if norm(h) not in actual]
            if missing:raise ValueError('Colonne Excel mancanti: '+', '.join(missing))
            raise ValueError('Le 16 intestazioni Excel devono essere nell’ordine concordato')
        # Le fotografie sono oggetti OOXML: estrazione indipendente da Pillow/openpyxl.
        embedded=_embedded_excel_photos(filepath)
        records=[];seen=set()
        for row in range(2,ws.max_row+1):
            cells=[ws.cell(row,col) for col in range(1,17)]
            if not any(c.value is not None and txt(c.value) for c in cells) and row not in embedded:continue
            values=[c.value for c in cells]
            nome=txt(values[2]);code=code_of(cells[10],row)
            if not nome:raise ValueError(f'Riga {row}: Nome obbligatorio')
            if code:
                if code in seen:raise ValueError(f'Codice a barre duplicato nel file: {code}')
                seen.add(code)
            prezzo=cents(num(values[4],'Prezzo di vendita',row))
            costo=cents(num(values[5],'Costo',row))
            giac=float(num(values[6],'Quantità giacenza fisica',row))
            prevista=float(num(values[7],'Quantità prevista',row))
            foto=txt(values[0]);blob=embedded.get(row)
            if blob is None and foto:
                candidate=foto if os.path.isabs(foto) else os.path.join(os.path.dirname(os.path.abspath(filepath)),foto)
                if os.path.isfile(candidate):
                    with open(candidate,'rb') as f:blob=f.read()
            if blob is not None and len(blob)>12*1024*1024:raise ValueError(f'Riga {row}: fotografia oltre 12 MB')
            records.append((nome,code,prezzo,costo,giac,prevista,txt(values[1]),txt(values[3]),
                txt(values[8]),txt(values[9]),date_str(values[11],wb),date_str(values[12],wb),
                txt(values[13]),txt(values[14]),txt(values[15]),foto,blob))
        if not records:raise ValueError('Nessun articolo nel file Excel')
        init_articles()
        with connect() as c:
            # Campi commerciali non presenti nella prima versione del modello.
            extra={'foto_blob':'BLOB','preferito':'TEXT NOT NULL DEFAULT ""',
              'riferimento_interno':'TEXT NOT NULL DEFAULT ""',
              'costo_centesimi':'INTEGER NOT NULL DEFAULT 0',
              'quantita_prevista':'REAL NOT NULL DEFAULT 0',
              'unita':'TEXT NOT NULL DEFAULT ""',
              'decorazione_eccezione_attivita':'TEXT NOT NULL DEFAULT ""',
              'data_pubblicazione':'TEXT NOT NULL DEFAULT ""',
              'etichette':'TEXT NOT NULL DEFAULT ""',
              'magazzino':'TEXT NOT NULL DEFAULT ""',
              'prodotti':'TEXT NOT NULL DEFAULT ""'}
            cols={r[1] for r in c.execute('PRAGMA table_info(Articoli)')}
            for col,definition in extra.items():
                if col not in cols:c.execute('ALTER TABLE Articoli ADD COLUMN '+col+' '+definition)
            nuovi=aggiornati=immagini=0
            for (nome,code,prezzo,costo,giac,prevista,preferito,rif,unita,decorazione,
                 scadenza,pubblicazione,etichette,magazzino,prodotti,foto,blob) in records:
                # Il magazzino Excel diventa il reparto visualizzato nella GUI.
                reparto=magazzino or 'Generale'
                c.execute('INSERT OR IGNORE INTO Reparti(nome) VALUES(?)',(reparto,))
                rid=c.execute('SELECT id FROM Reparti WHERE nome=?',(reparto,)).fetchone()[0]
                old=c.execute('SELECT id,giacenza FROM Articoli WHERE barcode=?',(code,)).fetchone() if code else None
                if old:
                    aid,old_giac=old
                    c.execute("""UPDATE Articoli SET nome=?,prezzo_centesimi=?,giacenza=?,reparto_id=?,
                        lotto=?,scadenza=?,foto=?,foto_blob=COALESCE(?,foto_blob),preferito=?,
                        riferimento_interno=?,costo_centesimi=?,quantita_prevista=?,unita=?,
                        decorazione_eccezione_attivita=?,data_pubblicazione=?,etichette=?,
                        magazzino=?,prodotti=? WHERE id=?""",
                        (nome,prezzo,giac,rid,rif,scadenza,foto,blob,preferito,rif,costo,
                         prevista,unita,decorazione,pubblicazione,etichette,magazzino,prodotti,aid))
                    aggiornati+=1
                else:
                    aid=c.execute("""INSERT INTO Articoli(barcode,nome,prezzo_centesimi,giacenza,
                        reparto_id,lotto,scadenza,foto,foto_blob,preferito,riferimento_interno,
                        costo_centesimi,quantita_prevista,unita,decorazione_eccezione_attivita,
                        data_pubblicazione,etichette,magazzino,prodotti)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (code,nome,prezzo,giac,rid,rif,scadenza,foto,blob,preferito,rif,
                         costo,prevista,unita,decorazione,pubblicazione,etichette,magazzino,prodotti)).lastrowid
                    old_giac=0;nuovi+=1
                delta=giac-old_giac
                if delta:
                    c.execute("""INSERT INTO Movimenti_Magazzino(articolo_id,momento,tipo,quantita,causale)
                        VALUES(?,?,?,?,?)""",(aid,now(),'CARICO' if delta>0 else 'RETTIFICA',delta,'IMPORTAZIONE_EXCEL'))
                if blob is not None:immagini+=1
            log(c,'IMPORTAZIONE_EXCEL','articoli',{'nuovi':nuovi,'aggiornati':aggiornati,'immagini':immagini})
        return {'nuovi':nuovi,'aggiornati':aggiornati,'immagini':immagini}
    finally:
        wb.close()
