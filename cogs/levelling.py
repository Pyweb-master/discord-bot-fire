import discord
import random
import time
import math
from discord.ext import commands
class AdminCommands(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content[:2] in ["f.", "p!"] or message.content[0] == ";": return
        result = await self.client.pg_con.fetchval("SELECT exp_muted FROM level_settings WHERE guild_id = $1", message.guild.id)
        if not result is None:
            if str(message.channel.id) in result: return

        author_id = message.author.id
        guild_id = message.guild.id

        result = await self.client.pg_con.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", guild_id, author_id)

        if not result:
            await self.client.pg_con.execute("INSERT INTO levels(guild_id, user_id, exp, lvl, last_msg) VALUES($1,$2,$3,$4,$5)",  guild_id, author_id, 0, 0, time.time()-60)
            result = await self.client.pg_con.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", guild_id, author_id)

        if time.time()-int(float(result["last_msg"]))>60:
            result2 = await self.client.pg_con.fetchrow("SELECT * FROM level_settings WHERE guild_id = $1", guild_id)
            if result2 is None:
                await self.client.pg_con.execute("INSERT INTO level_settings(guild_id, multiplier) VALUES($1, $2)", guild_id, 1)
                result2 = await self.client.pg_con.fetchrow("SELECT * FROM level_settings WHERE guild_id = $1", guild_id)

            exp = int(result["exp"])
            multiplier = int(result2["multiplier"])

            if len(message.content) > 100: message_addon = 100/2.5
            else: message_addon = round(len(message.content)/2.5)
            new_exp = (exp+random.randint(10,20)*multiplier)+message_addon
            await self.client.pg_con.execute("UPDATE levels SET exp = $1, last_msg = $2 WHERE guild_id = $3 and user_id = $4", new_exp, time.time(), guild_id, author_id)

            result2 = await self.client.pg_con.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", guild_id, author_id)
            exp_start = int(result2["exp"])
            lvl_start = int(result2["lvl"])
            exp_end = math.floor(5 * (lvl_start ** 2) + 50 * lvl_start + 100)

            if exp_end<exp_start:
                await self.client.pg_con.execute("UPDATE levels SET lvl = $1, exp = $2 WHERE guild_id = $3 and user_id = $4", lvl_start + 1, exp_start - exp_end, guild_id, author_id)

                if lvl_start+1 == 5: await message.author.add_roles(discord.utils.get(message.author.guild.roles, id=749699380214366318)) ## TODO change these hardcoded roles to server specific
                elif lvl_start+1 == 10: await message.author.add_roles(discord.utils.get(message.author.guild.roles, id=741008881563467989)) ## TODO change these hardcoded roles to server specific
                elif lvl_start+1 == 20: await message.author.add_roles(discord.utils.get(message.author.guild.roles, id=741008953911017553)) ## TODO change these hardcoded roles to server specific
                elif lvl_start+1 == 30: await message.author.add_roles(discord.utils.get(message.author.guild.roles, id=752222222269284456))  ## TODO change these hardcoded roles to server specific

    @commands.command()
    async def rank(self, ctx, user:discord.User=None):
        if user is None:
            result = await self.client.pg_con.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
            if not result:
                await ctx.send("You aren't ranked yet! Send messages to get exp.")
            else:
                embed = discord.Embed(colour=discord.Colour.orange())
                embed.set_author(name=f"{ctx.message.author.name}'s Rank", icon_url=ctx.message.author.avatar_url)
                embed.add_field(name=f"Level:", value=result["lvl"])
                embed.add_field(name=f"EXP:", value=f"{str(result['exp'])}/{math.floor(5 * ((int(result['lvl'])+1) ** 2) + 50 * (int(result['lvl'])+1) + 100)}")

                await ctx.send(embed=embed)

        else:
            result = await self.client.pg_con.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            if not result:
                await ctx.send("They aren't ranked yet! They have to send messages to get exp.")
            else:
                embed = discord.Embed(colour=discord.Colour.orange())
                embed.set_author(name=f"{user.name}'s Rank", icon_url=user.avatar_url)
                embed.add_field(name=f"Level:", value=result["lvl"])
                embed.add_field(name=f"EXP:", value=f"{result['exp']}/{math.floor(5 * ((int(result['lvl'])+1) ** 2) + 50 * (int(result['lvl'])+1) + 100)}")

                await ctx.send(embed=embed)

    @commands.command()
    async def exp_multiplier(self, ctx, number:float):
        if number > 5:
            await ctx.send("Sorry. The maximum multiplier you can have is 5")
            return
        result = await self.client.pg_con.fetchval("SELECT multiplier FROM level_settings WHERE guild_id = $1", ctx.guild.id)
        if result is None:
            await self.client.pg_con.execute("INSERT INTO level_settings(guild_id, multiplier) VALUES($1,$2)", ctx.guild.id, number)
            await ctx.send(f"The exp multiplier has been set to {number}")
        else:
            await self.client.pg_con.execute("UPDATE level_settings SET multiplier = $1 WHERE guild_id = $2", number, ctx.guild.id)
            await ctx.send(f"The exp multiplier has been updated to {number}")

    @commands.command(aliases=["set_level", "set_rank"])
    @commands.has_permissions(administrator=True)
    async def set_lvl(self, ctx, amount:int, *, user:discord.User=None):
        if user is None: user = ctx.author
        guild_id = ctx.guild.id

        result = await self.client.pg_con.fetchval("SELECT lvl FROM levels WHERE guild_id = $1 and user_id = $2", guild_id, user.id)
        if result is None:
            await self.client.pg_con.execute("INSERT INTO levels(guild_id, user_id, exp, lvl, last_msg) VALUES($1,$2,$3,$4,$5)",  guild_id, user.id, 0, amount, time.time()-60)
        else:
            await self.client.pg_con.execute("UPDATE levels SET lvl = $1 WHERE guild_id = $2 and user_id = $3", amount, guild_id, user.id)
        await ctx.send(f"{user.name}'s level has been set to {amount}")


    @commands.command(aliases=["set_experience", "set_ex"])
    @commands.has_permissions(administrator=True)
    async def set_exp(self, ctx, amount: int, *, user: discord.User = None):
        if user is None: user = ctx.author
        guild_id = ctx.guild.id

        result = await self.client.pg_con.fetchval("SELECT exp FROM levels WHERE guild_id = $1 and user_id = $2", guild_id, user.id)
        if result is None:
            if amount>=100:
                await ctx.send("You cannot give more exp than their current level exp requirement is")
                return
            await self.client.pg_con.execute("INSERT INTO levels(guild_id, user_id, exp, lvl, last_msg) VALUES($1,$2,$3,$4,$5)", guild_id, user.id, amount, 0, time.time() - 60)
        else:
            result = await self.client.pg_con.fetchval("SELECT lvl FROM levels WHERE guild_id = $1 and user_id = $2", guild_id, user.id)
            if amount>=math.floor(5*((int(result)+1)**2)+50*(int(result)+1)+100):
                await ctx.send("You cannot give more exp than their current level exp requirement is")
                return
            await self.client.pg_con.execute("UPDATE levels SET exp = $1 WHERE guild_id = $2 and user_id = $3", amount, guild_id, user.id)

        await ctx.send(f"{user.name}'s exp has been set to {amount}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def exp_mute(self, ctx, channel:discord.TextChannel):
        result = await self.client.pg_con.fetchrow("SELECT * FROM level_settings WHERE guild_id = $1", ctx.guild.id)
        if result["exp_muted"] is None: await self.client.pg_con.execute("UPDATE level_settings SET exp_muted = $1 WHERE guild_id = $2", [str(channel.id)], ctx.guild.id)
        else:
            lst = result["exp_muted"]
            lst.append(str(channel.id))
            await self.client.pg_con.execute("UPDATE level_settings SET exp_muted = $1 WHERE guild_id = $2", lst, ctx.guild.id)

        await ctx.send(f"{channel.mention} is now exp muted")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def exp_unmute(self, ctx, channel: discord.TextChannel):
        result = await self.client.pg_con.fetchrow("SELECT * FROM level_settings WHERE guild_id = $1", ctx.guild.id)
        if result["exp_muted"] is None: await ctx.send("You haven't exp muted anything!")
        else:
            lst = result["exp_muted"]
            if str(channel.id) not in lst: await ctx.send(f"The channel {channel.mention} is not currently exp muted")
            else:
                lst.remove(str(channel.id))
                await self.client.pg_con.execute("UPDATE level_settings SET exp_muted = $1 WHERE guild_id = $2", lst, ctx.guild.id)
                await ctx.send(f"{channel.mention} is no longer exp muted")

    @commands.command()
    async def show_exp_muted(self, ctx):
        result = await self.client.pg_con.fetchval("SELECT exp_muted FROM level_settings WHERE guild_id = $1", ctx.guild.id)
        lst = []
        for i in result:
            lst.append(f"<#{str(i)}>")

        embed = discord.Embed(colour=discord.Colour.orange(), description=", ".join(lst))
        embed.set_author(name=f"Exp Muted Channels", icon_url=self.client.user.avatar_url)

        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(AdminCommands(client))