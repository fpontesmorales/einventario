import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from .models import Sala, Bem

def _norm_key(s: str) -> str:
    s = (s or "").strip().lower()
    try:
        import unicodedata
        s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    except Exception:
        pass
    s = s.replace(" ", "_").replace("-", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s

def _clean(v) -> str:
    return "" if v is None else str(v).strip()

def _parse_date(val):
    s = _clean(val)
    if not s: return None
    for fmt in ("%d/%m/%Y","%d/%m/%y","%d-%m-%Y","%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None

def _parse_decimal(val):
    s = _clean(val)
    if not s: 
        return None
    s = s.replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        last = max(s.rfind(","), s.rfind("."))
        if s[last] == ",":
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        right = s.split(",")[-1]
        if right.isdigit() and len(right) == 3 and s.split(",")[0].isdigit():
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif "." in s:
        right = s.split(".")[-1]
        if right.isdigit() and len(right) == 3 and s.split(".")[0].isdigit():
            s = s.replace(".", "")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None

def _status_to_bool(val):
    s = _clean(val).lower()
    falsy = {"baixado","baixa","excluido","exclusao","inservivel","inativo","baixa patrimonial"}
    if s in falsy:
        return False
    return True

def _is_livro(ed):
    s = _clean(ed).replace(" ", "")
    return s in {"4490.52.18", "4491.52.18"}

_MAP = {
    "numero": "tombamento",
    "status": "status_original",
    "ed": "ed",
    "conta_contabil": "conta_contabil",
    "descricao": "descricao",
    "rotulos": "rotulos",
    "carga_atual": "carga_atual",
    "setor_do_responsavel": "setor_responsavel",
    "campus_da_carga": "campus_carga",
    "carga_contabil": "carga_contabil",
    "valor_aquisicao": "valor_aquisicao",
    "valor_depreciado": "valor_depreciado",
    "numero_nota_fiscal": "numero_nota_fiscal",
    "numero_de_serie": "numero_serie",
    "data_da_entrada": "data_entrada",
    "data_da_carga": "data_carga",
    "fornecedor": "fornecedor",
    "sala": "sala_texto",
    "estado_de_conservacao": "estado_conservacao",
}

def _guess_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        return dialect.delimiter or ";"
    except Exception:
        return ";"

def _read_text(file) -> str:
    raw = file.read()
    if isinstance(raw, str):
        return raw
    for enc in ("cp1252","latin1","utf-8-sig","utf-8"):
        try:
            return raw.decode(enc, errors="strict")
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")

rx_paren = re.compile(r"^(?P<nome>.*?)\s*\((?P<bloco>[^)]+)\)\s*$")

def _parse_row_map(header, header_norm, pos, r):
    valores = {}
    for h_norm, campo in _MAP.items():
        i = pos.get(h_norm)
        if i is None or i >= len(r): 
            continue
        valores[campo] = _clean(r[i])
    valores["ativo_bool"] = _status_to_bool(valores.get("status_original", ""))
    valores["data_entrada"] = _parse_date(valores.get("data_entrada"))
    valores["data_carga"] = _parse_date(valores.get("data_carga"))
    if "valor_aquisicao" in valores:
        valores["valor_aquisicao"] = _parse_decimal(valores["valor_aquisicao"])
    if "valor_depreciado" in valores:
        valores["valor_depreciado"] = _parse_decimal(valores["valor_depreciado"])
    # sala/bloco
    sala_txt = valores.get("sala_texto") or ""
    sala_nome, sala_bloco = sala_txt, ""
    m = rx_paren.match(sala_txt)
    if m:
        sala_nome = (m.group("nome") or "").strip()
        sala_bloco = (m.group("bloco") or "").strip()
    valores["sala_nome"] = sala_nome
    valores["sala_bloco"] = sala_bloco
    # tipo por ED
    valores["tipo"] = "LIVRO" if _is_livro(valores.get("ed")) else "BEM"
    # extras
    usados = set(_MAP.keys())
    extras = {}
    for idx, col_nome in enumerate(header):
        if idx >= len(r): 
            continue
        if _norm_key(col_nome) in usados or col_nome.strip() in {"#", "n", "№"}:
            continue
        extras[col_nome] = _clean(r[idx])
    valores["extras"] = extras
    return valores

def _load_csv(file):
    text = _read_text(file)
    delim = _guess_delimiter(text[:4096])
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    if not rows:
        return None
    header = rows[0]; data = rows[1:]
    if header and header[0].strip() in {"#", "n", "№"}:
        header = header[1:]; data = [r[1:] for r in data]
    header_norm = [_norm_key(h) for h in header]
    pos = {h: i for i, h in enumerate(header_norm)}
    return header, header_norm, pos, data

def simular_bens_csv(file):
    loaded = _load_csv(file)
    if not loaded: 
        return {"novos":0,"atualizados":0,"movidos":0,"baixados":0,"reativados":0,"sem_mudanca":0,"ausentes":0}, []
    header, header_norm, pos, data = loaded
    present = set()
    res = {"novos":0,"atualizados":0,"movidos":0,"baixados":0,"reativados":0,"sem_mudanca":0,"ausentes":0}
    exemplos = []
    for r in data:
        i_tomb = pos.get("numero")
        tomb = _clean(r[i_tomb]) if i_tomb is not None and i_tomb < len(r) else ""
        if not tomb: continue
        present.add(tomb)
        vals = _parse_row_map(header, header_norm, pos, r)
        try:
            b = Bem.objects.select_related("sala_oficial").get(tombamento=tomb)
            mud = {}
            moved = False
            campos = [
                ("descricao", b.descricao, vals.get("descricao") or "(sem descricao)"),
                ("numero_serie", b.numero_serie, vals.get("numero_serie","")),
                ("status_original", b.status_original, vals.get("status_original","")),
                ("ativo", b.ativo, bool(vals.get("ativo_bool"))),
                ("tipo", b.tipo, vals.get("tipo","BEM")),
                ("conta_contabil", b.conta_contabil, vals.get("conta_contabil","")),
                ("rotulos", b.rotulos, vals.get("rotulos","")),
                ("carga_atual", b.carga_atual, vals.get("carga_atual","")),
                ("setor_responsavel", b.setor_responsavel, vals.get("setor_responsavel","")),
                ("campus_carga", b.campus_carga, vals.get("campus_carga","")),
                ("carga_contabil", b.carga_contabil, vals.get("carga_contabil","")),
                ("valor_aquisicao", b.valor_aquisicao, vals.get("valor_aquisicao", None)),
                ("valor_depreciado", b.valor_depreciado, vals.get("valor_depreciado", None)),
                ("numero_nota_fiscal", b.numero_nota_fiscal, vals.get("numero_nota_fiscal","")),
                ("data_entrada", b.data_entrada, vals.get("data_entrada", None)),
                ("data_carga", b.data_carga, vals.get("data_carga", None)),
                ("fornecedor", b.fornecedor, vals.get("fornecedor","")),
                ("sala_texto", b.sala_texto, vals.get("sala_texto","")),
                ("estado_conservacao", b.estado_conservacao, vals.get("estado_conservacao","")),
                ("ed", b.ed, vals.get("ed","")),
            ]
            for campo, old, new in campos:
                if old != new:
                    mud[campo] = {"de": old, "para": new}
            sala_nome, sala_bloco = vals.get("sala_nome"), vals.get("sala_bloco")
            if sala_nome:
                old_repr = str(b.sala_oficial) if b.sala_oficial_id else ""
                new_repr = f"{sala_nome} ({sala_bloco})" if sala_bloco else sala_nome
                if old_repr != new_repr:
                    mud["sala_oficial"] = {"de": old_repr, "para": new_repr}
                    moved = True
            if b.ativo and not bool(vals.get("ativo_bool")):
                res["baixados"] += 1
            if (not b.ativo) and bool(vals.get("ativo_bool")):
                res["reativados"] += 1
            if mud:
                res["atualizados"] += 1
                if moved: res["movidos"] += 1
                if len(exemplos) < 20:
                    exemplos.append({"tombamento": tomb, "acao": "ATUALIZADO" if not moved else "MOVIDO", "mudancas": mud})
            else:
                res["sem_mudanca"] += 1
        except Bem.DoesNotExist:
            res["novos"] += 1
            if len(exemplos) < 20:
                exemplos.append({"tombamento": tomb, "acao": "NOVO", "mudancas": {"novo": True}})
    existentes = set(Bem.objects.values_list("tombamento", flat=True))
    res["ausentes"] = len(existentes - present)
    return res, exemplos

@transaction.atomic
def importar_bens_csv(file, usuario=None, arquivo_nome=""):
    from inventarios.models import Importacao, ImportacaoItem
    loaded = _load_csv(file)
    if not loaded:
        return {"novos":0,"atualizados":0,"movidos":0,"baixados":0,"reativados":0,"sem_mudanca":0,"ausentes":0}
    header, header_norm, pos, data = loaded
    present = set()
    res = {"novos":0,"atualizados":0,"movidos":0,"baixados":0,"reativados":0,"sem_mudanca":0,"ausentes":0}
    imp = Importacao.objects.create(usuario=usuario, arquivo_nome=arquivo_nome or "")
    for r in data:
        i_tomb = pos.get("numero")
        tomb = _clean(r[i_tomb]) if i_tomb is not None and i_tomb < len(r) else ""
        if not tomb: continue
        present.add(tomb)
        vals = _parse_row_map(header, header_norm, pos, r)
        sala = None
        if vals.get("sala_nome"):
            sala, _ = Sala.objects.get_or_create(nome=vals["sala_nome"], bloco=vals.get("sala_bloco",""))
        try:
            b = Bem.objects.select_related("sala_oficial").get(tombamento=tomb)
            mud = {}
            def set_if_diff(field, new):
                old = getattr(b, field)
                if old != new:
                    mud[field] = {"de": old, "para": new}
                    setattr(b, field, new)
            set_if_diff("descricao", vals.get("descricao") or "(sem descricao)")
            set_if_diff("numero_serie", vals.get("numero_serie",""))
            set_if_diff("status_original", vals.get("status_original",""))
            novo_ativo = bool(vals.get("ativo_bool"))
            if b.ativo and not novo_ativo:
                res["baixados"] += 1
                set_if_diff("ativo", False)
                if not b.baixado_em:
                    b.baixado_em = timezone.now().date()
            elif (not b.ativo) and novo_ativo:
                res["reativados"] += 1
                set_if_diff("ativo", True)
                b.baixado_em = None
            set_if_diff("tipo", vals.get("tipo","BEM"))
            set_if_diff("conta_contabil", vals.get("conta_contabil",""))
            set_if_diff("rotulos", vals.get("rotulos",""))
            set_if_diff("carga_atual", vals.get("carga_atual",""))
            set_if_diff("setor_responsavel", vals.get("setor_responsavel",""))
            set_if_diff("campus_carga", vals.get("campus_carga",""))
            set_if_diff("carga_contabil", vals.get("carga_contabil",""))
            set_if_diff("valor_aquisicao", vals.get("valor_aquisicao", None))
            set_if_diff("valor_depreciado", vals.get("valor_depreciado", None))
            set_if_diff("numero_nota_fiscal", vals.get("numero_nota_fiscal",""))
            set_if_diff("data_entrada", vals.get("data_entrada", None))
            set_if_diff("data_carga", vals.get("data_carga", None))
            set_if_diff("fornecedor", vals.get("fornecedor",""))
            set_if_diff("sala_texto", vals.get("sala_texto",""))
            set_if_diff("estado_conservacao", vals.get("estado_conservacao",""))
            set_if_diff("ed", vals.get("ed",""))
            if sala and (not b.sala_oficial_id or b.sala_oficial_id != sala.id):
                old_repr = str(b.sala_oficial) if b.sala_oficial_id else ""
                b.sala_oficial = sala
                mud["sala_oficial"] = {"de": old_repr, "para": str(sala)}
                res["movidos"] += 1
            if mud:
                res["atualizados"] += 1
                b.info_extra = vals.get("extras", {})
                b.ultima_atualizacao_csv = timezone.now()
                b.ausente_no_ultimo_csv = False
                b.save()
                ImportacaoItem.objects.create(importacao=imp, tombamento=tomb, acao="ATUALIZADO", mudancas=mud)
            else:
                res["sem_mudanca"] += 1
                ImportacaoItem.objects.create(importacao=imp, tombamento=tomb, acao="SEM_MUDANCA", mudancas={})
        except Bem.DoesNotExist:
            b = Bem.objects.create(
                tombamento=tomb,
                descricao=vals.get("descricao") or "(sem descricao)",
                numero_serie=vals.get("numero_serie",""),
                sala_oficial=sala,
                ativo=bool(vals.get("ativo_bool")),
                tipo=vals.get("tipo","BEM"),
                status_original=vals.get("status_original",""),
                ed=vals.get("ed",""),
                conta_contabil=vals.get("conta_contabil",""),
                rotulos=vals.get("rotulos",""),
                carga_atual=vals.get("carga_atual",""),
                setor_responsavel=vals.get("setor_responsavel",""),
                campus_carga=vals.get("campus_carga",""),
                carga_contabil=vals.get("carga_contabil",""),
                valor_aquisicao=vals.get("valor_aquisicao", None),
                valor_depreciado=vals.get("valor_depreciado", None),
                numero_nota_fiscal=vals.get("numero_nota_fiscal",""),
                data_entrada=vals.get("data_entrada", None),
                data_carga=vals.get("data_carga", None),
                fornecedor=vals.get("fornecedor",""),
                sala_texto=vals.get("sala_texto",""),
                estado_conservacao=vals.get("estado_conservacao",""),
                info_extra=vals.get("extras", {}),
                ultima_atualizacao_csv=timezone.now(),
                ausente_no_ultimo_csv=False,
            )
            res["novos"] += 1
            ImportacaoItem.objects.create(importacao=imp, tombamento=tomb, acao="NOVO", mudancas={"novo": True})
    existentes = set(Bem.objects.values_list("tombamento", flat=True))
    ausentes_set = existentes - present
    res["ausentes"] = len(ausentes_set)
    from inventarios.models import ImportacaoItem
    Bem.objects.filter(tombamento__in=present).update(ausente_no_ultimo_csv=False, ultima_atualizacao_csv=timezone.now())
    Bem.objects.exclude(tombamento__in=present).update(ausente_no_ultimo_csv=True)
    for tomb in list(ausentes_set)[:200]:
        ImportacaoItem.objects.create(importacao=imp, tombamento=tomb, acao="AUSENTE", mudancas={})
    for k, v in res.items():
        setattr(imp, k, v)
    imp.aplicado = True
    imp.save(update_fields=["novos","atualizados","movidos","baixados","reativados","sem_mudanca","ausentes","aplicado"])
    return res
