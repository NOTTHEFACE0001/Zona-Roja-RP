# ----------------------------------------------------------------------
# Copyright (C) 2026 Junior (NOT THE FACE / Player.banned).
# Todos los derechos reservados.
#
# Este sistema de DNI es propiedad intelectual exclusiva de:
# - Nombre de Usuario (Discord/Plataformas): Player.banned
# - Apodo Común: NOT THE FACE
# - Nombre de Rol: Junior
#
# Queda estrictamente prohibida la copia, traducción, modificación,
# distribución o replicación de este código y su lógica en otros
# servidores sin el consentimiento explícito y por escrito del autor.
# ----------------------------------------------------------------------

import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import datetime
import random
import json
import uuid
import time
import aiohttp
from datetime import timezone
from urllib.parse import urlparse

# ─────────────────────────────────────────────
#  KEEP ALIVE
# ─────────────────────────────────────────────
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot Zona Roja RP está en línea 🟢"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DEL BOT
# ─────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

LOGO_URL     = "https://cdn.discordapp.com/attachments/1498150124894031972/1520990016602378281/content.png"
IMG_APERTURA = "https://cdn.discordapp.com/attachments/1487136038496239870/1541921962060812349/ChatGPT_Image_25_ago_2026_17_27_14.png?ex=6a91547b&is=6a9002fb&hm=c382fc8fdeadbe41edf54dfc71dabad7ed16af5c052b8b0d0c42ce0b1ca5b000&"
IMG_CIERRE   = "https://cdn.discordapp.com/attachments/1487136038496239870/1541922295948513310/image.png?ex=6a9154ca&is=6a90034a&hm=39bae47e7bffe04776e0498ff3ce77519b1360b5525794f3c10472a31cc67b68&"
IMG_ENCUESTA = "https://cdn.discordapp.com/attachments/1487136038496239870/1541922652170752050/ChatGPT_Image_25_ago_2026_17_30_07.png?ex=6a91551f&is=6a90039f&hm=fec1f3d22cc3213e9a9316099a55ee295670576860ecb16e26f407e160f2d37b&"

ID_SERVIDOR = 1486083692089704619

