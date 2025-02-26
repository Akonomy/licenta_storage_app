from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from apps.inventory.models import Box  # Dacă este necesar




from django.contrib.auth.decorators import login_required, user_passes_test




from .models import Container, SYMBOL_CHOICES,COLOR_CHOICES, ContainerEvent, Zone ,ZONE_TYPE_CHOICES 



def home(request):
    """
    Pagină de start pentru fizic_inventory care afișează carduri cu principalele acțiuni.
    """
    return render(request, 'fizic_inventory/home.html')







# ---- Container Views ----



@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def move_container(request, code):
    """
    Permite mutarea containerului într-o altă zonă.
    Parametrul 'code' reprezintă codul containerului.
    """
    container = get_object_or_404(Container, code=code)
    if request.method == 'POST':
        new_zone_id = request.POST.get('zona_id')
        new_zone = get_object_or_404(Zone, id=new_zone_id)
        container.move_to_zone(new_zone)
        messages.success(request, f"Container {container.code} a fost mutat în zona {new_zone.name}.")
        return redirect('fizic_inventory:container_detail', code=container.code)
    zonas = Zone.objects.all()
    return render(request, 'fizic_inventory/move_container.html', {'container': container, 'zonas': zonas})

   



@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def container_list(request):
    containers = Container.objects.all()
    return render(request, 'fizic_inventory/container_list.html', {'containers': containers})


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def container_detail(request, code):
    container = get_object_or_404(Container, code=code)
    events = container.events.all().order_by('-event_date')
    return render(request, 'fizic_inventory/container_detail.html', {'container': container, 'events': events})

@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def add_box_view(request):
    """
    Permite adăugarea unui container (opțiunea add box).
    Dacă se specifică un cod și acesta există, containerul este marcat ca returned.
    Permite, de asemenea, selectarea opțională a unei zone.
    Dacă zona nu este specificată, se alege automat:
      - În primul rând, se caută o zonă de tip 'receptie' cu locuri libere.
      - Dacă nu se găsește, se caută o zonă de tip 'depozit' cu locuri libere.
    """
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        color = request.POST.get('color')
        symbol = request.POST.get('symbol')
        zone_id = request.POST.get('zone')  # noul câmp pentru selectarea zonei

        # Determină zona: dacă e specificată, folosește-o; altfel, auto-assign
        if zone_id:
            zone = get_object_or_404(Zone, id=zone_id)
        else:
            zone = None
            # Caută zone de tip 'receptie'
            receptie_zones = Zone.objects.filter(type='receptie')
            for z in receptie_zones:
                if z.capacity > z.current_occupancy:
                    zone = z
                    break
            # Dacă nu s-a găsit nicio zonă de receptie, caută zone de tip 'depozit'
            if not zone:
                depozit_zones = Zone.objects.filter(type='depozit')
                for z in depozit_zones:
                    if z.capacity > z.current_occupancy:
                        zone = z
                        break

        if code:
            container, status = Container.add_box(code, color, symbol)
        else:
            # Dacă nu se specifică cod, se creează unul cu cod auto-generat.
            container = Container.objects.create(color=color, symbol=symbol, status='free')
            ContainerEvent.objects.create(
                container=container,
                event_type='assigned',
                notes="New container created with auto-generated code."
            )
            status = "created"
        # Asociază containerul cu zona determinată (dacă există)
        if zone:
            container.zone = zone
            container.save()
            zone.update_occupancy()

        messages.success(request, f"Container {container.code} {status}.")
        return redirect('fizic_inventory:container_detail', code=container.code)
    
    # Adaugă opțiunile pentru simbol, culoare și lista zonelor disponibile în context
    context = {
        'container_symbol_choices': SYMBOL_CHOICES,
        'container_color_choices': COLOR_CHOICES,
        'zones': Zone.objects.all(),  # opțional, poți filtra doar zonele relevante
    }
    return render(request, 'fizic_inventory/add_box.html', context)


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def check_box_view(request):
    """
    Permite verificarea unui container după cod (check box).
    Afișează detaliile dacă containerul există.
    """
    container = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        container = Container.check_box(code)
        if not container:
            messages.error(request, f"Container with code {code} not found.")
    return render(request, 'fizic_inventory/check_box.html', {'container': container})


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def reset_container_view(request, code):
    """
    Resetează un container (setează statusul la free, elimină box-ul și înregistrează evenimentul).
    """
    container = get_object_or_404(Container, code=code)
    container.reset()
    messages.success(request, f"Container {container.code} has been reset.")
    return redirect('fizic_inventory:container_detail', code=container.code)


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def edit_container_view(request, code):
    """
    Permite modificarea detaliilor unui container (culoare, simbol, virtual_box_code).
    """
    container = get_object_or_404(Container, code=code)
    if request.method == 'POST':
        container.color = request.POST.get('color', container.color)
        container.symbol = request.POST.get('symbol', container.symbol)
        container.virtual_box_code = request.POST.get('virtual_box_code', container.virtual_box_code)
        container.save()
        messages.success(request, f"Container {container.code} updated.")
        return redirect('fizic_inventory:container_detail', code=container.code)
    
    context = {
        'container': container,
        'container_symbol_choices': SYMBOL_CHOICES,
        'container_color_choices': COLOR_CHOICES,
    }
    return render(request, 'fizic_inventory/edit_container.html', context)


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def add_virtual_box_view(request, code):
    """
    Asociază un cod de cutie virtuală unui container.
    """
    container = get_object_or_404(Container, code=code)
    if request.method == 'POST':
        virtual_code = request.POST.get('virtual_box_code')
        container.add_virtual_box(virtual_code)
        messages.success(request, f"Virtual box code added to container {container.code}.")
        return redirect('fizic_inventory:container_detail', code=container.code)
    return render(request, 'fizic_inventory/add_virtual_box.html', {'container': container})


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def reset_container_defaults_view(request):
    """
    Resetează toate containerele la valorile implicite:
    status free, fără zone, fără box, fără virtual_box_code.
    """
    containers = Container.objects.all()
    for container in containers:
        container.status = 'free'
        container.zone = None
        container.box = None
        container.virtual_box_code = None
        container.save()
        ContainerEvent.objects.create(
            container=container,
            event_type='checkin',
            notes="Container reset to default values."
        )
    messages.success(request, "All containers have been reset to defaults.")
    return redirect('fizic_inventory:container_list')

