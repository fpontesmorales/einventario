from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max, Count
from inventarios.models import Vistoria

class Command(BaseCommand):
    help = "Deduplica vistorias por (bem, inventario), mantendo a mais recente."

    def handle(self, *args, **opts):
        dups = (
            Vistoria.objects
            .values("bem_id", "inventario_id")
            .annotate(total=Count("id"), max_id=Max("id"))
            .filter(total__gt=1)
        )
        total_dups = dups.count()
        self.stdout.write(self.style.WARNING(f"Conjuntos duplicados: {total_dups}"))
        removed = 0

        with transaction.atomic():
            for g in dups:
                bem_id = g["bem_id"]
                inv_id = g["inventario_id"]
                keep_id = g["max_id"]  # mantém a mais recente (id maior)
                extras = (
                    Vistoria.objects
                    .filter(bem_id=bem_id, inventario_id=inv_id)
                    .exclude(id=keep_id)
                )
                count = extras.count()
                if count:
                    # TODO: migrar relacionamentos se necessário, antes de deletar
                    extras.delete()
                    removed += count

        self.stdout.write(self.style.SUCCESS(f"Removidas {removed} vistorias duplicadas."))
