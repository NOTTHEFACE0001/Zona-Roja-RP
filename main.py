# ----------------------------------------------------------------------
# Copyright (C) 2026 Junior (NOT THE FACE / Player.banned).
# Todos los derechos reservados.
#
# El sistema de Registro Civil / Cédula de Identidad incluido en este
# archivo (sección "REGISTRO CIVIL — CÉDULA DE IDENTIDAD" más abajo) es
# propiedad intelectual exclusiva de:
# - Nombre de Usuario (Discord/Plataformas): Player.banned
# - Apodo Común: NOT THE FACE
# - Nombre de Rol: Junior
#
# Queda estrictamente prohibida la copia, traducción, modificación,
# distribución o replicación de este código y su lógica en otros
# servidores sin el consentimiento explícito y por escrito del autor.
# ----------------------------------------------------------------------
"""
LAS CONDES RP — BOT PRINCIPAL (archivo único)

Incluye:
  1) Apertura/cierre del servidor con encuesta de roles (/abrir, /cerrar, /estado)
  2) Registro Civil — Cédula de Identidad (/crear-cedula, /ver-cedula, etc.)

Para correrlo: python main.py
"""

import datetime
import json
import os
import random
import string
from threading import Thread

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

# ═════════════════════════════════════════════════════════════════════════
#  ENTORNO / CONFIGURACIÓN GENERAL
# ═════════════════════════════════════════════════════════════════════════

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Rol que se menciona al abrir la encuesta
NOTIFY_ROLE_ID = int(os.getenv("NOTIFY_ROLE_ID", "1524900084297371768"))

# Rol de Staff autorizado para /abrir y /cerrar (0 = solo Administradores)
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0")) or None

# Código de invitación del servidor -> discord.gg/<codigo>
INVITE_CODE = os.getenv("INVITE_CODE", "WzMAg")

# Meta de votos por defecto de la encuesta de apertura
VOTE_GOAL_DEFAULT = int(os.getenv("VOTE_GOAL_DEFAULT", "6"))

# Logo del embed de apertura. El link de Discord CDN caduca (?ex=...), así
# que si lo dejas vacío el bot simplemente no pone thumbnail en ese embed.
THUMBNAIL_URL = os.getenv("THUMBNAIL_URL", "")

EMBED_COLOR = 0x1F3A5F         # azul acorde al logo de Las Condes RP
EMBED_COLOR_CIERRE = 0xC0392B  # rojo para el mensaje de cierre

STATE_FILE = "poll_state.json"
DB_FILE = "cedula_database.json"

# Opciones de rol con sus emojis personalizados del servidor Las Condes RP
ROLE_OPTIONS = [
    {"label": "Carabineros de Chile", "emoji_name": "CarabinerosDeChile", "emoji_id": 1540566592285446195},
    {"label": "PDI", "emoji_name": "PDI", "emoji_id": 1540567772210266212},
    {"label": "SAMU", "emoji_name": "SAMU", "emoji_id": 1540566867415007323},
    {"label": "Ciudadano", "emoji_name": "Ciudadano", "emoji_id": 1540566722287767655},
    {"label": "Bomberos", "emoji_name": "BomberosChile", "emoji_id": 1540567027197157416},
]

VIP_ROLES = ["VIP", "Donador", "Donador+", "Staff", "Administrador", "Moderador", "Owner", "Dueño"]

# Paleta bandera Chile 🇨🇱 (usada en las cédulas)
COLOR_ROJO = 0xD52B1E
COLOR_AZUL = 0x0033A0

CREDIT_MSG = (
    "\n```\n"
    "# ----------------------------------------------------------------------\n"
    "# Copyright (C) 2026 Junior (NOT THE FACE / Player.banned).\n"
    "# Todos los derechos reservados.\n"
    "#\n"
    "# Este sistema de DNI es propiedad intelectual exclusiva de:\n"
    "# - Nombre de Usuario (Discord/Plataformas): Player.banned\n"
    "# - Apodo Común: NOT THE FACE\n"
    "# - Nombre de Rol: Junior\n"
    "#\n"
    "# Queda estrictamente prohibida la copia, traducción, modificación,\n"
    "# distribución o replicación de este código y su lógica en otros\n"
    "# servidores sin el consentimiento explícito y por escrito del autor.\n"
    "# ----------------------------------------------------------------------\n"
    "```"
)

# ═════════════════════════════════════════════════════════════════════════
#  KEEP-ALIVE (Render / Railway) — abre un puerto HTTP de salud
# ═════════════════════════════════════════════════════════════════════════

flask_app = Flask("las_condes_rp_bot")


@flask_app.route("/")
def home():
    return "🇨🇱 Las Condes RP Bot — Online"


def keep_alive():
    def run():
        port = int(os.environ.get("PORT", 8080))
        flask_app.run(host="0.0.0.0", port=port)

    Thread(target=run, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════
#  ESTADO DE LA ENCUESTA (persiste en un archivo JSON)
# ═════════════════════════════════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "cerrado",
        "message_id": None,
        "channel_id": None,
        "meta_votos": VOTE_GOAL_DEFAULT,
        "hora_apertura": None,
    }


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


state = load_state()