COLOR_MARCA = 0x990000
CREDIT_MSG  = (
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

# ─────────────────────────────────────────────
#  VALIDACIÓN DE URLS
# ─────────────────────────────────────────────
def url_valida(url) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    try:
        partes = urlparse(url)
        if partes.scheme in ("http", "https") and partes.netloc:
            return url
    except Exception:
        pass
    return None

# ─────────────────────────────────────────────
#  ROBLOX API
# ─────────────────────────────────────────────
async def obtener_info_roblox(username: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None
                user_id      = users[0]["id"]
                display_name = users[0].get("displayName", username)

            async with session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar-bust"
                f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            ) as resp:
                if resp.status != 200:
                    return {"user_id": user_id, "display_name": display_name, "avatar_url": None}
                thumb_data = await resp.json()
                thumbs     = thumb_data.get("data", [])
                avatar_url = thumbs[0]["imageUrl"] if thumbs else None

            return {"user_id": user_id, "display_name": display_name, "avatar_url": avatar_url}
    except Exception as e:
        print(f"❌ Error Roblox API: {e}")
        return None

# ─────────────────────────────────────────────
#  BASE DE DATOS — DNI
# ─────────────────────────────────────────────
DB_FILE = "dnis.json"

def guardar_dni_db(user_id, datos):
    try:
        db = {}
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        db[str(user_id)] = datos
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error al guardar DNI: {e}")

def obtener_dni_db(user_id):
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get(str(user_id))
        return None
    except Exception as e:
        print(f"❌ Error al leer DNI: {e}")
        return None

# ─────────────────────────────────────────────
#  BASE DE DATOS — SANCIONES
# ─────────────────────────────────────────────
SANCIONES_FILE = "data/sanciones.json"

def _cargar_db() -> dict:
    if not os.path.exists(SANCIONES_FILE):
        os.makedirs(os.path.dirname(SANCIONES_FILE), exist_ok=True)
        return {}
    with open(SANCIONES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _guardar_db(data: dict):
    os.makedirs(os.path.dirname(SANCIONES_FILE), exist_ok=True)
    with open(SANCIONES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _obtener_sanciones_usuario(guild_id: str, user_id: str) -> list:
    return _cargar_db().get(guild_id, {}).get(user_id, [])

def _guardar_sancion(guild_id: str, user_id: str, sancion: dict):
    db = _cargar_db()
    db.setdefault(guild_id, {}).setdefault(user_id, []).append(sancion)
    _guardar_db(db)

def _actualizar_sancion(guild_id: str, user_id: str, sancion_id: str, cambios: dict) -> bool:
    db = _cargar_db()
    for s in db.get(guild_id, {}).get(user_id, []):
        if s["id"] == sancion_id:
            s.update(cambios)
            _guardar_db(db)
            return True
    return False

def _eliminar_sancion(guild_id: str, user_id: str, sancion_id: str) -> bool:
    db = _cargar_db()
    sanciones = db.get(guild_id, {}).get(user_id, [])
    nueva = [s for s in sanciones if s["id"] != sancion_id]
    if len(nueva) == len(sanciones):
        return False
    db[guild_id][user_id] = nueva
    _guardar_db(db)
    return True

# ─────────────────────────────────────────────
#  HELPERS — DNI
# ─────────────────────────────────────────────
def generar_rut() -> str:
    numero = random.randint(5_000_000, 25_000_000)
    dv = calcular_dv(numero)
    return f"{numero:,}".replace(",", ".") + "-" + str(dv)

def calcular_dv(rut: int) -> str:
    reversed_digits = [int(d) for d in reversed(str(rut))]
    factors = [2, 3, 4, 5, 6, 7]
    total = sum(d * factors[i % 6] for i, d in enumerate(reversed_digits))
    remainder = 11 - (total % 11)
    if remainder == 11: return "0"
    elif remainder == 10: return "K"
    return str(remainder)

def calcular_edad(fecha_nacimiento: str) -> str:
    try:
        nacimiento = datetime.datetime.strptime(fecha_nacimiento, "%d/%m/%Y")
        hoy = datetime.datetime.now()
        edad = hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
        return str(edad)
    except ValueError:
        return "INVALIDA"

def generar_firma(texto: str) -> str:
    resultado = []
    for ch in texto:
        if 'A' <= ch <= 'Z':
            resultado.append(chr(ord(ch) - ord('A') + 0x1D4D0))
        elif 'a' <= ch <= 'z':
            resultado.append(chr(ord(ch) - ord('a') + 0x1D4EA))
        else:
            resultado.append(ch)
    return "".join(resultado)

def barcode(seed: str) -> str:
    random.seed(seed)
    return "".join(random.choice(["█","▌","│","▐","║","▏","▎","▊"]) for _ in range(38))

# ─────────────────────────────────────────────
#  SESIÓN TEMPORAL
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
#  EMBEDS DNI
# ─────────────────────────────────────────────
def construir_embed_frente(datos, usuario_nombre, discord_avatar_url):
    embed = discord.Embed(
        title="🪪  CÉDULA DE IDENTIDAD — LA ZONA ROJA RP",
        description=(
            "```ansi\n"
            "\u001b[0;31m┌─────────────────────────────────────────────┐\u001b[0m\n"
            "\u001b[0;31m│\u001b[0m  \u001b[1;37mREPÚBLICA DE CHILE — LA ZONA ROJA RP\u001b[0m       \u001b[0;31m│\u001b[0m\n"
            "\u001b[0;31m│\u001b[0m  \u001b[0;33mREGISTRO CIVIL E IDENTIFICACIÓN — LZRRP\u001b[0m    \u001b[0;31m│\u001b[0m\n"
            "\u001b[0;31m│\u001b[0m  \u001b[0;31m★ ★ ★  F R E N T E  ★ ★ ★\u001b[0m                \u001b[0;31m│\u001b[0m\n"
            "\u001b[0;31m└─────────────────────────────────────────────┘\u001b[0m\n"
            "```"
        ),
        color=COLOR_MARCA,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name="La Zona Roja RP — Registro Civil", icon_url=url_valida(LOGO_URL))
    embed.set_thumbnail(url=url_valida(LOGO_URL))

    if url_valida(datos.get("roblox_avatar_url")):
        embed.set_image(url=url_valida(datos["roblox_avatar_url"]))

    embed.add_field(name="👤 Nombre completo",     value=f"`{datos['nombre']} {datos['apellido']}`", inline=True)
    embed.add_field(name="🎮 Usuario Roblox",      value=f"`{datos['nombre_roblox']}`",              inline=True)
    embed.add_field(name="🆔 ID Roblox",           value=f"`{datos.get('roblox_id', 'N/A')}`",       inline=True)
    embed.add_field(name="🪪 RUT",                 value=f"`{datos['rut']}`",                        inline=True)
    embed.add_field(name="⚧️ Sexo",                value=f"`{datos['sexo']}`",                       inline=True)
    embed.add_field(name="🩸 Tipo de sangre",      value=f"`{datos['tipo_sangre']}`",                inline=True)
    embed.add_field(name="💼 Ocupación",           value=f"`{datos['ocupacion']}`",                  inline=True)
    embed.add_field(name="💍 Estado civil",        value=f"`{datos['estado_civil']}`",               inline=True)
    embed.add_field(name="🌎 País de origen",      value=f"`{datos['pais']}`",                       inline=True)
    embed.add_field(name="📍 Ciudad / Localidad",  value=f"`{datos['ciudad']}`",                     inline=True)
    embed.add_field(name="🎂 Fecha de nacimiento", value=f"`{datos['fecha_nacimiento']}`",            inline=True)
    embed.add_field(name="🔢 Edad",                value=f"`{datos['edad']} años`",                  inline=True)
    embed.add_field(name="📅 Fecha de emisión",    value=f"`{datos['fecha_emision']}`",              inline=True)
    embed.add_field(
        name="\u200b",
        value=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *Documento emitido por el Registro Civil de La Zona Roja RP*\n"
            "⚠️ *Este documento es válido únicamente dentro del servidor.*"
            + CREDIT_MSG
        ),
        inline=False
    )
    embed.set_footer(
        text=f"Cédula de {usuario_nombre} • La Zona Roja RP",
        icon_url=url_valida(discord_avatar_url)
    )
    return embed


def construir_embed_reverso(datos, usuario_nombre, discord_avatar_url):
    nombre_completo      = f"{datos['nombre']} {datos['apellido']}"
    codigo_verificacion  = f"{datos['rut'].replace('.','').replace('-','')}-LZRRP-{datos.get('roblox_id','0')}"

    embed = discord.Embed(
        title="🪪  REVERSO — CÉDULA DE IDENTIDAD",
        description=(
            "```ansi\n"
            "\u001b[0;31m╔════════════════════════════════════════════════╗\u001b[0m\n"
            "\u001b[0;31m║\u001b[0m  \u001b[1;37mDAT O S   C O M P L E M E N T A R I O S\u001b[0m     \u001b[0;31m║\u001b[0m\n"
            "\u001b[0;31m║\u001b[0m  \u001b[0;33mREVERSO  ·  LA ZONA ROJA RP  ·  SRCeI\u001b[0m      \u001b[0;31m║\u001b[0m\n"
            "\u001b[0;31m╚════════════════════════════════════════════════╝\u001b[0m\n"
            "```"
        ),
        color=COLOR_MARCA,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name="La Zona Roja RP — Registro Civil", icon_url=url_valida(LOGO_URL))
    embed.set_thumbnail(url=url_valida(LOGO_URL))

    embed.add_field(
        name="✍️ Firma del titular",
        value=f"```{generar_firma(nombre_completo)}```",
        inline=False
    )
    embed.add_field(name="🔢 Código de verificación", value=f"`{codigo_verificacion}`", inline=False)

    # MRZ simulada
    mrz1 = f"IDCHL{datos['rut'].replace('.','').replace('-',''):20}"
    mrz2 = f"{datos['fecha_nacimiento'].replace('/','')}{datos['sexo'][0].upper()}{''.join(random.choices('0123456789', k=7))}"
    mrz3 = f"{datos['apellido'].upper()[:10]}<<{datos['nombre'].upper()[:10]}"
    embed.add_field(
        name="🔍 MRZ — Zona Legible por Máquina",
        value=f"```\n{mrz1[:30]}\n{mrz2[:30]}\n{mrz3[:30]}\n```",
        inline=False
    )

    embed.add_field(
        name="▦ Código de Barras PDF417",
        value=f"```{barcode(datos.get('rut', 'LZRRP'))}```",
        inline=False
    )
    embed.add_field(
        name="🏛️ Autoridad emisora",
        value="Registro Civil e Identificación — La Zona Roja RP",
        inline=False
    )
    embed.add_field(
        name="✍️ Firmas de Autoridad",
        value=(
            "```\n"
            f"Director SRCeI (RP):        {'_'*22}\n"
            f"Oficial Registro Civil:     {'_'*22}\n"
            f"Autoridad La Zona Roja RP:  {'_'*22}\n"
            "```"
        ),
        inline=False
    )
    embed.add_field(
        name="\u200b",
        value=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *Documento de rol exclusivo para uso dentro del servidor. No representa una identificación real.*"
            + CREDIT_MSG
        ),
        inline=False
    )
    embed.set_footer(
        text=f"Reverso de la cédula de {usuario_nombre} • La Zona Roja RP",
        icon_url=url_valida(discord_avatar_url)
    )
    return embed

# ─────────────────────────────────────────────
#  VIEW DOBLE CARA (Frente / Reverso)
# ─────────────────────────────────────────────
class DNIView(discord.ui.View):
    def __init__(self, datos, usuario_nombre, discord_avatar_url, owner_id):
        super().__init__(timeout=300)
        self.datos              = datos
        self.usuario_nombre     = usuario_nombre
        self.discord_avatar_url = discord_avatar_url
        self.owner_id           = owner_id
        self.cara               = "frente"
        self.btn_frente.disabled = True

    def _build(self):
        if self.cara == "frente":
            return construir_embed_frente(self.datos, self.usuario_nombre, self.discord_avatar_url)
        return construir_embed_reverso(self.datos, self.usuario_nombre, self.discord_avatar_url)

    @discord.ui.button(label="🪪 Ver Frente", style=discord.ButtonStyle.danger)
    async def btn_frente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cara = "frente"
        self.btn_frente.disabled  = True
        self.btn_reverso.disabled = False
        await interaction.response.edit_message(embed=self._build(), view=self)

    @discord.ui.button(label="🔄 Ver Reverso", style=discord.ButtonStyle.secondary)
    async def btn_reverso(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cara = "reverso"
        self.btn_frente.disabled  = False
        self.btn_reverso.disabled = True
        await interaction.response.edit_message(embed=self._build(), view=self)

    @discord.ui.button(label="🗑️ Cerrar", style=discord.ButtonStyle.danger)
    async def btn_cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("⛔ Solo quien creó la cédula puede cerrarla.", ephemeral=True)
            return
        await interaction.message.delete()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ─────────────────────────────────────────────
#  MODAL PASO 1 — DATOS BASE
# ─────────────────────────────────────────────
class ModalDatosBase(discord.ui.Modal, title="🇨🇱 La Zona Roja RP — Registro Civil"):
    nombre = discord.ui.TextInput(label="Nombre(s)", placeholder="Ej: Juan Andrés", max_length=50)
    apellido = discord.ui.TextInput(label="Apellido(s)", placeholder="Ej: Pérez Soto", max_length=60)
    fecha_nacimiento = discord.ui.TextInput(label="Fecha de Nacimiento (DD/MM/YYYY)", placeholder="Ej: 23/09/1998", max_length=10)
    pais = discord.ui.TextInput(label="País de Origen", placeholder="Ej: Chile, Argentina...", max_length=40)
    ciudad = discord.ui.TextInput(label="Ciudad / Localidad", placeholder="Ej: Santiago, Valparaíso...", max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        edad = calcular_edad(self.fecha_nacimiento.value)
        if edad == "INVALIDA":
            await interaction.response.send_message(
                "❌ **Fecha inválida.** Usa el formato `DD/MM/YYYY`.\nEjemplo: `23/09/1998`",
                ephemeral=True
            )
            return

        UserSession.set(interaction.user.id, {
            "nombre":           self.nombre.value.strip(),
            "apellido":         self.apellido.value.strip(),
            "fecha_nacimiento": self.fecha_nacimiento.value.strip(),
            "pais":             self.pais.value.strip(),
            "ciudad":           self.ciudad.value.strip(),
            "edad":             edad,
        })

        await interaction.response.send_message(
            "✅ **Paso 1 completado.**\n"
            "Ahora selecciona tu **Sexo**, **Tipo de Sangre**, **Ocupación** y **Estado Civil**.\n"
            "*(Al completar los cuatro, avanzarás automáticamente.)*",
            ephemeral=True,
            view=SelectsView(interaction.user.id)
        )

# ─────────────────────────────────────────────
#  SELECTS VIEW — PASO 2
# ─────────────────────────────────────────────
OPT_SEXO = [
    discord.SelectOption(label="♂️ Masculino",  value="Masculino",  emoji="👨"),
    discord.SelectOption(label="♀️ Femenino",   value="Femenino",   emoji="👩"),
    discord.SelectOption(label="⚧️ No binario", value="No binario", emoji="🏳️‍🌈"),
]
OPT_SANGRE = [
    discord.SelectOption(label="A+",  value="A+",  emoji="🩸"),
    discord.SelectOption(label="A-",  value="A-",  emoji="🩸"),
    discord.SelectOption(label="B+",  value="B+",  emoji="🩸"),
    discord.SelectOption(label="B-",  value="B-",  emoji="🩸"),
    discord.SelectOption(label="AB+", value="AB+", emoji="🩸"),
    discord.SelectOption(label="AB-", value="AB-", emoji="🩸"),
    discord.SelectOption(label="O+",  value="O+",  emoji="🩸"),
    discord.SelectOption(label="O-",  value="O-",  emoji="🩸"),
]
OPT_OCUPACION = [
    discord.SelectOption(label="👮 Carabinero",    value="Carabinero"),
    discord.SelectOption(label="🕵️ PDI",           value="Detective / PDI"),
    discord.SelectOption(label="🚑 SAMU",          value="Paramédico / SAMU"),
    discord.SelectOption(label="🚒 Bombero",       value="Bombero"),
    discord.SelectOption(label="⚖️ Abogado",       value="Abogado"),
    discord.SelectOption(label="👨‍⚕️ Médico",       value="Médico"),
    discord.SelectOption(label="🏦 Empresario",    value="Empresario"),
    discord.SelectOption(label="🔧 Mecánico",      value="Mecánico"),
    discord.SelectOption(label="🚖 Taxista",       value="Taxista"),
    discord.SelectOption(label="🍳 Chef",          value="Cocinero / Chef"),
    discord.SelectOption(label="🏗️ Constructor",   value="Obrero / Constructor"),
    discord.SelectOption(label="🎓 Estudiante",    value="Estudiante"),
    discord.SelectOption(label="💼 Desempleado",   value="Desempleado"),
    discord.SelectOption(label="🎭 Otros",         value="Otros"),
]
OPT_CIVIL = [
    discord.SelectOption(label="💛 Soltero/a",    value="Soltero/a",    emoji="💔"),
    discord.SelectOption(label="💍 Casado/a",     value="Casado/a",     emoji="💍"),
    discord.SelectOption(label="💔 Divorciado/a", value="Divorciado/a", emoji="📜"),
    discord.SelectOption(label="🖤 Viudo/a",      value="Viudo/a",      emoji="🕊️"),
]


class SelectsView(discord.ui.View):
    def __init__(self, uid: int):
        super().__init__(timeout=300)
        self.uid       = uid
        self._sexo     = None
        self._sangre   = None
        self._ocupacion= None
        self._civil    = None

        self.sel_sexo      = discord.ui.Select(placeholder="⚧️ Selecciona tu Sexo",       options=OPT_SEXO,      row=0)
        self.sel_sangre    = discord.ui.Select(placeholder="🩸 Tipo de Sangre",            options=OPT_SANGRE,    row=1)
        self.sel_ocupacion = discord.ui.Select(placeholder="💼 Ocupación",                options=OPT_OCUPACION, row=2)
        self.sel_civil     = discord.ui.Select(placeholder="💍 Estado Civil",             options=OPT_CIVIL,     row=3)

        self.sel_sexo.callback      = self._cb_sexo
        self.sel_sangre.callback    = self._cb_sangre
        self.sel_ocupacion.callback = self._cb_ocupacion
        self.sel_civil.callback     = self._cb_civil

        self.add_item(self.sel_sexo)
        self.add_item(self.sel_sangre)
        self.add_item(self.sel_ocupacion)
        self.add_item(self.sel_civil)

    def _status(self) -> str:
        sx = f"✅ **Sexo:** {self._sexo}"           if self._sexo      else "⬜ Sexo — pendiente"
        sg = f"✅ **Sangre:** {self._sangre}"        if self._sangre    else "⬜ Tipo de Sangre — pendiente"
        oc = f"✅ **Ocupación:** {self._ocupacion}"  if self._ocupacion else "⬜ Ocupación — pendiente"
        cv = f"✅ **Estado Civil:** {self._civil}"   if self._civil     else "⬜ Estado Civil — pendiente"
        return f"{sx}\n{sg}\n{oc}\n{cv}"

    async def _cb_sexo(self, interaction: discord.Interaction):
        self._sexo = self.sel_sexo.values[0]
        self.sel_sexo.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _cb_sangre(self, interaction: discord.Interaction):
        self._sangre = self.sel_sangre.values[0]
        self.sel_sangre.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _cb_ocupacion(self, interaction: discord.Interaction):
        self._ocupacion = self.sel_ocupacion.values[0]
        self.sel_ocupacion.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _cb_civil(self, interaction: discord.Interaction):
        self._civil = self.sel_civil.values[0]
        self.sel_civil.disabled = True
        await interaction.response.edit_message(content=self._status(), view=self)
        await self._check(interaction)

    async def _check(self, interaction: discord.Interaction):
        if not (self._sexo and self._sangre and self._ocupacion and self._civil):
            return
        UserSession.update(
            self.uid,
            sexo=self._sexo,
            tipo_sangre=self._sangre,
            ocupacion=self._ocupacion,
            estado_civil=self._civil,
        )
        await interaction.followup.send(
            "✅ **Paso 2 completado.**\n"
            "Último paso: ingresa tu **usuario de Roblox** para obtener tu foto en la cédula.",
            ephemeral=True,
            view=BotonRoblox(self.uid)
        )


# ─────────────────────────────────────────────
#  BOTÓN ROBLOX — PASO 3
# ─────────────────────────────────────────────
class BotonRoblox(discord.ui.View):
    def __init__(self, uid: int):
        super().__init__(timeout=300)
        self.uid = uid

    @discord.ui.button(label="🎮 Introducir usuario de Roblox", style=discord.ButtonStyle.success)
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRoblox(self.uid))


class ModalRoblox(discord.ui.Modal, title="🎮 Usuario de Roblox — Paso Final"):
    nombre_roblox = discord.ui.TextInput(
        label="Tu nombre de usuario en Roblox",
        placeholder="Ej: xXZonaRojaPlayerXx",
        max_length=50
    )

    def __init__(self, uid: int):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        session = UserSession.get(self.uid)
        if not session:
            await interaction.followup.send("❌ Tu sesión expiró. Usa `/crear_dni` de nuevo.", ephemeral=True)
            return

        roblox_user = self.nombre_roblox.value.strip()
        roblox_info = await obtener_info_roblox(roblox_user)

        if roblox_info is None:
            roblox_id     = "N/A"
            roblox_avatar = None
            aviso = (
                f"⚠️ No encontré **{roblox_user}** en Roblox. "
                "La cédula se creará sin foto de avatar."
            )
        else:
            roblox_id     = str(roblox_info["user_id"])
            roblox_avatar = roblox_info["avatar_url"]
            aviso = f"✅ Perfil Roblox encontrado: **{roblox_info['display_name']}** (ID: `{roblox_id}`)"

        datos_dni = {
            "nombre":            session["nombre"],
            "apellido":          session["apellido"],
            "fecha_nacimiento":  session["fecha_nacimiento"],
            "edad":              session["edad"],
            "pais":              session["pais"],
            "ciudad":            session["ciudad"],
            "sexo":              session.get("sexo", "—"),
            "tipo_sangre":       session.get("tipo_sangre", "—"),
            "ocupacion":         session.get("ocupacion", "—"),
            "estado_civil":      session.get("estado_civil", "—"),
            "nombre_roblox":     roblox_user,
            "roblox_id":         roblox_id,
            "roblox_avatar_url": roblox_avatar,
            "rut":               generar_rut(),
            "fecha_emision":     datetime.datetime.now().strftime("%d/%m/%Y"),
        }

        guardar_dni_db(self.uid, datos_dni)
        UserSession.clear(self.uid)

        nombre_completo = f"{session['nombre']} {session['apellido']}"
        await interaction.followup.send(aviso, ephemeral=True)

        embed_frente  = construir_embed_frente(datos_dni, interaction.user.display_name, interaction.user.display_avatar.url)
        embed_reverso = construir_embed_reverso(datos_dni, interaction.user.display_name, interaction.user.display_avatar.url)

        view = DNIView(
            datos=datos_dni,
            usuario_nombre=interaction.user.display_name,
            discord_avatar_url=str(interaction.user.display_avatar.url),
            owner_id=self.uid
        )
        view.btn_frente.disabled = True

        await interaction.channel.send(
            content=f"🎉 ¡Bienvenido/a a **La Zona Roja RP**, {nombre_completo}! Tu cédula ha sido creada." + CREDIT_MSG,
            embed=embed_frente,
            view=view
        )

# ─────────────────────────────────────────────
#  HELPERS — SANCIONES
# ─────────────────────────────────────────────
TIPOS_SANCION = [
    app_commands.Choice(name="⚠️  Advertencia",   value="advertencia"),
    app_commands.Choice(name="🔇  Mute",           value="mute"),
    app_commands.Choice(name="👢  Kick",           value="kick"),
    app_commands.Choice(name="🔨  Ban",            value="ban"),
    app_commands.Choice(name="⛔  Ban Permanente", value="ban_permanente"),
    app_commands.Choice(name="🚫  Blacklist",      value="blacklist"),
    app_commands.Choice(name="📛  Sanción Leve",   value="sancion_leve"),
    app_commands.Choice(name="🔴  Sanción Grave",  value="sancion_grave"),
    app_commands.Choice(name="🛑  Sanción Máxima", value="sancion_maxima"),
]
ESTADO_COLORES = {"activa": 0xE74C3C, "apelada": 0xF39C12, "inactiva": 0x95A5A6}
TIPO_EMOJIS = {
    "advertencia": "⚠️", "mute": "🔇", "kick": "👢", "ban": "🔨",
    "ban_permanente": "⛔", "blacklist": "🚫",
    "sancion_leve": "📛", "sancion_grave": "🔴", "sancion_maxima": "🛑",
}
TIPO_NOMBRES = {
    "advertencia": "Advertencia", "mute": "Mute", "kick": "Kick", "ban": "Ban",
    "ban_permanente": "Ban Permanente", "blacklist": "Blacklist",
    "sancion_leve": "Sanción Leve", "sancion_grave": "Sanción Grave", "sancion_maxima": "Sanción Máxima",
}

def _ts(dt_str: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(dt_str)
        return f"<t:{int(dt.timestamp())}:R>"
    except Exception:
        return dt_str

def _ahora() -> str:
    return datetime.datetime.now(timezone.utc).isoformat()

def _new_id() -> str:
    return str(uuid.uuid4())[:8].upper()

# ─────────────────────────────────────────────
#  VIEW — Confirmación borrado sanción
# ─────────────────────────────────────────────
class ConfirmarBorrado(discord.ui.View):
    def __init__(self, interaction, guild_id, user_id, sancion_id, usuario, sancion, motivo):
        super().__init__(timeout=30)
        self.orig_interaction = interaction
        self.guild_id   = guild_id
        self.user_id    = user_id
        self.sancion_id = sancion_id
        self.usuario    = usuario
        self.sancion    = sancion
        self.motivo     = motivo

    @discord.ui.button(label="Sí, eliminar", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.orig_interaction.user:
            await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
            return
        ok = _eliminar_sancion(self.guild_id, self.user_id, self.sancion_id)
        self.stop()
        for item in self.children:
            item.disabled = True
        if ok:
            emoji       = TIPO_EMOJIS.get(self.sancion["tipo"], "🔴")
            nombre_tipo = TIPO_NOMBRES.get(self.sancion["tipo"], self.sancion["tipo"])
            embed = discord.Embed(
                title="✅  Sanción Eliminada",
                description="La sanción fue eliminada permanentemente del historial.",
                color=0x2ECC71,
                timestamp=datetime.datetime.now(timezone.utc)
            )
            embed.set_author(name=str(self.usuario), icon_url=self.usuario.display_avatar.url)
            embed.add_field(name="🆔 ID",         value=f"`{self.sancion_id}`",      inline=True)
            embed.add_field(name="🏷️ Tipo",       value=f"{emoji} {nombre_tipo}",   inline=True)
            embed.add_field(name="📝 Motivo",      value=self.motivo,                inline=False)
            embed.add_field(name="🛡️ Borrado por", value=interaction.user.mention,   inline=True)
            embed.set_footer(text=f"Servidor: {interaction.guild.name}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(content="❌ No se pudo eliminar.", view=self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.orig_interaction.user:
            await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
            return
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="❎ Operación cancelada.", color=0x95A5A6),
            view=self
        )

# ─────────────────────────────────────────────
#  ON_READY
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'✅ Conectado como {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Moderando La Zona Roja RP 🇨🇱"))
    guild = discord.Object(id=ID_SERVIDOR)
    try:
        print("🔄 Sincronizando comandos Slash...")
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} comandos sincronizados.")
    except Exception as e:
        print(f"❌ Error al sincronizar: {e}")

# ══════════════════════════════════════════════
#  COMANDOS — DNI
# ══════════════════════════════════════════════

@bot.tree.command(name="crear_dni", description="Crea tu cédula de identidad de La Zona Roja RP con foto de Roblox")
async def crear_dni(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🇨🇱  LA ZONA ROJA RP — REGISTRO CIVIL",
        description=(
            "Bienvenido al **Servicio de Registro Civil** de La Zona Roja RP.\n\n"
            "📋 **El proceso tiene 3 pasos:**\n"
            "**1️⃣** Completa tus datos personales\n"
            "**2️⃣** Selecciona Sexo, Sangre, Ocupación y Estado Civil\n"
            "**3️⃣** Ingresa tu usuario de Roblox para la foto\n\n"
            "*Todo el proceso es privado — solo tú lo verás.*"
        ),
        color=COLOR_MARCA
    )
    embed.set_author(name="La Zona Roja RP — Registro Civil", icon_url=url_valida(LOGO_URL))
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="La Zona Roja RP  ·  Registro Civil v2.0")

    class IniciarView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)

        @discord.ui.button(label="🇨🇱 Crear mi Cédula de Identidad", style=discord.ButtonStyle.danger)
        async def btn_crear(self, inter: discord.Interaction, button: discord.ui.Button):
            await inter.response.send_modal(ModalDatosBase())

    await interaction.response.send_message(embed=embed, view=IniciarView(), ephemeral=True)


