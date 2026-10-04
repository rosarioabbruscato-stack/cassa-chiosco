import os
import sqlite3
import pandas as pd

DB_PATH = "database/negozio.db"

def esporta_magazzino_excel(file_path="export_magazzino.xlsx"):
    """
    Esporta tutti i prodotti dal database SQLite in un file Excel.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT id, codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante FROM prodotti", conn)
        conn.close()
        df.to_excel(file_path, index=False)
        return True, "Esportazione completata con successo!"
    except Exception as e:
        return False, str(e)

def importa_magazzino_excel(file_path):
    """
    Importa i prodotti da un file Excel nel database SQLite del magazzino.
    """
    if not os.path.exists(file_path):
        return False, f"Il file {file_path} non esiste."
    
    try:
        df = pd.read_excel(file_path)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            codice_barra = str(row.get('codice_barra', ''))
            nome = str(row.get('nome', 'Prodotto senza nome'))
            prezzo = float(row.get('prezzo', 0.0))
            categoria = str(row.get('categoria', ''))
            giacenza = float(row.get('giacenza', 0.0))
            lotto = str(row.get('lotto', ''))
            data_scadenza = str(row.get('data_scadenza', ''))
            categoria_pos = str(row.get('categoria_pos', ''))
            colore_pulsante = str(row.get('colore_pulsante', '#333333'))
            
            cursor.execute("""
                INSERT INTO prodotti (codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante))
            
        conn.commit()
        conn.close()
        return True, "Importazione completata con successo!"
    except Exception as e:
        return False, str(e)
