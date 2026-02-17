import os
import json
import copy
import uuid
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
WELCOME_AUDIO_PATH = os.getenv("WELCOME_AUDIO_PATH", "voice.mp3")

# Intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

# Bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Persistence files
TARGET_CHANNEL_FILE = "target_channel.txt"
LOG_CHANNEL_FILE = "log_channel.txt"
NOTIFY_CHANNEL_FILE = "notify_channel.txt"
EMBED_SETTINGS_FILE = "embed_settings.json"

BRING_BUTTON_LABEL = "سحب"

DEFAULT_EMBED_SETTINGS = {
    "global": {
        "color": "#3B82F6",
        "timestamp": True,
        "log_min_level": "info",
        "thumbnail_url": "{bot_avatar_url}",
        "footer_text": "بوت الانضمام الصوتي",
        "footer_icon_url": "{bot_avatar_url}"
    },
    "embeds": {
        "default": {
            "title": "بوت الانضمام الصوتي",
            "description": "{message}",
            "color": "#3B82F6"
        }
    }
}

EMBED_SETTINGS = {}
guild_voice_locks = {}
bot_enabled = True

DEFAULT_LOG_LEVEL = "info"
LOG_LEVEL_PRIORITIES = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}
LOG_LEVEL_ICONS = {
    "debug": "🔍",
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🔥",
}
LOG_EMBED_KEYS = {
    "debug": "log_debug",
    "info": "log_info",
    "warning": "log_warning",
    "error": "log_error",
    "critical": "log_critical",
}


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _deep_merge_dict(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_embed_settings() -> dict:
    if not os.path.exists(EMBED_SETTINGS_FILE):
        with open(EMBED_SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(DEFAULT_EMBED_SETTINGS, file, ensure_ascii=False, indent=2)
        return copy.deepcopy(DEFAULT_EMBED_SETTINGS)

    try:
        with open(EMBED_SETTINGS_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            raise ValueError("يجب أن يكون ملف إعدادات الـ Embed كائن JSON (Object).")
        return _deep_merge_dict(DEFAULT_EMBED_SETTINGS, loaded)
    except Exception as error:
        print(f"تعذر تحميل {EMBED_SETTINGS_FILE}: {error}")
        return copy.deepcopy(DEFAULT_EMBED_SETTINGS)


def _parse_color(color_value):
    if isinstance(color_value, int):
        return discord.Color(color_value & 0xFFFFFF)
    if isinstance(color_value, str):
        raw = color_value.strip().lower()
        if raw.startswith("#"):
            raw = raw[1:]
        if raw.startswith("0x"):
            raw = raw[2:]
        try:
            return discord.Color(int(raw, 16))
        except ValueError:
            pass
    return discord.Color.blue()


def _format_text(template, context: dict) -> str:
    if template is None:
        return ""
    safe_context = _SafeFormatDict({key: str(value) for key, value in context.items()})
    return str(template).format_map(safe_context)


def _normalize_log_level(level: str) -> str:
    normalized = str(level or DEFAULT_LOG_LEVEL).strip().lower()
    if normalized not in LOG_LEVEL_PRIORITIES:
        return DEFAULT_LOG_LEVEL
    return normalized


def _get_min_log_level() -> str:
    configured = EMBED_SETTINGS.get("global", {}).get("log_min_level", DEFAULT_LOG_LEVEL)
    return _normalize_log_level(configured)


def _should_emit_log(level: str) -> bool:
    normalized = _normalize_log_level(level)
    current_min = _get_min_log_level()
    return LOG_LEVEL_PRIORITIES[normalized] >= LOG_LEVEL_PRIORITIES[current_min]


def _shorten_text(text, limit: int = 1800) -> str:
    raw = str(text)
    if len(raw) <= limit:
        return raw
    return raw[: max(limit - 3, 0)] + "..."


def _channel_context(channel, prefix: str) -> dict:
    if channel is None:
        return {}
    mention = getattr(channel, "mention", str(channel))
    name = getattr(channel, "name", str(channel))
    channel_id = getattr(channel, "id", None)
    return {
        f"{prefix}_channel_mention": mention,
        f"{prefix}_channel_name": name,
        f"{prefix}_channel_id": str(channel_id) if channel_id is not None else "غير معروف",
    }


def build_context(guild: discord.Guild = None, actor=None, extra: dict = None) -> dict:
    context = {
        "event": "غير معروف",
        "details": "غير معروف",
        "event_id": "غير معروف",
        "level": DEFAULT_LOG_LEVEL,
        "level_upper": DEFAULT_LOG_LEVEL.upper(),
        "level_icon": LOG_LEVEL_ICONS[DEFAULT_LOG_LEVEL],
        "request_id": "غير معروف",
        "command_name": "غير معروف",
        "state": "غير معروف",
        "audio_path": WELCOME_AUDIO_PATH,
        "settings_file": EMBED_SETTINGS_FILE,
        "error_text": "غير معروف",
        "actor_mention": "غير معروف",
        "actor_display_name": "غير معروف",
        "actor_id": "غير معروف",
        "actor_avatar_url": "",
        "user_mention": "غير معروف",
        "user_display_name": "غير معروف",
        "user_id": "غير معروف",
        "user_avatar_url": "",
        "target_mention": "غير معروف",
        "target_display_name": "غير معروف",
        "target_id": "غير معروف",
        "voice_channel_mention": "غير معروف",
        "voice_channel_name": "غير معروف",
        "voice_channel_id": "غير معروف",
        "text_channel_mention": "غير معروف",
        "text_channel_name": "غير معروف",
        "text_channel_id": "غير معروف",
        "destination_channel_mention": "غير معروف",
        "destination_channel_name": "غير معروف",
        "destination_channel_id": "غير معروف",
        "guild_name": "غير معروف",
        "guild_id": "غير معروف",
        "bot_user": "غير معروف",
        "bot_id": "غير معروف",
        "bot_avatar_url": "",
    }
    if bot.user:
        context["bot_user"] = str(bot.user)
        context["bot_id"] = str(bot.user.id)
        context["bot_avatar_url"] = str(bot.user.display_avatar.url)

    if guild:
        context["guild_name"] = guild.name
        context["guild_id"] = str(guild.id)

    if actor:
        mention = getattr(actor, "mention", str(actor))
        display_name = getattr(actor, "display_name", getattr(actor, "name", str(actor)))
        avatar_url = str(actor.display_avatar.url) if hasattr(actor, "display_avatar") else ""
        actor_id = getattr(actor, "id", None)
        context["actor_mention"] = mention
        context["actor_display_name"] = display_name
        context["actor_id"] = str(actor_id) if actor_id is not None else "غير معروف"
        context["actor_avatar_url"] = avatar_url
        if context["user_mention"] == "غير معروف":
            context["user_mention"] = mention
            context["user_display_name"] = display_name
            context["user_id"] = context["actor_id"]
            context["user_avatar_url"] = avatar_url

    if extra:
        context.update(extra)

    return context


def build_embed(embed_key: str, context: dict = None) -> discord.Embed:
    context = context or {}
    global_settings = EMBED_SETTINGS.get("global", {})
    embeds = EMBED_SETTINGS.get("embeds", {})
    embed_settings = embeds.get(embed_key, embeds.get("default", {}))

    title = _format_text(embed_settings.get("title", "بوت الانضمام الصوتي"), context)
    description = _format_text(embed_settings.get("description", ""), context)
    color = _parse_color(embed_settings.get("color", global_settings.get("color", "#3B82F6")))

    embed = discord.Embed(title=title, description=description, color=color)

    if bool(embed_settings.get("timestamp", global_settings.get("timestamp", False))):
        embed.timestamp = discord.utils.utcnow()

    thumbnail_url = _format_text(embed_settings.get("thumbnail_url", global_settings.get("thumbnail_url", "")), context)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    image_url = _format_text(embed_settings.get("image_url", ""), context)
    if image_url:
        embed.set_image(url=image_url)

    author_name = _format_text(embed_settings.get("author_name", ""), context)
    author_icon_url = _format_text(embed_settings.get("author_icon_url", ""), context)
    if author_name:
        if author_icon_url:
            embed.set_author(name=author_name, icon_url=author_icon_url)
        else:
            embed.set_author(name=author_name)

    footer_text = _format_text(embed_settings.get("footer_text", global_settings.get("footer_text", "")), context)
    footer_icon_url = _format_text(embed_settings.get("footer_icon_url", global_settings.get("footer_icon_url", "")), context)
    if footer_text:
        if footer_icon_url:
            embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        else:
            embed.set_footer(text=footer_text)

    fields = embed_settings.get("fields", [])
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = _format_text(field.get("name", "-"), context)
            value = _format_text(field.get("value", "-"), context)
            inline = bool(field.get("inline", False))
            embed.add_field(name=name, value=value, inline=inline)

    return embed


async def send_channel_embed(
    channel: discord.abc.Messageable,
    embed_key: str,
    context: dict = None,
    view: discord.ui.View = None,
    content: str = None,
    allowed_mentions: discord.AllowedMentions = None,
):
    embed = build_embed(embed_key, context)
    kwargs = {"embed": embed}
    if view is not None:
        kwargs["view"] = view
    if content is not None:
        kwargs["content"] = content
    if allowed_mentions is not None:
        kwargs["allowed_mentions"] = allowed_mentions
    await channel.send(**kwargs)


async def send_interaction_embed(
    interaction: discord.Interaction,
    embed_key: str,
    context: dict = None,
    ephemeral: bool = True,
    allowed_mentions: discord.AllowedMentions = None,
):
    embed = build_embed(embed_key, context)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral, allowed_mentions=allowed_mentions)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral, allowed_mentions=allowed_mentions)


# File-backed ID helpers
def _read_id(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            raw = file.read().strip()
        return int(raw) if raw else None
    except Exception:
        return None


def _write_id(path: str, value: int):
    with open(path, "w", encoding="utf-8") as file:
        file.write(str(value))


def get_target_channel_id():
    return _read_id(TARGET_CHANNEL_FILE)


def set_target_channel_id(channel_id: int):
    _write_id(TARGET_CHANNEL_FILE, channel_id)


def get_log_channel_id():
    return _read_id(LOG_CHANNEL_FILE)


def set_log_channel_id(channel_id: int):
    _write_id(LOG_CHANNEL_FILE, channel_id)


def get_notify_channel_id():
    return _read_id(NOTIFY_CHANNEL_FILE)


def set_notify_channel_id(channel_id: int):
    _write_id(NOTIFY_CHANNEL_FILE, channel_id)


def get_guild_voice_lock(guild_id: int) -> asyncio.Lock:
    lock = guild_voice_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        guild_voice_locks[guild_id] = lock
    return lock


async def send_log(
    guild: discord.Guild,
    level: str,
    event: str,
    details: str,
    extra: dict = None,
    actor=None,
):
    normalized_level = _normalize_log_level(level)
    if not _should_emit_log(normalized_level):
        return

    event_id = uuid.uuid4().hex[:10]
    clean_details = _shorten_text(details)
    context = build_context(
        guild=guild,
        actor=actor,
        extra={
            "event_id": event_id,
            "event": _shorten_text(event, 250),
            "details": clean_details,
            "level": normalized_level,
            "level_upper": normalized_level.upper(),
            "level_icon": LOG_LEVEL_ICONS.get(normalized_level, LOG_LEVEL_ICONS[DEFAULT_LOG_LEVEL]),
            **(extra or {}),
        },
    )

    print(f"[{context['level_upper']}] [{event_id}] {context['event']} | {clean_details}")

    channel_id = get_log_channel_id()
    if not channel_id or guild is None:
        return

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        print(f"[WARNING] [{event_id}] قناة السجل غير صالحة أو ليست نصية: {channel_id}")
        return

    embed_key = LOG_EMBED_KEYS.get(normalized_level, "log_info")
    try:
        await send_channel_embed(channel, embed_key, context=context)
    except Exception as error:
        print(f"[ERROR] [{event_id}] تعذر إرسال سجل الـ Embed: {error}")


class BringMemberView(discord.ui.View):
    def __init__(self, member_id: int, source_channel_id: int, request_id: str):
        super().__init__(timeout=900)
        self.member_id = member_id
        self.source_channel_id = source_channel_id
        self.request_id = request_id
        bring_button = discord.ui.Button(
            label=BRING_BUTTON_LABEL,
            style=discord.ButtonStyle.primary,
            custom_id=f"bring:{request_id}",
        )
        bring_button.callback = self.bring_member
        self.add_item(bring_button)

    async def bring_member(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await send_interaction_embed(interaction, "button_server_only", context=build_context(extra={"request_id": self.request_id}))
            print(f"[WARNING] [bring:{self.request_id}] تم الضغط على زر السحب خارج السيرفر.")
            return

        clicker = guild.get_member(interaction.user.id)
        if clicker is None or not clicker.guild_permissions.administrator:
            await send_interaction_embed(interaction, "button_admin_only", context=build_context(guild=guild, actor=interaction.user, extra={"request_id": self.request_id}))
            await send_log(
                guild,
                "warning",
                "محاولة سحب بدون صلاحية",
                "تم الضغط على زر السحب من عضو لا يملك صلاحية الأدمن.",
                actor=interaction.user,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                },
            )
            return

        if clicker.voice is None or clicker.voice.channel is None:
            await send_interaction_embed(interaction, "button_join_voice_first", context=build_context(guild=guild, actor=clicker, extra={"request_id": self.request_id}))
            await send_log(
                guild,
                "warning",
                "محاولة سحب بدون روم صوتي",
                "العضو الذي ضغط الزر ليس داخل روم صوتي.",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                },
            )
            return

        target_member = guild.get_member(self.member_id)
        if target_member is None:
            await send_interaction_embed(interaction, "button_target_not_found", context=build_context(guild=guild, actor=clicker, extra={"request_id": self.request_id}))
            await send_log(
                guild,
                "warning",
                "المستخدم الهدف غير موجود",
                "تعذر العثور على العضو الهدف المرتبط بهذا الطلب.",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_id": str(self.member_id),
                },
            )
            return

        if target_member.voice is None or target_member.voice.channel is None:
            await send_interaction_embed(
                interaction,
                "button_target_not_in_voice",
                context=build_context(
                    guild=guild,
                    actor=clicker,
                    extra={
                        "request_id": self.request_id,
                        "target_mention": target_member.mention,
                        "target_display_name": target_member.display_name,
                    },
                ),
            )
            await send_log(
                guild,
                "warning",
                "المستخدم الهدف غادر الروم",
                f"{target_member.display_name} لم يعد داخل أي روم صوتي.",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_mention": target_member.mention,
                    "target_display_name": target_member.display_name,
                    "target_id": str(target_member.id),
                },
            )
            return

        if target_member.voice.channel.id != self.source_channel_id:
            await send_interaction_embed(
                interaction,
                "button_target_not_in_monitored",
                context=build_context(
                    guild=guild,
                    actor=clicker,
                    extra={
                        "request_id": self.request_id,
                        "target_mention": target_member.mention,
                        "target_display_name": target_member.display_name,
                    },
                ),
            )
            await send_log(
                guild,
                "warning",
                "المستخدم ليس في الروم المحدد",
                f"{target_member.display_name} لم يعد في الروم الصوتي المحدد للمراقبة.",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_mention": target_member.mention,
                    "target_display_name": target_member.display_name,
                    "target_id": str(target_member.id),
                    **_channel_context(target_member.voice.channel, "voice"),
                },
            )
            return

        try:
            await target_member.move_to(clicker.voice.channel, reason=f"طلب سحب بواسطة {clicker}")
            await send_interaction_embed(
                interaction,
                "button_move_success",
                context=build_context(
                    guild=guild,
                    actor=clicker,
                    extra={
                        "request_id": self.request_id,
                        "target_mention": target_member.mention,
                        "target_display_name": target_member.display_name,
                        "destination_channel_mention": clicker.voice.channel.mention,
                        "destination_channel_name": clicker.voice.channel.name,
                    },
                ),
            )
            await send_log(
                guild,
                "info",
                "تم سحب المستخدم",
                f"{clicker.display_name} قام بسحب {target_member.display_name} إلى {clicker.voice.channel.name} (طلب {self.request_id}).",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_mention": target_member.mention,
                    "target_display_name": target_member.display_name,
                    "target_id": str(target_member.id),
                    **_channel_context(clicker.voice.channel, "destination"),
                },
            )
        except discord.Forbidden:
            await send_interaction_embed(
                interaction,
                "button_move_forbidden",
                context=build_context(
                    guild=guild,
                    actor=clicker,
                    extra={
                        "request_id": self.request_id,
                        "target_mention": target_member.mention,
                        "target_display_name": target_member.display_name,
                    },
                ),
            )
            await send_log(
                guild,
                "error",
                "فشل السحب بسبب الصلاحيات",
                "البوت لا يملك صلاحية نقل العضو الهدف.",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_mention": target_member.mention,
                    "target_display_name": target_member.display_name,
                    "target_id": str(target_member.id),
                    **_channel_context(clicker.voice.channel, "destination"),
                },
            )
        except Exception as error:
            await send_interaction_embed(
                interaction,
                "button_move_failed",
                context=build_context(
                    guild=guild,
                    actor=clicker,
                    extra={
                        "request_id": self.request_id,
                        "target_mention": target_member.mention,
                        "target_display_name": target_member.display_name,
                        "error_text": str(error),
                    },
                ),
            )
            await send_log(
                guild,
                "error",
                "فشل تنفيذ السحب",
                f"فشل الطلب {self.request_id}: {error}",
                actor=clicker,
                extra={
                    "request_id": self.request_id,
                    "command_name": "bring_button",
                    "target_mention": target_member.mention,
                    "target_display_name": target_member.display_name,
                    "target_id": str(target_member.id),
                    "error_text": _shorten_text(error, 400),
                    **_channel_context(clicker.voice.channel, "destination"),
                },
            )


