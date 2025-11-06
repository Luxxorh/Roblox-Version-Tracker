import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
from datetime import datetime, timezone
import re
import math

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

class RobloxVersionBot:
    def __init__(self):
        self.api_url = "https://weao.xyz/api/versions/current"
        self.headers = {"User-Agent": "WEAO-3PService"}
        self.last_data = None
        self.current_presence_version = None
        self.update_channel_id = None

    async def fetch_versions(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"Error fetching data: {response.status}")
                        return None
        except asyncio.TimeoutError:
            print("❌ API request timed out")
            return None
        except Exception as e:
            print(f"Exception occurred: {e}")
            return None

    def has_data_changed(self, new_data):
        """Check if the data has changed since last fetch"""
        if self.last_data is None:
            return True
        
        fields_to_check = ['Windows', 'Mac', 'Android', 'iOS']
        for field in fields_to_check:
            if self.last_data.get(field) != new_data.get(field):
                return True
        
        return False

    def get_changed_platforms(self, new_data):
        """Get list of platforms that have changed"""
        if self.last_data is None:
            return []
        
        changed_platforms = []
        platforms = ['Windows', 'Mac', 'Android', 'iOS']
        
        for platform in platforms:
            if self.last_data.get(platform) != new_data.get(platform):
                changed_platforms.append(platform)
        
        return changed_platforms

    def format_date(self, date_string):
        """Format date string to match the image style"""
        try:
            date_obj = datetime.strptime(date_string, '%m/%d/%Y, %I:%M:%S %p %Z')
            return date_obj.strftime('%A, %d %B %Y %I:%M %p')
        except:
            return date_string

    def get_download_link(self, platform, version_hash):
        """Generate download link for Windows and Mac platforms"""
        if platform == "Windows":
            return f"https://rdd.weao.gg/?channel=live&binaryType=WindowsPlayer&version={version_hash}"
        elif platform == "Mac":
            return f"https://rdd.weao.gg/?channel=live&binaryType=MacPlayer&version={version_hash}"
        else:
            return None

    def create_current_version_embed(self, data, platform):
        """Create a simple embed showing current version for a platform"""
        platform_info = {
            'Windows': {'emoji': '🪟', 'hash': data['Windows'], 'date': data['WindowsDate'], 'color': 0x0078d7},
            'Mac': {'emoji': '🍎', 'hash': data['Mac'], 'date': data['MacDate'], 'color': 0x999999},
            'Android': {'emoji': '🤖', 'hash': data['Android'], 'date': data['AndroidDate'], 'color': 0x3ddc84},
            'iOS': {'emoji': '📱', 'hash': data['iOS'], 'date': data['iOSDate'], 'color': 0x007aff}
        }
        
        platform_data = platform_info[platform]
        
        embed = discord.Embed(
            title=f"{platform_data['emoji']} Current Roblox Version - {platform}",
            color=platform_data['color'],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="🔑 Current Version:", value=f"`{platform_data['hash']}`", inline=False)
        embed.add_field(name="📅 Last Updated:", value=self.format_date(platform_data['date']), inline=False)
        
        download_link = self.get_download_link(platform, platform_data['hash'])
        if download_link:
            embed.add_field(name="⬇️ Download:", value=f"[Click to download]({download_link})", inline=False)
        
        embed.set_footer(text="Powered by WEAO API | Admin Only")
        return embed

    def create_update_embed(self, data, platform, old_version):
        """Create an update detection embed"""
        platform_info = {
            'Windows': {'emoji': '🪟', 'hash': data['Windows'], 'date': data['WindowsDate'], 'color': 0x0078d7},
            'Mac': {'emoji': '🍎', 'hash': data['Mac'], 'date': data['MacDate'], 'color': 0x999999},
            'Android': {'emoji': '🤖', 'hash': data['Android'], 'date': data['AndroidDate'], 'color': 0x3ddc84},
            'iOS': {'emoji': '📱', 'hash': data['iOS'], 'date': data['iOSDate'], 'color': 0x007aff}
        }
        
        platform_data = platform_info[platform]
        
        embed = discord.Embed(
            title="🚀 A future Roblox update has been detected!",
            description="This is a future update, no need to worry about Roblox exploits being patched yet.\n\u200b",
            color=platform_data['color']
        )
        
        embed.add_field(name="📋 Platform:", value=f"**{platform}** {platform_data['emoji']}", inline=True)
        embed.add_field(name="🔑 Hash:", value=f"`{platform_data['hash']}`", inline=True)
        embed.add_field(name="📅 Date:", value=self.format_date(platform_data['date']), inline=False)
        
        download_link = self.get_download_link(platform, platform_data['hash'])
        if download_link:
            embed.add_field(name="⬇️ Download", value=f"[Click to download]({download_link})", inline=False)
        
        embed.add_field(name="🔄 Change Detected", value=f"**Previous version:** `{old_version}`\n**New version:** `{platform_data['hash']}`", inline=False)
        
        embed.set_footer(text="Powered by WEAO, The #1 Roblox exploit status tracker | Channel LIVE")
        return embed

    def create_versions_embed(self, data):
        """Create a comprehensive embed showing all platforms"""
        embed = discord.Embed(title="📊 All Roblox Versions", color=0x5865F2, timestamp=datetime.now(timezone.utc))
        
        platforms = [
            ('Windows', '🪟', data['Windows'], data['WindowsDate']),
            ('Mac', '🍎', data['Mac'], data['MacDate']),
            ('Android', '🤖', data['Android'], data['AndroidDate']),
            ('iOS', '📱', data['iOS'], data['iOSDate'])
        ]
        
        for platform, emoji, version, date in platforms:
            download_link = self.get_download_link(platform, version)
            if download_link:
                value = f"**Version:** `{version}`\n**Updated:** {self.format_date(date)}\n**Download:** [Click here]({download_link})"
            else:
                value = f"**Version:** `{version}`\n**Updated:** {self.format_date(date)}\n**Download:** *Not available*"
            
            embed.add_field(name=f"{emoji} {platform}", value=value, inline=False)
        
        embed.set_footer(text="Powered by WEAO API | Admin Only")
        return embed