@bot.tree.command(name="ver_dni", description="Muestra tu cédula de identidad registrada (o la de otro usuario)")
@app_commands.describe(usuario="El miembro del que quieres ver el DNI (opcional)")
async def ver_dni(interaction: discord.Interaction, usuario: discord.Member = None):
    objetivo = usuario if usuario else interaction.user
    datos    = obtener_dni_db(objetivo.id)
    if not datos:
        msg = (
            f"❌ {objetivo.mention} aún no ha creado su cédula."
            if usuario else
            "❌ No tienes cédula. Usa `/crear_dni` para crearla."
        )
        await interaction.response.send_message(msg, ephemeral=True)
        return

    embed_f = construir_embed_frente(datos, objetivo.display_name, objetivo.display_avatar.url)
    view    = DNIView(
        datos=datos,
        usuario_nombre=objetivo.display_name,
        discord_avatar_url=str(objetivo.display_avatar.url),
        owner_id=interaction.user.id
    )
    view.btn_frente.disabled = True
    await interaction.response.send_message(embed=embed_f, view=view)


@bot.tree.command(name="actualizar_dni", description="Actualiza tu foto de Roblox si ya tienes cédula registrada")
@app_commands.describe(nuevo_usuario_roblox="Nuevo nombre de usuario de Roblox")
async def actualizar_dni(interaction: discord.Interaction, nuevo_usuario_roblox: str):
    await interaction.response.defer(ephemeral=True)
    datos = obtener_dni_db(interaction.user.id)
    if not datos:
        await interaction.followup.send("❌ No tienes cédula registrada. Usa `/crear_dni` primero.", ephemeral=True)
        return

    roblox_info = await obtener_info_roblox(nuevo_usuario_roblox)
    if roblox_info is None:
        await interaction.followup.send(
            f"❌ No encontré el usuario **{nuevo_usuario_roblox}** en Roblox.", ephemeral=True
        )
        return

    datos["nombre_roblox"]     = nuevo_usuario_roblox
    datos["roblox_id"]         = str(roblox_info["user_id"])
    datos["roblox_avatar_url"] = roblox_info["avatar_url"]
    guardar_dni_db(interaction.user.id, datos)

    embed_f = construir_embed_frente(datos, interaction.user.display_name, interaction.user.display_avatar.url)
    view    = DNIView(
        datos=datos,
        usuario_nombre=interaction.user.display_name,
        discord_avatar_url=str(interaction.user.display_avatar.url),
        owner_id=interaction.user.id
    )
    view.btn_frente.disabled = True
    await interaction.followup.send(
        content=f"✅ ¡Cédula actualizada con el avatar de **{nuevo_usuario_roblox}**!",
        embed=embed_f, view=view, ephemeral=False
    )

