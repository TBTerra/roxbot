from discord.ext import commands


class UserConverter(commands.UserConverter):
	"""Overriding the discord version to add a slower global look up for when it is a requirement to return a user who has left the guild.

	Converts to a :class:`User`.

	All lookups are via the global user cache. (Excluding the last one which makes an api call to discord.

	The lookup strategy is as follows (in order):

	1. Lookup by ID.
	2. Lookup by mention.
	3. Lookup by name#discrim
	4. Lookup by name
	5. Lookup by get_user_info
	"""
	async def convert(self, ctx, argument):
		try:
			result = await super().convert(ctx, argument)
		except commands.BadArgument as e:
			try:
				result = await ctx.bot.get_user_info(argument)
			except:  # Bare except or otherwise it will raise its own BadArgument and have a pretty shitty error message that isnt useful.
				raise e

		return result