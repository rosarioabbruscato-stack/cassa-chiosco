# -*- coding: utf-8 -*-
"""Tema condiviso: contrasto elevato, tonalita' riposanti."""
from kivy.uix.button import Button as KivyButton
from kivy.uix.label import Label as KivyLabel
from kivy.uix.spinner import Spinner as KivySpinner
from kivy.uix.textinput import TextInput as KivyTextInput
from kivy.uix.popup import Popup as KivyPopup
from kivy.core.window import Window

Window.clearcolor = (0.929, 0.949, 0.961, 1)

class Button(KivyButton):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('background_color', (0.145, 0.455, 0.475, 1))
        if 'color' not in kwargs:
            bg = kwargs.get('background_color', (0.145, 0.455, 0.475, 1))
            def linear(v): return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
            luminance = sum(w * linear(c) for w,c in zip((.2126,.7152,.0722),bg[:3]))
            kwargs['color'] = (.10,.16,.21,1) if luminance > .30 else (1,1,1,1)
        kwargs.setdefault('font_size', '15sp')
        super().__init__(**kwargs)

class TextInput(KivyTextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_color', (1, 1, 1, 1))
        kwargs.setdefault('foreground_color', (0.12, 0.18, 0.23, 1))
        kwargs.setdefault('cursor_color', (0.14, 0.44, 0.47, 1))
        super().__init__(**kwargs)

class Popup(KivyPopup):
    def __init__(self, **kwargs):
        kwargs.setdefault('background', '')
        kwargs.setdefault('background_color', (0.929, 0.949, 0.961, 1))
        kwargs.setdefault('title_color', (0.12, 0.18, 0.23, 1))
        super().__init__(**kwargs)


class Label(KivyLabel):
    def __init__(self, **kwargs):
        kwargs.setdefault('color', (0.11, 0.19, 0.26, 1))
        super().__init__(**kwargs)

class Spinner(KivySpinner):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_color', (0.145, 0.455, 0.475, 1))
        kwargs.setdefault('color', (1, 1, 1, 1))
        super().__init__(**kwargs)
