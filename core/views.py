from django.shortcuts import render

def home_view(request):
    return render(request, 'home.html')

def venue_list(request):
    venues = [
        {
            "id": 1,
            "name": "Jakarta Convention Center",
            "address": "Jl. Gatot Subroto No.1, Jakarta",
            "city": "Jakarta",
            "capacity": 1000,
            "has_reserved_seating": True,
        },
        {
            "id": 2,
            "name": "Taman Impian Jaya Ancol",
            "address": "Jl. Lodan Timur No.7, Jakarta Utara",
            "city": "Jakarta",
            "capacity": 500,
            "has_reserved_seating": False,
        },
    ]

    return render(request, "venue/venue_list.html", {
        "role": "admin",
        "venues": venues,
    })

semua_dummy_event = [
    {
        "title": "Konser Melodi Senja",
        "date": "2026-05-15",
        "time": "19:00",
        "venue": "Jakarta Convention Center",
        "artists": ["Fourtwnty", "Hindia"],
        "price": "250.000",
        "categories": ["VIP"],
        "icon": "🎵",
        "organizer_id": 1,
    },
    {
        "title": "Festival Seni Budaya",
        "date": "2026-05-22",
        "time": "10:00",
        "venue": "Taman Impian Jaya Ancol",
        "artists": ["Tulus"],
        "price": "150.000",
        "categories": ["Regular"],
        "icon": "🎨",
        "organizer_id": 1,
    },
    {
        "title": "Malam Akustik Bandung",
        "date": "2026-06-10",
        "time": "18:00",
        "venue": "Bandung Hall Center",
        "artists": ["Pamungkas", "Nadin Amizah"],
        "price": "350.000",
        "categories": ["VIP", "Regular"],
        "icon": "🎸",
        "organizer_id": 2,
    },
]

def event_list(request):
    # Customer: semua event, read-only
    events = semua_dummy_event
    return render(request, "event/event_list.html", {
        "role": "customer",
        "events": events,
    })


def my_event_list(request):
    # Organizer: hanya event miliknya
    events = [event for event in semua_dummy_event if event["organizer_id"] == 1]
    return render(request, "event/my_event_list.html", {
        "role": "organizer",
        "events": events,
    })


def admin_event_list(request):
    # Admin: semua event
    events = semua_dummy_event
    return render(request, "event/my_event_list.html", {
        "role": "admin",
        "events": events,
    })