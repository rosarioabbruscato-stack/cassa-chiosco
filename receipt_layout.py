# -*- coding: utf-8 -*-
"""Formato colonne dello scontrino (larghezza fissa per stampa monospace)."""
from decimal import Decimal, ROUND_HALF_UP
WIDTH = 48

def money(value):
    return f'{Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):.2f}'

def row(description, qty, unit, total, header=False):
    # Le intestazioni sono testo, non importi monetari.
    unit_text = str(unit) if header else money(unit)
    total_text = str(total) if header else money(total)
    return f'{str(description)[:21]:<21} {str(qty):>5} {unit_text:>9} {total_text:>10}'

def format_receipt_lines(ident, momento, cassa, items, totale, metodo, ricevuto, resto):
    lines=['Scontrino gestionale NON fiscale', f'Vendita #{ident}  {momento}',
           'Cassa: '+str(cassa), '-'*WIDTH,
           row('DESCRIZIONE', 'QTA', 'UNIT.', 'TOTALE', header=True), '-'*WIDTH]
    for item in items:
        qty=Decimal(str(item.get('qta',0)))
        unit=Decimal(str(item.get('prezzo',0)))
        qtext=f'{qty.normalize():f}'
        lines.append(row(str(item.get('nome','Articolo')),qtext,unit,qty*unit))
        if item.get('iva') is not None:
            lines.append('  IVA: {}%'.format(item['iva']))
    lines.extend(['-'*WIDTH,
                  f'{"TOTALE CHF":<32}{money(totale):>16}',
                  f'{"PAGAMENTO":<32}{str(metodo):>16}',
                  f'{"RICEVUTO CHF":<32}{money(ricevuto):>16}',
                  f'{"RESTO CHF":<32}{money(resto):>16}'])
    return lines
