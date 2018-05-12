import asyncio
import datetime

from roxbot import checks, guild_settings, EmbedColours

import discord
from discord.ext import commands

# TODO: yes the menu system fucking sucks and will be fixed in the next version I just cba right now.
# TODO: Module the menu system
# TODO: Display the settings your changing in the menu as yu change them.

class Settings:
	"""
	Settings is a mix of settings and admin stuff for the bot. OWNER OR ADMIN ONLY.
	"""
	def __init__(self, bot_client):
		self.bot = bot_client
		self.bg_task = self.bot.loop.create_task(self.auto_backups())

	def get_channel(self, ctx, channel):
		if ctx.message.channel_mentions:
			return ctx.message.channel_mentions[0]
		else:
			return self.bot.get_channel(channel)

	async def auto_backups(self):
		await self.bot.wait_until_ready()
		raw_settings = guild_settings._open_config()
		while not self.bot.is_closed():
			if raw_settings != guild_settings._open_config():
				raw_settings = guild_settings._open_config()
				time = datetime.datetime.now()
				guild_settings.backup(raw_settings, "{:%Y.%m.%d %H:%M:%S} Auto Backup".format(time))
			await asyncio.sleep(300)

	@commands.command()
	@commands.is_owner()
	async def backup(self, ctx):
		time = datetime.datetime.now()
		filename = "{:%Y.%m.%d %H:%M:%S} Manual Backup".format(time)
		guild_settings.backup(guild_settings._open_config(), filename)
		return await ctx.send("Settings file backed up as '{}.json'".format(filename))

	def parse_setting(self, ctx, settings_to_copy, raw=False):
		settingcontent = ""
		setting = settings_to_copy.copy()
		convert = setting.get("convert", None)
		if convert is not None and not raw:
			for x in convert.keys():
				if convert[x] == "bool":
					if setting[x] == 0:
						setting[x] = "False"
					else:
						setting[x] = "True"
				elif convert[x] == "channel":
					if isinstance(setting[x], list):
						new_channels = []
						for channel in setting[x]:
							try:
								new_channels.append(self.bot.get_channel(channel).mention)
							except AttributeError:
								new_channels.append(channel)
						setting[x] = new_channels
					else:
						try:
							setting[x] = self.bot.get_channel(setting[x]).mention
						except AttributeError:
							pass
				elif convert[x] == "role":
					if isinstance(setting[x], list):
						new_roles = []
						for role_id in setting[x]:
							try:
								new_roles.append(discord.utils.get(ctx.guild.roles, id=role_id).name)
							except AttributeError:
								new_roles.append(role_id)
						setting[x] = new_roles
					else:
						try:
							setting[x] = discord.utils.get(ctx.guild.roles, id=setting[x]).name
						except AttributeError:
							pass
				elif convert[x] == "user":
					if isinstance(setting[x], list):
						new_users = []
						for user_id in setting[x]:

							user = self.bot.get_user(user_id)
							if user is None:
								new_users.append(str(user_id))
							else:
								new_users.append(str(user))
						setting[x] = new_users
					else:
						user = self.bot.get_user(setting[x])
						if user is None:
							setting[x] = str(setting[x])
						else:
							setting[x] = str(user)
		for x in setting.items():
			if x[0] != "convert":
				settingcontent += str(x).strip("()") + "\n"
		return settingcontent

	@commands.command(aliases=["printsettingsraw"])
	@checks.is_admin_or_mod()
	async def printsettings(self, ctx, option=None):
		"OWNER OR ADMIN ONLY: Prints the servers settings file."
		# TODO: Use paginator to make the output here not break all the time.
		config = guild_settings.get(ctx.guild)
		settings = dict(config.settings.copy())  # Make a copy of settings so we don't change the actual settings.
		em = discord.Embed(colour=EmbedColours.pink)
		em.set_author(name="{} settings for {}.".format(self.bot.user.name, ctx.message.guild.name), icon_url=self.bot.user.avatar_url)
		if option in settings:
			if ctx.invoked_with == "printsettingsraw":
				raw = True
			else:
				raw = False
			settingcontent = self.parse_setting(ctx, settings[option], raw=raw)
			em.add_field(name=option, value=settingcontent, inline=False)
			return await ctx.send(embed=em)
		else:
			for setting in settings:
				if setting != "custom_commands" and setting != "warnings":
					if ctx.invoked_with == "printsettingsraw":
						raw = True
					else:
						raw = False
					settingcontent = self.parse_setting(ctx, settings[setting], raw=raw)
					em.add_field(name=setting, value=settingcontent, inline=False)
				elif setting == "custom_commands":
					em.add_field(name="custom_commands", value="For Custom Commands, use the custom list command.", inline=False)
			return await ctx.send(embed=em)

	def _make_settings_menu(self, ctx):
		x = 0
		output = "'Roxbot Settings:' #Note: Some of this options aren't finish and don't work.\n—————————————————————————————\n"
		settings = []
		for setting in self.guild_settings:
			# is_anal has its own command for now but should be put into this menu when 2.0 hits.
			if setting in ["warnings", "custom_commands", "is_anal"]:
				pass
			elif setting == "gss" and ctx.guild.id != 393764974444675073:
				pass
			else:
				output += "[{}] Edit '{}' settings\n".format(x, setting)
				x += 1
				settings.append(setting)
		output += "[{}] Exit\n".format(0)
		x += 1
		settings.append("exit")
		return "```python\n" + output + "```", x, settings

	@commands.group(case_insensitive=True)
	@checks.is_admin_or_mod()
	async def settings(self, ctx):
		self.guild_settings = guild_settings.get(ctx.guild)
		if ctx.invoked_subcommand is None:
			output, count, settings = self._make_settings_menu(ctx)
			msg = await ctx.send(output)
			def author_reply(m):
				return m.author.id == ctx.author.id and ctx.channel.id == m.channel.id
			try:
				reply = await self.bot.wait_for("message", check=author_reply, timeout=40)
				if 0 > int(reply.content) > count:
					return await ctx.send("Option out of range. Exiting...")
				else:
					option = int(reply.content)
					if settings[option] == "logging":
						return await ctx.invoke(self.logging, msg=msg)
					elif settings[option] == "gss":
						return await ctx.invoke(self.gss, msg=msg)
					elif settings[option] == "self_assign":
						return await ctx.invoke(self.selfassign, msg=msg)
					elif settings[option] == "is_anal":
						return await ctx.invoke(self.serverisanal, msg=msg)
					elif settings[option] == "twitch":
						return await ctx.invoke(self.twitch, msg=msg)
					elif settings[option] == "nsfw":
						return await ctx.invoke(self.nsfw, msg=msg)
					elif settings[option] == "perm_roles":
						return await ctx.invoke(self.permrole, msg=msg)
					elif settings[option] == "voice":
						return await ctx.invoke(self.voice, msg=msg)
					elif settings[option] == "greets":
						return await ctx.invoke(self.joinleave, changes="greets", msg=msg)
					elif settings[option] == "goodbyes":
						return await ctx.invoke(self.joinleave, changes="goodbyes", msg=msg)
					else:
						await msg.delete()
						return await ctx.send("Exiting...")
			except ValueError:
				await msg.delete()
				raise commands.BadArgument("Invalid index given for menu. Exiting...")
			except asyncio.TimeoutError:
				await msg.delete()
				raise commands.CommandError("Menu timed out. Exiting...")

	@settings.command(aliases=["log"])
	async def logging(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits the logging settings.

		Options:
			enable/disable: Enable/disables logging.
			channel: sets the channel.
		"""
		# TODO: Optimise the menu system to be dynamic at some point
		if selection is None:
			output = """
```python
'Roxbot Settings: Logging'
—————————————————————————————
[0] Enable Logging
[1] Disable Logging
[2] Set Logging Channel
```
			"""
			if msg is None:
				msg = await ctx.send(output)
			else:
				msg = await msg.edit(content=output)

			def menu_check(m):
				return ctx.author == m.author and ctx.channel == m.channel

			try:
				response = await self.bot.wait_for("message", timeout=40, check=menu_check)
				if response.content == "0":
					selection = "enable"
				elif response.content == "1":
					selection = "disable"
				elif response.content == "2":
					selection = "channel"
					output = """
```python
'Roxbot Settings: Logging Channel'
—————————————————————————————
What channel should the Logging Channel be set to?
```
					"""
					msg = await msg.edit(content=output)
					res = await self.bot.wait_for("message", timeout=40, check=menu_check)
					channel = self.get_channel(ctx, res.content)
					if channel is False:
						raise commands.BadArgument("Channel {} not found. Exiting...".format(res.content))
					await msg.delete()
				else:
					await msg.delete()
					raise commands.BadArgument("Invalid index given for menu. Exiting...")
			except asyncio.TimeoutError:
				await msg.delete()
				raise commands.CommandError("Menu timed out. Exiting...")

		selection = selection.lower()
		settings = guild_settings.get(ctx.guild)

		if selection == "enable":
			settings.logging["enabled"] = 1
			await ctx.send("'logging' was enabled!")
		elif selection == "disable":
			settings.logging["enabled"] = 0
			await ctx.send("'logging' was disabled :cry:")
		elif selection == "channel":
			channel = self.get_channel(ctx, changes)
			settings.logging["channel"] = channel.id
			await ctx.send("{} has been set as the logging channel!".format(channel.mention))
		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(settings.logging, "logging")

	@settings.command(aliases=["sa"])
	async def selfassign(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits settings for self assign cog.

		Options:
			enable/disable: Enable/disables the cog.
			addrole/removerole: adds or removes a role that can be self assigned in the server.
		"""
		if selection is None:
			output = """
```python
'Roxbot Settings: Self Assign'
—————————————————————————————
[1] Enable Self Assign
[2] Disable Self Assign
[3] Add a role to the Self Assign list
[4] Remove a role to the Self Assign list
[5] List all roles that can be self-assigned
```
					"""
			if msg is None:
				msg = await ctx.send(output)
			else:
				msg = await msg.edit(content=output)

			def menu_check(m):
				return ctx.author == m.author and ctx.channel == m.channel

			try:
				response = await self.bot.wait_for("message", timeout=40, check=menu_check)
				if response.content == "1":
					selection = "enable"
				elif response.content == "2":
					selection = "disable"
				elif response.content == "3":
					selection = "addrole"
					output = """
```python
'Roxbot Settings: Self Assign - Add Role'
—————————————————————————————
What role do you want to make self-assignable?
```"""
				elif response.content == "4":
					selection = "removerole"
					output = """
```python
'Roxbot Settings: Self Assign - Remove Role'
—————————————————————————————
What role do you want remove from the self-assignable list?
```"""
				elif response.content == "5":
					return await ctx.invoke(self.printsettings, option="self_assign")
				else:
					await msg.delete()
					raise commands.BadArgument("Invalid index given for menu. Exiting...")

				if selection in ["removerole", "addrole"]:
					await msg.edit(content=output)
					res = await self.bot.wait_for("message", timeout=40, check=menu_check)
					role = discord.utils.get(ctx.guild.roles, name=res.content)
					if role is None:
						raise commands.BadArgument("Role {} not found. Exiting...".format(res.content))
					await msg.delete()
			except asyncio.TimeoutError:
				await msg.delete()
				raise commands.CommandError("Menu timed out. Exiting...")

		else:
			selection = selection.lower()
			role = discord.utils.find(lambda u: u.name == changes, ctx.message.guild.roles)

		self_assign = self.guild_settings.self_assign

		if selection == "enable":
			self_assign["enabled"] = 1
			await ctx.send("'self_assign' was enabled!")
		elif selection == "disable":
			self_assign["enabled"] = 0
			await ctx.send("'self_assign' was disabled :cry:")
		elif selection == "addrole":
			if role.id in self_assign["roles"]:
				return await ctx.send("{} is already a self-assignable role.".format(role.name))
			self_assign["roles"].append(role.id)
			await ctx.send('Role "{}" added'.format(str(role)))
		elif selection == "removerole":
			if role.id in self_assign["roles"]:
				self_assign["roles"].remove(role.id)
				await ctx.send('"{}" has been removed from the self-assignable roles.'.format(str(role)))
			else:
				return await ctx.send("That role was not in the list.")
		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(self_assign, "self_assign")

	@settings.command(aliases=["jl"])
	async def joinleave(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits settings for joinleave cog.

		Options:
			enable/disable: Enable/disables parts of the cog. Needs to specify which part.
				Example:
					;settings joinleave enable greets|goodbyes
			greetschannel/goodbyeschannel: Sets the channels for either option. Must be a ID or mention.
			custommessage: specifies a custom message for the greet messages.
		"""
		if selection is None:
			def menu_check(m):
				return ctx.author == m.author and ctx.channel == m.channel

			if changes is None:
				try:
					output = """
```python
'Roxbot Settings: JoinLeave'
—————————————————————————————
[1] Edit Greets
[2] Edit Goodbyes
```					
"""
					if msg is None:
						msg = await ctx.send(output)
					else:
						await msg.edit(content=output)
					response = await self.bot.wait_for("message", timeout=40, check=menu_check)
					if response.content == "1":
						changes = "greets"
					elif response.content == "2":
						changes = "goodbyes"
					else:
						await msg.delete()
						raise commands.BadArgument("Invalid index given for menu. Exiting...")
				except asyncio.TimeoutError:
					await msg.delete()
					raise commands.CommandError("Menu timed out. Exiting...")

			if changes == "greets":
				output = """
```python
'Roxbot Settings: JoinLeave - Greets'
—————————————————————————————
[1] Enable Greets
[2] Disable Greets
[3] Set Greets channel
[4] Add custom Greets message
```
						"""
			else:  # The only other option is goodbyes due to how this command is structured.
				output = """
```python
'Roxbot Settings: JoinLeave - Goodbyes'
—————————————————————————————
[1] Enable Goodbyes
[2] Disable Goodbyes
[3] Set Goodbyes channel
```
										"""
			await msg.edit(output)
			try:
				response = await self.bot.wait_for("message", timeout=40, check=menu_check)
				if response.content == "1":
					selection = "enable"
				elif response.content == "2":
					selection = "disable"
				elif response.content == "3" and changes == "greets":
					selection = "greetschannel"
				elif response.content == "3" and changes == "goodbyes":
					selection = "goodbyeschannel"
				elif response.content == "4" and changes == "greets":
					selection = "custommessage"
				else:
					await msg.delete()
					raise commands.BadArgument("Invalid index given for menu. Exiting...")
				if response.content == "3":
					output  = """
```python
'Roxbot Settings: JoinLeave - {0}'
—————————————————————————————
What channel do you want to set as the {0} channel?
```
""".format(changes.title())
					await msg.edit(content=output)
					response = await self.bot.wait_for("message", timeout=40, check=menu_check)
					channel = self.get_channel(ctx, response.content)
				elif response.content == "4":
					output = """
```python
'Roxbot Settings: JoinLeave - Greets'
—————————————————————————————
What channel do you want to set as the custom greets message?
```
					"""
					await msg.edit(content=output)
					response = await self.bot.wait_for("message", timeout=40, check=menu_check)
					changes = response.content
				else:
					await msg.delete()
					raise commands.BadArgument("Invalid index given for menu. Exiting...")
			except asyncio.TimeoutError:
				await msg.delete()
				raise commands.CommandError("Menu timed out. Exiting...")

		selection = selection.lower()
		channel = self.get_channel(ctx, changes)
		greets = self.guild_settings.greets
		goodbyes = self.guild_settings.goodbyes

		if changes == "greets":
			if selection == "enable":
				greets["enabled"] = 1
				await ctx.send("'greets' was enabled!")
			elif selection == "disable":
				greets["enabled"] = 0
				await ctx.send("'greets' was disabled :cry:")

		elif changes == "goodbyes":
			if selection == "enable":
				goodbyes["enabled"] = 1
				await ctx.send("'goodbyes' was enabled!")
			elif selection == "disable":
				goodbyes["enabled"] = 0
				await ctx.send("'goodbyes' was disabled :cry:")

		else:
			if selection == "greetschannel":
				greets["welcome-channel"] = channel.id
				changes = "greets"
				await ctx.send("{} has been set as the welcome channel!".format(channel.mention))
			elif selection == "goodbyeschannel":
				goodbyes["goodbye-channel"] = channel.id
				changes = "goodbyes"
				await ctx.send("{} has been set as the goodbye channel!".format(channel.mention))
			elif selection == "custommessage":
				greets["custom-message"] = changes
				await ctx.send("Custom message set to '{}'".format(changes))
				changes = "greets"
			else:
				return await ctx.send("No valid option given.")

		if changes == "greets":
			return self.guild_settings.update(greets, "greets")
		elif changes == "goodbyes":
			return self.guild_settings.update(goodbyes, "goodbyes")

	@settings.command()
	async def twitch(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits settings for self assign cog.

		Options:
			enable/disable: Enable/disables the cog.
			channel: Sets the channel to shill in.
		"""
		# TODO: Menu also needs editing since I edited the twitch backend
		selection = selection.lower()
		twitch = self.guild_settings.twitch

		if selection == "enable":
			twitch["enabled"] = 1
			await ctx.send("'twitch' was enabled!")
		elif selection == "disable":
			twitch["enabled"] = 0
			await ctx.send("'twitch' was disabled :cry:")
		elif selection == "channel":
			channel = self.get_channel(ctx, changes)
			twitch["channel"] = channel.id
			await ctx.send("{} has been set as the twitch shilling channel!".format(channel.mention))
		# Is lacking whitelist options. Might be added or might be depreciated.
		# Turns out this is handled in the cog and I don't think it needs changing but may be confusing.
		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(twitch, "twitch")

	@settings.command(aliases=["perms"])
	async def permrole(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits settings for permission roles.

		Options:
			addadmin/removeadmin: Adds/Removes admin role.
			addmod/removemod: Adds/Removes mod role.
		Example:
			;settings permrole addadmin Admin
		"""
		if selection is None:
			output = """
```python
'Roxbot Settings: Perm Roles'
—————————————————————————————
[1] Add Admin Role
[2] Remove Admin Role
[3] Add Mod Role
[4] Remove Mod Role
```
"""
			if msg is None:
				msg = await ctx.send(output)
			else:
				await msg.edit(content=output)

			def menu_check(m):
				return ctx.author == m.author and ctx.channel == m.channel

			try:
				response = await self.bot.wait_for("message", timeout=40, check=menu_check)
				if response.content == "1":
					selection = "addadmin"
				elif response.content == "2":
					selection = "removeadmin"
				elif response.content == "3":
					selection = "addmod"
				elif response.content == "4":
					selection = "removemod"
				else:
					await msg.delete()
					raise commands.BadArgument("Invalid index given for menu. Exiting...")
				if response.content in ["1", "3"]:
					output = """
```python
'Roxbot Settings: Perm Roles'
—————————————————————————————
What role do you want to add?
```
				"""
					await msg.edit(content=output)
					response = await self.bot.wait_for("message", timeout=40, check=menu_check)
					role = discord.utils.get(ctx.guild.roles, name=response.content)
					if role is None:
						raise commands.BadArgument("Role {} not found. Exiting...".format(response.content))
					await msg.delete()
			except asyncio.TimeoutError:
				await msg.delete()
				raise commands.CommandError("Menu timed out. Exiting...")

		selection = selection.lower()
		role = discord.utils.find(lambda u: u.name == changes, ctx.message.guild.roles)
		perm_roles = self.guild_settings.perm_roles

		if selection == "addadmin":
			if role.id not in perm_roles["admin"]:
				perm_roles["admin"].append(role.id)
				await ctx.send("'{}' has been added to the Admin role list.".format(role.name))
			else:
				return await ctx.send("'{}' is already in the list.".format(role.name))
		elif selection == "addmod":
			if role.id not in perm_roles["mod"]:
				perm_roles["mod"].append(role.id)
				await ctx.send("'{}' has been added to the Mod role list.".format(role.name))
			else:
				return await ctx.send("'{}' is already in the list.".format(role.name))
		elif selection == "removeadmin":
			try:
				perm_roles["admin"].remove(role.id)
				await ctx.send("'{}' has been removed from the Admin role list.".format(role.name))
			except ValueError:
				return await ctx.send("That role was not in the list.")
		elif selection == "removemod":
			try:
				perm_roles["mod"].remove(role.id)
				await ctx.send("'{}' has been removed from the Mod role list.".format(role.name))
			except ValueError:
				return await ctx.send("That role was not in the list.")

		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(perm_roles, "perm_roles")

	@settings.command()
	async def gss(self, ctx, selection=None, *, changes=None, msg=None):
		"""Custom Cog for the GaySoundsShitposts Discord Server."""
		# TODO: Menu
		selection = selection.lower()
		gss = self.guild_settings.gss

		if selection == "loggingchannel":
			channel = self.get_channel(ctx, changes)
			gss["log_channel"] = channel.id
			await ctx.send("Logging Channel set to '{}'".format(channel.name))
		elif selection == "requireddays":
			gss["required_days"] = int(changes)
			await ctx.send("Required days set to '{}'".format(str(changes)))
		elif selection == "requiredscore":
			gss["required_score"] = int(changes)
			await ctx.send("Required score set to '{}'".format(str(changes)))
		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(gss, "gss")


	@settings.command()
	async def nsfw(self, ctx, selection=None, *, changes=None, msg=None):
		"""Edits settings for the nsfw cog and other nsfw commands.
		If nsfw is enabled and nsfw channels are added, the bot will only allow nsfw commands in the specified channels.

		Options:
			enable/disable: Enable/disables nsfw commands.
			addchannel/removechannel: Adds/Removes a nsfw channel.
			addbadtag/removebadtag: Add/Removes blacklisted tags so that you can avoid em with the commands.
			Example:
				;settings nsfw addchannel #nsfw_stuff
		"""
		# TODO: Menu
		selection = selection.lower()
		nsfw = self.guild_settings.nsfw

		if selection == "enable":
			nsfw["enabled"] = 1
			await ctx.send("'nsfw' was enabled!")
		elif selection == "disable":
			nsfw["enabled"] = 0
			await ctx.send("'nsfw' was disabled :cry:")
		elif selection == "addchannel":
			channel = self.get_channel(ctx, changes)
			if channel.id not in nsfw["channels"]:
				nsfw["channels"].append(channel.id)
				await ctx.send("'{}' has been added to the nsfw channel list.".format(channel.name))
			else:
				return await ctx.send("'{}' is already in the list.".format(channel.name))
		elif selection == "removechannel":
			channel = self.get_channel(ctx, changes)
			try:
				nsfw["channels"].remove(channel.id)
				await ctx.send("'{}' has been removed from the nsfw channel list.".format(channel.name))
			except ValueError:
				return await ctx.send("That role was not in the list.")
		elif selection == "addbadtag":
			if changes not in nsfw["blacklist"]:
				nsfw["blacklist"].append(changes)
				await ctx.send("'{}' has been added to the blacklisted tag list.".format(changes))
			else:
				return await ctx.send("'{}' is already in the list.".format(changes))
		elif selection == "removebadtag":
			try:
				nsfw["blacklist"].remove(changes)
				await ctx.send("'{}' has been removed from the blacklisted tag list.".format(changes))
			except ValueError:
				return await ctx.send("That tag was not in the blacklisted tag list.")
		else:
			return await ctx.send("No valid option given.")
		return self.guild_settings.update(nsfw, "nsfw")

	@settings.command()
	async def voice(self, ctx, setting=None, change=None, msg=None):
		"""Edits settings for the voice cog.
		Options:
			enable/disable: Enable/disables specified change.
			skipratio: Specify what the ratio should be for skip voting if enabled. Example: 0.6 for 60%
			maxlength/duration: Specify (in seconds) the max duration of a video that can be played. Ignored if staff of the server/bot owner.
		Possible settings to enable/disable:
			needperms: specifies whether volume controls and other bot functions need mod/admin perms.
			skipvoting: specifies whether skipping should need over half of voice users to vote to skip. Bypassed by mods.
		Example:
			;settings voice enable skipvoting
		"""
		# TODO: Menu
		setting = setting.lower()
		change = change.lower()
		voice = self.guild_settings.voice

		if setting == "enable":
			if change == "needperms":
				voice["need_perms"] = 1
				await ctx.send("'{}' has been enabled!".format(change))
			elif change == "skipvoting":
				voice["skip_voting"] = 1
				await ctx.send("'{}' has been enabled!".format(change))
			else:
				return await ctx.send("Not a valid change.")
		elif setting == "disable":
			if change == "needperms":
				voice["need_perms"] = 1
				await ctx.send("'{}' was disabled :cry:".format(change))
			elif change == "skipvoting":
				voice["skip_voting"] = 1
				await ctx.send("'{}' was disabled :cry:".format(change))
			else:
				return await ctx.send("Not a valid change.")
		elif setting == "skipratio":
			change = float(change)
			if change < 1 and change > 0:
				voice["skip_ratio"] = change
			elif change > 0 and change <= 100:
				change = change/10
				voice["skip_ratio"] = change
			else:
				return await ctx.send("Valid ratio not given.")
			await ctx.send("Skip Ratio was set to {}".format(change))
		elif setting == "maxlength" or setting == "maxduration":
			change = int(change)
			if change >= 1:
				voice["skip_ratio"] = change
			else:
				return await ctx.send("Valid max duration not given.")
			await ctx.send("Max Duration was set to {}".format(change))
		else:
			return await ctx.send("Valid option not given.")
		return self.guild_settings.update(voice, "voice")

	@checks.is_admin_or_mod()
	@commands.command()
	async def serverisanal(self, ctx):
		"""Tells the bot where the server is anal or not.
		This only changes if roxbot can do the suck and spank commands outside of the specified nsfw channels."""
		is_anal = self.guild_settings.is_anal
		if is_anal["y/n"] == 0:
			is_anal["y/n"] = 1
			self.guild_settings.update(is_anal, "is_anal")
			await ctx.send("I now know this server is anal")
		else:
			is_anal["y/n"] = 0
			self.guild_settings.update(is_anal, "is_anal")
			await ctx.send("I now know this server is NOT anal")
		return self.guild_settings.update()


def setup(bot_client):
	bot_client.add_cog(Settings(bot_client))