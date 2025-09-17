from django.db import models

class Sala(models.Model):
    nome = models.CharField(max_length=120)
    bloco = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nome", "bloco"], name="unique_sala_nome_bloco")
        ]

    def __str__(self):
        return f"{self.nome} ({self.bloco})" if self.bloco else self.nome

class Bem(models.Model):
    class Tipo(models.TextChoices):
        BEM = "BEM", "Bem"
        LIVRO = "LIVRO", "Livro"

    tombamento = models.CharField(max_length=50, unique=True)
    descricao = models.CharField(max_length=255)
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    sala_oficial = models.ForeignKey(Sala, on_delete=models.SET_NULL, null=True, related_name="bens_oficiais")
    ativo = models.BooleanField(default=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.BEM)

    status_original = models.CharField(max_length=60, blank=True, default="")
    ed = models.CharField(max_length=30, blank=True, default="")
    conta_contabil = models.CharField(max_length=80, blank=True, default="")
    rotulos = models.CharField(max_length=255, blank=True, default="")
    carga_atual = models.CharField(max_length=120, blank=True, default="")
    setor_responsavel = models.CharField(max_length=120, blank=True, default="")
    campus_carga = models.CharField(max_length=120, blank=True, default="")
    carga_contabil = models.CharField(max_length=120, blank=True, default="")
    valor_aquisicao = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valor_depreciado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    numero_nota_fiscal = models.CharField(max_length=60, blank=True, default="")
    data_entrada = models.DateField(null=True, blank=True)
    data_carga = models.DateField(null=True, blank=True)
    fornecedor = models.CharField(max_length=255, blank=True, default="")
    sala_texto = models.CharField(max_length=120, blank=True, default="")
    estado_conservacao = models.CharField(max_length=120, blank=True, default="")

    baixado_em = models.DateField(null=True, blank=True)
    ausente_no_ultimo_csv = models.BooleanField(default=False)
    ultima_atualizacao_csv = models.DateTimeField(null=True, blank=True)

    info_extra = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Bens"

    def __str__(self):
        return f"{self.tombamento} – {self.descricao}"
