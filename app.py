from flask import Flask, jsonify, render_template_string
import threading
import os
import asyncio
import discord
from bot import bot, version_bot
import math

app = Flask(__name__)

# HTML template for the status page
STATUS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Roblox Version Tracker Bot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0;
        }
        .status-card {
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
        }
        .online { color: #4CAF50; }
        .offline { color: #f44336; }
        h1, h2 { text-align: center; }
        .version-info { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .platform {
            background: rgba(255,255,255,0.15);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .loading {
            color: #ffa500;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Roblox Version Tracker Bot</h1>
        
        <div class="status-card">
            <h2>Bot Status: 
                {% if bot_status == "online" %}
                    <span class="online">🟢 ONLINE</span>
                {% elif bot_status == "offline" %}
                    <span class="offline">🔴 OFFLINE</span>
                {% else %}
                    <span class="loading">🟡 CONNECTING...</span>
                {% endif %}
            </h2>
            <p><strong>Guilds Serving:</strong> {{ guild_count }}</p>
            <p><strong>Latency:</strong> {{ latency }}</p>
            <p><strong>Uptime:</strong> {{ uptime }}</p>
        </div>

        <div class="status-card">
            <h2>📊 Current Roblox Versions</h2>
            {% if versions %}
            <div class="version-info">
                {% for platform, data in versions.items() %}
                <div class="platform">
                    <h3>{{ data.emoji }} {{ platform }}</h3>
                    <p><strong>Version:</strong> {{ data.version }}</p>
                    <p><strong>Updated:</strong> {{ data.date }}</p>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p>No version data available</p>
            {% endif %}
        </div>

        <div class="status-card">
            <h2>🔄 Auto-Update Status</h2>
            <p><strong>Update Channel:</strong> {{ update_channel or "Not set" }}</p>
            <p><strong>Check Interval:</strong> 1 minute</p>
            <p><strong>Last Check:</strong> {{ last_check }}</p>
        </div>
    </div>
</body>
</html>
"""

def run_discord_bot():
    """Run the Discord bot in a separate thread"""
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not set!")
        return
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Discord bot error: {e}")

def get_bot_status():
    """Safely get bot status and latency"""
    try:
        if not bot.is_ready():
            return "connecting", 0, 0
        
        # Safely handle latency (could be NaN or float)
        latency = bot.latency
        if latency is None or math.isnan(latency):
            latency_ms = "Calculating..."
        else:
            latency_ms = f"{round(latency * 1000)}ms"
        
        return "online", len(bot.guilds), latency_ms
        
    except Exception as e:
        print(f"Error getting bot status: {e}")
        return "offline", 0, "Unknown"

@app.route('/')
def index():
    """Main status page"""
    bot_status, guild_count, latency = get_bot_status()
    
    # Get version data
    versions = {}
    if version_bot.last_data:
        platform_info = {
            'Windows': {'emoji': '🪟', 'version': version_bot.last_data['Windows'], 'date': version_bot.last_data['WindowsDate']},
            'Mac': {'emoji': '🍎', 'version': version_bot.last_data['Mac'], 'date': version_bot.last_data['MacDate']},
            'Android': {'emoji': '🤖', 'version': version_bot.last_data['Android'], 'date': version_bot.last_data['AndroidDate']},
            'iOS': {'emoji': '📱', 'version': version_bot.last_data['iOS'], 'date': version_bot.last_data['iOSDate']}
        }
        versions = platform_info
    
    # Get update channel info
    update_channel = None
    if version_bot.update_channel_id:
        try:
            channel = bot.get_channel(version_bot.update_channel_id)
            if channel:
                update_channel = f"#{channel.name}"
        except:
            update_channel = "Unknown"

    return render_template_string(STATUS_HTML,
        bot_status=bot_status,
        guild_count=guild_count,
        latency=latency,
        uptime="Running",
        versions=versions,
        update_channel=update_channel,
        last_check="Active" if bot_status == "online" else "Inactive"
    )

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    bot_status, guild_count, latency = get_bot_status()
    
    health_data = {
        "status": "healthy" if bot_status == "online" else "starting",
        "timestamp": discord.utils.utcnow().isoformat() if bot.is_ready() else "unknown",
        "guilds": guild_count,
        "latency": latency
    }
    
    status_code = 200 if bot_status == "online" else 503
    return jsonify(health_data), status_code

@app.route('/versions')
def versions_api():
    """API endpoint to get current versions"""
    if version_bot.last_data:
        return jsonify(version_bot.last_data)
    else:
        return jsonify({"error": "No version data available"}), 503

# Global error handler
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error", "message": str(error)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

if __name__ == '__main__':
    # Start Discord bot in a separate thread
    print("🚀 Starting Discord bot in background thread...")
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