version_bot = RobloxVersionBot()

def is_administrator():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has successfully connected to Discord!')
    print(f'📊 Serving {len(bot.guilds)} guild(s)')
    
    initial_data = await version_bot.fetch_versions()
    if initial_data:
        version_bot.last_data = initial_data
        version_bot.current_presence_version = initial_data['Android']
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"Roblox v{initial_data['Android']} | Auto-Update")
        await bot.change_presence(activity=activity)
        print(f"✅ Initial presence set to: Roblox v{initial_data['Android']}")
    
    auto_check_updates.start()
    auto_update_presence.start()

@bot.command(name='setchannel')
@is_administrator()
async def set_channel(ctx):
    """Set the current channel for automatic update notifications (Admin Only)"""
    version_bot.update_channel_id = ctx.channel.id
    embed = discord.Embed(
        title="✅ Update Channel Set",
        description=f"Automatic update notifications will be sent to this channel: {ctx.channel.mention}",
        color=0x00ff00,
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)
    print(f"📢 Update channel set to: #{ctx.channel.name} (ID: {ctx.channel.id})")

@bot.command(name='versions')
@is_administrator()
async def versions(ctx):
    """Get current Roblox versions for all platforms (Admin Only)"""
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        try:
            await ctx.author.send("I don't have permission to send messages in that channel.")
        except:
            pass
        return
    
    if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
        await ctx.send("I need the 'Embed Links' permission to display version information properly.")
        return

    data = await version_bot.fetch_versions()
    
    if data:
        embed = version_bot.create_versions_embed(data)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to fetch version data from the API.")

@bot.command(name='windows') 
@is_administrator()
async def windows_update(ctx):
    """Get current Windows Roblox version (Admin Only)"""
    await send_platform_current_version(ctx, 'Windows')

@bot.command(name='mac')
@is_administrator()
async def mac_update(ctx):
    """Get current Mac Roblox version (Admin Only)"""
    await send_platform_current_version(ctx, 'Mac')

@bot.command(name='android')
@is_administrator()
async def android_update(ctx):
    """Get current Android Roblox version (Admin Only)"""
    await send_platform_current_version(ctx, 'Android')

@bot.command(name='ios')
@is_administrator()
async def ios_update(ctx):
    """Get current iOS Roblox version (Admin Only)"""
    await send_platform_current_version(ctx, 'iOS')

async def send_platform_current_version(ctx, platform):
    """Helper function to send platform-specific current version embeds"""
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        return
    if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
        await ctx.send("I need the 'Embed Links' permission to display version information properly.")
        return

    data = await version_bot.fetch_versions()
    
    if data:
        embed = version_bot.create_current_version_embed(data, platform)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Failed to fetch {platform} version data from the API.")

