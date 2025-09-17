import os
from io import BytesIO
from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except Exception:
    PIL_OK = False

User = get_user_model()


class Inventario(models.Model):
    ano = models.PositiveIntegerField()
    ativo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-ativo", "-ano"]

    def __str__(self):
        return f"{self.ano}"


class Importacao(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    arquivo_nome = models.CharField(max_length=255, blank=True, default="")
    aplicado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    novos = models.PositiveIntegerField(default=0)
    atualizados = models.PositiveIntegerField(default=0)
    movidos = models.PositiveIntegerField(default=0)
    baixados = models.PositiveIntegerField(default=0)
    reativados = models.PositiveIntegerField(default=0)
    sem_mudanca = models.PositiveIntegerField(default=0)
    ausentes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        lab = "aplicada" if self.aplicado else "simulada"
        return f"ImportaÃ§Ã£o {lab} {self.criado_em:%d/%m/%Y %H:%M}"


class ImportacaoItem(models.Model):
    class Acao(models.TextChoices):
        NOVO = "NOVO", "Novo"
        ATUALIZADO = "ATUALIZADO", "Atualizado"
        MOVIDO = "MOVIDO", "Movido"
        BAIXADO = "BAIXADO", "Baixado"
        REATIVADO = "REATIVADO", "Reativado"
        SEM_MUDANCA = "SEM_MUDANCA", "Sem MudanÃ§a"
        AUSENTE = "AUSENTE", "Ausente"

    importacao = models.ForeignKey(Importacao, on_delete=models.CASCADE, related_name="itens")
    tombamento = models.CharField(max_length=50)
    acao = models.CharField(max_length=20, choices=Acao.choices)
    diff = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.tombamento} - {self.acao}"


class Vistoria(models.Model):
    class Status(models.TextChoices):
        CONFERIDO = "CONFERIDO", "Conferido"
        DIVERGENTE = "DIVERGENTE", "Divergente"
        NAO_LOCALIZADO = "NAO_LOCALIZADO", "NÃ£o Localizado"
        SEM_REGISTRO = "SEM_REGISTRO", "Sem Registro"

    ESTADO_CHOICES = [
        ("OTIMO", "Ã“timo"),
        ("BOM", "Bom"),
        ("REGULAR", "Regular"),
        ("RUIM", "Ruim"),
        ("INSERVIVEL", "InservÃ­vel"),
    ]

    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="vistorias")
    bem = models.ForeignKey("patrimonio.Bem", on_delete=models.CASCADE, related_name="vistorias")
    sala_encontrada = models.ForeignKey("patrimonio.Sala", on_delete=models.SET_NULL, null=True, blank=True)
    vistoriador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    estado_encontrado = models.CharField(max_length=12, choices=ESTADO_CHOICES, blank=True, default="")
    responsavel_encontrado = models.CharField(max_length=120, blank=True, default="")
    observacao = models.CharField(max_length=255, blank=True, default="")
    foto = models.ImageField(upload_to="vistorias/", blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.bem.tombamento} - {self.status} ({self.inventario.ano})"

    def save(self, *args, **kwargs):
        # sÃ³ vamos aplicar marca d'Ã¡gua quando o arquivo de foto for novo neste save
        do_wm = False
        if PIL_OK and self.foto:
            if getattr(self, "_new_foto_uploaded", False) or (self._state.adding and self.foto):
                do_wm = True
        # limpa o hint para chamadas subsequentes
        if hasattr(self, "_new_foto_uploaded"):
            try:
                delattr(self, "_new_foto_uploaded")
            except Exception:
                pass

        super().save(*args, **kwargs)

        if do_wm and self.foto and os.path.exists(getattr(self.foto, "path", "")):
            try:
                self._aplicar_marca_dagua()
            except Exception:
                pass

    def _aplicar_marca_dagua(self):
        img = Image.open(self.foto.path).convert("RGBA")
        w, h = img.size

        # fonte
        font_size = max(int(w * 0.042), 22)
        font = None
        try_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        ]
        for p in try_paths:
            try:
                if os.path.exists(p):
                    font = ImageFont.truetype(p, font_size)
                    break
                else:
                    font = ImageFont.truetype(p, font_size)
                    break
            except Exception:
                font = None
        if not font:
            font = ImageFont.load_default()

        # textos wrap
        info_raw = [
            f"Tombamento: {self.bem.tombamento}",
            f"Sala: {self.sala_encontrada or '-'}",
            f"Vistoriador: {self.vistoriador or '-'}",
            f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ]

        padding_x = 18
        padding_y = 10
        max_w = w - padding_x * 2
        line_spacing = 6

        def wrap(text):
            words = str(text).split()
            lines = []
            cur = ""
            for word in words:
                test = (cur + " " + word).strip()
                try:
                    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), test, font=font)
                    tw = bbox[2] - bbox[0]
                except Exception:
                    tw = len(test) * font_size * 0.6
                if tw <= max_w:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
            if cur:
                lines.append(cur)
            return lines

        lines = []
        for t in info_raw:
            lines.extend(wrap(t))

        try:
            bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), "Ag", font=font)
            lh = bbox[3] - bbox[1]
        except Exception:
            lh = font_size + 6
        band_h = max(padding_y * 2 + len(lines) * (lh + line_spacing), max(int(h * 0.18), 90))

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([0, h - band_h, w, h], fill=(0, 0, 0, 200))

        y = h - band_h + padding_y
        for line in lines:
            try:
                draw.text(
                    (padding_x, y),
                    line,
                    font=font,
                    fill=(255, 255, 255, 255),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0, 255),
                )
                bbox = draw.textbbox((0, 0), line, font=font)
                lh2 = bbox[3] - bbox[1]
            except Exception:
                draw.text((padding_x + 1, y + 1), line, font=font, fill=(0, 0, 0, 255))
                draw.text((padding_x, y), line, font=font, fill=(255, 255, 255, 255))
                lh2 = lh
            y += lh2 + line_spacing

        out = Image.alpha_composite(img, overlay).convert("RGB")
        buf = BytesIO()
        out.save(buf, format="JPEG", quality=88, optimize=True)
        buf.seek(0)
        nome = os.path.basename(self.foto.name)
        self.foto.save(nome, ContentFile(buf.read()), save=False)
        super().save(update_fields=["foto"])


class SemRegistro(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="sem_registro")
    sala_encontrada = models.ForeignKey("patrimonio.Sala", on_delete=models.SET_NULL, null=True, blank=True)
    vistoriador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tombamento_informado = models.CharField(max_length=50, blank=True, default="")
    descricao = models.CharField(max_length=255)
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    foto = models.ImageField(upload_to="sem_registro/", blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"SemRegistro {self.tombamento_informado or 's/ tombamento'} â€“ {self.descricao}"