# ══════════════════════════════════════════════
#  COMANDOS — SANCIONES
# ══════════════════════════════════════════════

@bot.tree.command(name="sancionar", description="Aplica una sanción a un miembro del servidor.")
@app_commands.describe(
    usuario="Miembro a sancionar", tipo="Tipo de sanción", razon="Razón de la sanción",
    duracion="Duración (ej: 1d, 3h, 7d) — opcional",
    prueba="URL de imagen/evidencia — opcional",
    notificar="¿Notificar al usuario por DM? (por defecto: Sí)",
)
@app_commands.choices(tipo=TIPOS_SANCION)
@app_commands.checks.has_permissions(moderate_members=True)
async def sancionar(
    interaction: discord.Interaction,
    usuario: discord.Member,
    tipo: app_commands.Choice[str],
    razon: str,
    duracion: str = None,
    prueba: str = None,
    notificar: bool = True,
):
    await interaction.response.defer()
    if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.followup.send(
            embed=discord.Embed(description="❌ No puedes sancionar a alguien con rol igual o superior.", color=0xE74C3C),
            ephemeral=True
        )
        return

    sid = _new_id()
    _guardar_sancion(str(interaction.guild_id), str(usuario.id), {
        "id": sid, "tipo": tipo.value, "razon": razon,
        "moderador_id": str(interaction.user.id), "fecha": _ahora(),
        "duracion": duracion, "prueba": prueba, "estado": "activa", "apelacion": None,
    })

    emoji       = TIPO_EMOJIS.get(tipo.value, "🔴")
    nombre_tipo = TIPO_NOMBRES.get(tipo.value, tipo.value)
    total       = len(_obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id)))

    embed = discord.Embed(title=f"{emoji}  Sanción Aplicada", color=ESTADO_COLORES["activa"], timestamp=datetime.datetime.now(timezone.utc))
    embed.set_author(name=str(usuario), icon_url=usuario.display_avatar.url)
    embed.add_field(name="👤 Usuario",         value=usuario.mention,          inline=True)
    embed.add_field(name="🏷️ Tipo",            value=nombre_tipo,              inline=True)
    embed.add_field(name="🆔 ID Sanción",      value=f"`{sid}`",               inline=True)
    embed.add_field(name="📋 Razón",           value=razon,                    inline=False)
    if duracion:
        embed.add_field(name="⏱️ Duración",    value=duracion,                 inline=True)
    embed.add_field(name="🛡️ Moderador",       value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 Total sanciones", value=f"`{total}`",             inline=True)
    if prueba:
        embed.add_field(name="🔗 Evidencia",   value=f"[Ver prueba]({prueba})", inline=False)
        if prueba.lower().endswith((".png",".jpg",".jpeg",".gif",".webp")) and url_valida(prueba):
            embed.set_image(url=url_valida(prueba))
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    await interaction.followup.send(embed=embed)

    if notificar:
        try:
            dm = discord.Embed(title=f"{emoji}  Has recibido una sanción", description=f"Has sido sancionado en **{interaction.guild.name}**.", color=ESTADO_COLORES["activa"], timestamp=datetime.datetime.now(timezone.utc))
            dm.add_field(name="🏷️ Tipo",  value=nombre_tipo, inline=True)
            dm.add_field(name="🆔 ID",    value=f"`{sid}`",  inline=True)
            dm.add_field(name="📋 Razón", value=razon,       inline=False)
            if duracion:
                dm.add_field(name="⏱️ Duración", value=duracion, inline=True)
            dm.set_footer(text="Si crees que es injusta, puedes apelarla con /apelar_sancion")
            await usuario.send(embed=dm)
        except discord.Forbidden:
            pass


@bot.tree.command(name="historial", description="Muestra el historial de sanciones de un miembro.")
@app_commands.describe(usuario="Miembro a consultar", pagina="Página (por defecto: 1)", filtro="Filtrar por tipo — opcional", solo_activas="Mostrar solo sanciones activas")
@app_commands.choices(filtro=TIPOS_SANCION)
@app_commands.checks.has_permissions(moderate_members=True)
async def historial(interaction: discord.Interaction, usuario: discord.Member, pagina: int = 1, filtro: app_commands.Choice[str] = None, solo_activas: bool = False):
    await interaction.response.defer(ephemeral=True)
    sanciones = _obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id))
    if filtro:
        sanciones = [s for s in sanciones if s["tipo"] == filtro.value]
    if solo_activas:
        sanciones = [s for s in sanciones if s["estado"] == "activa"]
    sanciones = sorted(sanciones, key=lambda s: s["fecha"], reverse=True)

    POR_PAG    = 4
    total      = len(sanciones)
    total_pags = max(1, (total + POR_PAG - 1) // POR_PAG)
    pagina     = max(1, min(pagina, total_pags))
    items      = sanciones[(pagina-1)*POR_PAG: pagina*POR_PAG]

    conteo  = {}
    for s in sanciones:
        conteo[s["tipo"]] = conteo.get(s["tipo"], 0) + 1
    activas  = sum(1 for s in sanciones if s["estado"] == "activa")
    apeladas = sum(1 for s in sanciones if s["estado"] == "apelada")

    embed = discord.Embed(title="📂  Historial de Sanciones", color=0x2F3136, timestamp=datetime.datetime.now(timezone.utc))
    embed.set_author(name=f"{usuario} — {total} sanción(es) total", icon_url=usuario.display_avatar.url)
    resumen = "\n".join(f"{TIPO_EMOJIS.get(t,'•')} {TIPO_NOMBRES.get(t,t)}: **{c}**" for t,c in conteo.items()) or "Sin registros."
    embed.add_field(name="📊 Resumen", value=resumen, inline=True)
    embed.add_field(name="📌 Estado",  value=f"🔴 Activas: **{activas}**\n🟠 Apeladas: **{apeladas}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    if not items:
        embed.add_field(name="Sin resultados", value="No hay sanciones con ese filtro.", inline=False)
    else:
        for s in items:
            emoji       = TIPO_EMOJIS.get(s["tipo"],"🔴")
            nombre_tipo = TIPO_NOMBRES.get(s["tipo"],s["tipo"])
            estado_badge = {"activa":"🔴 Activa","apelada":"🟠 Apelada","inactiva":"⚫ Inactiva"}.get(s.get("estado","activa"),s.get("estado","activa"))
            linea = f"**Razón:** {s['razon']}\n**Moderador:** <@{s['moderador_id']}> · **Fecha:** {_ts(s['fecha'])}\n**Estado:** {estado_badge}"
            if s.get("duracion"):   linea += f" · **Duración:** {s['duracion']}"
            if s.get("apelacion"):  linea += f"\n**Apelación:** {s['apelacion']}"
            embed.add_field(name=f"{emoji} [{s['id']}] {nombre_tipo}", value=linea, inline=False)
    embed.set_footer(text=f"Página {pagina}/{total_pags} · {interaction.guild.name}")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="apelar_sancion", description="Apela una sanción.")
@app_commands.describe(usuario="Miembro cuya sanción se apela", sancion_id="ID de la sanción", motivo="Motivo de la apelación")
@app_commands.checks.has_permissions(moderate_members=True)
async def apelar_sancion(interaction: discord.Interaction, usuario: discord.Member, sancion_id: str, motivo: str):
    await interaction.response.defer(ephemeral=True)
    sancion_id = sancion_id.upper().strip()
    sanciones  = _obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id))
    sancion    = next((s for s in sanciones if s["id"] == sancion_id), None)
    if not sancion:
        await interaction.followup.send(embed=discord.Embed(description=f"❌ No encontré la sanción `{sancion_id}`.", color=0xE74C3C), ephemeral=True)
        return
    if sancion["estado"] == "apelada":
        await interaction.followup.send(embed=discord.Embed(description=f"⚠️ La sanción `{sancion_id}` ya fue apelada.", color=0xF39C12), ephemeral=True)
        return
    _actualizar_sancion(str(interaction.guild_id), str(usuario.id), sancion_id, {"estado": "apelada", "apelacion": motivo, "apelado_por": str(interaction.user.id), "fecha_apelacion": _ahora()})
    emoji       = TIPO_EMOJIS.get(sancion["tipo"],"🔴")
    nombre_tipo = TIPO_NOMBRES.get(sancion["tipo"],sancion["tipo"])
    embed = discord.Embed(title="🟠  Sanción Apelada", description="La sanción queda registrada como **apelada**.", color=0xF39C12, timestamp=datetime.datetime.now(timezone.utc))
    embed.set_author(name=str(usuario), icon_url=usuario.display_avatar.url)
    embed.add_field(name="🆔 ID",               value=f"`{sancion_id}`",        inline=True)
    embed.add_field(name="🏷️ Tipo",             value=f"{emoji} {nombre_tipo}", inline=True)
    embed.add_field(name="📋 Razón original",   value=sancion["razon"],          inline=False)
    embed.add_field(name="📝 Motivo apelación", value=motivo,                    inline=False)
    embed.add_field(name="🛡️ Apelado por",      value=interaction.user.mention, inline=True)
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    await interaction.followup.send(embed=embed)
    try:
        dm = discord.Embed(title="🟠  Tu sanción ha sido apelada", description=f"Una de tus sanciones en **{interaction.guild.name}** fue marcada como apelada.", color=0xF39C12)
        dm.add_field(name="🆔 ID",    value=f"`{sancion_id}`", inline=True)
        dm.add_field(name="🏷️ Tipo",  value=nombre_tipo,       inline=True)
        dm.add_field(name="📝 Motivo",value=motivo,            inline=False)
        await usuario.send(embed=dm)
    except discord.Forbidden:
        pass


