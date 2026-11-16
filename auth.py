# -*- coding: utf-8 -*-
"""Credenziali locali: identificativi e password non in chiaro."""
import os,hashlib,hmac,secrets
from cryptography.fernet import Fernet
ROOT=os.path.dirname(os.path.abspath(__file__))
PATH=os.path.join(ROOT,'psd.json')
ITER=260000
KEY_PATH=os.path.join(ROOT,'.display_names.key')

def _name_cipher():
    if not os.path.exists(KEY_PATH):
        fd=os.open(KEY_PATH,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(Fernet.generate_key())
    with open(KEY_PATH,'rb') as f:return Fernet(f.read())

def cashier_display_name(cid):
    record=read().get('cassieri',{}).get(str(cid),{})
    token=record.get('nome_cifrato')
    if not token:return None
    try:return _name_cipher().decrypt(token.encode('ascii')).decode('utf-8')
    except Exception:return None


def namehash(name): return hashlib.sha256(name.strip().casefold().encode('utf-8')).hexdigest()
def derive(password,salt): return hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),ITER).hex()
def credential(password):
    if len(password)<8: raise ValueError('La password deve contenere almeno 8 caratteri')
    salt=secrets.token_hex(16)
    return {'salt':salt,'hash':derive(password,salt),'algoritmo':'pbkdf2_sha256','iterazioni':ITER}
def check(password,record):
    if not record: return False
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(record['salt']),int(record['iterazioni'])).hex()
    return hmac.compare_digest(digest,record['hash'])
def _auth_schema(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS Credenziali_Admin(
        id INTEGER PRIMARY KEY CHECK(id=1),salt TEXT NOT NULL,hash TEXT NOT NULL,
        algoritmo TEXT NOT NULL,iterazioni INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS Credenziali_Cassieri(
        cassiere_id INTEGER PRIMARY KEY REFERENCES cassieri(id),
        nome_hash TEXT NOT NULL,nome_cifrato TEXT NOT NULL,
        salt TEXT NOT NULL,hash TEXT NOT NULL,algoritmo TEXT NOT NULL,iterazioni INTEGER NOT NULL);
    """)

def read():
    import storage
    with storage.connect() as c:
        _auth_schema(c)
        a=c.execute('SELECT salt,hash,algoritmo,iterazioni FROM Credenziali_Admin WHERE id=1').fetchone()
        rows=c.execute('SELECT cassiere_id,nome_hash,nome_cifrato,salt,hash,algoritmo,iterazioni FROM Credenziali_Cassieri').fetchall()
        return {'admin':dict(zip(('salt','hash','algoritmo','iterazioni'),a)) if a else None,
                'cassieri':{str(r[0]):{'nome_hash':r[1],'nome_cifrato':r[2],
                'password':dict(zip(('salt','hash','algoritmo','iterazioni'),r[3:]))} for r in rows}}

def write(data):
    import storage
    with storage.connect() as c:
        _auth_schema(c)
        c.execute('DELETE FROM Credenziali_Admin')
        if data.get('admin'):
            a=data['admin']
            c.execute('INSERT INTO Credenziali_Admin VALUES(1,?,?,?,?)',
                      (a['salt'],a['hash'],a['algoritmo'],a['iterazioni']))
        existing={r[0] for r in c.execute('SELECT cassiere_id FROM Credenziali_Cassieri')}
        desired={int(k) for k in data.get('cassieri',{})}
        for cid in existing-desired:
            c.execute('DELETE FROM Credenziali_Cassieri WHERE cassiere_id=?',(cid,))
        for cid,rec in data.get('cassieri',{}).items():
            pwd=rec['password']
            c.execute("""INSERT INTO Credenziali_Cassieri VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(cassiere_id) DO UPDATE SET nome_hash=excluded.nome_hash,
                nome_cifrato=excluded.nome_cifrato,salt=excluded.salt,hash=excluded.hash,
                algoritmo=excluded.algoritmo,iterazioni=excluded.iterazioni""",
                (int(cid),rec['nome_hash'],rec['nome_cifrato'],pwd['salt'],pwd['hash'],pwd['algoritmo'],pwd['iterazioni']))

def admin_exists(): return bool(read().get('admin'))
def set_admin(password):
    if not password_available(password):
        raise ValueError("Password non valida. Sceglierne un'altra.")
    d=read();d['admin']=credential(password);write(d)
def is_admin(password): return check(password,read().get('admin'))
def password_available(password, exclude_cid=None):
    """Non rivela a quale account appartiene una password gia' utilizzata."""
    data=read()
    if check(password,data.get('admin')):
        return False
    for cid,record in data.get('cassieri',{}).items():
        if exclude_cid is not None and str(cid)==str(exclude_cid):
            continue
        if check(password,record.get('password')):
            return False
    return True

def set_cashier(cid,name,password):
    if not password_available(password,exclude_cid=cid):
        raise ValueError('Password non valida. Sceglierne un\'altra.')
    d=read();d['cassieri'][str(cid)]={'nome_hash':namehash(name),'nome_cifrato':_name_cipher().encrypt(name.strip().encode('utf-8')).decode('ascii'),'password':credential(password)};write(d)
def is_cashier(cid,password): return check(password,read()['cassieri'].get(str(cid),{}).get('password'))
def cashier_by_password(password):
    for cid,record in read()['cassieri'].items():
        if check(password,record.get('password')): return int(cid)
    return None
def remove_cashier(cid):
    d=read();d['cassieri'].pop(str(cid),None);write(d)
