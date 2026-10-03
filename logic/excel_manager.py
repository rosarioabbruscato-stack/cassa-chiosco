import sqlite3
import openpyxl
from database.db_manager import DB_PATH

def esporta_magazzino_excel(file_path="export_magazzino.xlsx"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prodotti")
    righe = cursor.fetchall()
    nomi_colonne = [description[0] for description in cursor.description]
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Magazzino"
    
    ws.append(nomi_colonne)
    for riga in righe:
        ws.append(riga)
        
    wb.save(file_path)
    return file_path

def importa_magazzino_excel(file_path):
    if not os.path.exists(file_path):
        return False, "File non trovato"
        
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    righe = list(ws.iter_rows(values_only=True))
    if len(righe) < 2:
        return False, "File vuoto o privo di dati"
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ignoriamo la prima riga (intestazioni) e inseriamo/aggiorniamo i dati
    conteggio = 0
    for riga in righe[1:]:
        # Assumiamo la struttura: id, codice_barra, nome, categoria, categoria_pos, prezzo, giacenza, gestisce_lotti, lotto, data_scadenza, gestione_scadenza, colore_pulsante, foto_path
        if len(riga) >= 3 and riga[2]: # Almeno nome presente
            codice_barra = riga[1]
            nome = riga[2]
            categoria = riga[3] if len(riga) > 3 else ""
            categoria_pos = riga[4] if len(riga) > 4 else ""
            prezzo = riga[5] if len(riga) > 5 and riga[5] is not None else 0.0
            giacenza = riga[6] if len(riga) > 6 and riga[6] is not None else 0.0
            gestisce_lotti = riga[7] if len(riga) > 7 and riga[7] is not None else 0
            lotto = riga[8] if len(riga) > 8 else ""
            data_scadenza = riga[9] if len(riga) > 9 else ""
            gestione_scadenza = riga[10] if len(riga) > 10 else ""
            colore_pulsante = riga[11] if len(riga) > 11 and riga[11] else "#333333"
            foto_path = riga[12] if len(riga) > 12 else ""

            cursor.execute("""
                INSERT INTO prodotti (codice_barra, nome, categoria, categoria_pos, prezzo, giacenza, gestisce_lotti, lotto, data_scadenza, gestione_scadenza, colore_pulsante, foto_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codice_barra) DO UPDATE SET
                    nome=excluded.nome,
                    categoria=excluded.categoria,
                    categoria_pos=excluded.categoria_pos,
                    prezzo=excluded.prezzo,
                    giacenza=excluded.giacenza,
                    gestisce_lotti=excluded.gestisce_lotti,
                    lotto=excluded.lotto,
                    data_scadenza=excluded.data_scadenza,
                    gestione_scadenza=excluded.gestione_scadenza,
                    colore_pulsante=excluded.colore_pulsante,
                    foto_path=excluded.foto_path
            """, (codice_barra, nome, categoria, categoria_pos, prezzo, giacenza, gestisce_lotti, lotto, data_scadenza, gestione_scadenza, colore_pulsante, foto_path))
            conteggio += 1
            
    conn.commit()
    conn.close()