@bot.tree.command(name="borrar_sancion", description="Elimina permanentemente una sanción del historial.")
@app_commands.describe(usuario="Miembro al que se le borra la sanción", sancion_id="ID de la sanción", motivo="Razón para borrarla")
@app_commands.checks.has_permissions(administrator=True)
async def borrar_sancion(interaction: discord.Interaction, usuario: discord.Member, sancion_id: str, motivo: str):
    await interaction.response.defer(ephemeral=True)
    sancion_id = sancion_id.upper().strip()
    sanciones  = _obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id))
    sancion    = next((s for s in sanciones if s["id"] == sancion_id), None)
    if not sancion:
        await interaction.followup.send(embed=discord.Embed(description=f"❌ No encontré la sanción `{sancion_id}`.", color=0xE74C3C), ephemeral=True)
        return
    emoji       = TIPO_EMOJIS.get(sancion["tipo"],"🔴")
    nombre_tipo = TIPO_NOMBRES.get(sancion["tipo"],sancion["tipo"])
    confirm_embed = discord.Embed(title="🗑️  Confirmar eliminación", description="¿Seguro que quieres **borrar permanentemente** esta sanción?\nEsta acción **no se puede deshacer**.", color=0xE74C3C)
    confirm_embed.add_field(name="🆔 ID",             value=f"`{sancion_id}`",        inline=True)
    confirm_embed.add_field(name="🏷️ Tipo",           value=f"{emoji} {nombre_tipo}", inline=True)
    confirm_embed.add_field(name="📋 Razón",          value=sancion["razon"],         inline=False)
    confirm_embed.add_field(name="📝 Motivo borrado", value=motivo,                   inline=False)
    view = ConfirmarBorrado(interaction=interaction, guild_id=str(interaction.guild_id), user_id=str(usuario.id), sancion_id=sancion_id, usuario=usuario, sancion=sancion, motivo=motivo)
    await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)