@bot.command(name='status')
@is_administrator()
async def status(ctx):
    """Check bot status and update configuration (Admin Only)"""
    embed = discord.Embed(
        title="🤖 Bot Status & Configuration",
        color=0x3498db,
        timestamp=datetime.now(timezone.utc)
    )
    
    if version_bot.last_data:
        embed.add_field(
            name="📊 Current Versions",
            value=f"**Windows:** `{version_bot.last_data['Windows']}`\n**Android:** `{version_bot.last_data['Android']}`\n**Last Check:** Automatic monitoring",
            inline=False
        )
    else:
        embed.add_field(
            name="📊 Current Data",
            value="No data fetched yet",
            inline=False
        )
    
    update_channel_info = "Not set - Use `!setchannel`"
    if version_bot.update_channel_id:
        channel = bot.get_channel(version_bot.update_channel_id)
        if channel:
            update_channel_info = f"{channel.mention} (`{version_bot.update_channel_id}`)"
        else:
            update_channel_info = f"Channel not found (`{version_bot.update_channel_id}`)"
    
    # Safely handle latency - FIXED NaN issue
    try:
        latency = bot.latency
        if latency is None or math.isnan(latency):
            latency_display = "Calculating..."
        else:
            latency_display = f"{round(latency * 1000)}ms"
    except (TypeError, ValueError):
        latency_display = "Unknown"
    
    embed.add_field(
        name="🔄 Auto-Update Settings",
        value=f"**Update Channel:** {update_channel_info}\n**Check Interval:** 1 minute\n**Mode:** Update detection only",
        inline=False
    )
    
    embed.add_field(
        name="⚡ System Info",
        value=f"**Latency:** {latency_display}\n**Guilds:** {len(bot.guilds)}",
        inline=False
    )
    
    await ctx.send(embed=embed)

@tasks.loop(minutes=1)
async def auto_check_updates():
    """Automatically check for updates and send update detection embeds"""
    try:
        data = await version_bot.fetch_versions()
        if data:
            # Check for changes
            changed_platforms = version_bot.get_changed_platforms(data)
            
            if changed_platforms and version_bot.update_channel_id:
                # Get the update channel
                update_channel = bot.get_channel(version_bot.update_channel_id)
                
                if update_channel and update_channel.permissions_for(update_channel.guild.me).send_messages:
                    
                    # Send update detection embeds for each changed platform
                    for platform in changed_platforms:
                        old_version = version_bot.last_data.get(platform)
                        embed = version_bot.create_update_embed(data, platform, old_version)
                        await update_channel.send(embed=embed)
                        print(f"🚀 Update detected for {platform}: {old_version} → {data[platform]}")
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)
                
                # Update last data
                version_bot.last_data = data
                
            elif changed_platforms:
                # Changes detected but no channel set
                print(f"🔔 Updates detected for {changed_platforms} but no update channel configured")
                version_bot.last_data = data
                
            else:
                # No changes detected
                print("✅ No updates detected in auto-check")
                
        else:
            print("❌ Failed to fetch data for auto-update check")
            
    except Exception as e:
        print(f"Error in auto_check_updates: {e}")

@tasks.loop(minutes=1)
async def auto_update_presence():
    """Auto-update bot presence only when data changes"""
    try:
        data = await version_bot.fetch_versions()
        if data:
            # Check if Android version has changed
            if version_bot.has_data_changed(data):
                old_version = version_bot.current_presence_version
                version_bot.current_presence_version = data['Android']
                
                # Update bot presence with latest Android version
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"Roblox v{data['Android']} | Auto-Update"
                )
                await bot.change_presence(activity=activity)
                
                print(f"🔄 Presence updated: Roblox v{old_version} → v{data['Android']}")
        else:
            print("❌ Failed to fetch data for presence check")
    except Exception as e:
        print(f"Error in auto_update_presence: {e}")

@auto_check_updates.before_loop
@auto_update_presence.before_loop
async def before_tasks():
    """Wait until the bot is ready before starting the task"""
    await bot.wait_until_ready()

# Error handling for non-admin users
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="This bot is restricted to **Administrators** only.",
            color=0xff0000
        )
        embed.add_field(
            name="Required Permissions",
            value="You need **Administrator** permissions in this server to use bot commands.",
            inline=False
        )
        
        try:
            await ctx.send(embed=embed)
        except:
            try:
                await ctx.author.send(embed=embed)
            except:
                pass
    
    elif isinstance(error, commands.CommandInvokeError):
        if "Missing Permissions" in str(error):
            try:
                await ctx.author.send("I don't have the necessary permissions to execute that command.")
            except:
                pass
        else:
            print(f"Command error: {error}")
    elif isinstance(error, commands.CommandNotFound):
        if ctx.author.guild_permissions.administrator:
            await ctx.send("Command not found. Available commands: `!versions`, `!setchannel`, `!windows`, `!mac`, `!android`, `!ios`, `!status`")
    else:
        print(f"Unexpected error: {error}")

# Prevent non-admins from using any commands
@bot.check
async def global_check(ctx):
    """Global check that applies to all commands"""
    return ctx.author.guild_permissions.administrator
