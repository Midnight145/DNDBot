from discord.ext import commands
import discord
import datetime
import io

nl = "\n"


class Member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = self.bot.config["member_log"]

    @commands.Cog.listener()
    async def on_member_join(self, member):

        days_ago = discord.utils.utcnow() - member.created_at
        embed = discord.Embed(
            title="Join Notification",
            description=f'{member.mention} ({str(member)}) has joined the server!',
            timestamp=discord.utils.utcnow(),
            color=discord.Color.from_rgb(5, 110, 247)
        )
        embed.add_field(name="Creation Date", value=f'{member.created_at.strftime("%a %b %d %H:%M:%S")}\n{days_ago.days} days ago', inline=False)

        embed.set_image(url=member.display_avatar.replace(format='png'))
        embed.set_footer(text=f'There are now {member.guild.member_count} members')
        channel = member.guild.get_channel(self.log_channel)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Kick Logging
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target == member:
                embed = discord.Embed(
                    description=f'**Kicked {member.name}**{member.discriminator} *(ID: {member.id})*\n\n**Reason**: '
                                f'{entry.reason if entry.reason is not None else "None"}',
                    color=discord.Color.from_rgb(242, 160, 19),
                    timestamp=discord.utils.utcnow())
                embed.set_author(name=f'{entry.user} ({entry.user.id})',
                                 icon_url=entry.user.display_avatar.replace(format='png'))
                embed.set_thumbnail(url=member.display_avatar.replace(format='png'))
                channel = self.bot.get_channel(self.log_channel)
                await channel.send(embed=embed)
                return

        # Leave Logging
        embed = discord.Embed(
            title="Leave Notification",
            description=f'{member.mention} ({str(member)}) has left the server!',
            timestamp=discord.utils.utcnow(),
            color=discord.Color.from_rgb(5, 110, 247)
        )
        embed.add_field(name="Roles",
                        value=f'{(" ".join([i.mention for i in member.roles][1::])) if len(member.roles[1::]) > 0 else "None"}')
        embed.set_footer(text=f'There are now {member.guild.member_count} members')
        embed.set_image(url=member.display_avatar.replace(format='png'))

        channel = self.bot.get_channel(self.log_channel)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        channel = before.guild.get_channel(self.bot.config["member_log"])
        # Nickname Logging
        by = False
        audit = None
        if before.nick != after.nick:
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.before.nick == before.nick and entry.after.nick == after.nick:
                    by = True
                    audit = entry
            embed = discord.Embed(
                description=f'**Nickname Change**\n`{before.nick}` → '
                            f'`{after.nick}`\n{"Changed by " + str(audit.user) if by else ""}',
                color=discord.Color.from_rgb(255, 140, 0),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=f"{str(after)} ({after.id})", icon_url=after.display_avatar.replace(format='png'))
            await channel.send(embed=embed)

        # Role Logging
        if sorted(before.roles, key=lambda x: x.id) != sorted(after.roles, key=lambda x: x.id):
            audit = None
            reason = False
            async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry is not None:
                    audit = entry
                    reason = True
            diff = [i for i in after.roles + before.roles if i not in after.roles or i not in before.roles]
            new_roles = []
            removed_roles = []
            for i in diff:
                if i in after.roles and i not in before.roles:
                    new_roles.append(i)
                if i in before.roles and i not in after.roles:
                    removed_roles.append(i)

            embed = discord.Embed(
                title="Member Role Change",
                timestamp=discord.utils.utcnow(),
                color=discord.Color.from_rgb(241, 196, 15))
            embed.add_field(name="ID", value=str(before.id))
            if len(before.roles) != 0:
                embed.add_field(name="Old Roles", value=(" ".join([i.mention for i in before.roles][1::])) if len(
                    before.roles[1::]) > 0 else "None", inline=False)
            if len(new_roles) != 0:
                embed.add_field(name="Roles Added", value=" ".join([i.mention for i in new_roles]), inline=False)
            if len(removed_roles) != 0:
                embed.add_field(name="Roles Removed", value=" ".join([i.mention for i in removed_roles]), inline=False)
            embed.set_author(name=before, icon_url=before.display_avatar.replace(format='png'))
            embed.add_field(name="Change made by:",
                            value=f'{str(before) if reason == False else str(audit.user) + (" because " + audit.reason if audit.reason is not None else "")}',
                            inline=False)

            if not len(embed) >= 2000:
                await channel.send(embed=embed)
                return
            string = f"Member Role Change\nID: {str(before.id)}"
            if len(before.roles) != 0:
                string += f"Old Roles: {', '.join([i.name for i in before.roles][1::]) if len(before.roles[1::]) > 0 else 'None'}\n"
            if len(new_roles) != 0:
                string += f"Roles Added: {', '.join([i.name for i in new_roles])}\n"
            if len(removed_roles) != 0:
                string += f"Roles Removed: {', '.join([i.name for i in removed_roles])}"

            file = io.BytesIO()
            file.write(string.encode("utf-8"))
            attach = discord.File(filename=f"{before.display_name}_role_change.txt", fp=file)
            await channel.send(file=attach)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        reason = None
        channel = self.bot.get_channel(self.log_channel)
        audit = None
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            audit = entry
            reason = entry.reason
        embed = discord.Embed(
            title=f"⛔️ User Banned by {str(audit.user)}",
            timestamp=discord.utils.utcnow(),
            color=discord.Color.from_rgb(255, 0, 0))
        embed.add_field(name="Username", value=str(user))
        embed.add_field(name="ID", value=str(user.id))
        embed.add_field(name="Reason", value=reason if reason is not None else "None")
        embed.set_thumbnail(url=user.display_avatar.replace(format='png'))
        embed.set_author(name=str(audit.user), icon_url=audit.user.display_avatar.replace(format='png'))
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = self.bot.get_channel(self.log_channel)
        audit = None
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            audit = entry
        embed = discord.Embed(
            title=f"✅️ User Unbanned by {str(audit.user)}",
            timestamp=discord.utils.utcnow(),
            color=discord.Color.from_rgb(98, 198, 95))
        embed.add_field(name="Username", value=str(user))
        embed.add_field(name="ID", value=str(user.id))
        embed.set_thumbnail(url=user.display_avatar.replace(format='png'))
        embed.set_author(name=str(audit.user), icon_url=audit.user.display_avatar.replace(format='png'))
        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Member(bot))