# ══════════════════════════════════════════════
#  COMANDOS — ANUNCIO
# ══════════════════════════════════════════════

TIPO_CONFIG_ANUNCIO = {
    "informacion_general": {"emoji": "📢", "color": 0x3498DB,   "label": "Información General",               "footer": "La Zona Roja RP — Información"},
    "informacion_staff":   {"emoji": "🛡️", "color": 0x8E44AD,   "label": "Información para el Staff",         "footer": "La Zona Roja RP — Staff Interno"},
    "normativa":           {"emoji": "📋", "color": COLOR_MARCA, "label": "Normativa Oficial",                 "footer": "La Zona Roja RP — Normativa"},
    "evento":              {"emoji": "🎉", "color": 0xF39C12,   "label": "Evento",                            "footer": "La Zona Roja RP — Eventos"},
    "actualizacion":       {"emoji": "🔧", "color": 0x2ECC71,   "label": "Actualización del Servidor",        "footer": "La Zona Roja RP — Actualizaciones"},
    "alerta":              {"emoji": "⚠️", "color": 0xE74C3C,   "label": "Alerta Importante",                 "footer": "La Zona Roja RP — Alertas"},
    "economia":            {"emoji": "🏦", "color": 0x27AE60,   "label": "Economía",                          "footer": "La Zona Roja RP — Economía"},
    "reclutamiento":       {"emoji": "📝", "color": 0x1ABC9C,   "label": "Reclutamiento de Staff",            "footer": "La Zona Roja RP — Reclutamiento"},
}

