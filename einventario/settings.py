from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
ALLOWED_HOSTS = ["*"]  # DEV apenas


INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts",
    "patrimonio",
    "inventarios",
    "mobile",
    "relatorios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "einventario.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "einventario.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "einventario" / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

JAZZMIN_SETTINGS = {
    "site_title": "e-InventÃ¡rio IFCE",
    "site_header": "e-InventÃ¡rio IFCE",
    "welcome_sign": "IFCE Campus Caucaia",
}

# FormataÃ§Ã£o numÃ©rica (pt-BR)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
DEBUG = True
ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost"]

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/vistoria/"
LOGOUT_REDIRECT_URL = "/admin/login/"
# formato numÃ©rico
USE_THOUSAND_SEPARATOR = False
NUMBER_GROUPING = 0

# --- Jazzmin: link 'DivergÃªncias' no menu ---
try:
    JAZZMIN_SETTINGS
except NameError:
    JAZZMIN_SETTINGS = {}

JAZZMIN_SETTINGS.setdefault("topmenu_links", [])
if not any(isinstance(x, dict) and x.get("url") == "inventarios:relatorio_divergencias" for x in JAZZMIN_SETTINGS["topmenu_links"]):
    JAZZMIN_SETTINGS["topmenu_links"].append({
        "name": "DivergÃªncias",
        "url": "inventarios:relatorio_divergencias",
        "permissions": ["inventarios.view_vistoria"],
    })

JAZZMIN_SETTINGS.setdefault("custom_links", {})
JAZZMIN_SETTINGS["custom_links"].setdefault("inventarios", [])
if not any(isinstance(x, dict) and x.get("url") == "inventarios:relatorio_divergencias" for x in JAZZMIN_SETTINGS["custom_links"]["inventarios"]):
    JAZZMIN_SETTINGS["custom_links"]["inventarios"].append({
        "name": "RelatÃ³rio de DivergÃªncias",
        "url": "inventarios:relatorio_divergencias",
        "permissions": ["inventarios.view_vistoria"],
    })
# ---------------------------------------------
# --- templates dir raiz ---
from pathlib import Path
try:
    BASE_DIR
except NameError:
    BASE_DIR = Path(__file__).resolve().parent.parent
try:
    TEMPLATES
    if isinstance(TEMPLATES, (list, tuple)) and TEMPLATES:
        _dirs = TEMPLATES[0].get("DIRS", [])
        _root = str(BASE_DIR / "templates")
        if _root not in [str(Path(p)) for p in _dirs]:
            TEMPLATES[0]["DIRS"] = list(_dirs) + [BASE_DIR / "templates"]
except Exception:
    pass
# --------------------------
from pathlib import Path
try:
    BASE_DIR
except NameError:
    BASE_DIR = Path(__file__).resolve().parent.parent
try:
    TEMPLATES
    if isinstance(TEMPLATES, (list, tuple)) and TEMPLATES:
        D = TEMPLATES[0].get('DIRS', [])
        P = BASE_DIR / 'templates'
        # compara por string para evitar objetos Path diferentes
        if str(P) not in [str(x) for x in D]:
            TEMPLATES[0]['DIRS'] = [P] + list(D)
except Exception:
    pass
# --- Jazzmin: link "Prévia de Importação" ---
try:
    JAZZMIN_SETTINGS
except NameError:
    JAZZMIN_SETTINGS = {}

JAZZMIN_SETTINGS.setdefault("topmenu_links", [])
if not any(isinstance(x, dict) and x.get("url") == "inventarios:importacao_previa" for x in JAZZMIN_SETTINGS["topmenu_links"]):
    JAZZMIN_SETTINGS["topmenu_links"].append({
        "name": "Prévia de Importação",
        "url": "inventarios:importacao_previa",
        "permissions": ["inventarios.view_importacao"],
    })
# --- fim Jazzmin ---