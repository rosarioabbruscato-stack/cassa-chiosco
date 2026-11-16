Kristin_Cassa - Windows / Python - GUI touch originale preservata

Avvio: python main.py (richiede Kivy, openpyxl, pandas e cryptography).
Al primo avvio SQLite crea Kristina_DB.sqlite3 vuoto. Nessuna migrazione.
La grafica, i menu e i pulsanti provengono dalla V7.8, derivata dalla V7.7.
Il campo Bar Code accetta EAN-8 / EAN-13 con checksum valido, INVIO oppure CONFERMA.
Le giacenze sono in Articoli; carichi/rettifiche in Movimenti_Magazzino.
Le vendite scaricano le giacenze in una singola transazione.
Le credenziali sono in SQLite; la chiave Fernet per i nomi e un file tecnico locale.
ATTENZIONE: non certificato per obblighi fiscali svizzeri; stampa e GUI Windows
richiedono prova su dispositivo touchscreen reale.