async def send_join_notification(member: discord.Member, joined_channel: discord.VoiceChannel):
    notify_channel_id = get_notify_channel_id()
    if not notify_channel_id:
        return

    notify_channel = member.guild.get_channel(notify_channel_id)
    if not isinstance(notify_channel, discord.TextChannel):
        return

    request_id = uuid.uuid4().hex[:8]
    view = BringMemberView(member.id, joined_channel.id, request_id)
    context = build_context(
        guild=member.guild,
        actor=member,
        extra={
            "request_id": request_id,
            "user_mention": member.mention,
            "user_display_name": member.display_name,
            "user_id": str(member.id),
            "user_avatar_url": str(member.display_avatar.url),
            "voice_channel_mention": joined_channel.mention,
            "voice_channel_name": joined_channel.name,
        },
    )

    try:
        await send_channel_embed(
            notify_channel,
            "join_notification",
            context=context,
            view=view,
            content=member.mention,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        await send_log(
            member.guild,
            "info",
            "تم إرسال تنبيه الانضمام",
            f"تم إرسال تنبيه انضمام لـ {member.display_name} في {joined_channel.name} (طلب {request_id}).",
            actor=member,
            extra={
                "request_id": request_id,
                "command_name": "voice_join_notify",
                "user_mention": member.mention,
                "user_display_name": member.display_name,
                "user_id": str(member.id),
                **_channel_context(joined_channel, "voice"),
                **_channel_context(notify_channel, "text"),
            },
        )
    except Exception as error:
        print("خطأ في إرسال تنبيه الانضمام:", error)
        await send_log(
            member.guild,
            "error",
            "فشل إرسال تنبيه الانضمام",
            str(error),
            actor=member,
            extra={
                "request_id": request_id,
                "command_name": "voice_join_notify",
                "user_mention": member.mention,
                "user_display_name": member.display_name,
                "user_id": str(member.id),
                "error_text": _shorten_text(error, 400),
                **_channel_context(joined_channel, "voice"),
                **_channel_context(notify_channel, "text"),
            },
        )


# Events
@bot.event
async def on_ready():
    EMBED_SETTINGS.clear()
    EMBED_SETTINGS.update(_load_embed_settings())
    if bot.user:
        print(f"تم تسجيل الدخول كـ {bot.user} ({bot.user.id})")
    else:
        print("تم تسجيل الدخول لكن لا يوجد مستخدم للبوت")

    try:
        synced = await bot.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر Slash.")
    except Exception as error:
        print("فشلت مزامنة أوامر Slash:", error)
        for guild in bot.guilds:
            await send_log(
                guild,
                "error",
                "فشل مزامنة أوامر Slash",
                str(error),
                extra={
                    "command_name": "tree.sync",
                    "error_text": _shorten_text(error, 400),
                },
            )

    for guild in bot.guilds:
        await send_log(
            guild,
            "info",
            "تم تشغيل البوت",
            f"تم تشغيل البوت بالحساب {bot.user}.",
            extra={"state": "مشغل"},
        )


@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    if member.bot:
        return
    if not bot_enabled:
        return

    target_id = get_target_channel_id()
    if not target_id:
        return

    if after.channel and after.channel.id == target_id:
        if before.channel is None or before.channel.id != target_id:
            await send_join_notification(member, after.channel)
            if not os.path.exists(WELCOME_AUDIO_PATH):
                print(f"ملف الترحيب غير موجود: {WELCOME_AUDIO_PATH}")
                await send_log(
                    member.guild,
                    "error",
                    "ملف الترحيب غير موجود",
                    f"تعذر العثور على ملف الترحيب: {WELCOME_AUDIO_PATH}",
                    actor=member,
                    extra={
                        "audio_path": WELCOME_AUDIO_PATH,
                        "command_name": "voice_join_playback",
                        **_channel_context(after.channel, "voice"),
                    },
                )
                return

            async with get_guild_voice_lock(member.guild.id):
                try:
                    vc = member.guild.voice_client
                    if not vc:
                        vc = await after.channel.connect()
                    elif vc.channel.id != target_id:
                        await vc.move_to(after.channel)

                    await asyncio.sleep(1)

                    if not vc.is_playing():
                        source = discord.FFmpegPCMAudio(executable="ffmpeg", source=WELCOME_AUDIO_PATH)
                        vc.play(source)
                        print(f"تم تشغيل صوت الترحيب لـ {member}")
                        await send_log(
                            member.guild,
                            "info",
                            "تم تشغيل صوت الترحيب",
                            f"تم تشغيل صوت الترحيب للعضو {member.display_name} في {after.channel.name}.",
                            actor=member,
                            extra={
                                "command_name": "voice_join_playback",
                                "user_mention": member.mention,
                                "user_display_name": member.display_name,
                                "user_id": str(member.id),
                                **_channel_context(after.channel, "voice"),
                            },
                        )
                except Exception as error:
                    print("خطأ صوتي:", error)
                    await send_log(
                        member.guild,
                        "error",
                        "فشل تشغيل صوت الترحيب",
                        str(error),
                        actor=member,
                        extra={
                            "command_name": "voice_join_playback",
                            "error_text": _shorten_text(error, 400),
                            "user_mention": member.mention,
                            "user_display_name": member.display_name,
                            "user_id": str(member.id),
                            **_channel_context(after.channel, "voice"),
                        },
                    )


# Slash commands (admin only)
@bot.tree.command(name="setchannel", description="تحديد الروم الصوتي الذي يراقبه البوت")
@app_commands.describe(channel="الروم الصوتي المراد مراقبته")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    set_target_channel_id(channel.id)
    context = build_context(
        guild=interaction.guild,
        actor=interaction.user,
        extra={"voice_channel_mention": channel.mention, "voice_channel_name": channel.name},
    )
    await send_interaction_embed(interaction, "set_channel_success", context=context, ephemeral=True)
    if interaction.guild:
        await send_log(
            interaction.guild,
            "info",
            "تم تحديث الروم الصوتي المراقب",
            f"{channel.name} بواسطة {context.get('actor_display_name', 'غير معروف')}.",
            actor=interaction.user,
            extra={
                "command_name": "setchannel",
                **_channel_context(channel, "voice"),
            },
        )


@bot.tree.command(name="setlogchannel", description="تحديد قناة النص لإرسال السجلات")
@app_commands.describe(channel="القناة النصية الخاصة بالسجلات")
@app_commands.checks.has_permissions(administrator=True)
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel_id(channel.id)
    context = build_context(
        guild=interaction.guild,
        actor=interaction.user,
        extra={"text_channel_mention": channel.mention, "text_channel_name": channel.name},
    )
    await send_interaction_embed(interaction, "set_log_channel_success", context=context, ephemeral=True)
    if interaction.guild:
        await send_log(
            interaction.guild,
            "info",
            "تم تحديث قناة السجلات",
            f"{channel.name} بواسطة {context.get('actor_display_name', 'غير معروف')}.",
            actor=interaction.user,
            extra={
                "command_name": "setlogchannel",
                **_channel_context(channel, "text"),
            },
        )


@bot.tree.command(name="setnotifychannel", description="تحديد قناة نصية لإشعارات الانضمام")
@app_commands.describe(channel="القناة النصية لإشعارات الانضمام")
@app_commands.checks.has_permissions(administrator=True)
async def setnotifychannel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_notify_channel_id(channel.id)
    context = build_context(
        guild=interaction.guild,
        actor=interaction.user,
        extra={"text_channel_mention": channel.mention, "text_channel_name": channel.name},
    )
    await send_interaction_embed(interaction, "set_notify_channel_success", context=context, ephemeral=True)
    if interaction.guild:
        await send_log(
            interaction.guild,
            "info",
            "تم تحديث قناة إشعارات الانضمام",
            f"{channel.name} بواسطة {context.get('actor_display_name', 'غير معروف')}.",
            actor=interaction.user,
            extra={
                "command_name": "setnotifychannel",
                **_channel_context(channel, "text"),
            },
        )


@bot.tree.command(name="reloadaudio", description="التحقق من ملف صوت الترحيب وإعادة تحميله")
@app_commands.checks.has_permissions(administrator=True)
async def reloadaudio(interaction: discord.Interaction):
    context = build_context(
        guild=interaction.guild,
        actor=interaction.user,
        extra={"audio_path": WELCOME_AUDIO_PATH},
    )
    if os.path.exists(WELCOME_AUDIO_PATH):
        await send_interaction_embed(interaction, "audio_validated", context=context, ephemeral=True)
        if interaction.guild:
            await send_log(
                interaction.guild,
                "info",
                "تم التحقق من ملف الصوت",
                f"{context.get('actor_display_name', 'غير معروف')} تحقق من {WELCOME_AUDIO_PATH}.",
                actor=interaction.user,
                extra={
                    "command_name": "reloadaudio",
                    "audio_path": WELCOME_AUDIO_PATH,
                },
            )
    else:
        await send_interaction_embed(interaction, "audio_missing", context=context, ephemeral=True)
        if interaction.guild:
            await send_log(
                interaction.guild,
                "error",
                "ملف الصوت غير موجود",
                f"{context.get('actor_display_name', 'غير معروف')} لم يجد الملف {WELCOME_AUDIO_PATH}.",
                actor=interaction.user,
                extra={
                    "command_name": "reloadaudio",
                    "audio_path": WELCOME_AUDIO_PATH,
                },
            )


@bot.tree.command(name="togglebot", description="تفعيل أو تعطيل سلوك البوت التلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def togglebot(interaction: discord.Interaction):
    global bot_enabled
    bot_enabled = not bot_enabled
    state = "مفعل" if bot_enabled else "معطل"
    context = build_context(guild=interaction.guild, actor=interaction.user, extra={"state": state})
    if bot_enabled:
        await send_interaction_embed(interaction, "bot_enabled", context=context, ephemeral=True)
    else:
        await send_interaction_embed(interaction, "bot_disabled", context=context, ephemeral=True)
    if interaction.guild:
        await send_log(
            interaction.guild,
            "info",
            "تم تغيير حالة البوت",
            f"{context.get('actor_display_name', 'غير معروف')} غيّر حالة البوت إلى {state}.",
            actor=interaction.user,
            extra={
                "command_name": "togglebot",
                "state": state,
            },
        )


@bot.tree.command(name="leave", description="فصل البوت من الروم الصوتي")
@app_commands.checks.has_permissions(administrator=True)
async def leave(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await send_interaction_embed(interaction, "button_server_only", context=build_context(extra={"request_id": "غير معروف"}), ephemeral=True)
        return

    vc = guild.voice_client
    context = build_context(guild=guild, actor=interaction.user)
    if vc:
        channel_name = vc.channel.name if vc.channel else "غير معروف"
        voice_channel = vc.channel
        await vc.disconnect()
        context["voice_channel_name"] = channel_name
        await send_interaction_embed(interaction, "leave_disconnected", context=context, ephemeral=True)
        await send_log(
            guild,
            "info",
            "تم فصل البوت من الروم الصوتي",
            f"{context.get('actor_display_name', 'غير معروف')} فصل البوت من {channel_name}.",
            actor=interaction.user,
            extra={
                "command_name": "leave",
                **_channel_context(voice_channel, "voice"),
            },
        )
    else:
        await send_interaction_embed(interaction, "leave_not_connected", context=context, ephemeral=True)


@bot.tree.command(name="reloadembeds", description="إعادة تحميل إعدادات الـ Embed من ملف JSON")
@app_commands.checks.has_permissions(administrator=True)
async def reloadembeds(interaction: discord.Interaction):
    EMBED_SETTINGS.clear()
    EMBED_SETTINGS.update(_load_embed_settings())
    context = build_context(
        guild=interaction.guild,
        actor=interaction.user,
        extra={"settings_file": EMBED_SETTINGS_FILE},
    )
    await send_interaction_embed(interaction, "reload_embeds_success", context=context, ephemeral=True)
    if interaction.guild:
        await send_log(
            interaction.guild,
            "info",
            "تمت إعادة تحميل إعدادات الـ Embed",
            f"{context.get('actor_display_name', 'غير معروف')} أعاد تحميل {EMBED_SETTINGS_FILE}.",
            actor=interaction.user,
            extra={
                "command_name": "reloadembeds",
                "settings_file": EMBED_SETTINGS_FILE,
            },
        )


# App command error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await send_interaction_embed(
            interaction,
            "permission_denied",
            context=build_context(guild=interaction.guild, actor=interaction.user),
            ephemeral=True,
        )
        if interaction.guild:
            await send_log(
                interaction.guild,
                "warning",
                "محاولة تنفيذ بدون صلاحية",
                "تمت محاولة تنفيذ أمر بدون صلاحيات كافية.",
                actor=interaction.user,
                extra={"command_name": interaction.command.name if interaction.command else "غير معروف"},
            )
        return

    await send_interaction_embed(
        interaction,
        "generic_command_error",
        context=build_context(
            guild=interaction.guild,
            actor=interaction.user,
            extra={
                "error_text": str(error),
                "command_name": interaction.command.name if interaction.command else "غير معروف",
            },
        ),
        ephemeral=True,
    )

    if interaction.guild:
        await send_log(
            interaction.guild,
            "error",
            "حدث خطأ أثناء تنفيذ أمر",
            str(error),
            actor=interaction.user,
            extra={
                "command_name": interaction.command.name if interaction.command else "غير معروف",
                "error_text": _shorten_text(error, 400),
            },
        )


if __name__ == "__main__":
    EMBED_SETTINGS = _load_embed_settings()
    if not TOKEN:
        print("المتغير DISCORD_TOKEN غير موجود في ملف .env")
    else:
        bot.run(TOKEN)

