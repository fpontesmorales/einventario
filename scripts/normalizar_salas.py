ï»¿import os, sys, re
# garante que a pasta do projeto (onde fica manage.py) esteja no sys.path
THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # .../scripts
PROJECT_ROOT = os.path.dirname(THIS_DIR)                       # raiz do projeto
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "einventario.settings")
import django; django.setup()

from patrimonio.models import Sala, Bem

rx_paren = re.compile(r"^(?P<nome>.*?)\s*\((?P<bloco>[^)]+)\)\s*$")

ajustados = 0
for b in Bem.objects.select_related("sala_oficial").all():
    sala_txt = (b.sala_texto or "").strip()
    if not sala_txt:
        continue
    nome, bloco = sala_txt, ""
    m = rx_paren.match(sala_txt)
    if m:
        nome = (m.group("nome") or "").strip()
        bloco = (m.group("bloco") or "").strip()
    if not nome:
        continue
    sala, _ = Sala.objects.get_or_create(nome=nome, bloco=bloco)
    if not b.sala_oficial_id or (b.sala_oficial_id != sala.id):
        b.sala_oficial = sala
        b.save(update_fields=["sala_oficial"])
        ajustados += 1

# remover salas sem bens associados
orphans = Sala.objects.filter(bens_oficiais__isnull=True)
count_orphans = orphans.count()
orphans.delete()

print("Bens reassociados:", ajustados, "| Salas Ã³rfÃ£s removidas:", count_orphans)
