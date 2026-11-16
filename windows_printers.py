# -*- coding: utf-8 -*-
"""Dialogo stampante nativo Windows (comdlg32.PrintDlgW)."""
import sys

def choose_printer():
    if sys.platform != 'win32':
        raise RuntimeError('La selezione stampante Windows non e disponibile su questa piattaforma')
    import ctypes
    from ctypes import wintypes
    class PRINTDLGW(ctypes.Structure):
        _fields_ = [('lStructSize', wintypes.DWORD), ('hwndOwner', wintypes.HWND),
            ('hDevMode', wintypes.HGLOBAL), ('hDevNames', wintypes.HGLOBAL),
            ('hDC', wintypes.HDC), ('Flags', wintypes.DWORD), ('nFromPage', wintypes.WORD),
            ('nToPage', wintypes.WORD), ('nMinPage', wintypes.WORD), ('nMaxPage', wintypes.WORD),
            ('nCopies', wintypes.WORD), ('hInstance', wintypes.HINSTANCE),
            ('lCustData', ctypes.c_size_t), ('lpfnPrintHook', ctypes.c_void_p),
            ('lpfnSetupHook', ctypes.c_void_p), ('lpPrintTemplateName', wintypes.LPCWSTR),
            ('lpSetupTemplateName', wintypes.LPCWSTR), ('hPrintTemplate', wintypes.HGLOBAL),
            ('hSetupTemplate', wintypes.HGLOBAL)]
    # DEVNAMES contiene offset in WCHAR, non byte.
    class DEVNAMES(ctypes.Structure):
        _fields_ = [('wDriverOffset', wintypes.WORD), ('wDeviceOffset', wintypes.WORD),
                    ('wOutputOffset', wintypes.WORD), ('wDefault', wintypes.WORD)]
    comdlg=ctypes.WinDLL('comdlg32', use_last_error=True)
    kernel=ctypes.WinDLL('kernel32', use_last_error=True)
    gdi=ctypes.WinDLL('gdi32', use_last_error=True)
    gdi.DeleteDC.argtypes=[wintypes.HDC]
    gdi.DeleteDC.restype=wintypes.BOOL
    comdlg.PrintDlgW.argtypes=[ctypes.POINTER(PRINTDLGW)]
    comdlg.PrintDlgW.restype=wintypes.BOOL
    kernel.GlobalLock.argtypes=[wintypes.HGLOBAL]
    kernel.GlobalLock.restype=ctypes.c_void_p
    kernel.GlobalUnlock.argtypes=[wintypes.HGLOBAL]
    kernel.GlobalUnlock.restype=wintypes.BOOL
    kernel.GlobalFree.argtypes=[wintypes.HGLOBAL]
    kernel.GlobalFree.restype=wintypes.HGLOBAL
    pd=PRINTDLGW()
    pd.lStructSize=ctypes.sizeof(PRINTDLGW)
    pd.Flags=0x00000100  # PD_RETURNDC: mostra il dialogo e restituisce la selezione
    try:
        if not comdlg.PrintDlgW(ctypes.byref(pd)):
            return None  # Annulla (o errore dialogo)
        if not pd.hDevNames:
            raise RuntimeError('Il dialogo non ha restituito una stampante')
        ptr=kernel.GlobalLock(pd.hDevNames)
        if not ptr:raise RuntimeError('Impossibile leggere la stampante selezionata')
        try:
            dev=DEVNAMES.from_address(ptr)
            return ctypes.wstring_at(ptr + 2 * dev.wDeviceOffset)
        finally:
            kernel.GlobalUnlock(pd.hDevNames)
    finally:
        if pd.hDC:
            gdi.DeleteDC(pd.hDC)
        if pd.hDevMode:kernel.GlobalFree(pd.hDevMode)
        if pd.hDevNames:kernel.GlobalFree(pd.hDevNames)
