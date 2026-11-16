# -*- coding: utf-8 -*-
"""Invia testo al driver di stampa Windows selezionato, senza associazioni .txt.
Usa GDI (CreateDCW / StartDocW / TextOutW); funziona anche con stampanti PDF.
"""
import ctypes
from ctypes import wintypes

class DOCINFOW(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_int), ('lpszDocName', wintypes.LPCWSTR),
                ('lpszOutput', wintypes.LPCWSTR), ('lpszDatatype', wintypes.LPCWSTR),
                ('fwType', wintypes.DWORD)]

def print_text(text, printer_name=None, document_name='Kristina - Scontrino gestionale'):
    gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    winspool = ctypes.WinDLL('winspool.drv', use_last_error=True)
    gdi.CreateDCW.argtypes = [wintypes.LPCWSTR]*4
    gdi.CreateDCW.restype = wintypes.HDC
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    gdi.DeleteDC.restype = wintypes.BOOL
    gdi.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi.GetDeviceCaps.restype = ctypes.c_int
    gdi.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(DOCINFOW)]
    gdi.StartDocW.restype = ctypes.c_int
    gdi.EndDoc.argtypes = [wintypes.HDC]
    gdi.EndDoc.restype = ctypes.c_int
    gdi.AbortDoc.argtypes = [wintypes.HDC]
    gdi.AbortDoc.restype = ctypes.c_int
    gdi.StartPage.argtypes = [wintypes.HDC]
    gdi.StartPage.restype = ctypes.c_int
    gdi.EndPage.argtypes = [wintypes.HDC]
    gdi.EndPage.restype = ctypes.c_int
    gdi.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int]
    gdi.TextOutW.restype = wintypes.BOOL
    gdi.CreateFontW.argtypes = [ctypes.c_int]*5 + [wintypes.DWORD]*3 + [wintypes.DWORD]*5 + [wintypes.LPCWSTR]
    gdi.CreateFontW.restype = wintypes.HANDLE
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi.SelectObject.restype = wintypes.HANDLE
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteObject.restype = wintypes.BOOL
    winspool.GetDefaultPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    winspool.GetDefaultPrinterW.restype = wintypes.BOOL
    if not printer_name:
        size = wintypes.DWORD(0)
        winspool.GetDefaultPrinterW(None, ctypes.byref(size))
        if not size.value:
            raise RuntimeError('Nessuna stampante predefinita Windows')
        buf = ctypes.create_unicode_buffer(size.value)
        if not winspool.GetDefaultPrinterW(buf, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        printer_name = buf.value
    dc = gdi.CreateDCW('WINSPOOL', printer_name, None, None)
    if not dc:
        raise RuntimeError('Stampante non disponibile: ' + printer_name)
    doc_started = False
    font = None
    old_font = None
    try:
        # DeviceCaps: LOGPIXELSY 90, HORZRES 8, VERTRES 10.
        dpi = max(72, gdi.GetDeviceCaps(dc, 90))
        page_width = gdi.GetDeviceCaps(dc, 8)
        page_height = gdi.GetDeviceCaps(dc, 10)
        font_height = max(12, round(dpi * 9 / 72))
        line_height = max(18, round(font_height * 1.5))
        margin = max(12, round(dpi * 0.25))
        font = gdi.CreateFontW(-font_height, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, 'Consolas')
        if font:
            old_font = gdi.SelectObject(dc, font)
        info = DOCINFOW(ctypes.sizeof(DOCINFOW), document_name, None, None, 0)
        if gdi.StartDocW(dc, ctypes.byref(info)) <= 0:
            raise RuntimeError('Impossibile avviare il documento di stampa')
        doc_started = True
        lines = text.splitlines()
        y = margin
        if gdi.StartPage(dc) <= 0:
            raise RuntimeError('Impossibile iniziare la pagina')
        for line in lines:
            if y + line_height > page_height - margin:
                if gdi.EndPage(dc) <= 0 or gdi.StartPage(dc) <= 0:
                    raise RuntimeError('Errore cambio pagina')
                y = margin
            # Le righe sono limitate per evitare che invadano la pagina.
            max_chars = max(12, (page_width - 2 * margin) // max(1, round(font_height * 0.60)))
            for chunk in ([line[i:i+max_chars] for i in range(0, len(line), max_chars)] or ['']):
                if y + line_height > page_height - margin:
                    if gdi.EndPage(dc) <= 0 or gdi.StartPage(dc) <= 0:
                        raise RuntimeError('Errore cambio pagina')
                    y = margin
                if chunk and not gdi.TextOutW(dc, margin, y, chunk, len(chunk)):
                    raise RuntimeError('Errore scrittura sulla stampante')
                y += line_height
        if gdi.EndPage(dc) <= 0 or gdi.EndDoc(dc) <= 0:
            raise RuntimeError('Errore chiusura documento di stampa')
        doc_started = False
        return printer_name
    finally:
        if doc_started:
            gdi.AbortDoc(dc)
        if old_font and font:
            gdi.SelectObject(dc, old_font)
        if font:
            gdi.DeleteObject(font)
        gdi.DeleteDC(dc)
