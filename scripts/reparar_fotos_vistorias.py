import os
import sys
from pathlib import Path

# adiciona o diretório do projeto (onde fica manage.py) no sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in map(str, sys.path):
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "einventario.settings")

import django
django.setup()

from django.core.files.storage import default_storage
from inventarios.models import Vistoria

def candidatos_para(name: str):
    name = name.replace("\\", "/")
    base, ext = os.path.splitext(name)
    bfile = os.path.splitext(os.path.basename(name))[0]
    folder = os.path.dirname(name) or "vistorias"
    cand = [
        name,
        f"{base}_wm.jpg",
        f"{base}_wm.jpeg",
        f"{base}.jpg",
        f"{base}.jpeg",
        name.replace(".JPG", ".jpg"),
        name.replace(".JPEG", ".jpg"),
        name.replace(".PNG",  ".jpg"),
        name.replace(".png",  ".jpg"),
    ]
    try:
        dirs, files = default_storage.listdir(folder)
        low = bfile.lower()
        for f in files:
            fname = f.lower()
            if fname.startswith(low) or fname.startswith(low + "_wm"):
                if fname.endswith(".jpg") or fname.endswith(".jpeg"):
                    cand.insert(0, f"{folder}/{f}")
                else:
                    cand.append(f"{folder}/{f}")
    except Exception:
        pass
    seen = set()
    out = []
    for c in cand:
        k = c.lower()
        if k not in seen:
            out.append(c)
            seen.add(k)
    return out

ajustadas = 0
ausentes  = []

qs = Vistoria.objects.exclude(foto="").exclude(foto__isnull=True)
for v in qs:
    name = (v.foto.name or "").replace("\\", "/")
    if not name:
        continue
    if default_storage.exists(name):
        continue
    novo = None
    for c in candidatos_para(name):
        if default_storage.exists(c):
            novo = c
            break
    if novo:
        v.foto.name = novo
        v.save(update_fields=["foto"])
        ajustadas += 1
    else:
        ausentes.append(name)

print(f"ajustadas: {ajustadas}, ausentes: {len(ausentes)}")
if ausentes:
    print("exemplos ausentes:")
    for m in ausentes[:30]:
        print(" -", m)