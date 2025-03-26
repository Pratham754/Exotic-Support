import discord
import random
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os
import asyncio
import aiohttp
import shutil
import zipfile
import logging
import json

from keep_alive import keep_alive
keep_alive()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
logging.basicConfig(level=logging.ERROR)

bot = commands.Bot(command_prefix=commands.when_mentioned_or('>'), intents=intents, help_command=None)

# Event to handle errors
@bot.event
async def on_command_error(ctx, error):
    # Handle missing argument error
    if isinstance(error, commands.MissingRequiredArgument):
        # Log only the missing argument name
        logging.error(f"Missing required argument: {error.param}")
        await ctx.send(f"Error: Missing argument `{error.param}`. Please provide all required information.")
    # Handle other errors
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Unknown command: `{ctx.invoked_with}`.")
    else:
        # For any other error, log it as a generic error
        logging.error(f"An error occurred: {error}")
        await ctx.send(f"An error occurred: {error}")

# Event to handle on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


SUPPORTER_FILE = "supporter_roles.json"
# Load supporter roles from file
def load_supporter_roles():
    try:
        with open(SUPPORTER_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save supporter roles to the file
def save_supporter_roles():
    with open(SUPPORTER_FILE, "w") as file:
        json.dump(supporter_roles, file)

# Load supporter roles on bot startup
supporter_roles = load_supporter_roles()

# Helper function to get role by ID
def get_role(ctx, role_id):
    return discord.utils.get(ctx.guild.roles, id=role_id)

# Command to set the supporter role dynamically
@bot.command()
@commands.has_permissions(administrator=True)
async def setsupporter(ctx, role_id: int):
    role = get_role(ctx, role_id)
    if role is None:
        return await ctx.send("The provided role ID does not exist in this server.")

    supporter_roles[str(ctx.guild.id)] = role_id
    save_supporter_roles()
    await ctx.send(f"Supporter role set to `{role.name}` for this server.")

# Helper function to modify roles
async def modify_supporter_role(ctx, assign=True):
    guild_id = str(ctx.guild.id)
    role_id = supporter_roles.get(guild_id)

    if role_id is None:
        return await ctx.send("No supporter role has been set. Use `>setsupporter role_id` first.")

    role = get_role(ctx, role_id)
    if role is None:
        return await ctx.send("The stored 'Supporter' role does not exist in this server.")

    modified_members = []
    for member in ctx.guild.members:
        if member.status == discord.Status.offline:
            continue
        about_me = getattr(member, 'bio', "").lower()
        status_activities = [activity.name.lower() for activity in member.activities if isinstance(activity, discord.CustomActivity)]
        has_tropical = any(keyword in about_me or any(keyword in activity for activity in status_activities) for keyword in [".gg/tropical", "/tropical", "discord.gg/tropical"])

        if (assign and has_tropical and role not in member.roles) or (not assign and not has_tropical and role in member.roles):
            try:
                await (member.add_roles(role) if assign else member.remove_roles(role))
                modified_members.append(member.name)
            except (discord.Forbidden, discord.HTTPException) as e:
                await ctx.send(f"Error modifying {member.name}: {e}")

    action = "Assigned" if assign else "Removed"
    await ctx.send(f"{action} 'Supporter' role to/from:\n" + "\n".join(modified_members) if modified_members else "No changes made.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def addsupporter(ctx):
    await modify_supporter_role(ctx, assign=True)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removesupporter(ctx):
    await modify_supporter_role(ctx, assign=False)

@bot.command()
@commands.has_permissions(administrator=True)
async def userwith(ctx, role_id: int):
    role = get_role(ctx, role_id)
    if role is None:
        return await ctx.send(f"Role ID '{role_id}' not found.")

    members = [member.mention for member in ctx.guild.members if role in member.roles]
    if not members:
        return await ctx.send(f"No members have the role '{role.name}'.")

    # Split members into chunks of 50 per embed (to stay within Discord's limits)
    chunk_size = 50
    for i in range(0, len(members), chunk_size):
        embed = discord.Embed(
            title=f"Members with '{role.name}' role:",
            description="\n".join(members[i:i + chunk_size]),
            color=discord.Color.teal()
        )
        await ctx.send(embed=embed)
        
@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-"):
        await asyncio.sleep(0.5)
        await send_ticket_message(channel)

async def send_ticket_message(channel):
    embed = discord.Embed(
        title="**How May We Provide Assistance**",
        description=( 
            "<:1095flowerblue:1335625225706012824> — Roles\n"
            "<:2699flowerred:1335625230541914194> — Invite Rewards\n"
            "<:1916flowergreen:1335625226922364988> — Partnership\n"
            "<:2632flowerpurple:1335625220274257920> — Complaint\n"
            "<:1916floweryellow:1335625228197298186> — Any Other Query"
        ),
        color=discord.Color(0x00FFFF)
    )
    
    buttons = [
        ("Roles", discord.ButtonStyle.primary, "assistance_roles"),
        ("Invite Rewards", discord.ButtonStyle.primary, "assistance_rewards"),
        ("Partnership", discord.ButtonStyle.primary, "assistance_partnership"),
        ("Complaint", discord.ButtonStyle.danger, "assistance_complaint"),
        ("Any Other Query", discord.ButtonStyle.secondary, "assistance_other")
    ]
    
    view = View()
    for label, style, custom_id in buttons:
        view.add_item(Button(label=label, style=style, custom_id=custom_id))
    
    await channel.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def ticketmessage(ctx, channel_id: int):
    await ctx.message.delete()
    channel = bot.get_channel(channel_id)
    if not channel:
        return await ctx.send("Channel not found.")
    await send_ticket_message(channel)

@bot.command()
@commands.has_permissions(administrator=True)
async def simonsays(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="<:ex_announce:1353337649015951400> **What is Simon Says?**",
        description=( 
            "> <a:ex_dotblue:1353341050504216739> Simon Says is a game where you have to do what we say. "
            "If you don't do them you'll be eliminated from the game.\n\n"
            "> <a:ex_dotblue:1353341050504216739> You only have to do the task when we say **`simon says`** in the start. "
            "If we don't say it or wrong spelling you'll get eliminated\n‏"
        ),
        color=discord.Color(0x00FFFF)
    )
    embed.add_field(
        name="<a:ex_rules:1353340509661429831> **Example :**",
        value=( 
            "> <a:ex_yes:1353338267642363924> __Simon/simon__ __Says/says__ join VC\n"
            "> <a:ex_no:1353338261074088066> join VC\n"
            "> <a:ex_no:1353338261074088066> Simon say join VC\n"
            "> <a:ex_no:1353338261074088066> Simone says join VC\n‏"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

# Adding on_interaction for button interactions
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    initial_responses = {
        "assistance_roles": "You'll be taken care of ASAP regarding roles!\nTill then, please mention your query.",
        "assistance_rewards": "You'll be taken care of ASAP regarding invite rewards!\nTill then, please mention your query.",
        "assistance_partnership": "You'll be taken care of ASAP regarding partnership!\nTill then, please mention your query.",
        "assistance_complaint": "We'll address your complaint ASAP!\nTill then, please mention your query.",
        "assistance_other": "We'll assist you ASAP!\nTill then, please mention your query."
    }

    embed_details = {
        "assistance_roles": {
            "fields": [
                {"name": "**Supporter Role**", "value": "Have **.gg/tropical** or **/tropical** in your bio/status, drag exotic on top of the list, and send screenshots of the same.\n ‏", "inline": False},
                {"name": "**Access Role**", "value": "The role is given automatically when you have 3 invites. We use <@758592094964285441> for tracking invites.\nCheck: !invites", "inline": False}
            ]
        },
        "assistance_rewards": {
            "fields": [
                {"name": "**Fisch Rewards**", "value": "Enter your game username\nSend proof of every invite — Screenshots of DMs, Screenshots of mutual Fisch server or DMs about Fisch.\n ‏", "inline": False},
                {"name": "**Nitro Rewards: Members Event**", "value": "NO ALTS/J4Js INSTANT DISQUALIFY\nSend proof of every invite — Screenshots of DMs.", "inline": False}
            ]
        },
        "assistance_partnership": {
            "fields": [
                {"name": "**Partnership**", "value": "**Req:** We won't ping everyone.\nSend a screenshot of our ad in your server first.\n**Our Ad:** <#1340784723169116201>.\n ‏", "inline": False},
                {"name": "**Promotion**", "value": "Want everyone ping, Read: **<#1346856984070328453>**", "inline": False}
            ]
        },
        "assistance_complaint": {
            "fields": [
                {"name": "**For Complaints**", "value": "Please provide screenshots and details of the issue.", "inline": False}
            ]
        },
        "assistance_other": {
            "fields": [
                {"name": "Help", "value": "We'll assist you ASAP!", "inline": False}
            ]
        }
    }

    # Get the interaction's custom_id
    custom_id = interaction.data.get("custom_id", "")

    # Retrieve the initial response message
    response_message = initial_responses.get(custom_id, "Unknown selection.")

    # Create an embed with fields if extra details exist
    embed = None
    if custom_id in embed_details and custom_id != "assistance_other":
        embed_data = embed_details[custom_id]
        embed = discord.Embed(
            color=random.randint(0, 0xFFFFFF)  # Generates a random color
        )
        for field in embed_data["fields"]:
            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])

    # Disable all buttons after selection
    view = View()
    for row in interaction.message.components:
        for component in row.children:
            component.disabled = True
            button = Button(
                label=component.label,
                style=component.style,
                custom_id=component.custom_id,
                disabled=True
            )
            view.add_item(button)

    await interaction.message.edit(view=view)
    # Send the first line as a normal message and the details as an embed
    await interaction.response.send_message(response_message, embed=embed)

# Command to download all emojis in the server
@bot.command()
async def downloademojis(ctx):
    folder_path = "emojis"
    zip_filename = "emojis.zip"

    # Create a folder to store the emojis
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)  # Remove if already exists
    os.makedirs(folder_path)

    async with aiohttp.ClientSession() as session:
        for emoji in ctx.guild.emojis:
            emoji_url = emoji.url
            file_extension = "gif" if emoji.animated else "png"
            file_path = os.path.join(folder_path, f"{emoji.name}.{file_extension}")

            async with session.get(str(emoji_url)) as response:
                if response.status == 200:
                    with open(file_path, "wb") as file:
                        file.write(await response.read())

    # Create a ZIP file
    shutil.make_archive("emojis", "zip", folder_path)

    # Send the ZIP file
    await ctx.send(file=discord.File(zip_filename))

    # Clean up
    os.remove(zip_filename)
    shutil.rmtree(folder_path)

#Event to handle ticket closure
@bot.event
async def on_guild_channel_update(before, after):
    # Check if the channel was renamed to start with "closed-"
    if before.name != after.name and after.name.startswith("closed-"):
        embed = discord.Embed(
            title="Ticket Closure Notice",
            description="This ticket has been marked as closed.\n\n"
                        "To delete this ticket, use the following command:\n\n"
                        "`>delete @ticket_owner {reason}`\n\n"
                        "**Example:**\n"
                        "`>delete @wumpus Issue resolved, closing the ticket.`",
            color=discord.Color.red()
        )
        embed.set_footer(text="Use this command when you're sure the issue is resolved.")

        # Send the embed inside the ticket channel
        await after.send(embed=embed)

# Command to delete a ticket channel
@bot.command()
@commands.has_permissions(manage_channels=True)
async def delete(ctx, ticket_owner: discord.User, *, reason: str = "No reason provided"):

    who_closed = ctx.author  # The staff member who closed the ticket

    if not isinstance(ctx.channel, discord.TextChannel):
        return await ctx.send("This command can only be used in a server channel.")

    # DM the ticket owner if they are still in the server
    dm_message = (
        f"Hello {ticket_owner.mention},\n\n"
        f"Your ticket `{ctx.channel.name}` has been deleted by {who_closed.mention}.\n"
        f"**Reason:** {reason}"
    )

    try:
        await ticket_owner.send(dm_message)
        await ctx.send(f"✅ Sent a DM to {ticket_owner.mention} before deleting the ticket.")
    except discord.Forbidden:
        await ctx.send(f"⚠️ Could not DM {ticket_owner.mention}. Deleting the ticket anyway.")
    except AttributeError:  # If the user left the server, `ticket_owner` is no longer a Member
        await ctx.send(f"⚠️ Ticket owner is no longer in the server. Skipping DM.")

    # Delete the ticket channel
    try:
        await ctx.channel.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete this channel.")
    except discord.HTTPException:
        await ctx.send("❌ An error occurred while trying to delete the channel.")

@bot.command()
async def staffbreak(ctx):
    await ctx.message.delete()
    # Check if the command is run in the specific channel
    if ctx.channel.id != 1344360595335548988:
        return await ctx.send("This command can only be used in the designated channel.")
    
    # Ask the user to enter the reason
    prompt_reason = await ctx.send("Please provide the reason for the staff break:")
    
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        reason_msg = await bot.wait_for('message', check=check, timeout=60)
        reason = reason_msg.content
        
        # Delete both the bot's question and the user's response
        await asyncio.sleep(1)
        await prompt_reason.delete()  
        await reason_msg.delete()

        # Now ask for the duration
        prompt_duration = await ctx.send("Please provide the duration of the break (e.g., 15 days):")
        
        duration_msg = await bot.wait_for('message', check=check, timeout=60)
        duration = duration_msg.content
        
        # Delete both the bot's question and the user's response
        await asyncio.sleep(1)
        await prompt_duration.delete()
        await duration_msg.delete()

        # Finally, ask for the return date
        prompt_return_date = await ctx.send("Please provide the return date (e.g., 13/04/25):")
        
        return_date_msg = await bot.wait_for('message', check=check, timeout=60)
        return_date = return_date_msg.content
        
        # Delete both the bot's question and the user's response
        await asyncio.sleep(1)
        await prompt_return_date.delete()
        await return_date_msg.delete()

        # Create the embed with the provided information
        embed = discord.Embed(
            title="<a:exh_imp:1353418774782672917> **STAFF BREAK** <a:exh_imp:1353418774782672917>",
            description=f"""
            <a:exh_dotpink:1353418747125174392> **User:** {ctx.author.mention}
            <a:exh_dotpink:1353418747125174392> **Reason:** {reason}
            <a:exh_dotpink:1353418747125174392> **Duration:** {duration}
            <a:exh_dotpink:1353418747125174392> **Returning:** {return_date}
            """,
            color=discord.Color.from_str("#00FFFF")
        )
        embed.set_footer(text="I accept the consequences if I fail to return by the specified date.")

        # Send the embed to the same channel
        await ctx.send(embed=embed)

    except asyncio.TimeoutError:
        await ctx.send("You took too long to respond. Please try again.")



# Command to show available commands
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="**Exotic Commands**",
        description="Here are the available commands and their descriptions:",
        color=discord.Color(0x00FFFF)  # Aqua color
    )
    
    # Add commands and their descriptions
    embed.add_field(name=">addsupporter", 
                value="Assign the 'Supporter' role to users who have '.gg/tropical' or '/tropical' in their bio or status.\n ‏", inline=False)
    
    embed.add_field(name=">removesupporter", 
                value="Remove the 'Supporter' role from users who no longer meet the criteria.\n ‏", inline=False)
    
    embed.add_field(name=">userwith {role_id}",
                    value="List all members with a specific role.\n ‏", inline=False)
    
    embed.add_field(name=">ticketmessage {channel_id}", 
                value="Send an interactive ticket message with buttons to the specified channel.\n ‏", inline=False)

    embed.add_field(name=">simonsays", 
                value="Explains the Simon Says game rules and examples.\n ‏", inline=False)

    embed.add_field(name=">downloademojis", 
                value="Download all emojis from the server as a ZIP file.\n ‏", inline=False)
    
    embed.add_field(name=">delete @ticket_owner {reason}",
                    value="Delete a closed ticket channel with a reason.\n ‏", inline=False)

    embed.add_field(name=">staffbreak",
                    value="Initiate a staff break by providing a reason, duration, and return date.\n ‏", inline=False)
    
    embed.add_field(name=">help",
                    value="Show this list of available commands.\n ‏", inline=False)

    embed.set_footer(text="Exotic", icon_url=bot.user.display_avatar.url)

    await ctx.send(embed=embed)

bot.run(TOKEN)
