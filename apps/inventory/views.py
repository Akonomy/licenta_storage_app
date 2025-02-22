from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Count, OuterRef
from .forms import BoxForm, SectionForm
from .models import Box, Section
from apps.robot_interface.models import Task  # Modelul Task pentru crearea de taskuri
import json
from django.contrib import messages

@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def inventory_home(request):
    return render(request, 'inventory/home.html')

# Vizualizare pentru adăugarea unei noi cutii (Box)
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def add_box(request):
    if request.method == 'POST':
        form = BoxForm(request.POST, request.FILES)
        if form.is_valid():
            box = form.save()
            # Verifică dacă s-a bifat opțiunea 'add_move_task' și dacă secțiunea cutiei este 'receptie'
            add_move_task = form.cleaned_data.get('add_move_task')
            if add_move_task and box.section and box.section.tip_sectie == 'receptie':
                # Găsește toate secțiunile de tip 'depozit'
                depozit_sections = Section.objects.filter(tip_sectie='depozit')
                if depozit_sections.exists():
                    # Alege secțiunea de depozit cu cele mai puține cutii
                    depozit_section = depozit_sections.annotate(box_count=Count('box')).order_by('box_count').first()
                    # Creează un Task pentru a muta cutia din 'receptie' în secțiunea de 'depozit' selectată
                    Task.objects.create(
                        task_type='move_box',
                        box=box,
                        source_section=box.section,
                        target_section=depozit_section,
                        status='pending',
                        created_by=request.user  # Presupunem că Task are câmpul 'created_by'
                    )
            return redirect('box_list')
    else:
        form = BoxForm()
    
    return render(request, 'inventory/add_box.html', {'form': form})

# Vizualizare pentru adăugarea unei noi secțiuni (Section)
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def add_section(request):
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('section_list')
    else:
        form = SectionForm()
    
    return render(request, 'inventory/add_section.html', {'form': form})

# Vizualizare pentru afișarea cutiilor
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def box_list(request):
    color = request.GET.get('color')
    section = request.GET.get('section')
    order_by = request.GET.get('order_by')

    # Obține toate cutiile, folosind select_related pentru a optimiza accesul la secțiune
    boxes = Box.objects.select_related('section')

    # Filtrează după culoare dacă este specificată
    if color:
        boxes = boxes.filter(color=color)
    
    # Filtrează după numele secțiunii (nume_custom) dacă este specificată
    if section:
        boxes = boxes.filter(section__nume_custom=section)

    # Permite ordonarea doar pe câmpurile acceptate
    allowed_orderings = ['name', 'code', 'price', 'section__nume_custom', 'color']
    if order_by:
        order_field = order_by.lstrip('-')
        if order_field in allowed_orderings:
            boxes = boxes.order_by(order_by)
        else:
            boxes = boxes.order_by('name')
    else:
        boxes = boxes.order_by('name')

    # Anotează fiecare cutie cu flag-ul 'in_task' (dacă există un task pending pentru aceasta)
    pending_tasks = Task.objects.filter(box=OuterRef('pk'), status='pending')
    for box in boxes:
        box.in_task = Task.is_box_in_task(box)

    # Definim câmpurile și etichetele pentru afișare în template
    field_labels = [
        ('name', 'Nume'),
        ('color', 'Culoare'),
        ('code', 'Cod'),
        ('price', 'Preț'),
        ('section__nume_custom', 'Secțiune')
    ]

    return render(request, 'inventory/box_list.html', {
        'boxes': boxes,
        'current_order': order_by,
        'field_labels': field_labels
    })

# Vizualizare pentru afișarea secțiunilor
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def section_list(request):
    sections = Section.objects.all()
    return render(request, 'inventory/section_list.html', {'sections': sections})

# Funcția de editare a cutiilor

@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def edit_box(request, box_id):
    box = get_object_or_404(Box, id=box_id)
    if request.method == 'POST':
        form = BoxForm(request.POST, request.FILES, instance=box)
        if form.is_valid():
            form.save()
            return redirect('box_list')
    else:
        form = BoxForm(instance=box)

    return render(request, 'inventory/edit_box.html', {'form': form})

# Funcția de ștergere a cutiilor
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def delete_box(request, box_id):
    box = get_object_or_404(Box, id=box_id)
    if request.method == 'POST':
        box.delete()
        return redirect('box_list')
    return render(request, 'inventory/delete_box.html', {'box': box})

# Funcția de editare a secțiunilor
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def edit_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            return redirect('section_list')
    else:
        form = SectionForm(instance=section)
    return render(request, 'inventory/edit_section.html', {'form': form})

# Funcția de ștergere a secțiunilor
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def delete_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    if request.method == 'POST':
        section.delete()
        return redirect('section_list')
    return render(request, 'inventory/delete_section.html', {'section': section})




# Vizualizare pentru adăugarea unei noi cutii (Box)
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def export_data(request):
    # Export pentru Box-uri
    boxes = Box.objects.all()
    boxes_data = []
    for box in boxes:
        boxes_data.append({
            "name": box.name,
            "color": box.color,
            "status": box.status,
            "price": box.price,
            # "section": box.section.code sau nume_custom – alegi ce e mai potrivit
            "section": box.section.nume_custom if box.section else None,
        })

    # Export pentru Secțiuni
    sections = Section.objects.all()
    sections_data = []
    for sec in sections:
        sections_data.append({
            "nume_custom": sec.nume_custom,
            "tip_sectie": sec.tip_sectie,
            "max_capacity": sec.max_capacity,
        })

    # Combinăm datele într-un singur dicționar
    data = {
        "boxes": boxes_data,
        "sections": sections_data,
    }
    response = HttpResponse(
        json.dumps(data, indent=4),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="export_data.json"'
    return response


# Vizualizare pentru adăugarea unei noi cutii (Box)
@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def import_data(request):
    if request.method == "POST":
        # Presupunem că avem un input file cu numele 'json_file'
        json_file = request.FILES.get('json_file')
        if not json_file:
            messages.error(request, "Nu a fost selectat niciun fișier!")
            return redirect('import_data')
        try:
            data = json.load(json_file)
        except Exception as e:
            messages.error(request, "Eroare la citirea fișierului JSON: " + str(e))
            return redirect('import_data')
        
        # Import pentru Secțiuni (mai întâi importăm secțiunile, apoi le putem asocia cutiilor)
        sections_mapping = {}
        for sec_data in data.get("sections", []):
            section, created = Section.objects.get_or_create(
                nume_custom=sec_data["nume_custom"],
                defaults={
                    "tip_sectie": sec_data.get("tip_sectie", "unknown"),
                    "max_capacity": sec_data.get("max_capacity", 0),
                    "current_capacity": 0,
                }
            )
            sections_mapping[section.nume_custom] = section
        
        # Import pentru Box-uri
        for box_data in data.get("boxes", []):
            # Găsim secțiunea după nume; dacă nu se găsește, se poate seta None sau un fallback (ex: secțiunea 'unknown')
            sec_name = box_data.get("section")
            section = sections_mapping.get(sec_name)
            # Creăm obiectul Box fără a specifica code, image, added_date sau sold_date
            Box.objects.create(
                name=box_data["name"],
                color=box_data["color"],
                status=box_data["status"],
                price=box_data["price"],
                section=section,
            )
        messages.success(request, "Datele au fost importate cu succes!")
        return redirect('import_data')
    return render(request, "inventory/import_data.html")

