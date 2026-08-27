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

LOGO_URL    = "PON_AQUI_LA_URL_DEL_LOGO_NUEVO"  # 👈 sube el logo de Zona Roja RP a un canal de Discord (como con las otras imágenes) y pega el link aquí
IMG_APERTURA = "https://cdn.discordapp.com/attachments/1497999534759084032/1503081674538221568/Captura_de_pantalla_2026-05-10_125245.jpg"
IMG_CIERRE   = "https://cdn.discordapp.com/attachments/1497999534759084032/1503082415990636727/Captura_de_pantalla_2026-05-10_125631.jpg"
IMG_ENCUESTA = "https://cdn.discordapp.com/attachments/1497999534759084032/1503084596177277080/Captura_de_pantalla_2026-05-07_211448.jpg"

ID_SERVIDOR = 1486083692089704619

# 🎨 Identidad visual de Zona Roja RP
COLOR_MARCA = 0x990000  # Rojo oscuro — reemplaza el rojo/azul/blanco de antes
CREDIT_MSG  = "🔒 *Bot desarrollado por NOT THE FACE — prohibida su copia o reventa sin autorización.*"  # 👈 cambia el texto si usas otra frase

# ─────────────────────────────────────────────
#  ROBLOX API
# ─────────────────────────────────────────────
async def obtener_info_roblox(username: str) -> dict | None:
    """
    Busca el userId y el avatar bust/headshot del usuario de Roblox.
    Devuelve dict con 'user_id', 'display_name' y 'avatar_url', o None si no existe.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Buscar usuario por nombre
            url_user = "https://users.roblox.com/v1/usernames/users"
            payload  = {"usernames": [username], "excludeBannedUsers": False}
            async with session.post(url_user, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None
                user_id      = users[0]["id"]
                display_name = users[0].get("displayName", username)

            # 2. Obtener avatar bust (busto) para el DNI
            url_avatar = (
                f"https://thumbnails.roblox.com/v1/users/avatar-bust"
                f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            )
            async with session.get(url_avatar) as resp:
                if resp.status != 200:
                    return {"user_id": user_id, "display_name": display_name, "avatar_url": None}
                thumb_data = await resp.json()
                thumbs = thumb_data.get("data", [])
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
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return str(edad)
    except ValueError:
        return "INVALIDA"

def construir_embed_dni(datos, usuario_nombre, discord_avatar_url):
    """
    Construye el embed del DNI.
    - Si hay avatar de Roblox, lo muestra como imagen principal (grande).
    - El thumbnail es siempre el logo del servidor.
    """
    embed = discord.Embed(
        title="🪪  CÉDULA DE IDENTIDAD — ZONA ROJA RP",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🇨🇱  **ZONA ROJA ROLEPLAY — CHILE**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MARCA,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name="Zona Roja RP — Registro Civil", icon_url=LOGO_URL)
    embed.set_thumbnail(url=LOGO_URL)

    # Avatar de Roblox como imagen grande si está disponible
    if datos.get("roblox_avatar_url"):
        embed.set_image(url=datos["roblox_avatar_url"])

    embed.add_field(name="👤 Nombre completo",    value=f"`{datos['nombre']} {datos['apellido']}`",  inline=True)
    embed.add_field(name="🎮 Usuario Roblox",     value=f"`{datos['nombre_roblox']}`",               inline=True)
    embed.add_field(name="🆔 ID Roblox",          value=f"`{datos.get('roblox_id', 'N/A')}`",        inline=True)
    embed.add_field(name="🪪 RUT",                value=f"`{datos['rut']}`",                         inline=True)
    embed.add_field(name="⚧️ Sexo",               value=f"`{datos['sexo']}`",                        inline=True)
    embed.add_field(name="🩸 Tipo de sangre",     value=f"`{datos['tipo_sangre']}`",                 inline=True)
    embed.add_field(name="💼 Ocupación",          value=f"`{datos['ocupacion']}`",                   inline=True)
    embed.add_field(name="💍 Estado civil",       value=f"`{datos['estado_civil']}`",                inline=True)
    embed.add_field(name="🌎 País de origen",     value=f"`{datos['pais']}`",                        inline=True)
    embed.add_field(name="📍 Ciudad / Localidad", value=f"`{datos['ciudad']}`",                      inline=True)
    embed.add_field(name="🎂 Fecha de nacimiento",value=f"`{datos['fecha_nacimiento']}`",             inline=True)
    embed.add_field(name="🔢 Edad",               value=f"`{datos['edad']} años`",                   inline=True)
    embed.add_field(name="📅 Fecha de emisión",   value=f"`{datos['fecha_emision']}`",               inline=True)
    embed.add_field(
        name="\u200b",
        value=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *Documento emitido por el Registro Civil de Zona Roja RP*\n"
            "⚠️ *Este documento es válido únicamente dentro del servidor.*\n"
            f"{CREDIT_MSG}"
        ),
        inline=False
    )
    embed.set_footer(
        text=f"Cédula de {usuario_nombre} • Zona Roja RP",
        icon_url=discord_avatar_url
    )
    return embed

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
            emoji = TIPO_EMOJIS.get(self.sancion["tipo"], "🔴")
            nombre_tipo = TIPO_NOMBRES.get(self.sancion["tipo"], self.sancion["tipo"])
            embed = discord.Embed(
                title="✅  Sanción Eliminada",
                description="La sanción fue eliminada permanentemente del historial.",
                color=0x2ECC71,
                timestamp=datetime.datetime.now(timezone.utc)
            )
            embed.set_author(name=str(self.usuario), icon_url=self.usuario.display_avatar.url)
            embed.add_field(name="🆔 ID",         value=f"`{self.sancion_id}`",       inline=True)
            embed.add_field(name="🏷️ Tipo",       value=f"{emoji} {nombre_tipo}",    inline=True)
            embed.add_field(name="📝 Motivo",      value=self.motivo,                 inline=False)
            embed.add_field(name="🛡️ Borrado por", value=interaction.user.mention,    inline=True)
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
    await bot.change_presence(activity=discord.Game(name="Moderando Zona Roja RP 🇨🇱"))

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

@bot.tree.command(name="dni", description="Crea tu cédula de identidad de Zona Roja RP con foto de Roblox")
@app_commands.describe(
    nombre="Tu nombre RP",
    apellido="Tu apellido RP",
    nombre_roblox="Tu usuario exacto de Roblox (se usará para traer tu avatar)",
    fecha_nacimiento="Fecha de nacimiento en formato DD/MM/AAAA",
    sexo="Sexo del personaje",
    tipo_sangre="Tipo de sangre",
    ocupacion="Profesión u ocupación",
    estado_civil="Estado civil",
    pais="País de origen",
    ciudad="Ciudad o localidad"
)
@app_commands.choices(
    sexo=[
        app_commands.Choice(name="♂️ Masculino",  value="Masculino"),
        app_commands.Choice(name="♀️ Femenino",   value="Femenino"),
        app_commands.Choice(name="⚧️ No binario", value="No binario"),
    ],
    tipo_sangre=[
        app_commands.Choice(name="🩸 A+",  value="A+"),  app_commands.Choice(name="🩸 A-",  value="A-"),
        app_commands.Choice(name="🩸 B+",  value="B+"),  app_commands.Choice(name="🩸 B-",  value="B-"),
        app_commands.Choice(name="🩸 AB+", value="AB+"), app_commands.Choice(name="🩸 AB-", value="AB-"),
        app_commands.Choice(name="🩸 O+",  value="O+"),  app_commands.Choice(name="🩸 O-",  value="O-"),
    ],
    ocupacion=[
        app_commands.Choice(name="👮 Carabinero",  value="Carabinero"),
        app_commands.Choice(name="🕵️ PDI",         value="Detective / PDI"),
        app_commands.Choice(name="🚑 SAMU",        value="Paramédico / SAMU"),
        app_commands.Choice(name="🚒 Bombero",     value="Bombero"),
        app_commands.Choice(name="⚖️ Abogado",     value="Abogado"),
        app_commands.Choice(name="👨‍⚕️ Médico",     value="Médico"),
        app_commands.Choice(name="🏦 Empresario",  value="Empresario"),
        app_commands.Choice(name="🔧 Mecánico",    value="Mecánico"),
        app_commands.Choice(name="🚖 Taxista",     value="Taxista"),
        app_commands.Choice(name="🍳 Chef",        value="Cocinero / Chef"),
        app_commands.Choice(name="🏗️ Constructor", value="Obrero / Constructor"),
        app_commands.Choice(name="🎓 Estudiante",  value="Estudiante"),
        app_commands.Choice(name="💼 Desempleado", value="Desempleado"),
        app_commands.Choice(name="🎭 Otros",       value="Otros"),
    ],
    estado_civil=[
        app_commands.Choice(name="💛 Soltero/a",    value="Soltero/a"),
        app_commands.Choice(name="💍 Casado/a",     value="Casado/a"),
        app_commands.Choice(name="💔 Divorciado/a", value="Divorciado/a"),
        app_commands.Choice(name="🖤 Viudo/a",      value="Viudo/a"),
    ]
)
async def dni(
    interaction: discord.Interaction,
    nombre: str,
    apellido: str,
    nombre_roblox: str,
    fecha_nacimiento: str,
    sexo: str,
    tipo_sangre: str,
    ocupacion: str,
    estado_civil: str,
    pais: str,
    ciudad: str
):
    await interaction.response.defer()

    edad = calcular_edad(fecha_nacimiento)
    if edad == "INVALIDA":
        await interaction.followup.send("❌ Fecha inválida. Usa el formato **DD/MM/AAAA**.", ephemeral=True)
        return

    # ── Buscar usuario en Roblox ──
    await interaction.followup.send(
        embed=discord.Embed(
            description=f"🔍 Buscando tu perfil de Roblox como **{nombre_roblox}**...",
            color=0x3498DB
        ),
        ephemeral=True
    )

    roblox_info = await obtener_info_roblox(nombre_roblox)

    if roblox_info is None:
        await interaction.edit_original_response(
            embed=discord.Embed(
                description=(
                    f"⚠️ No encontré el usuario **{nombre_roblox}** en Roblox.\n"
                    "Verifica que el nombre esté escrito exactamente igual (respeta mayúsculas).\n\n"
                    "Se creará el DNI **sin foto de Roblox**."
                ),
                color=0xF39C12
            )
        )
        roblox_id     = "N/A"
        roblox_avatar = None
    else:
        roblox_id     = str(roblox_info["user_id"])
        roblox_avatar = roblox_info["avatar_url"]
        # Actualizar ephemeral a "encontrado"
        await interaction.edit_original_response(
            embed=discord.Embed(
                description=f"✅ Perfil de Roblox encontrado: **{roblox_info['display_name']}** (ID: `{roblox_id}`)",
                color=0x2ECC71
            )
        )

    datos_dni = {
        "nombre":          nombre,
        "apellido":        apellido,
        "nombre_roblox":   nombre_roblox,
        "roblox_id":       roblox_id,
        "roblox_avatar_url": roblox_avatar,
        "fecha_nacimiento": fecha_nacimiento,
        "edad":            edad,
        "rut":             generar_rut(),
        "sexo":            sexo,
        "tipo_sangre":     tipo_sangre,
        "ocupacion":       ocupacion,
        "estado_civil":    estado_civil,
        "pais":            pais,
        "ciudad":          ciudad,
        "fecha_emision":   datetime.datetime.now().strftime("%d/%m/%Y")
    }

    guardar_dni_db(interaction.user.id, datos_dni)
    embed = construir_embed_dni(datos_dni, interaction.user.display_name, interaction.user.display_avatar.url)

    await interaction.channel.send(
        content=f"🎉 ¡Bienvenido/a a **Zona Roja RP**, {nombre}! Tu cédula ha sido creada y registrada.",
        embed=embed
    )


@bot.tree.command(name="ver_dni", description="Muestra tu cédula de identidad registrada (o la de otro usuario)")
@app_commands.describe(usuario="El miembro del que quieres ver el DNI (opcional)")
async def ver_dni(interaction: discord.Interaction, usuario: discord.Member = None):
    objetivo = usuario if usuario else interaction.user
    datos = obtener_dni_db(objetivo.id)
    if not datos:
        msg = (
            f"❌ {objetivo.mention} aún no ha creado su DNI."
            if usuario else
            "❌ No tienes DNI. Usa `/dni` para crearlo."
        )
        await interaction.response.send_message(msg, ephemeral=True)
        return
    embed = construir_embed_dni(datos, objetivo.display_name, objetivo.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="actualizar_dni", description="Actualiza tu foto de Roblox si ya tienes DNI registrado")
@app_commands.describe(nuevo_usuario_roblox="Nuevo nombre de usuario de Roblox")
async def actualizar_dni(interaction: discord.Interaction, nuevo_usuario_roblox: str):
    await interaction.response.defer(ephemeral=True)

    datos = obtener_dni_db(interaction.user.id)
    if not datos:
        await interaction.followup.send("❌ No tienes DNI registrado. Usa `/dni` primero.", ephemeral=True)
        return

    roblox_info = await obtener_info_roblox(nuevo_usuario_roblox)
    if roblox_info is None:
        await interaction.followup.send(
            f"❌ No encontré el usuario **{nuevo_usuario_roblox}** en Roblox. Verifica el nombre.",
            ephemeral=True
        )
        return

    datos["nombre_roblox"]    = nuevo_usuario_roblox
    datos["roblox_id"]        = str(roblox_info["user_id"])
    datos["roblox_avatar_url"]= roblox_info["avatar_url"]
    guardar_dni_db(interaction.user.id, datos)

    embed = construir_embed_dni(datos, interaction.user.display_name, interaction.user.display_avatar.url)
    await interaction.followup.send(
        content=f"✅ ¡DNI actualizado con el avatar de **{nuevo_usuario_roblox}**!",
        embed=embed,
        ephemeral=False
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
            embed=discord.Embed(
                description="❌ No puedes sancionar a alguien con un rol igual o superior al tuyo.",
                color=0xE74C3C
            ),
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

    embed = discord.Embed(
        title=f"{emoji}  Sanción Aplicada",
        color=ESTADO_COLORES["activa"],
        timestamp=datetime.datetime.now(timezone.utc)
    )
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
        if prueba.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            embed.set_image(url=prueba)
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    await interaction.followup.send(embed=embed)

    if notificar:
        try:
            dm = discord.Embed(
                title=f"{emoji}  Has recibido una sanción",
                description=f"Has sido sancionado en **{interaction.guild.name}**.",
                color=ESTADO_COLORES["activa"],
                timestamp=datetime.datetime.now(timezone.utc)
            )
            dm.add_field(name="🏷️ Tipo",  value=nombre_tipo,    inline=True)
            dm.add_field(name="🆔 ID",    value=f"`{sid}`",      inline=True)
            dm.add_field(name="📋 Razón", value=razon,           inline=False)
            if duracion:
                dm.add_field(name="⏱️ Duración", value=duracion, inline=True)
            dm.set_footer(text="Si crees que es injusta, puedes apelarla con /apelar_sancion")
            await usuario.send(embed=dm)
        except discord.Forbidden:
            pass


@bot.tree.command(name="historial", description="Muestra el historial de sanciones de un miembro.")
@app_commands.describe(
    usuario="Miembro a consultar", pagina="Página (por defecto: 1)",
    filtro="Filtrar por tipo — opcional", solo_activas="Mostrar solo sanciones activas",
)
@app_commands.choices(filtro=TIPOS_SANCION)
@app_commands.checks.has_permissions(moderate_members=True)
async def historial(
    interaction: discord.Interaction,
    usuario: discord.Member,
    pagina: int = 1,
    filtro: app_commands.Choice[str] = None,
    solo_activas: bool = False,
):
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
    items      = sanciones[(pagina - 1) * POR_PAG: pagina * POR_PAG]

    conteo   = {}
    for s in sanciones:
        conteo[s["tipo"]] = conteo.get(s["tipo"], 0) + 1
    activas  = sum(1 for s in sanciones if s["estado"] == "activa")
    apeladas = sum(1 for s in sanciones if s["estado"] == "apelada")

    embed = discord.Embed(
        title="📂  Historial de Sanciones",
        color=0x2F3136,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    embed.set_author(name=f"{usuario} — {total} sanción(es) total", icon_url=usuario.display_avatar.url)

    resumen = "\n".join(
        f"{TIPO_EMOJIS.get(t,'•')} {TIPO_NOMBRES.get(t,t)}: **{c}**"
        for t, c in conteo.items()
    ) or "Sin registros."

    embed.add_field(name="📊 Resumen", value=resumen, inline=True)
    embed.add_field(name="📌 Estado",
        value=f"🔴 Activas: **{activas}**\n🟠 Apeladas: **{apeladas}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    if not items:
        embed.add_field(name="Sin resultados", value="No hay sanciones con ese filtro.", inline=False)
    else:
        for s in items:
            emoji       = TIPO_EMOJIS.get(s["tipo"], "🔴")
            nombre_tipo = TIPO_NOMBRES.get(s["tipo"], s["tipo"])
            estado_badge = {
                "activa": "🔴 Activa", "apelada": "🟠 Apelada", "inactiva": "⚫ Inactiva"
            }.get(s.get("estado", "activa"), s.get("estado", "activa"))
            linea = (
                f"**Razón:** {s['razon']}\n"
                f"**Moderador:** <@{s['moderador_id']}> · **Fecha:** {_ts(s['fecha'])}\n"
                f"**Estado:** {estado_badge}"
            )
            if s.get("duracion"):
                linea += f" · **Duración:** {s['duracion']}"
            if s.get("apelacion"):
                linea += f"\n**Apelación:** {s['apelacion']}"
            embed.add_field(name=f"{emoji} [{s['id']}] {nombre_tipo}", value=linea, inline=False)

    embed.set_footer(text=f"Página {pagina}/{total_pags} · {interaction.guild.name}")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="apelar_sancion", description="Apela una sanción (queda marcada como apelada, no se elimina).")
@app_commands.describe(
    usuario="Miembro cuya sanción se apela",
    sancion_id="ID de la sanción (ej: A1B2C3D4)",
    motivo="Motivo de la apelación",
)
@app_commands.checks.has_permissions(moderate_members=True)
async def apelar_sancion(
    interaction: discord.Interaction,
    usuario: discord.Member,
    sancion_id: str,
    motivo: str,
):
    await interaction.response.defer(ephemeral=True)
    sancion_id = sancion_id.upper().strip()
    sanciones  = _obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id))
    sancion    = next((s for s in sanciones if s["id"] == sancion_id), None)

    if not sancion:
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"❌ No encontré la sanción `{sancion_id}` para ese usuario.",
                color=0xE74C3C
            ), ephemeral=True
        )
        return
    if sancion["estado"] == "apelada":
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"⚠️ La sanción `{sancion_id}` ya fue apelada.",
                color=0xF39C12
            ), ephemeral=True
        )
        return

    _actualizar_sancion(str(interaction.guild_id), str(usuario.id), sancion_id, {
        "estado": "apelada", "apelacion": motivo,
        "apelado_por": str(interaction.user.id), "fecha_apelacion": _ahora(),
    })

    emoji       = TIPO_EMOJIS.get(sancion["tipo"], "🔴")
    nombre_tipo = TIPO_NOMBRES.get(sancion["tipo"], sancion["tipo"])

    embed = discord.Embed(
        title="🟠  Sanción Apelada",
        description="La sanción queda registrada en el historial como **apelada**.",
        color=0xF39C12,
        timestamp=datetime.datetime.now(timezone.utc)
    )
    embed.set_author(name=str(usuario), icon_url=usuario.display_avatar.url)
    embed.add_field(name="🆔 ID Sanción",       value=f"`{sancion_id}`",         inline=True)
    embed.add_field(name="🏷️ Tipo",             value=f"{emoji} {nombre_tipo}", inline=True)
    embed.add_field(name="📋 Razón original",   value=sancion["razon"],          inline=False)
    embed.add_field(name="📝 Motivo apelación", value=motivo,                    inline=False)
    embed.add_field(name="🛡️ Apelado por",      value=interaction.user.mention, inline=True)
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    await interaction.followup.send(embed=embed)

    try:
        dm = discord.Embed(
            title="🟠  Tu sanción ha sido apelada",
            description=f"Una de tus sanciones en **{interaction.guild.name}** fue marcada como apelada.",
            color=0xF39C12
        )
        dm.add_field(name="🆔 ID",    value=f"`{sancion_id}`", inline=True)
        dm.add_field(name="🏷️ Tipo",  value=nombre_tipo,       inline=True)
        dm.add_field(name="📝 Motivo",value=motivo,            inline=False)
        await usuario.send(embed=dm)
    except discord.Forbidden:
        pass


@bot.tree.command(name="borrar_sancion", description="Elimina permanentemente una sanción del historial.")
@app_commands.describe(
    usuario="Miembro al que se le borra la sanción",
    sancion_id="ID de la sanción (ej: A1B2C3D4)",
    motivo="Razón para borrarla",
)
@app_commands.checks.has_permissions(administrator=True)
async def borrar_sancion(
    interaction: discord.Interaction,
    usuario: discord.Member,
    sancion_id: str,
    motivo: str,
):
    await interaction.response.defer(ephemeral=True)
    sancion_id = sancion_id.upper().strip()
    sanciones  = _obtener_sanciones_usuario(str(interaction.guild_id), str(usuario.id))
    sancion    = next((s for s in sanciones if s["id"] == sancion_id), None)

    if not sancion:
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"❌ No encontré la sanción `{sancion_id}`.",
                color=0xE74C3C
            ), ephemeral=True
        )
        return

    emoji       = TIPO_EMOJIS.get(sancion["tipo"], "🔴")
    nombre_tipo = TIPO_NOMBRES.get(sancion["tipo"], sancion["tipo"])

    confirm_embed = discord.Embed(
        title="🗑️  Confirmar eliminación",
        description=(
            "¿Seguro que quieres **borrar permanentemente** esta sanción?\n"
            "Esta acción **no se puede deshacer**."
        ),
        color=0xE74C3C
    )
    confirm_embed.add_field(name="🆔 ID",          value=f"`{sancion_id}`",        inline=True)
    confirm_embed.add_field(name="🏷️ Tipo",        value=f"{emoji} {nombre_tipo}", inline=True)
    confirm_embed.add_field(name="📋 Razón",       value=sancion["razon"],         inline=False)
    confirm_embed.add_field(name="📝 Motivo borrado", value=motivo,                inline=False)

    view = ConfirmarBorrado(
        interaction=interaction, guild_id=str(interaction.guild_id),
        user_id=str(usuario.id), sancion_id=sancion_id,
        usuario=usuario, sancion=sancion, motivo=motivo,
    )
    await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)


# ══════════════════════════════════════════════
#  COMANDOS — ANUNCIO
# ══════════════════════════════════════════════

TIPO_CONFIG_ANUNCIO = {
    "informacion_general": {"emoji": "📢", "color": 0x3498DB, "label": "Información General",              "footer": "Zona Roja RP — Información"},
    "informacion_staff":   {"emoji": "🛡️", "color": 0x8E44AD, "label": "Información para el Staff",        "footer": "Zona Roja RP — Staff Interno"},
    "normativa":           {"emoji": "📋", "color": COLOR_MARCA, "label": "Normativa Oficial",                "footer": "Zona Roja RP — Normativa"},
    "evento":              {"emoji": "🎉", "color": 0xF39C12, "label": "Evento",                           "footer": "Zona Roja RP — Eventos"},
    "actualizacion":       {"emoji": "🔧", "color": 0x2ECC71, "label": "Actualización del Servidor",       "footer": "Zona Roja RP — Actualizaciones"},
    "alerta":              {"emoji": "⚠️", "color": 0xE74C3C, "label": "Alerta Importante",                "footer": "Zona Roja RP — Alertas"},
    "economia":            {"emoji": "🏦", "color": 0x27AE60, "label": "Economía — Banco Alianza Santander","footer": "Zona Roja RP — Economía"},
    "reclutamiento":       {"emoji": "📝", "color": 0x1ABC9C, "label": "Reclutamiento de Staff",           "footer": "Zona Roja RP — Reclutamiento"},
}

@bot.tree.command(name="anuncio", description="Publica un anuncio oficial en el canal que elijas.")
@app_commands.describe(
    tipo        = "Tipo de anuncio",
    canal       = "Canal donde se publicará",
    titulo      = "Título del anuncio",
    descripcion = "Contenido / descripción del anuncio",
    ping        = "A quién mencionar",
    imagen      = "URL de imagen para el anuncio (opcional)",
)
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="📢  Información General",               value="informacion_general"),
        app_commands.Choice(name="🛡️  Información para el Staff",         value="informacion_staff"),
        app_commands.Choice(name="📋  Normativa Oficial",                 value="normativa"),
        app_commands.Choice(name="🎉  Evento",                            value="evento"),
        app_commands.Choice(name="🔧  Actualización del Servidor",        value="actualizacion"),
        app_commands.Choice(name="⚠️  Alerta Importante",                 value="alerta"),
        app_commands.Choice(name="🏦  Economía / Banco Alianza Santander",value="economia"),
        app_commands.Choice(name="📝  Reclutamiento de Staff",            value="reclutamiento"),
    ],
    ping=[
        app_commands.Choice(name="🔕  Sin mención", value="ninguno"),
        app_commands.Choice(name="📣  @everyone",   value="everyone"),
        app_commands.Choice(name="🟢  @here",       value="here"),
        app_commands.Choice(name="🛡️  @Staff",      value="staff"),
    ],
)
@app_commands.checks.has_permissions(manage_messages=True)
async def anuncio(
    interaction: discord.Interaction,
    tipo: app_commands.Choice[str],
    canal: discord.TextChannel,
    titulo: str,
    descripcion: str,
    ping: app_commands.Choice[str],
    imagen: str = None,
):
    await interaction.response.defer(ephemeral=True)

    cfg = TIPO_CONFIG_ANUNCIO.get(tipo.value, TIPO_CONFIG_ANUNCIO["informacion_general"])

    embed = discord.Embed(
        title=f"{cfg['emoji']}  {titulo}",
        description=descripcion,
        color=cfg["color"],
        timestamp=datetime.datetime.now(timezone.utc)
    )
    embed.set_author(name=f"Zona Roja Roleplay — {cfg['label']}", icon_url=LOGO_URL)
    embed.set_thumbnail(url=LOGO_URL)
    if imagen:
        embed.set_image(url=imagen)
    embed.set_footer(
        text=f"{cfg['footer']} • Publicado por {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    ping_texto = None
    if ping.value == "everyone":
        ping_texto = "@everyone"
    elif ping.value == "here":
        ping_texto = "@here"
    elif ping.value == "staff":
        rol_staff  = discord.utils.get(interaction.guild.roles, name="Staff")
        ping_texto = rol_staff.mention if rol_staff else None

    await canal.send(content=ping_texto, embed=embed)
    await interaction.followup.send(
        embed=discord.Embed(description=f"✅ Anuncio publicado en {canal.mention}", color=0x2ECC71),
        ephemeral=True
    )


# ══════════════════════════════════════════════
#  COMANDOS — SESIÓN (del bot de anuncios)
# ══════════════════════════════════════════════

@bot.tree.command(name="abrir_servidor", description="Anuncio oficial de apertura del servidor")
@app_commands.describe(
    horario_cierre="¿A qué hora cierra el servidor? (ej: 22:00)",
    modo="Modo de roleplay de la sesión"
)
@app_commands.choices(modo=[
    app_commands.Choice(name="🟢 Modo Normal",     value="🟢 Normal"),
    app_commands.Choice(name="🟡 Modo Evento",     value="🟡 Evento Especial"),
    app_commands.Choice(name="🔴 Modo Emergencia", value="🔴 Emergencia Activa"),
])
@app_commands.checks.has_permissions(manage_messages=True)
async def abrir(interaction: discord.Interaction, horario_cierre: str, modo: str = "🟢 Normal"):
    embed = discord.Embed(
        title="✨ ¡SERVIDOR ABIERTO! ✨",
        description="La sesión de roleplay ha comenzado oficialmente.\n¡Bienvenidos a **Zona Roja RP**! 🇨🇱",
        color=0x2ecc71
    )
    embed.add_field(name="🆔 CÓDIGO",           value="`ZRRP`",                          inline=True)
    embed.add_field(name="🕒 CIERRE ESTIMADO",  value=f"**{horario_cierre}**",             inline=True)
    embed.add_field(name="🎮 MODO DE SESIÓN",   value=modo,                                inline=True)
    embed.add_field(name="🎙️ HOST DE SESIÓN",  value=interaction.user.mention,            inline=True)
    embed.add_field(name="📅 FECHA",            value=f"<t:{int(time.time())}:D>",         inline=True)
    embed.add_field(name="⏱️ INICIO",           value=f"<t:{int(time.time())}:t>",         inline=True)
    embed.add_field(
        name="📢 RECUERDA",
        value=(
            "▸ Sigue el reglamento en todo momento.\n"
            "▸ Respeta a los demás jugadores.\n"
            "▸ Mantén el rol activo y de calidad."
        ),
        inline=False
    )
    embed.set_image(url=IMG_APERTURA)
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)

    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="cerrar_servidor", description="Anuncio oficial de cierre del servidor")
@app_commands.describe(motivo="Motivo del cierre (opcional)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cerrar(interaction: discord.Interaction, motivo: str = "Fin de sesión normal."):
    embed = discord.Embed(
        title="⛔ SERVIDOR CERRADO ⛔",
        description="La sesión de roleplay ha finalizado.\n¡Gracias por participar en **Zona Roja RP**! 🇨🇱",
        color=0xe74c3c
    )
    embed.add_field(name="🌐 ESTADO",         value="🔴 OFFLINE",                  inline=True)
    embed.add_field(name="⚒️ CERRADO POR",    value=interaction.user.mention,      inline=True)
    embed.add_field(name="⏱️ HORA DE CIERRE", value=f"<t:{int(time.time())}:t>",  inline=True)
    embed.add_field(name="📝 MOTIVO",         value=motivo,                        inline=False)
    embed.add_field(
        name="📌 INFO",
        value="▸ Guardamos tu progreso automáticamente.\n▸ ¡Vuelve pronto para la próxima sesión!",
        inline=False
    )
    embed.set_image(url=IMG_CIERRE)
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="pausar_servidor", description="Pausa temporal la sesión")
@app_commands.describe(
    duracion="¿Cuánto dura la pausa? (ej: 15 minutos)",
    motivo="¿Por qué se pausa?"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def pausar(interaction: discord.Interaction, duracion: str, motivo: str = "Descanso."):
    embed = discord.Embed(
        title="⏸️ SERVIDOR EN PAUSA",
        description="La sesión ha sido pausada temporalmente.\nEsperamos reanudar pronto.",
        color=0xf39c12
    )
    embed.add_field(name="⏱️ DURACIÓN ESTIMADA", value=f"**{duracion}**",         inline=True)
    embed.add_field(name="📝 MOTIVO",             value=motivo,                   inline=True)
    embed.add_field(name="🎙️ PAUSADO POR",        value=interaction.user.mention, inline=True)
    embed.add_field(
        name="💡 MIENTRAS TANTO",
        value="▸ Puedes usar los canales de OOC.\n▸ No abandones el servidor.\n▸ Espera el aviso de reanudación.",
        inline=False
    )
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="reanudar_servidor", description="Reanuda la sesión tras una pausa")
@app_commands.checks.has_permissions(manage_messages=True)
async def reanudar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="▶️ ¡SESIÓN REANUDADA!",
        description="La pausa ha terminado.\n¡Volvemos al roleplay en **Zona Roja RP**! 🇨🇱",
        color=0x1abc9c
    )
    embed.add_field(name="🕒 HORA DE REANUDACIÓN", value=f"<t:{int(time.time())}:t>", inline=True)
    embed.add_field(name="🎙️ REANUDADO POR",       value=interaction.user.mention,    inline=True)
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(name="emergencia", description="Alerta de emergencia o situación crítica en el rol")
@app_commands.describe(
    tipo="Tipo de emergencia",
    descripcion="Descripción breve de la emergencia"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="🚒 Incendio",             value="🚒 Incendio"),
    app_commands.Choice(name="🚑 Emergencia Médica",    value="🚑 Emergencia Médica"),
    app_commands.Choice(name="🚔 Persecución Policial", value="🚔 Persecución Policial"),
    app_commands.Choice(name="💥 Desastre Natural",     value="💥 Desastre Natural"),
    app_commands.Choice(name="⚠️ Alerta General",       value="⚠️ Alerta General"),
])
@app_commands.checks.has_permissions(manage_messages=True)
async def emergencia(interaction: discord.Interaction, tipo: str, descripcion: str):
    embed = discord.Embed(
        title=f"🚨 EMERGENCIA ACTIVA — {tipo}",
        description=f"**{descripcion}**",
        color=0xff0000
    )
    embed.add_field(name="⏱️ HORA",          value=f"<t:{int(time.time())}:t>", inline=True)
    embed.add_field(name="📣 REPORTADO POR", value=interaction.user.mention,    inline=True)
    embed.add_field(
        name="🆘 INSTRUCCIONES",
        value=(
            "▸ Todos los servicios de emergencia al lugar.\n"
            "▸ Ciudadanos: manténganse alejados de la zona.\n"
            "▸ Sigan las instrucciones de los oficiales."
        ),
        inline=False
    )
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)
    await interaction.response.send_message(content="@everyone 🚨", embed=embed)


@bot.tree.command(name="evento_especial", description="Anuncia un evento especial en el servidor")
@app_commands.describe(
    nombre="Nombre del evento",
    descripcion="Descripción del evento",
    hora="Hora del evento (ej: 20:00)",
    premio="Premio o recompensa del evento (opcional)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def evento(
    interaction: discord.Interaction,
    nombre: str,
    descripcion: str,
    hora: str,
    premio: str = "Sin premio definido."
):
    embed = discord.Embed(
        title=f"🎉 EVENTO ESPECIAL — {nombre}",
        description=descripcion,
        color=0x9b59b6
    )
    embed.add_field(name="🕒 HORA DEL EVENTO",     value=f"**{hora}**",              inline=True)
    embed.add_field(name="📅 FECHA",               value=f"<t:{int(time.time())}:D>", inline=True)
    embed.add_field(name="🎙️ ORGANIZADO POR",     value=interaction.user.mention,   inline=True)
    embed.add_field(name="🏆 PREMIO / RECOMPENSA", value=premio,                     inline=False)
    embed.add_field(
        name="📌 PARTICIPA",
        value="▸ Preséntate a tiempo.\n▸ Sigue las reglas del evento.\n▸ ¡Diviértete!",
        inline=False
    )
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="✅ ¡Me anoto!",
        style=discord.ButtonStyle.success,
        custom_id="evento_anotarse",
        disabled=True
    ))
    await interaction.response.send_message(content="@everyone 🎉", embed=embed, view=view)


@bot.tree.command(name="votar_apertura", description="Votación para abrir sesión")
@app_commands.describe(hora_propuesta="Hora propuesta para abrir (ej: 20:00)")
async def votar(interaction: discord.Interaction, hora_propuesta: str = "Por definir"):
    embed = discord.Embed(
        title="📊 ¿ABRIMOS SESIÓN?",
        description=(
            f"**Hora propuesta:** `{hora_propuesta}`\n\n"
            "Vota con las reacciones para que los hosts decidan.\n"
            "✅ Sí, quiero jugar · ❌ No puedo hoy"
        ),
        color=COLOR_MARCA
    )
    embed.add_field(name="🎙️ PROPUESTO POR", value=interaction.user.mention, inline=True)
    embed.add_field(name="🌐 SERVIDOR",       value="Zona Roja RP 🇨🇱",      inline=True)
    embed.set_image(url=IMG_ENCUESTA)
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text="ZRRP System • Zona Roja RP", icon_url=LOGO_URL)

    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")


# ══════════════════════════════════════════════
#  INICIO
# ══════════════════════════════════════════════
keep_alive()
bot.run(os.environ.get('TOKEN'))