@bot.tree.command(name="anuncio", description="Publica un anuncio oficial en el canal que elijas.")
@app_commands.describe(tipo="Tipo de anuncio", canal="Canal donde se publicará", titulo="Título del anuncio", descripcion="Contenido del anuncio", ping="A quién mencionar", imagen="URL de imagen (opcional)")
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="📢  Información General",        value="informacion_general"),
        app_commands.Choice(name="🛡️  Información para el Staff",  value="informacion_staff"),
        app_commands.Choice(name="📋  Normativa Oficial",          value="normativa"),
        app_commands.Choice(name="🎉  Evento",                     value="evento"),
        app_commands.Choice(name="🔧  Actualización del Servidor", value="actualizacion"),
        app_commands.Choice(name="⚠️  Alerta Importante",          value="alerta"),
        app_commands.Choice(name="🏦  Economía",                   value="economia"),
        app_commands.Choice(name="📝  Reclutamiento de Staff",     value="reclutamiento"),
    ],
    ping=[
        app_commands.Choice(name="🔕  Sin mención", value="ninguno"),
        app_commands.Choice(name="📣  @everyone",   value="everyone"),
        app_commands.Choice(name="🟢  @here",       value="here"),
        app_commands.Choice(name="🛡️  @Staff",      value="staff"),
    ],
)
@app_commands.checks.has_permissions(manage_messages=True)
async def anuncio(interaction: discord.Interaction, tipo: app_commands.Choice[str], canal: discord.TextChannel, titulo: str, descripcion: str, ping: app_commands.Choice[str], imagen: str = None):
    await interaction.response.defer(ephemeral=True)
    cfg = TIPO_CONFIG_ANUNCIO.get(tipo.value, TIPO_CONFIG_ANUNCIO["informacion_general"])
    embed = discord.Embed(title=f"{cfg['emoji']}  {titulo}", description=descripcion, color=cfg["color"], timestamp=datetime.datetime.now(timezone.utc))
    embed.set_author(name=f"La Zona Roja RP — {cfg['label']}", icon_url=url_valida(LOGO_URL))
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    if url_valida(imagen):
        embed.set_image(url=url_valida(imagen))
    embed.set_footer(text=f"{cfg['footer']} • Publicado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    ping_texto = None
    if ping.value == "everyone":   ping_texto = "@everyone"
    elif ping.value == "here":     ping_texto = "@here"
    elif ping.value == "staff":
        rol_staff  = discord.utils.get(interaction.guild.roles, name="Staff")
        ping_texto = rol_staff.mention if rol_staff else None
    await canal.send(content=ping_texto, embed=embed)
    await interaction.followup.send(embed=discord.Embed(description=f"✅ Anuncio publicado en {canal.mention}", color=0x2ECC71), ephemeral=True)

# ══════════════════════════════════════════════
#  COMANDOS — SESIÓN
# ══════════════════════════════════════════════

@bot.tree.command(name="abrir_servidor", description="Anuncio oficial de apertura del servidor")
@app_commands.describe(horario_cierre="¿A qué hora cierra el servidor?", modo="Modo de roleplay de la sesión")
@app_commands.choices(modo=[
    app_commands.Choice(name="🟢 Modo Normal",     value="🟢 Normal"),
    app_commands.Choice(name="🟡 Modo Evento",     value="🟡 Evento Especial"),
    app_commands.Choice(name="🔴 Modo Emergencia", value="🔴 Emergencia Activa"),
])
@app_commands.checks.has_permissions(manage_messages=True)
async def abrir(interaction: discord.Interaction, horario_cierre: str, modo: str = "🟢 Normal"):
    embed = discord.Embed(title="✨ ¡SERVIDOR ABIERTO! ✨", description="La sesión de roleplay ha comenzado oficialmente.\n¡Bienvenidos a **La Zona Roja RP**! 🇨🇱", color=0x2ecc71)
    embed.add_field(name="🆔 CÓDIGO",          value="`LZRRP`",                         inline=True)
    embed.add_field(name="🕒 CIERRE ESTIMADO", value=f"**{horario_cierre}**",            inline=True)
    embed.add_field(name="🎮 MODO DE SESIÓN",  value=modo,                               inline=True)
    embed.add_field(name="🎙️ HOST DE SESIÓN", value=interaction.user.mention,           inline=True)
    embed.add_field(name="📅 FECHA",           value=f"<t:{int(time.time())}:D>",        inline=True)
    embed.add_field(name="⏱️ INICIO",          value=f"<t:{int(time.time())}:t>",        inline=True)
    embed.add_field(name="📢 RECUERDA", value="▸ Sigue el reglamento en todo momento.\n▸ Respeta a los demás jugadores.\n▸ Mantén el rol activo y de calidad.", inline=False)
    embed.set_image(url=url_valida(IMG_APERTURA))
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="cerrar_servidor", description="Anuncio oficial de cierre del servidor")
@app_commands.describe(motivo="Motivo del cierre (opcional)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cerrar(interaction: discord.Interaction, motivo: str = "Fin de sesión normal."):
    embed = discord.Embed(title="⛔ SERVIDOR CERRADO ⛔", description="La sesión de roleplay ha finalizado.\n¡Gracias por participar en **La Zona Roja RP**! 🇨🇱", color=0xe74c3c)
    embed.add_field(name="🌐 ESTADO",         value="🔴 OFFLINE",                 inline=True)
    embed.add_field(name="⚒️ CERRADO POR",    value=interaction.user.mention,     inline=True)
    embed.add_field(name="⏱️ HORA DE CIERRE", value=f"<t:{int(time.time())}:t>", inline=True)
    embed.add_field(name="📝 MOTIVO",         value=motivo,                       inline=False)
    embed.add_field(name="📌 INFO", value="▸ Guardamos tu progreso automáticamente.\n▸ ¡Vuelve pronto para la próxima sesión!", inline=False)
    embed.set_image(url=url_valida(IMG_CIERRE))
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="pausar_servidor", description="Pausa temporal la sesión")
@app_commands.describe(duracion="¿Cuánto dura la pausa?", motivo="¿Por qué se pausa?")
@app_commands.checks.has_permissions(manage_messages=True)
async def pausar(interaction: discord.Interaction, duracion: str, motivo: str = "Descanso."):
    embed = discord.Embed(title="⏸️ SERVIDOR EN PAUSA", description="La sesión ha sido pausada temporalmente.", color=0xf39c12)
    embed.add_field(name="⏱️ DURACIÓN ESTIMADA", value=f"**{duracion}**",        inline=True)
    embed.add_field(name="📝 MOTIVO",             value=motivo,                  inline=True)
    embed.add_field(name="🎙️ PAUSADO POR",        value=interaction.user.mention,inline=True)
    embed.add_field(name="💡 MIENTRAS TANTO", value="▸ Puedes usar los canales de OOC.\n▸ No abandones el servidor.\n▸ Espera el aviso de reanudación.", inline=False)
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="reanudar_servidor", description="Reanuda la sesión tras una pausa")
@app_commands.checks.has_permissions(manage_messages=True)
async def reanudar(interaction: discord.Interaction):
    embed = discord.Embed(title="▶️ ¡SESIÓN REANUDADA!", description="¡Volvemos al roleplay en **La Zona Roja RP**! 🇨🇱", color=0x1abc9c)
    embed.add_field(name="🕒 HORA DE REANUDACIÓN", value=f"<t:{int(time.time())}:t>", inline=True)
    embed.add_field(name="🎙️ REANUDADO POR",       value=interaction.user.mention,    inline=True)
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="emergencia", description="Alerta de emergencia o situación crítica en el rol")
@app_commands.describe(tipo="Tipo de emergencia", descripcion="Descripción breve de la emergencia")
@app_commands.choices(tipo=[
    app_commands.Choice(name="🚒 Incendio",             value="🚒 Incendio"),
    app_commands.Choice(name="🚑 Emergencia Médica",    value="🚑 Emergencia Médica"),
    app_commands.Choice(name="🚔 Persecución Policial", value="🚔 Persecución Policial"),
    app_commands.Choice(name="💥 Desastre Natural",     value="💥 Desastre Natural"),
    app_commands.Choice(name="⚠️ Alerta General",       value="⚠️ Alerta General"),
])
@app_commands.checks.has_permissions(manage_messages=True)
async def emergencia(interaction: discord.Interaction, tipo: str, descripcion: str):
    embed = discord.Embed(title=f"🚨 EMERGENCIA ACTIVA — {tipo}", description=f"**{descripcion}**", color=0xff0000)
    embed.add_field(name="⏱️ HORA",          value=f"<t:{int(time.time())}:t>", inline=True)
    embed.add_field(name="📣 REPORTADO POR", value=interaction.user.mention,    inline=True)
    embed.add_field(name="🆘 INSTRUCCIONES", value="▸ Todos los servicios de emergencia al lugar.\n▸ Ciudadanos: manténganse alejados.\n▸ Sigan las instrucciones de los oficiales.", inline=False)
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(content="@everyone 🚨", embed=embed)


