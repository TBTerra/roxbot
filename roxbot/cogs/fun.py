import re
import random
import discord
from discord.ext.commands import bot

import roxbot


class Fun:
	def __init__(self, bot_client):
		self.bot = bot_client

	@bot.command()  # Terra made this and it just work's but im too scared to clean it up so i hope it doesn't break
	async def roll(self, ctx, expression=""):
		"""
		Rolls a die using dice expression format.
		Usage:
			{command_prefix}roll expression
			spaces in expression are ignored
		Example:
			.roll 2d20h1 + 7 # Rolls two D20s takes the highest 1, then adds 7
			.roll #will give brief overview of dice expression format

		Dice expression format:
			An expression can consist of many sub expressions added together and then a multiplier at the end to indicate how many times the expression should be rolled.
			Sub expressions can be of many types:
				<number> #add this number to the total
				d<sides> #roll a dice with that many sides and add it to the total
				<n>d<sides> #roll n dice. each of those dice have <sides> number of sides, sum all the dice and add to the total
					add r<number> #reroll any rolls below <number>
					add h<number> #only sum the <number> highest rolls rather than all of them
					add l<number> #only sum the <number> lowest rolls rather than all of them
				+<number> # Add this number to the sum.
				x<number> #only use at the end. roll the rest of the expression <number> times(max 10)")
		Credit: TBTerra#5677
		"""
		rollMaxRolls = 10
		rollMaxVerbose = 10
		rollMaxDice = 1000
		response = ''
		rollVerbose = True
		# sanitise input by removing all spaces, converting to lower case
		expression = expression.lower().replace(' ','')
		# check end of expression for a 'x<number>'
		parts = expression.split('x',1)
		times = 1
		if len(parts) == 2:#if theres a x
			try:#try and work out the number after the x
				times = int(parts[1])
				if times < 1:#cant roll less than once
					times = 1
				if times > rollMaxRolls:#dont want to lag the bot/spam the chat by rolling hundreds of times
					response += "*Warning:* cannot roll an expression more than {0} times. will roll {0} times rather than {1}.\n".format(rollMaxRolls,times)
					times = rollMaxRolls
			except ValueError:#probably an input syntax error. safest to just roll once.
				times = 1
				response += "*Warning:* was unable to resolve how many times this command was meant to run. defaulted to once.\n"
		m=re.findall('(-?)((?:(\d*)d(\d*))|\d+)(r\d*)?([h,l]{1}\d*)?',parts[0])#voodoo magic regex (matches A,dB,AdB,AdBrC and AdBh/lD all at once, and splits them up to be processed)
		if m == []:#either there were no arguments, or the expression contained nothing that could be seen as a number or roll
			return await ctx.send("Expression missing. If you are unsure of what the format should be, please use `{}help roll`".format(ctx.prefix))
		dice = []#this is the list of all dice sets to be rolled
		#each element of the list is a 5 element list, containing the sign of the set, how many dice it has, how many sides on each dice, what numbers to re-roll, and how many to select(in that order)
		for item in m:
			temp = [0]*5
			temp[0] = 1 if item[0] == '' else -1#if theres a - at the beginning of the sub expression there needs to be a -1 multiplier applied to the sub expression total
			if 'd' in item[1]:#if its a dice/set of dice rather than a number
				if item[2] == '':#if its just a dY rather than an XdY
					temp[1] = 1
					temp[2] = int(item[3])
				else:#its a XdY type unknown if it has r,h,l modifyers, but they dont matter when sorting out the number and sides of dice
					temp[1] = int(item[2])
					if temp[1] > rollMaxDice:#if there are an unreasonable number of dice, error out. almost no-one needs to roll 9999d20
						return await ctx.send("I'm sorry {}, I'm afraid I cant do that. (To many dice to roll, max {})".format(self.bot.user.name,rollMaxDice))
					if temp[1] > rollMaxVerbose and rollVerbose == True:#if there is a sub expression that involves lots of rolls then turn off verbose mode
						rollVerbose = False
						response += '*Warning:* large number of rolls detected, will not use verbose rolling.\n'
					temp[2] = int(item[3])
			else:#numbers are stored as N, 1 sided dice
				temp[1] = int(item[1])
				temp[2] = 1
			temp[3] = 0 if item[4] == '' else int(item[4][1:])#if it has a reroll value use that. if not, reroll on 0
			if item[5] == '':#it has no select requirment
				temp[4] = 0
			else:
				if item[5][0] == 'h':#select highest use positive select argument
					temp[4] = int(item[5][1:])
				else:#select lowest so use negative select argument
					temp[4] = -int(item[5][1:])
			dice.append(temp)
		#at this point dice contains everything needed to do a roll. if you saved dice then you could roll it again without having to re-parse everything (possible roll saving feature in future?)
		for i in range(times):
			total = 0
			if times > 1:
				response += 'Roll {}: '.format(i+1)
			else:
				response += 'Rolled: '
			for j in range(len(dice)):#for each dice set in the expression
				if j != 0 and rollVerbose:#dont need the + before the first element
					response += ' + '
				if dice[j][0] == -1 and rollVerbose:#all the dice sets will return positive numbers so the sign is set entirely by the sign value (element 0)
					response += '-'
				if dice[j][2] == 1:#its just a number
					if rollVerbose:
						response += '{}'.format(dice[j][1])
					total += dice[j][0] * dice[j][1]
				else:#its a dice or set of dice
					if rollVerbose:
						response += '('
					temp = []
					for k in range(dice[j][1]):#for each dice in number of dice
						t = [0,'']
						t[0] = random.randint(1,dice[j][2])#roll the dice
						t[1] = '{}'.format(t[0])
						if t[0] <= dice[j][3]:#if its below or equal to the re-roll value, then re-roll it
							t[0] = random.randint(1,dice[j][2])
							t[1] += '__{}__'.format(t[0])#underline the re-roll so its clear thats the one to pay attention to
						temp.append(t)
					def takeFirst(ele):
						return ele[0]
					if dice[j][4] > 0:#if its selecting highest
						temp.sort(key=takeFirst, reverse=True)#sort the rolled dice. highest first
						for k in range(len(temp)):
							if k >= dice[j][4]:#if the position in the sorted list is greater than the number of dice wanted, cross it out, and make it not count towards the total
								temp[k][1] = '~~' + temp[k][1] + '~~'
								temp[k][0] = 0
					if dice[j][4] < 0:#if its selecting lowest
						temp.sort(key=takeFirst)
						for k in range(len(temp)):#sort the rolled dice. lowest first
							if k >= -dice[j][4]:#if the position in the sorted list is greater than the number of dice wanted, cross it out, and make it not count towards the total
								temp[k][1] = '~~' + temp[k][1] + '~~'
								temp[k][0] = 0
					for k in range(len(temp)):##loop through all dice rolled and add them to the total. also print them if in verbose mode
						if rollVerbose:
							response += '{},'.format(temp[k][1])
						total+= dice[j][0] * temp[k][0]
					if rollVerbose:
						response = response[:-1] + ')'#clip the trailing ',' and replace it with a ')'
			if rollVerbose:
				response += ' Totaling: {}'.format(total)
			else:
				response += ' Total: {}'.format(total)
			if i < (times-1): response += '\n'
		return await ctx.send(response)

	@roxbot.checks.isnt_anal()
	@bot.command()
	async def spank(self, ctx, *, user: discord.User = None):
		"""
		Spanks the mentioned user ;)
		Usage:
			{command_prefix}spank @roxbot#4170
			{command_prefix}spank roxbot
		"""
		if not user:
			return await ctx.send("You didn't mention someone for me to spank")
		return await ctx.send(":peach: :wave: *{} spanks {}*".format(self.bot.user.name, user.name))

	@roxbot.checks.isnt_anal()
	@bot.command(aliases=["succ"])
	async def suck(self, ctx, *, user: discord.User = None):
		"""
		Sucks the mentioned user ;)
		Usage:
			{command_prefix}suck @roxbot#4170
			{command_prefix}suck roxbot
		"""
		if not user:
			return await ctx.send("You didn't mention someone for me to suck")
		return await ctx.send(":eggplant: :sweat_drops: :tongue: *{} sucks {}*".format(self.bot.user.name, user.name))

	@bot.command()
	async def hug(self, ctx, *, user: discord.User = None):
		"""
		Hugs the mentioned user :3
		Usage:
			{command_prefix}hug @roxbot#4170
			{command_prefix}hug Roxbott
		"""
		if not user:
			return await ctx.send("You didn't mention someone for me to hug")
		return await ctx.send(":blush: *{} hugs {}*".format(self.bot.user.name, user.name))

	@bot.command(aliases=["headpat", "pat"])
	async def pet(self, ctx, *, user: discord.User = None):
		"""
		Gives headpats to the mentioned user :3
		Usage:
			{command_prefix}pet @roxbot#4170
			{command_prefix}pet roxbot
		"""
		if not user:
			return await ctx.send("You didn't mention someone for me to headpat")
		return await ctx.send("Nyaa! :3 *{} gives headpats to {}*".format(self.bot.user.name, user.name))

	@bot.command(aliases=["wf", "wr", "husbandorate", "hr", "spousurate", "sr"])
	async def waifurate(self, ctx):
		"""
		Rates the mentioned waifu(s). husbando/spousurate also work.
		Usage:
			{command_prefix}waifurate @user#9999
		This command is in dedicated to Hannah, who suggested this command to me. I hope she's out there, somewhere, getting her waifus rated in peace.
		"""
		mentions = ctx.message.mentions
		if ctx.invoked_with in ["hr", "husbandorate"]:
			waifu = "husbando"
		elif ctx.invoked_with in ["sr", "spousurate"]:
			waifu = "spousu"
		else:
			waifu = "waifu"

		if not mentions:
			return await ctx.send("You didn't mention anyone for me to rate.", delete_after=10)

		rating = random.randrange(1, 11)
		if rating <= 2:
			emoji = ":sob:"
		elif rating <= 4:
			emoji = ":disappointed:"
		elif rating <= 6:
			emoji = ":thinking:"
		elif rating <= 8:
			emoji = ":blush:"
		elif rating == 9:
			emoji = ":kissing_heart:"
		else:
			emoji = ":heart_eyes:"

		if len(mentions) > 1:
			return await ctx.send("Oh poly {} rating? :smirk: Your combined waifu rating is {}/10. {}".format(waifu, rating, emoji))
		else:
			return await ctx.send("Oh that's your {}? I rate them a {}/10. {}".format(waifu, rating, emoji))

	@bot.command(aliases=["cf"])
	async def coinflip(self, ctx):
		"""Flip a coin"""
		return await ctx.send("The coin landed on {}!".format(random.choice(["heads", "tails"])))

	@bot.command()
	async def aesthetics(self, ctx, *, convert):
		"""Converts text to be more  a e s t h e t i c s"""
		WIDE_MAP = dict((i, i + 0xFEE0) for i in range(0x21, 0x7F))
		WIDE_MAP[0x20] = 0x3000
		converted = str(convert).translate(WIDE_MAP)
		await ctx.send(converted)

		logging = roxbot.guild_settings.get(ctx.guild).logging
		log_channel = self.bot.get_channel(logging["channel"])
		await roxbot.log(ctx.guild, log_channel, "aesthetics", User=ctx.author, Argument_Given=convert, Channel=ctx.channel, Channel_Mention=ctx.channel.mention)

	@bot.command(aliases=["ft", "frog"])
	async def frogtips(self, ctx):
		"""RETURNS FROG TIPS FOR HOW TO OPERATE YOUR FROG"""
		endpoint = "https://frog.tips/api/1/tips/"
		croak = await roxbot.http.api_request(endpoint)
		tip = random.choice(croak["tips"])
		embed = discord.Embed(title="Frog Tip #{}".format(tip["number"]), description=tip["tip"], colour=roxbot.EmbedColours.frog_green)
		embed.set_author(name="HOW TO OPERATE YOUR FROG")
		embed.set_footer(text="https://frog.tips")
		return await ctx.send(embed=embed)


def setup(bot_client):
	bot_client.add_cog(Fun(bot_client))