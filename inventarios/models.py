import os
from io import BytesIO
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
from patrimonio.models import Bem, Sala
from django.contrib.auth import get_user_model


class Inventario(models.Model):
    ano = models.PositiveIntegerField(unique=True)
    inicio = models.DateField(null=True, blank=True)
    fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    def __str__(self): return str(self.ano)

class Vistoria(models.Model):
    class Status(models.TextChoices):
        CONFERIDO = "CONFERIDO", "Conferido"
        DIVERGENTE = "DIVERGENTE", "Divergente"
        NAO_LOCALIZADO = "NAO_LOCALIZADO", "Não Localizado"
        SEM_REGISTRO = "SEM_REGISTRO", "Sem Registro"
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    bem = models.ForeignKey(Bem, on_delete=models.CASCADE, related_name="vistorias")
    sala_encontrada = models.ForeignKey(Sala, on_delete=models.SET_NULL, null=True, blank=True)
    vistoriador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    observacao = models.TextField(blank=True, default="")
    foto = models.ImageField(upload_to="vistorias/", blank=True, null=True)
    foto_marcada = models.ImageField(upload_to="vistorias/", blank=True, null=True)
    foto_watermarked = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.bem.tombamento} @ {self.inventario.ano} – {self.status}"
    def save(self, *a, **k):
        super().save(*a, **k)
        if self.foto and not self.foto_watermarked:
            self._apply_watermark()
    def _apply_watermark(self):
        self.foto.open("rb")
        image = Image.open(self.foto).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        text = (f"Tomb: {self.bem.tombamento} | Sala: {self.sala_encontrada or self.bem.sala_oficial} | "
                f"Vistoriador: {self.vistoriador.username if self.vistoriador else '-'} | "
                f"Data: {timezone.localtime(self.criado_em).strftime('%d/%m/%Y %H:%M')}")
        try: font = ImageFont.truetype("arial.ttf", 22)
        except Exception: font = ImageFont.load_default()
        margin = 16; w, h = image.size
        text_w, text_h = draw.textbbox((0, 0), text, font=font)[2:]
        box_h = text_h + margin * 2
        draw.rectangle([(0, h - box_h), (w, h)], fill=(0, 0, 0, 140))
        draw.text((margin, h - box_h + margin), text, font=font, fill=(255, 255, 255, 255))
        composed = Image.alpha_composite(image, overlay).convert("RGB")
        buffer = BytesIO(); composed.save(buffer, format="JPEG", quality=90)
        file_content = ContentFile(buffer.getvalue())
        import os
        fname = os.path.splitext(self.foto.name)[0] + "_wm.jpg"
        self.foto_marcada.save(os.path.basename(fname), file_content, save=False)
        self.foto_watermarked = True
        super().save(update_fields=["foto_marcada", "foto_watermarked"])

class Importacao(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    arquivo_nome = models.CharField(max_length=255, blank=True, default="")
    novos = models.PositiveIntegerField(default=0)
    atualizados = models.PositiveIntegerField(default=0)
    movidos = models.PositiveIntegerField(default=0)
    baixados = models.PositiveIntegerField(default=0)
    reativados = models.PositiveIntegerField(default=0)
    sem_mudanca = models.PositiveIntegerField(default=0)
    ausentes = models.PositiveIntegerField(default=0)
    aplicado = models.BooleanField(default=True)
    def __str__(self): return f"Importação {self.id} – {self.criado_em:%d/%m/%Y %H:%M}"

class ImportacaoItem(models.Model):
    class Acao(models.TextChoices):
        NOVO = "NOVO", "Novo"
        ATUALIZADO = "ATUALIZADO", "Atualizado"
        MOVIDO = "MOVIDO", "Movido"
        BAIXADO = "BAIXADO", "Baixado"
        REATIVADO = "REATIVADO", "Reativado"
        SEM_MUDANCA = "SEM_MUDANCA", "Sem Mudança"
        AUSENTE = "AUSENTE", "Ausente"
    importacao = models.ForeignKey(Importacao, related_name="itens", on_delete=models.CASCADE)
    tombamento = models.CharField(max_length=50)
    acao = models.CharField(max_length=20, choices=Acao.choices)
    mudancas = models.JSONField(default=dict, blank=True)
    def __str__(self): return f"{self.tombamento} – {self.acao}"

class SemRegistro(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="sem_registro")
    sala_encontrada = models.ForeignKey("patrimonio.Sala", on_delete=models.SET_NULL, null=True, blank=True)
    vistoriador = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    tombamento_informado = models.CharField(max_length=50, blank=True, default="")
    descricao = models.CharField(max_length=255)
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    foto = models.ImageField(upload_to="sem_registro/", blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"SemRegistro {self.tombamento_informado or 's/ tombamento'} – {self.descricao}"

class SemRegistro(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="sem_registro")
    sala_encontrada = models.ForeignKey("patrimonio.Sala", on_delete=models.SET_NULL, null=True, blank=True)
    vistoriador = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    tombamento_informado = models.CharField(max_length=50, blank=True, default="")
    descricao = models.CharField(max_length=255)
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    foto = models.ImageField(upload_to="sem_registro/", blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"SemRegistro {self.tombamento_informado or 's/ tombamento'} – {self.descricao}"
