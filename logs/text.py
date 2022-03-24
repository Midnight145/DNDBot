import discord
from columnar import columnar
from discord.ext import commands
import datetime
import os


class Text(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel = self.bot.config["text_log"]

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, message_list):
        message_channel = message_list[0].channel
        filename = message_channel.name + "_on_" + datetime.datetime.utcnow().strftime("%a_%b_%d_at_%H_%M_%S") + ".txt"
        headers = ["discord tag", "user id", "content", "timestamp"]
        data = [[i.author.name + "#" + i.author.discriminator, i.author.id, i.content, i.created_at.strftime("%a_%b_%d_at_%H_%M_%S")] for i in message_list]
        table = columnar(data, headers, no_borders=True, terminal_width=200)
        with open(filename, 'w+') as file:
            file.write(table)

        embed = discord.Embed(
            title='Messages Bulk Deleted',
            description=f'Messages bulk deleted from {message_channel.mention}. Deleted messages are available in the attached file.',
            color=discord.Color.from_rgb(241, 196, 14),
            timestamp=datetime.datetime.utcnow()
        )
        channel = message_channel.guild.get_channel(self.channel)
        file = open(filename, 'r')
        await channel.send(embed=embed, file=discord.File(file, filename))
        file.close()
        os.remove(filename)


def setup(bot):
    bot.add_cog(Text(bot))
