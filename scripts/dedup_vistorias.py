import os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in map(str, sys.path):
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "einventario.settings")

import django
django.setup()

from django.db import transaction
from django.core.files.storage import default_storage
from inventarios.models import Vistoria

def has_foto(v):
    try:
        name = (v.foto.name or "").strip()
    except Exception:
        name = ""
    return bool(name and default_storage.exists(name))

deleted = 0
kept = 0

with transaction.atomic():
    groups = {}
    to_delete = []
    # mais recente primeiro (id maior costuma ser mais novo)
    for v in Vistoria.objects.order_by("inventario_id", "bem_id", "-id"):
        key = (v.inventario_id, v.bem_id)
        if key not in groups:
            groups[key] = v
        else:
            keeper = groups[key]
            # se o atual tem foto e o keeper nÃ£o, trocamos o keeper
            if (not has_foto(keeper)) and has_foto(v):
                to_delete.append(keeper.id)
                groups[key] = v
            else:
                to_delete.append(v.id)
    if to_delete:
        Vistoria.objects.filter(id__in=to_delete).delete()
        deleted = len(to_delete)
    kept = len(groups)

print(f"grupos mantidos: {kept} | removidos (duplicatas): {deleted}")