# ═════════════════════════════════════════════════════════════════════════
#  REGISTRO CIVIL — CÉDULA DE IDENTIDAD
#  (ver aviso de derechos de autor al inicio del archivo)
# ═════════════════════════════════════════════════════════════════════════

# ── Base de datos JSON ──────────────────────────────────────────────────

def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_cedula(uid: int) -> dict | None:
    return load_db().get(str(uid))


def set_cedula(uid: int, data: dict):
    db = load_db()
    db[str(uid)] = data
    save_db(db)


def del_cedula(uid: int):
    db = load_db()
    db.pop(str(uid), None)
    save_db(db)


# ── Utilidades ───────────────────────────────────────────────────────────

def calcular_edad(fecha_str: str) -> int | None:
    """Calcula edad exacta desde DD/MM/YYYY."""
    try:
        d, m, y = fecha_str.strip().split("/")
        nac = datetime.date(int(y), int(m), int(d))
        hoy = datetime.date.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except Exception:
        return None


def generar_rut() -> str:
    """Genera un RUT chileno simulado con dígito verificador correcto."""
    num = random.randint(5_000_000, 25_000_000)
    reversed_digits = [int(d) for d in reversed(str(num))]
    factors = [2, 3, 4, 5, 6, 7]
    total = sum(d * factors[i % 6] for i, d in enumerate(reversed_digits))
    resto = 11 - (total % 11)
    if resto == 11:
        dv = "0"
    elif resto == 10:
        dv = "K"
    else:
        dv = str(resto)
    s = str(num)
    return f"{s[:-6]}.{s[-6:-3]}.{s[-3:]}-{dv}"


def generar_num_serie() -> str:
    """Genera número de serie de cédula chilena simulado."""
    letra = random.choice(string.ascii_uppercase)
    nums = "".join(random.choices(string.digits, k=9))
    return f"{letra}{nums}"


def barcode(seed: str) -> str:
    random.seed(seed)
    return "".join(random.choice(["█", "▌", "│", "▐", "║", "▏", "▎", "▊"]) for _ in range(38))