# ---- Zone Views ----


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def add_zone_view(request):
    """
    Permite adăugarea unei noi zone.
    Dacă se specifică datele, creează o zonă cu un cod auto-generat.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        zone_type = request.POST.get('type', 'depozit')
        capacity = request.POST.get('capacity')
        if not name:
            messages.error(request, "Numele zonei este obligatoriu.")
            return redirect('fizic_inventory:add_zone')
        try:
            capacity = int(capacity)
        except (ValueError, TypeError):
            messages.error(request, "Capacitatea trebuie să fie un număr întreg.")
            return redirect('fizic_inventory:add_zone')
        
        zone = Zone.objects.create(name=name, type=zone_type, capacity=capacity)
        messages.success(request, f"Zone {zone.code} a fost adăugată cu succes.")
        return redirect('fizic_inventory:zone_detail', code=zone.code)
    
    context = {
        'zone_type_choices': ZONE_TYPE_CHOICES,
    }
    return render(request, 'fizic_inventory/add_zone.html', context)





@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def zone_list(request):
    zones = Zone.objects.all()
    return render(request, 'fizic_inventory/zone_list.html', {'zones': zones})


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def zone_detail(request, code):
    zone = get_object_or_404(Zone, code=code)
    containers = zone.containers.all()
    return render(request, 'fizic_inventory/zone_detail.html', {'zone': zone, 'containers': containers})


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def edit_zone_view(request, code):
    zone = get_object_or_404(Zone, code=code)
    if request.method == 'POST':
        zone.name = request.POST.get('name', zone.name)
        zone.type = request.POST.get('type', zone.type)
        zone.capacity = request.POST.get('capacity', zone.capacity)
        zone.save()
        messages.success(request, f"Zone {zone.code} updated.")
        return redirect('fizic_inventory:zone_detail', code=zone.code)
    context = {
        'zone': zone,
        'zone_type_choices': ZONE_TYPE_CHOICES,  # Transmiți opțiunile aici
    }
    return render(request, 'fizic_inventory/edit_zone.html', context)


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def clear_zone_view(request, code):
    """
    Resetează toate containerele din zona respectivă (clear zone).
    """
    zone = get_object_or_404(Zone, code=code)
    zone.clear_zone()
    messages.success(request, f"Zone {zone.code} has been cleared (all containers reset).")
    return redirect('fizic_inventory:zone_detail', code=zone.code)


@login_required
@user_passes_test(lambda u: u.has_page_access('admin'))
def reset_zone_defaults_view(request):
    """
    Resetează valorile implicite pentru toate zonele.
    (Ex.: setează tipul la 'depozit' și actualizează ocuparea)
    """
    zones = Zone.objects.all()
    for zone in zones:
        zone.type = 'depozit'
        zone.current_occupancy = zone.containers.count()
        zone.save()
    messages.success(request, "Zone defaults have been reset.")
    return redirect('fizic_inventory:zone_list')
