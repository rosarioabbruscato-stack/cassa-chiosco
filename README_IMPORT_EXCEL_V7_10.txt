Kristin_Cassa V7.10 - Importazione Excel Magazzino

Modifica circoscritta al pulsante Importa Excel: GUI touchscreen invariata.
Tracciato XLSX (prima riga intestazioni):
Nome Prodotto | Codice a Barre | Categoria | Lotto | Scadenza | Immagine

- Le immagini incorporate nel foglio sono memorizzate nella colonna Articoli.foto_blob (BLOB).
- Il campo Immagine testuale viene salvato in Articoli.foto; se indica un file accessibile viene anche acquisito in BLOB.
- Prezzo e giacenza iniziali dei nuovi articoli sono zero, perché non presenti nel tracciato.
- Codici a barre esistenti aggiornano le informazioni anagrafiche senza azzerare prezzo e giacenza.
- Codici a barre non presenti sono consentiti; in importazioni successive verranno creati come nuove righe.
- Codici a barre duplicati nello stesso file bloccano l'importazione.
- Errori annullano l'intera importazione; il risultato è mostrato in un popup.
- Richiede openpyxl installato in Python (pip install openpyxl).
- Supporta .xlsx e .xlsm; non il vecchio formato binario .xls.
- Le immagini archiviate come BLOB sono predisposte per successiva visualizzazione nel form.