async def get_roblox_avatar(username: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False},
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                users = data.get("data", [])
                if not users:
                    return None
                uid = users[0]["id"]

            async with s.get(
                "https://thumbnails.roblox.com/v1/users/avatar-headshot"
                f"?userIds={uid}&size=420x420&format=Png&isCircular=false"
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                thumbs = data.get("data", [])
                return thumbs[0].get("imageUrl") if thumbs else None
    except Exception:
        return None


def tiene_vip(member: discord.Member) -> bool:
    return any(r.name in VIP_ROLES for r in member.roles)


def logo(guild: discord.Guild | None) -> str | None:
    """Usa el ícono del propio servidor como logo (evita URLs fijas, que caducan)."""
    if guild and guild.icon:
        return guild.icon.url
    return None


class UserSession:
    _data: dict = {}

    @classmethod
    def set(cls, uid: int, data: dict):
        cls._data[uid] = data

    @classmethod
    def get(cls, uid: int) -> dict | None:
        return cls._data.get(uid)

    @classmethod
    def update(cls, uid: int, **kwargs):
        if uid in cls._data:
            cls._data[uid].update(kwargs)

    @classmethod
    def clear(cls, uid: int):
        cls._data.pop(uid, None)


# ── Embeds de la cédula ──────────────────────────────────────────────────

def embed_frente(ced: dict, avatar_url: str | None, guild: discord.Guild | None) -> discord.Embed:
    color_raw = ced.get("custom_color")
    color = int(color_raw, 16) if color_raw else COLOR_AZUL

    e = discord.Embed(color=color)
    icon = logo(guild)
    e.set_author(name="🇨🇱  REPÚBLICA DE CHILE  ·  CÉDULA DE IDENTIDAD", icon_url=icon)

    e.description = (
        "```ansi\n"
        "\u001b[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        "\u001b[1;37mSERVICIO DE REGISTRO CIVIL E IDENTIFICACIÓN\u001b[0m\n"
        "\u001b[0;36mLAS CONDES RP  ·  ROLEPLAY  ·  DOCUMENTO OFICIAL\u001b[0m\n"
        "\u001b[0;31m★ ★ ★  FRENTE  ★ ★ ★\u001b[0m\n"
        "\u001b[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        "```"
    )

    nombre = f"{ced['nombres']} {ced['apellidos']}"
    e.add_field(name="👤  NOMBRES Y APELLIDOS", value=f"```{nombre.upper()}```", inline=False)
    e.add_field(name="🪪  RUT", value=f"```{ced.get('rut', '—')}```", inline=True)
    e.add_field(name="📅  FECHA DE NACIMIENTO", value=f"```{ced['fecha_nacimiento']}```", inline=True)
    e.add_field(name="🔢  EDAD", value=f"```{ced['edad']} años```", inline=True)
    e.add_field(name="⚧️  SEXO", value=f"```{ced['sexo']}```", inline=True)
    e.add_field(name="🏙️  REGIÓN DE NACIMIENTO", value=f"```{ced['region_nacimiento']}```", inline=True)
    e.add_field(name="🇨🇱  NACIONALIDAD", value="```CHILENO/A```", inline=True)
    e.add_field(name="💼  OCUPACIÓN", value=f"```{ced['ocupacion']}```", inline=True)
    e.add_field(name="🎮  USUARIO ROBLOX", value=f"```{ced['roblox_username']}```", inline=True)
    e.add_field(name="📋  N° SERIE", value=f"```{ced.get('num_serie', '—')}```", inline=True)

    if ced.get("lema"):
        e.add_field(name="✨  LEMA PERSONAL", value=f"*\"{ced['lema']}\"*", inline=False)

    exp_año = datetime.date.today().year + 5
    e.set_footer(
        text=f"📅 Vencimiento: {exp_año}  ·  SRCeI  ·  Las Condes RP\n"
             f"🛡️ Sistema desarrollado por Player.banned (NOT THE FACE)  ·  © 2026",
        icon_url=icon,
    )

    if avatar_url:
        e.set_thumbnail(url=avatar_url)
    if ced.get("banner_url"):
        e.set_image(url=ced["banner_url"])

    return e


def embed_reverso(ced: dict, guild: discord.Guild | None) -> discord.Embed:
    color_raw = ced.get("custom_color")
    color = int(color_raw, 16) if color_raw else COLOR_ROJO

    e = discord.Embed(color=color)
    icon = logo(guild)
    e.set_author(name="🇨🇱  REGISTRO CIVIL — REVERSO DE CÉDULA  ·  LAS CONDES RP", icon_url=icon)

    e.description = (
        "```ansi\n"
        "\u001b[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        "\u001b[1;37mDATOS COMPLEMENTARIOS\u001b[0m\n"
        "\u001b[0;33mREVERSO  ·  LAS CONDES RP  ·  SRCeI\u001b[0m\n"
        "\u001b[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        "```"
    )

    e.add_field(name="💑  ESTADO CIVIL", value=f"```{ced.get('estado_civil', '—')}```", inline=True)
    e.add_field(name="🩸  GRUPO SANGUÍNEO", value=f"```{ced.get('tipo_sangre', '—')}```", inline=True)
    e.add_field(name="🪪  RUT", value=f"```{ced.get('rut', '—')}```", inline=True)

    mrz1 = f"IDCHL{ced.get('rut', '000000000').replace('.', '').replace('-', ''):20}"
    mrz2 = f"{ced['fecha_nacimiento'].replace('/', '')}{ced['sexo'][0].upper()}{''.join(random.choices(string.digits, k=7))}"
    nombre_apellido = f"{ced['apellidos'].upper()[:10]}<<{ced['nombres'].upper()[:10]}"
    e.add_field(
        name="🔍  MRZ — ZONA LEGIBLE POR MÁQUINA",
        value=f"```\n{mrz1[:30]}\n{mrz2[:30]}\n{nombre_apellido[:30]}\n```",
        inline=False,
    )

    e.add_field(
        name="▦  CÓDIGO DE BARRAS PDF417",
        value=f"```{barcode(ced.get('rut', 'LASCONDESRP'))}```",
        inline=False,
    )

    e.add_field(
        name="✍️  FIRMAS DE AUTORIDAD",
        value=(
            "```\n"
            f"Director SRCeI (RP):        {'_' * 22}\n"
            f"Oficial de Registro Civil:  {'_' * 22}\n"
            f"Autoridad Las Condes RP:    {'_' * 22}\n"
            "```"
        ),
        inline=False,
    )

    e.add_field(
        name="⚖️  AVISO LEGAL",
        value=(
            "*Documento de uso exclusivo para el servidor de roleplay **Las Condes RP**. "
            "Este documento es simulado y no tiene validez fuera del servidor. "
            "Su falsificación o mal uso será sancionado conforme al reglamento.*"
        ),
        inline=False,
    )

    e.set_footer(
        text=f"🔏 N° Serie: {ced.get('num_serie', '—')}  ·  Emitida: {ced.get('fecha_creacion', '—')}  ·  Las Condes RP\n"
             f"🛡️ Sistema desarrollado por Player.banned (NOT THE FACE)  ·  © 2026",
        icon_url=icon,
    )

    return e


# ── Views / Modales ──────────────────────────────────────────────────────

class CedulaView(discord.ui.View):
    def __init__(self, ced: dict, avatar_url: str | None, guild: discord.Guild | None, owner_id: int):
        super().__init__(timeout=300)
        self.ced = ced
        self.avatar = avatar_url
        self.guild = guild
        self.owner_id = owner_id
        self.cara = "frente"
        self.btn_frente.disabled = True

    def _build(self) -> discord.Embed:
        if self.cara == "frente":
            return embed_frente(self.ced, self.avatar, self.guild)
        return embed_reverso(self.ced, self.guild)

    @discord.ui.button(label="🪪 Ver Frente", style=discord.ButtonStyle.success)
    async def btn_frente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cara = "frente"
        self.btn_frente.disabled = True
        self.btn_reverso.disabled = False
        await interaction.response.edit_message(embed=self._build(), view=self)

    @discord.ui.button(label="🔄 Ver Reverso", style=discord.ButtonStyle.primary)
    async def btn_reverso(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cara = "reverso"
        self.btn_frente.disabled = False
        self.btn_reverso.disabled = True
        await interaction.response.edit_message(embed=self._build(), view=self)

    @discord.ui.button(label="🗑️ Cerrar", style=discord.ButtonStyle.danger)
    async def btn_cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("⛔ Solo quien usó el comando puede cerrarlo.", ephemeral=True)
            return
        await interaction.message.delete()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ModalDatosBase(discord.ui.Modal, title="🇨🇱 Registro Civil — Las Condes RP"):
    nombres = discord.ui.TextInput(label="Nombres", placeholder="Ej: Ignacio Andrés", max_length=50)
    apellidos = discord.ui.TextInput(label="Apellidos", placeholder="Ej: Muñoz Contreras", max_length=60)
    fecha_nacimiento = discord.ui.TextInput(
        label="Fecha de Nacimiento (DD/MM/YYYY)", placeholder="Ej: 23/09/1998", max_length=10
    )
    ocupacion = discord.ui.TextInput(
        label="Ocupación / Profesión", placeholder="Ej: Carabinero, Médico, Estudiante...", max_length=60
    )
    region_nacimiento = discord.ui.TextInput(
        label="Región de Nacimiento", placeholder="Ej: Región Metropolitana, Valparaíso...", max_length=60
    )

    async def on_submit(self, interaction: discord.Interaction):
        edad = calcular_edad(self.fecha_nacimiento.value)
        if edad is None or not (0 <= edad <= 120):
            await interaction.response.send_message(
                "❌ **Fecha inválida.** Usa el formato `DD/MM/YYYY`.\nEjemplo: `23/09/1998`", ephemeral=True
            )
            return

        UserSession.set(interaction.user.id, {
            "nombres": self.nombres.value.strip(),
            "apellidos": self.apellidos.value.strip(),
            "fecha_nacimiento": self.fecha_nacimiento.value.strip(),
            "ocupacion": self.ocupacion.value.strip(),
            "region_nacimiento": self.region_nacimiento.value.strip(),
            "edad": edad,
        })

        await interaction.response.send_message(
            "✅ **Paso 1 completado.**\n"
            "Ahora selecciona tu **Sexo**, **Estado Civil** y **Grupo Sanguíneo** en los menús de abajo.\n"
            "*(Al seleccionar los tres, avanzarás automáticamente al siguiente paso)*",
            ephemeral=True,
            view=SelectsView(interaction.user.id),
        )


OPT_SEXO = [
    discord.SelectOption(label="Masculino", value="Masculino", emoji="👨"),
    discord.SelectOption(label="Femenino", value="Femenino", emoji="👩"),
]
OPT_CIVIL = [
    discord.SelectOption(label="Soltero/a", value="Soltero/a", emoji="💔"),
    discord.SelectOption(label="Casado/a", value="Casado/a", emoji="💍"),
    discord.SelectOption(label="Divorciado/a", value="Divorciado/a", emoji="📜"),
    discord.SelectOption(label="Viudo/a", value="Viudo/a", emoji="🕊️"),
    discord.SelectOption(label="Conviviente", value="Conviviente", emoji="🤝"),
    discord.SelectOption(label="Separado/a", value="Separado/a", emoji="📋"),
]
OPT_SANGRE = [
    discord.SelectOption(label="A+", value="A+", emoji="🩸"),
    discord.SelectOption(label="A-", value="A-", emoji="🩸"),
    discord.SelectOption(label="B+", value="B+", emoji="🩸"),
    discord.SelectOption(label="B-", value="B-", emoji="🩸"),
    discord.SelectOption(label="AB+", value="AB+", emoji="🩸"),
    discord.SelectOption(label="AB-", value="AB-", emoji="🩸"),
    discord.SelectOption(label="O+", value="O+", emoji="🩸"),
    discord.SelectOption(label="O-", value="O-", emoji="🩸"),
]


class SelectsView(discord.ui.View):
    def __init__(self, uid: int):
        super().__init__(timeout=300)
        self.uid = uid
        self._sexo = None
        self._civil = None
        self._sangre = None

        self.sel_sexo = discord.ui.Select(placeholder="⚧️ Selecciona tu Sexo", options=OPT_SEXO, row=0)
        self.sel_civil = discord.ui.Select(placeholder="💑 Estado Civil", options=OPT_CIVIL, row=1)
        self.sel_sang = discord.ui.Select(placeholder="🩸 Grupo Sanguíneo", options=OPT_SANGRE, row=2)

        self.sel_sexo.callback = self._cb_sexo
        self.sel_civil.callback = self._cb_civil
        self.sel_sang.callback = self._cb_sang

        self.add_item(self.sel_sexo)
        self.add_item(self.sel_civil)
        self.add_item(self.sel_sang)

    def _status(self) -> str:
        sx = f"✅ **Sexo:** {self._sexo}" if self._sexo else "⬜ Sexo — pendiente"
        cv = f"✅ **Estado Civil:** {self._civil}" if self._civil else "⬜ Estado Civil — pendiente"
        sg = f"✅ **Grupo Sanguíneo:** {self._sangre}" if self._sangre else "⬜ Grupo Sanguíneo — pendiente"
        return f"Selecciona los tres campos para continuar:\n{sx}\n{cv}\n{sg}"

    async def _cb_sexo(self, interaction: discord.Interaction):
        self._sexo = self.sel_sexo.values[0]
        self.sel_sexo.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _cb_civil(self, interaction: discord.Interaction):
        self._civil = self.sel_civil.values[0]
        self.sel_civil.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _cb_sang(self, interaction: discord.Interaction):
        self._sangre = self.sel_sang.values[0]
        self.sel_sang.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _check(self, interaction: discord.Interaction):
        if not (self._sexo and self._civil and self._sangre):
            return
        UserSession.update(self.uid, sexo=self._sexo, estado_civil=self._civil, tipo_sangre=self._sangre)
        await interaction.followup.send(
            "✅ **Paso 2 completado.**\n"
            "Ahora ingresa tu **usuario de Roblox** para obtener tu foto de avatar en la cédula.",
            ephemeral=True,
            view=BotonRoblox(self.uid),
        )


class BotonRoblox(discord.ui.View):
    def __init__(self, uid: int):
        super().__init__(timeout=300)
        self.uid = uid

    @discord.ui.button(label="🎮 Introducir usuario de Roblox", style=discord.ButtonStyle.success)
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRoblox(self.uid))


class ModalRoblox(discord.ui.Modal, title="🎮 Usuario de Roblox — Paso Final"):
    roblox_username = discord.ui.TextInput(
        label="Tu nombre de usuario en Roblox", placeholder="Ej: xXChilePlayer123Xx", max_length=50
    )

    def __init__(self, uid: int):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        session = UserSession.get(self.uid)
        if not session:
            await interaction.followup.send("❌ Tu sesión expiró. Vuelve a usar `/crear-cedula`.", ephemeral=True)
            return

        roblox_user = self.roblox_username.value.strip()
        hoy = datetime.date.today().strftime("%d/%m/%Y")

        ced_data = {
            "nombres": session["nombres"],
            "apellidos": session["apellidos"],
            "fecha_nacimiento": session["fecha_nacimiento"],
            "edad": session["edad"],
            "sexo": session.get("sexo", "—"),
            "ocupacion": session["ocupacion"],
            "region_nacimiento": session["region_nacimiento"],
            "estado_civil": session.get("estado_civil", "—"),
            "tipo_sangre": session.get("tipo_sangre", "—"),
            "rut": generar_rut(),
            "num_serie": generar_num_serie(),
            "roblox_username": roblox_user,
            "fecha_creacion": hoy,
            "custom_color": None,
            "banner_url": None,
            "lema": None,
        }

        set_cedula(self.uid, ced_data)
        UserSession.clear(self.uid)

        nombre_completo = f"{session['nombres']} {session['apellidos']}"
        await interaction.followup.send(
            f"✅ **¡Cédula de Identidad creada exitosamente!**\n\n"
            f"**Nombre:** {nombre_completo.upper()}\n"
            f"**RUT:** {ced_data['rut']}\n"
            f"**Edad:** {session['edad']} años\n"
            f"**Región:** {session['region_nacimiento']}\n"
            f"**Roblox:** `{roblox_user}`\n\n"
            f"Usa `/ver-cedula` para ver tu documento con tu avatar. 🇨🇱" + CREDIT_MSG,
            ephemeral=True,
        )


class ModalPersonalizar(discord.ui.Modal, title="✨ Personalizar Cédula — VIP"):
    color_hex = discord.ui.TextInput(
        label="Color del Embed (HEX sin #)", placeholder="Ej: D52B1E  |  vacío = sin cambio",
        required=False, max_length=6,
    )
    banner_url = discord.ui.TextInput(
        label="URL de Banner / Imagen de Fondo", placeholder="https://i.imgur.com/...  (vacío = sin cambio)",
        required=False, max_length=300,
    )
    lema = discord.ui.TextInput(
        label="Lema o Frase de tu Personaje", placeholder="Ej: 'Por la razón o la fuerza.'",
        required=False, max_length=120,
    )
    roblox_username = discord.ui.TextInput(
        label="Actualizar Usuario de Roblox", placeholder="Nuevo nombre en Roblox (vacío = sin cambio)",
        required=False, max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        ced = get_cedula(interaction.user.id)
        if not ced:
            await interaction.response.send_message("❌ No tienes una cédula creada. Usa `/crear-cedula` primero.", ephemeral=True)
            return

        cambios = []
        if self.color_hex.value.strip():
            try:
                int(self.color_hex.value.strip(), 16)
                ced["custom_color"] = self.color_hex.value.strip().upper()
                cambios.append(f"🎨 Color → `#{self.color_hex.value.strip().upper()}`")
            except ValueError:
                cambios.append("⚠️ Color inválido — ignorado")

        if self.banner_url.value.strip():
            ced["banner_url"] = self.banner_url.value.strip()
            cambios.append("🖼️ Banner actualizado")

        if self.lema.value.strip():
            ced["lema"] = self.lema.value.strip()
            cambios.append(f"✨ Lema → *\"{self.lema.value.strip()}\"*")

        if self.roblox_username.value.strip():
            ced["roblox_username"] = self.roblox_username.value.strip()
            cambios.append(f"🎮 Roblox → `{self.roblox_username.value.strip()}`")

        set_cedula(interaction.user.id, ced)
        resumen = "\n".join(cambios) if cambios else "*(Sin cambios aplicados)*"
        await interaction.response.send_message(
            f"✅ **Cédula personalizada.**\n\n{resumen}\n\nUsa `/ver-cedula` para verla.", ephemeral=True
        )


class ConfirmarEliminar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="✅ Sí, eliminar", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        del_cedula(interaction.user.id)
        await interaction.response.edit_message(
            content="🗑️ Tu cédula ha sido eliminada del **Registro Civil de Las Condes RP**.", embed=None, view=None
        )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✅ Eliminación cancelada. Tu cédula sigue activa.", embed=None, view=None
        )


# ═════════════════════════════════════════════════════════════════════════
#  BOT
# ═════════════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.reactions = True
intents.guilds = True
intents.members = True          # requerido para revisar roles VIP
intents.message_content = True  # requerido por commands.Bot con prefijo "!"

bot = commands.Bot(command_prefix="!", intents=intents)


def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if STAFF_ROLE_ID:
            role = interaction.guild.get_role(STAFF_ROLE_ID)
            if role and role in interaction.user.roles:
                return True
        await interaction.response.send_message(
            "❌ No tienes permisos de Staff para usar este comando.", ephemeral=True
        )
        return False

    return app_commands.check(predicate)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Conectado como {bot.user} | {len(synced)} comandos sincronizados")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")

    activity = discord.Activity(type=discord.ActivityType.watching, name="Las Condes RP 🇨🇱 | /ayuda")
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return  # ya se respondió dentro del check (is_staff / has_permissions)
    print(f"Error en comando: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message("❌ Ocurrió un error al ejecutar el comando.", ephemeral=True)


# ── Apertura / Cierre del servidor ───────────────────────────────────────

def build_apertura_embed(hora: str, meta_votos: int) -> discord.Embed:
    embed = discord.Embed(
        title="🇨🇱 ENCUESTA DE APERTURA | LAS CONDES RP",
        description=(
            "🏙️ **Las Condes RP** se prepara para una nueva sesión de Roleplay.\n"
            "Queremos saber qué institución/rol representarás durante la apertura.\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        ),
        color=EMBED_COLOR,
    )
    embed.add_field(
        name="📊 INFORMACIÓN DE LA APERTURA",
        value=(
            f"🎯 **Meta de votos:** {meta_votos}\n"
            f"🕐 **Hora de apertura:** {hora}\n"
            f"🟢 **Estado:** ENCUESTA ACTIVA"
        ),
        inline=False,
    )
    opciones = "\n\n".join(f"<:{r['emoji_name']}:{r['emoji_id']}> {r['label']}" for r in ROLE_OPTIONS)
    embed.add_field(name="🗳️ SELECCIONA TU ROL", value=opciones, inline=False)
    embed.add_field(
        name="⚠️ IMPORTANTE",
        value="Tu reacción cuenta como un voto. Selecciona solo una opción y mantente atento a los anuncios del Staff.",
        inline=False,
    )
    if INVITE_CODE:
        embed.add_field(name="🔗 Invita a tus amigos", value=f"discord.gg/{INVITE_CODE}", inline=False)
    if THUMBNAIL_URL:
        embed.set_thumbnail(url=THUMBNAIL_URL)
    embed.set_footer(text="🇨🇱 LAS CONDES RP · Seriedad • Realismo • Roleplay")
    return embed


@bot.tree.command(name="abrir", description="Abre el servidor y publica la encuesta de apertura")
@app_commands.describe(
    hora="Hora de apertura (ej: 12:00)",
    meta_votos="Meta de votos para la encuesta",
    canal="Canal donde publicar (por defecto, el canal actual)",
)
@is_staff()
async def abrir(
    interaction: discord.Interaction,
    hora: str = "12:00",
    meta_votos: int = None,
    canal: discord.TextChannel = None,
):
    global state
    canal = canal or interaction.channel
    meta = meta_votos or VOTE_GOAL_DEFAULT
    embed = build_apertura_embed(hora, meta)
    role_mention = f"<@&{NOTIFY_ROLE_ID}>" if NOTIFY_ROLE_ID else ""

    await interaction.response.send_message("✅ Abriendo servidor y publicando encuesta...", ephemeral=True)
    msg = await canal.send(content=role_mention, embed=embed)

    for r in ROLE_OPTIONS:
        try:
            await msg.add_reaction(discord.PartialEmoji(name=r["emoji_name"], id=r["emoji_id"]))
        except discord.HTTPException:
            pass  # el emoji no existe en este servidor o el bot no tiene acceso a él

    state = {
        "status": "abierto",
        "message_id": msg.id,
        "channel_id": canal.id,
        "meta_votos": meta,
        "hora_apertura": hora,
        "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_state(state)


@bot.tree.command(name="cerrar", description="Cierra la encuesta activa y el servidor, mostrando los resultados")
@is_staff()
async def cerrar(interaction: discord.Interaction):
    global state
    if state.get("status") != "abierto" or not state.get("message_id"):
        await interaction.response.send_message("⚠️ No hay ninguna encuesta abierta actualmente.", ephemeral=True)
        return

    canal = bot.get_channel(state["channel_id"])
    try:
        msg = await canal.fetch_message(state["message_id"])
    except (discord.NotFound, AttributeError):
        await interaction.response.send_message(
            "⚠️ No se encontró el mensaje de la encuesta original (¿fue borrado?). Se marcará como cerrado.",
            ephemeral=True,
        )
        state["status"] = "cerrado"
        save_state(state)
        return

    resultados = []
    for r in ROLE_OPTIONS:
        count = 0
        for reaction in msg.reactions:
            emoji_id = getattr(reaction.emoji, "id", None)
            if emoji_id == r["emoji_id"]:
                count = max(reaction.count - 1, 0)
                break
        resultados.append((r["label"], count))

    resultados.sort(key=lambda x: x[1], reverse=True)
    lista = "\n".join(f"**{label}:** {count} votos" for label, count in resultados)
    total = sum(c for _, c in resultados)

    embed_cierre = discord.Embed(
        title="🔴 SERVIDOR CERRADO | LAS CONDES RP",
        description=f"La encuesta de apertura ha finalizado.\n\n{lista}\n\n**Total de votos:** {total}",
        color=EMBED_COLOR_CIERRE,
    )
    embed_cierre.set_footer(text="🇨🇱 LAS CONDES RP · Gracias por participar")

    await interaction.response.send_message("✅ Cerrando servidor y publicando resultados...", ephemeral=True)
    await canal.send(embed=embed_cierre)

    try:
        await msg.clear_reactions()
    except discord.HTTPException:
        pass

    state["status"] = "cerrado"
    save_state(state)


@bot.tree.command(name="estado", description="Muestra el estado actual del servidor/encuesta")
async def estado(interaction: discord.Interaction):
    status = state.get("status", "cerrado")
    emoji = "🟢" if status == "abierto" else "🔴"
    texto = "ABIERTO" if status == "abierto" else "CERRADO"
    await interaction.response.send_message(f"{emoji} El servidor está actualmente **{texto}**.", ephemeral=True)


@bot.tree.command(name="ayuda", description="📖 Muestra todos los comandos disponibles del bot")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Comandos — Las Condes RP", color=EMBED_COLOR)
    embed.add_field(
        name="🏙️ Apertura / Cierre del servidor",
        value=(
            "`/abrir` — Abre el servidor y publica la encuesta *(Staff)*\n"
            "`/cerrar` — Cierra la encuesta y muestra resultados *(Staff)*\n"
            "`/estado` — Ver si el servidor está abierto o cerrado"
        ),
        inline=False,
    )
    embed.add_field(
        name="🪪 Registro Civil — Cédula de Identidad",
        value=(
            "`/crear-cedula` — Crea tu cédula de identidad\n"
            "`/ver-cedula` — Muestra tu cédula (o la de otro usuario)\n"
            "`/personalizar-cedula` — Personaliza color, banner y lema *(VIP)*\n"
            "`/eliminar-cedula` — Elimina tu cédula\n"
            "`/registro-info` — Estadísticas del Registro Civil\n"
            "`/admin-cedula` — Elimina la cédula de otro usuario *(Admin)*"
        ),
        inline=False,
    )
    embed.set_footer(text="🇨🇱 LAS CONDES RP · Seriedad • Realismo • Roleplay")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Registro Civil — comandos ─────────────────────────────────────────────

@bot.tree.command(name="crear-cedula", description="🪪 Crea tu Cédula de Identidad del Registro Civil de Las Condes RP")
async def cmd_crear_cedula(interaction: discord.Interaction):
    icon = logo(interaction.guild)
    e = discord.Embed(
        title="🇨🇱  REGISTRO CIVIL DE CHILE — LAS CONDES RP",
        description=(
            "Bienvenido al **Servicio de Registro Civil e Identificación** de Las Condes RP.\n\n"
            "Aquí podrás crear tu **Cédula de Identidad** oficial del servidor.\n\n"
            "📋 **El proceso tiene 3 pasos:**\n"
            "**1️⃣** Completar tus datos personales (formulario)\n"
            "**2️⃣** Seleccionar Sexo, Estado Civil y Grupo Sanguíneo\n"
            "**3️⃣** Ingresar tu usuario de Roblox para obtener tu foto\n\n"
            "*Todo el proceso es privado — solo tú lo verás.*"
        ),
        color=COLOR_AZUL,
    )
    if icon:
        e.set_author(name="Las Condes RP — Registro Civil", icon_url=icon)
        e.set_thumbnail(url=icon)
    e.set_footer(text="SRCeI  ·  Las Condes RP  ·  Registro Civil v1.0", icon_url=icon)

    class IniciarView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)

        @discord.ui.button(label="🇨🇱 Crear mi Cédula de Identidad", style=discord.ButtonStyle.primary)
        async def btn_crear(self, inter: discord.Interaction, button: discord.ui.Button):
            await inter.response.send_modal(ModalDatosBase())

    await interaction.response.send_message(embed=e, view=IniciarView(), ephemeral=True)


@bot.tree.command(name="ver-cedula", description="🪪 Muestra la Cédula de Identidad de un usuario")
@app_commands.describe(usuario="Usuario cuya cédula quieres ver (vacío = la tuya)")
async def cmd_ver_cedula(interaction: discord.Interaction, usuario: discord.Member = None):
    await interaction.response.defer()

    target = usuario or interaction.user
    ced = get_cedula(target.id)

    if not ced:
        icon = logo(interaction.guild)
        e = discord.Embed(
            title="❌ Cédula no encontrada",
            description=f"**{target.display_name}** no tiene una cédula registrada en Las Condes RP.\n\nUsa `/crear-cedula` para crear la tuya.",
            color=COLOR_ROJO,
        )
        if icon:
            e.set_author(name="Las Condes RP — Registro Civil", icon_url=icon)
        await interaction.followup.send(embed=e, ephemeral=True)
        return

    avatar_url = await get_roblox_avatar(ced.get("roblox_username", ""))
    embed = embed_frente(ced, avatar_url, interaction.guild)
    view = CedulaView(ced=ced, avatar_url=avatar_url, guild=interaction.guild, owner_id=interaction.user.id)
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="personalizar-cedula", description="✨ [VIP] Personaliza el color, banner y lema de tu cédula")
async def cmd_personalizar_cedula(interaction: discord.Interaction):
    if not tiene_vip(interaction.user):
        icon = logo(interaction.guild)
        e = discord.Embed(
            title="⛔ Acceso VIP Requerido",
            description=(
                "Este comando es exclusivo para usuarios con roles **VIP, Donador o Staff**.\n"
                "Contacta a la administración de **Las Condes RP** para obtener acceso."
            ),
            color=COLOR_ROJO,
        )
        if icon:
            e.set_author(name="Las Condes RP — Registro Civil", icon_url=icon)
        await interaction.response.send_message(embed=e, ephemeral=True)
        return

    if not get_cedula(interaction.user.id):
        await interaction.response.send_message("❌ No tienes una cédula creada. Usa `/crear-cedula` primero.", ephemeral=True)
        return

    await interaction.response.send_modal(ModalPersonalizar())


@bot.tree.command(name="registro-info", description="📊 Estadísticas del Registro Civil de Las Condes RP")
async def cmd_registro_info(interaction: discord.Interaction):
    db = load_db()
    total = len(db)
    vip_cnt = sum(1 for v in db.values() if any([v.get("lema"), v.get("banner_url"), v.get("custom_color")]))
    hoy = datetime.date.today().strftime("%d/%m/%Y")

    regiones = {}
    for v in db.values():
        reg = v.get("region_nacimiento", "Desconocida")
        regiones[reg] = regiones.get(reg, 0) + 1
    top_region = max(regiones, key=regiones.get) if regiones else "—"

    icon = logo(interaction.guild)
    e = discord.Embed(title="📊  LAS CONDES RP — REGISTRO CIVIL", color=COLOR_AZUL)
    if icon:
        e.set_author(name="Servicio de Registro Civil e Identificación", icon_url=icon)
        e.set_thumbnail(url=icon)

    e.add_field(name="🪪  Cédulas Registradas", value=f"```{total}```", inline=True)
    e.add_field(name="✨  Cédulas VIP", value=f"```{vip_cnt}```", inline=True)
    e.add_field(name="📅  Fecha", value=f"```{hoy}```", inline=True)
    e.add_field(name="🏙️  Región Más Común", value=f"```{top_region}```", inline=False)

    e.set_footer(text="SRCeI  ·  Las Condes RP  ·  Registro Civil v1.0", icon_url=icon)
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="eliminar-cedula", description="🗑️ Elimina tu cédula del Registro Civil (permanente)")
async def cmd_eliminar_cedula(interaction: discord.Interaction):
    if not get_cedula(interaction.user.id):
        await interaction.response.send_message("❌ No tienes una cédula registrada.", ephemeral=True)
        return

    icon = logo(interaction.guild)
    e = discord.Embed(
        title="⚠️ ¿Confirmar eliminación?",
        description="Esta acción es **permanente e irreversible**.\n¿Deseas eliminar tu **Cédula de Identidad** del Registro Civil de Las Condes RP?",
        color=0xFF6B00,
    )
    if icon:
        e.set_author(name="Las Condes RP — Registro Civil", icon_url=icon)

    await interaction.response.send_message(embed=e, view=ConfirmarEliminar(), ephemeral=True)


@bot.tree.command(name="admin-cedula", description="🔧 [Admin] Elimina la cédula de cualquier usuario")
@app_commands.describe(usuario="El usuario cuya cédula deseas eliminar")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_admin_cedula(interaction: discord.Interaction, usuario: discord.Member):
    if not get_cedula(usuario.id):
        await interaction.response.send_message(f"❌ **{usuario.display_name}** no tiene cédula registrada.", ephemeral=True)
        return
    del_cedula(usuario.id)
    await interaction.response.send_message(f"🗑️ Cédula de **{usuario.display_name}** eliminada del Registro Civil.", ephemeral=True)


@cmd_admin_cedula.error
async def admin_error(interaction: discord.Interaction, error):
    await interaction.response.send_message("⛔ Solo administradores pueden usar este comando.", ephemeral=True)


# ═════════════════════════════════════════════════════════════════════════
#  ARRANQUE
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
