from ui.theme import Button
COLORS=[(.16,.38,.59,1),(.14,.47,.40,1),(.48,.32,.62,1),(.68,.37,.16,1),(.53,.28,.39,1),(.23,.38,.48,1)]
def menu_button(text,**kwargs):
    idx=sum(ord(c) for c in text)%len(COLORS)
    return Button(text=text,background_normal='',background_color=COLORS[idx],color=(1,1,1,1),**kwargs)
class MenuButton(Button):
    def __init__(self, **kwargs):
        title=str(kwargs.get('text',''))
        idx=sum(ord(c) for c in title)%len(COLORS)
        kwargs.setdefault('background_normal','')
        kwargs.setdefault('background_color',COLORS[idx])
        kwargs.setdefault('color',(1,1,1,1))
        super().__init__(**kwargs)
