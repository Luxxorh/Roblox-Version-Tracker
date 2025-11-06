import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
from datetime import datetime, timezone
import re

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
    version_bot.update_channel_id = ctx.channel.id
    embed = discord.Embed(title="✅ Update Channel Set", description=f"Automatic update notifications will be sent to this channel: {ctx.channel.mention}", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name='versions')
@is_administrator()
async def versions(ctx):
    data = await version_bot.fetch_versions()
    if data:
        embed = version_bot.create_versions_embed(data)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to fetch version data from the API.")

@bot.command(name='windows') 
@is_administrator()
async def windows_update(ctx):
    await send_platform_current_version(ctx, 'Windows')

@bot.command(name='mac')
@is_administrator()
async def mac_update(ctx):
    await send_platform_current_version(ctx, 'Mac')

@bot.command(name='android')
@is_administrator()
async def android_update(ctx):
    await send_platform_current_version(ctx, 'Android')

@bot.command(name='ios')
@is_administrator()
async def ios_update(ctx):
    await send_platform_current_version(ctx, 'iOS')

async def send_platform_current_version(ctx, platform):
    data = await version_bot.fetch_versions()
    if data:
        embed = version_bot.create_current_version_embed(data, platform)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Failed to fetch {platform} version data from the API.")

@bot.command(name='status')
@is_administrator()
async def status(ctx):
    embed = discord.Embed(title="🤖 Bot Status", color=0x3498db)
    
    if version_bot.last_data:
        embed.add_field(name="📊 Current Versions", value=f"**Windows:** `{version_bot.last_data['Windows']}`\n**Android:** `{version_bot.last_data['Android']}`", inline=False)
    
    update_channel_info = "Not set"
    if version_bot.update_channel_id:
        channel = bot.get_channel(version_bot.update_channel_id)
        if channel:
            update_channel_info = f"{channel.mention}"
    
    embed.add_field(name="🔄 Auto-Update", value=f"**Channel:** {update_channel_info}\n**Interval:** 1 minute", inline=False)
    embed.add_field(name="⚡ System", value=f"**Latency:** {round(bot.latency * 1000)}ms\n**Guilds:** {len(bot.guilds)}", inline=False)
    
    await ctx.send(embed=embed)

@tasks.loop(minutes=1)
async def auto_check_updates():
    try:
        data = await version_bot.fetch_versions()
        if data:
            changed_platforms = version_bot.get_changed_platforms(data)
            
            if changed_platforms and version_bot.update_channel_id:
                update_channel = bot.get_channel(version_bot.update_channel_id)
                
                if update_channel:
                    for platform in changed_platforms:
                        old_version = version_bot.last_data.get(platform)
                        embed = version_bot.create_update_embed(data, platform, old_version)
                        await update_channel.send(embed=embed)
                        print(f"🚀 Update detected for {platform}: {old_version} → {data[platform]}")
                        await asyncio.sleep(1)
                
                version_bot.last_data = data
                
            elif changed_platforms:
                print(f"🔔 Updates detected for {changed_platforms} but no update channel configured")
                version_bot.last_data = data
                
            else:
                print("✅ No updates detected")
                
    except Exception as e:
        print(f"Error in auto_check_updates: {e}")

@tasks.loop(minutes=1)
async def auto_update_presence():
    try:
        data = await version_bot.fetch_versions()
        if data and version_bot.has_data_changed(data):
            version_bot.current_presence_version = data['Android']
            activity = discord.Activity(type=discord.ActivityType.watching, name=f"Roblox v{data['Android']} | Auto-Update")
            await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Error in auto_update_presence: {e}")

@auto_check_updates.before_loop
@auto_update_presence.before_loop
async def before_tasks():
    await bot.wait_until_ready()

@bot.check
async def global_check(ctx):
    return ctx.author.guild_permissions.administrator
