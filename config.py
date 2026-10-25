import os

# ==========================================================
# Telegram Music Bot Configuration
# ==========================================================

# Telegram API credentials from https://my.telegram.org
API_ID: int = int(os.getenv("API_ID", 38953431))
API_HASH: str = os.getenv("API_HASH", "2ba6fc60c837d5dfa52352304831a7c1")

# Telegram Bot Token from @BotFather
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8975164612:AAFiuzuhMKMxCGkRHesmdopGKThivrxkjes")

# Pyrogram String Session for the Assistant User Account
# You can generate this using `python generate_session.py`
STRING_SESSION: str = os.getenv("STRING_SESSION", "BQJSYdcAR1yTyI5E4mIjHuKsF2yPhzV1_abq2TBl3R6IWqUL3IFT2B1ur3dUVYUO470tfLwV6iQpAYtIIhdo_9NUeTQ44tulD-ciTq-o8AKPNQ6vqc26ycOyKYccCrt_BIiKW9UodxKu2Y3WcYX-UM4q-jhjHVH_K96CbWW64CaSpAY6J9m3YnKJhIaEES0qVVpZg08oCzGqSNIBqCgtcHcpflcYg6SRezqh-WzLWwworWHw-_-7T9Ao3u1tTxzdTA3o2K7KMBM42wkaLC-TCWw8FBC_kbzzmWN_xA4XTUJCE1281znxdNExPyS546x_QNUpM_G8zk0rEzXaZN82QgFegv15AwAAAAHDOmXpAA")

# Bot metadata & command prefixes
BOT_NAME: str = os.getenv("BOT_NAME", "Mario Music")
COMMAND_PREFIXES: list[str] = ["/", "!", "."]

# Assistant name for logs
ASSISTANT_NAME: str = os.getenv("ASSISTANT_NAME", "Music Assistant")

# Owner & Support configuration (Admin Panel is strictly visible ONLY to Owner in private chat)
OWNER_ID: int = int(os.getenv("OWNER_ID", 7670796126))
OWNER_USERNAME: str = os.getenv("OWNER_USERNAME", "Yes_Im_Mario")
SUPPORT_URL: str = os.getenv("SUPPORT_URL", "https://t.me/mariostore_1z")

