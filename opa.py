import os
from dotenv import load_dotenv

load_dotenv()


def test():
    if 'TG_TOKEN' and 'YP_TOKEN' and 'CHAT_ID' in os.environ:
        return True
    else:
        return False

