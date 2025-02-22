from django import template
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def box_image_url(box):
    """
    Construieste calea statica a imaginii pentru o cutie, avand in vedere ca imaginea
    este mereu din acelasi director, dar numele imaginii se formeaza in functie de datele cutiei.
    Dacă nu se găsește o literă validă sau combinația este inexistentă, se folosește imaginea default.
    """
    valid_letters = ['A', 'K', 'O']
    letter = None
    # Căutăm în numele cutiei o literă validă care apare exact o dată.
    for l in valid_letters:
        if box.name.count(l) == 1:
            letter = l
            break

    # Dacă nu s-a găsit o literă validă sau combinația este invalidă (blue + O), folosește imaginea default.
    if not letter or (box.color == 'blue' and letter == 'O'):
        image_name = "black-cat.png"
    else:
        image_name = f"{box.color}{letter}.webp"

    # Returnează calea statică către imagine, la fel ca în primul exemplu.
    
    return image_name
