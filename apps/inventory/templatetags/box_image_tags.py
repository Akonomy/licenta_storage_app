# apps/inventory/templatetags/box_image_tags.py
from django import template
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def box_image_url(box):
    """
    Returnează calea statică a imaginii pentru o cutie, pe baza culorii și a unei litere extrase din nume.
    
    Se caută în numele cutiei o literă din setul valid (A, K, O) care apare exact o dată.
    Dacă nu se găsește nicio literă, se va returna calea default către imaginea 'black-cat.png'.
    Dacă culoarea este 'blue' și litera obținută este 'O' (combinație inexistentă), se va înlocui cu 'A'.
    """
    valid_letters = ['A', 'K', 'O']
    letter = None
    # Căutăm în numele cutiei o literă din setul valid care apare exact o dată.
    for l in valid_letters:
        if box.name.count(l) == 1:
            letter = l
            break
    # Dacă nu s-a găsit o literă validă, returnează imaginea default.
    if not letter:
        return static("home/images/black-cat.png")
    
    # Corectăm combinația inexistentă: blueO nu există, deci înlocuim cu blueA.
    if box.color == 'blue' and letter == 'O':

        return static("home/images/black-cat.png")

    # Construcția căii pentru imaginea cutiei.
    image_path = f"home/images/{box.color}{letter}.webp"
    return static(image_path)
