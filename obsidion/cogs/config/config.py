"""Images cog."""
import asyncio
import logging
from typing import Optional

import discord
from babel import Locale as BabelLocale
from babel import UnknownLocaleError
from discord.ext import commands
from obsidion import __version__
from obsidion.core import i18n
from obsidion.core.i18n import cog_i18n
from obsidion.core.i18n import Translator
from obsidion.core.utils.chat_formatting import pagify
from obsidion.core.utils.predicates import MessagePredicate
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option


log = logging.getLogger(__name__)

_ = Translator("Config", __file__)


@cog_i18n(_)
class Config(commands.Cog):
    def __init__(self, bot) -> None:
        """Init."""
        self.bot = bot

    @commands.command(aliases=["serverprefixes"])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix(self, ctx, _prefix: Optional[str]):
        """Sets Obsidion's server prefix(es)."""
        if not _prefix:
            await ctx.bot.set_prefixes(guild=ctx.guild)
            await ctx.send(_("Guild prefixes have been reset."))
            return
        await ctx.bot.set_prefixes(guild=ctx.guild, prefix=_prefix)
        await ctx.send(_("Prefix set."))

    @cog_ext.cog_slash(name="prefix")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def slash_prefix(self, ctx, _prefix: Optional[str]):
        """Sets Obsidion's server prefix(es)."""
        await ctx.defer()
        await self.prefix(_prefix)

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def locale(self, ctx, language_code: str):
        """
        Changes the bot's locale in this server.

        `<language_code>` can be any language code with country code included,
        e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.


        Use "default" to return to the bot's default set language.
        To reset to English, use "en-US".
        """
        if language_code.lower() == "default":
            global_locale = await self.bot._config.locale()
            i18n.set_contextual_locale(global_locale)
            await self.bot._i18n_cache.set_locale(ctx.guild, None)
            await ctx.send(_("Locale has been set to the default."))
            return
        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _(
                    "Invalid format - language code has to "
                    "include country code, e.g. `en-US`"
                )
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_contextual_locale(standardized_locale_name)
        await self.bot._i18n_cache.set_locale(ctx.guild, standardized_locale_name)
        await ctx.send(_("Locale has been set."))

    @cog_ext.cog_slash(name="locale")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def slash_locale(self, ctx, language_code: str):
        """Changes the bot's locale in this server."""
        await ctx.defer()
        await self.locale(language_code)

    @commands.command(aliases=["region"])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def regionalformat(self, ctx, language_code: str = None):
        """
        Changes bot's regional format in this server. This
        is used for formatting date, time and numbers.

        `<language_code>` can be any language code with country code included,
        e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.

        Leave `<language_code>` empty to base regional formatting on
        bot's locale in this server.
        """
        if language_code is None:
            i18n.set_contextual_regional_format(None)
            await self.bot._i18n_cache.set_regional_format(ctx.guild, None)
            await ctx.send(
                _(
                    "Regional formatting will now be based "
                    "on bot's locale in this server."
                )
            )
            return

        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _(
                    "Invalid format - language code has to "
                    "include country code, e.g. `en-US`"
                )
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_contextual_regional_format(standardized_locale_name)
        await self.bot._i18n_cache.set_regional_format(
            ctx.guild, standardized_locale_name
        )
        await ctx.send(
            _(
                "Regional formatting will now be based on `{language_code}` locale."
            ).format(language_code=standardized_locale_name)
        )

    @cog_ext.cog_slash(name="regionalformat")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def slash_regionalformat(self, ctx, language_code: str = None):
        """Changes bot's regional format in this server."""
        await ctx.defer()
        await self.regionalformat(language_code)

    @commands.group()
    async def account(self, ctx) -> None:
        """Link Minecraft account to Discord account."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @account.command(name="link")
    async def account_link(self, ctx, username: str) -> None:
        """Link account to discord account."""
        await ctx.channel.trigger_typing()
        profile_info = await self.bot.mojang_player(ctx.author, username)
        uuid: str = profile_info["uuid"]
        await self.bot._account_cache.set_account(ctx.author, uuid)

        await ctx.reply(f"Your account has been linked to {username}")

    @account.command(name="unlink")
    async def account_unlink(self, ctx) -> None:
        """Unlink minecraft account from discord account."""
        await self.bot._account_cache.set_account(ctx.author, None)
        await ctx.reply("Your account has been unlinked from any minecraft account")

    @commands.group()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def serverlink(self, ctx) -> None:
        """Link Minecraft server to Discord guild."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @serverlink.command(name="link")
    async def serverlink_link(self, ctx, server: str) -> None:
        """Link Minecraft server to Discord guild."""
        await self.bot._guild_cache.set_server(ctx.guild, server)
        await ctx.reply(f"Your guild has been linked to {server}")

    @serverlink.command(name="unlink")
    async def serverlink_unlink(self, ctx) -> None:
        """Unlink minecraft server from discord guild."""
        await self.bot._guild_cache.set_server(ctx.guild, None)
        await ctx.reply("Your guild has been unlinked from any minecraft server")

    @commands.group()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def autopost(self, ctx) -> None:
        """Link Minecraft account to Discord account."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autopost.group(name="setup")
    async def autopost_setup(self, ctx) -> None:
        """Autopost Minecraft News"""
        categories = ("release", "snapshot", "article", "outage")
        cat = {}

        def channel_check(m: discord.Message):
            channel_mention = True
            if m.author == ctx.author:
                if len(m.channel_mentions) != 0:
                    return True
                else:
                    channel_mention = False
            return False

        embed = discord.Embed(colour=self.bot.color)
        embed.description = _(
            "You have completed the automatic posting setup process. "
            "You can change these settings using /autopost edit"
        )
        for category in categories:

            pred = MessagePredicate.yes_or_no(ctx)
            await ctx.send(
                _("Would you like automatic posts of new {category}?").format(
                    category=category
                )
            )
            try:
                await self.bot.wait_for("message", check=pred, timeout=15.0)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return
            if pred.result is True:
                await ctx.send(
                    _(
                        "Which channel would you like this to happen in? "
                        "Mention the channel, for example #general"
                    )
                )
                try:
                    channel: discord.Message = await self.bot.wait_for(
                        "message", check=channel_check, timeout=15.0
                    )
                    cat[category] = channel.channel_mentions[0].id
                    embed.add_field(
                        name=category.capitalize(),
                        value=channel.channel_mentions[0].mention,
                    )
                except asyncio.TimeoutError:
                    await ctx.send(_("Response timed out."))
                    return
            else:
                cat[category] = None
                embed.add_field(name=category.capitalize(), value="None")
                await ctx.send(_("Ok."))
        await ctx.send("Completed automatic posting setup")

        await self.bot._guild_cache.set_news(ctx.guild, cat)
        await ctx.send(embed=embed)

    @autopost.group(name="edit")
    async def autopost_edit(self, ctx) -> None:
        """Autopost Minecraft News"""
        categories = ("release", "snapshot", "article", "outage")
        cat = {}

    @autopost.group(name="settings")
    async def autopost_settings(self, ctx) -> None:
        """Autopost Minecraft News"""
        news = await self.bot._guild_cache.get_news(ctx.guild)
        embed = discord.Embed(colour=self.bot.color)
        embed.description = _(
            "You have completed the automatic posting setup process. "
            "You can change these settings using /autopost edit"
        )
        for category in news.keys():
            if news[category] is not None:
                embed.add_field(
                    name=category.capitalize(),
                    value=self.bot.get_channel(news[category]).mention,
                )
            else:
                embed.add_field(name=category.capitalize(), value=news[category])
        await ctx.send(embed=embed)

    @autopost.group(name="test")
    async def autopost_test(self, ctx) -> None:
        """Autopost Minecraft News"""
        news = await self.bot._guild_cache.get_news(ctx.guild)
        for category in news.keys():
            if news[category] is not None:
                channel = self.bot.get_channel(news[category])
                await channel.send("test")

    @commands.group()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def rconconfig(self, ctx) -> None:
        """Link Minecraft account to Discord account."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @rconconfig.group(name="setup")
    async def rcon_setup(self, ctx) -> None:
        """Autopost Minecraft News"""

        def channel_check(m: discord.Message):
            if m.author == ctx.author:
                if len(m.channel_mentions) != 0:
                    return True

            return False

        def role_check(m: discord.Message):
            if m.author == ctx.author:
                if len(m.role_mentions) != 0:
                    return True

            return False

        def author_check(m: discord.Message):
            return m.author == ctx.author

        config = {}
        embed = discord.Embed(colour=self.bot.color)
        embed.description = _(
            "You have completed the rcon setup process. "
            "You can change these settings using /rconconfig edit"
        )

        await ctx.send(_("What is the ip address of your minecraft server"))
        try:
            config["address"] = await self.bot.wait_for(
                "message", check=author_check, timeout=15.0
            )
            embed.add_field(
                name=_("Address"),
                value=config["address"],
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return

        await ctx.send(_("What is the port of your minecraft server"))
        try:
            config["port"] = int(
                await self.bot.wait_for("message", check=author_check, timeout=15.0)
            )
            embed.add_field(
                name=_("Port"),
                value=config["port"],
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        await ctx.send(_("What is the password of your minecraft server rcon"))
        try:
            config["password"] = await self.bot.wait_for(
                "message", check=author_check, timeout=15.0
            )
            embed.add_field(
                name=_("Password"),
                value="************",
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        await ctx.send(_("What is the password of your minecraft server rcon"))
        try:
            roles: discord.Message = await self.bot.wait_for(
                "message", check=channel_check, timeout=15.0
            )
            config["roles"] = [role.id for role in roles.role_mentions]
            embed.add_field(
                name=_("Roles"),
                value="".join([role.mention for role in roles.role_mentions]),
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        await ctx.send(_("What is the password of your minecraft server rcon"))
        try:
            channel: discord.Message = await self.bot.wait_for(
                "message", check=channel_check, timeout=15.0
            )
            embed.add_field(
                name=_("Channel"),
                value=channel.channel_mentions[0].mention,
            )
            config["channel"] = channel.channel_mentions[0].id
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return

        await self.bot._rcon_cache.set_rcon(ctx.guild, config)
        await ctx.send(embed=embed)

    @rconconfig.group(name="edit")
    async def rcon_edit(self, ctx) -> None:
        """Autopost Minecraft News"""
        pass

    @rconconfig.group(name="settings")
    async def rcon_settings(self, ctx) -> None:
        """Autopost Minecraft News"""
        pass

    @rconconfig.group(name="test")
    async def rcon_test(self, ctx) -> None:
        """Autopost Minecraft News"""
        pass