@bot.tree.command(name="evento_especial", description="Anuncia un evento especial en el servidor")
@app_commands.describe(nombre="Nombre del evento", descripcion="Descripción del evento", hora="Hora del evento", premio="Premio o recompensa (opcional)")
@app_commands.checks.has_permissions(manage_messages=True)
async def evento(interaction: discord.Interaction, nombre: str, descripcion: str, hora: str, premio: str = "Sin premio definido."):
    embed = discord.Embed(title=f"🎉 EVENTO ESPECIAL — {nombre}", description=descripcion, color=0x9b59b6)
    embed.add_field(name="🕒 HORA DEL EVENTO",     value=f"**{hora}**",               inline=True)
    embed.add_field(name="📅 FECHA",               value=f"<t:{int(time.time())}:D>", inline=True)
    embed.add_field(name="🎙️ ORGANIZADO POR",     value=interaction.user.mention,    inline=True)
    embed.add_field(name="🏆 PREMIO / RECOMPENSA", value=premio,                      inline=False)
    embed.add_field(name="📌 PARTICIPA", value="▸ Preséntate a tiempo.\n▸ Sigue las reglas del evento.\n▸ ¡Diviértete!", inline=False)
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="✅ ¡Me anoto!", style=discord.ButtonStyle.success, custom_id="evento_anotarse", disabled=True))
    await interaction.response.send_message(content="@everyone 🎉", embed=embed, view=view)


@bot.tree.command(name="votar_apertura", description="Votación para abrir sesión")
@app_commands.describe(hora_propuesta="Hora propuesta para abrir (ej: 20:00)")
async def votar(interaction: discord.Interaction, hora_propuesta: str = "Por definir"):
    embed = discord.Embed(title="📊 ¿ABRIMOS SESIÓN?", description=f"**Hora propuesta:** `{hora_propuesta}`\n\nVota con las reacciones.\n✅ Sí, quiero jugar · ❌ No puedo hoy", color=COLOR_MARCA)
    embed.add_field(name="🎙️ PROPUESTO POR", value=interaction.user.mention, inline=True)
    embed.add_field(name="🌐 SERVIDOR",       value="La Zona Roja RP 🇨🇱",   inline=True)
    embed.set_image(url=url_valida(IMG_ENCUESTA))
    embed.set_thumbnail(url=url_valida(LOGO_URL))
    embed.set_footer(text="LZRRP System • La Zona Roja RP", icon_url=url_valida(LOGO_URL))
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

# ══════════════════════════════════════════════
#  INICIO
# ══════════════════════════════════════════════
keep_alive()
bot.run(os.environ.get('TOKEN'))
