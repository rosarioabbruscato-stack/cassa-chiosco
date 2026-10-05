import os
import sqlite3
import pandas as pd
import glob

DB_PATH = "database/negozio.db"

def esporta_magazzino_excel(file_path="export_magazzino.xlsx"):
    """Esporta tutti i prodotti dal database SQLite in un file Excel."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT id, codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante FROM prodotti", conn)
        conn.close()
        df.to_excel(file_path, index=False)
        return True, "Esportazione completata con successo!"
    except Exception as e:
        return False, str(e)

def importa_magazzino_excel(file_path=None):
    """Importa i prodotti da un file Excel nel database SQLite."""
    if not file_path:
        files_xlsx = glob.glob("*.xlsx")
        if files_xlsx:
            file_path = files_xlsx[0]
        else:
            return False, "Nessun file Excel trovato nella cartella."
            
    if not os.path.exists(file_path):
        return False, f"Il file {file_path} non esiste."
    
    try:
        df = pd.read_excel(file_path)
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            codice_barra = str(row.get('codice_barra', ''))
            if pd.isna(codice_barra): codice_barra = ''
                
            nome = str(row.get('nome', 'Prodotto senza nome'))
            if pd.isna(nome): nome = 'Prodotto senza nome'
                
            try:
                prezzo = float(row.get('prezzo', 0.0))
                if pd.isna(prezzo): prezzo = 0.0
            except:
                prezzo = 0.0
                
            categoria = str(row.get('categoria', ''))
            if pd.isna(categoria): categoria = ''
            
            try:
                giacenza = float(row.get('giacenza', 0.0))
                if pd.isna(giacenza): giacenza = 0.0
            except:
                giacenza = 0.0
                
            lotto = str(row.get('lotto', ''))
            if pd.isna(lotto): lotto = ''
            
            data_scadenza = str(row.get('data_scadenza', ''))
            if pd.isna(data_scadenza): data_scadenza = ''
            
            categoria_pos = str(row.get('categoria_pos', ''))
            if pd.isna(categoria_pos): categoria_pos = ''
            
            colore_pulsante = str(row.get('colore_pulsante', '#333333'))
            if pd.isna(colore_pulsante): colore_pulsante = '#333333'
            
            cursor.execute("""
                INSERT INTO prodotti (codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codice_barra, nome, prezzo, categoria, giacenza, lotto, data_scadenza, categoria_pos, colore_pulsante))
            
        conn.commit()
        conn.close()
        return True, "Importazione completata con successo!"
    except Exception as e:
        return False, str(e)
