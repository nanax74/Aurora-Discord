import discord
import asyncio
import os
import subprocess
from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE"))

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
EXE_PATH = os.getenv("EXE_PATH")
BOT_NAME = os.getenv("BOT_NAME")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

process = None

async def read_stdout(channel):
    buffer = []
    last_send = asyncio.get_event_loop().time()
    incomplete_line = ""  # 途中の行を保持

    while True:
        if process is None:
            await asyncio.sleep(0.01)
            continue

        chunk = await process.stdout.read(1024)
        if not chunk:
            await asyncio.sleep(0.01)
            continue

        text = chunk.decode(errors="ignore")
        lines = text.splitlines()

        # 途中行を先頭に結合
        if incomplete_line:
            lines[0] = incomplete_line + lines[0]
            incomplete_line = ""

        # 最後の行が改行で終わっていなければ incomplete_line として保持
        if not text.endswith("\n") and lines:
            incomplete_line = lines.pop()

        buffer.extend([line.strip() for line in lines if line.strip()])

        now = asyncio.get_event_loop().time()
        if buffer and (len(buffer) >= 10 or (now - last_send) >= 0.2):
            try:
                await channel.send("```\n" + "\n".join(buffer) + "\n```")
            except Exception as e:
                print("Discord send error:", e)
            buffer.clear()
            last_send = now

        await asyncio.sleep(0.01)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    channel = client.get_channel(CHANNEL_ID)

    global process
    process = await asyncio.create_subprocess_exec(
        EXE_PATH,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # 標準出力読み取りループを開始
    asyncio.create_task(read_stdout(channel))
    await channel.send(f"[{BOT_NAME}] Aurora-Discord has started")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != CHANNEL_ID:
        return

    cmd = message.content

    if process and cmd:
        process.stdin.write((cmd + "\n").encode())
        await process.stdin.drain()

client.run(TOKEN)
