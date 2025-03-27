# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import os
from dotenv import load_dotenv
from typing import Final

load_dotenv()

TOKEN: Final[str] = os.getenv("DISCORD_BOT_TOKEN", "")
ROLE_ID: Final[str] = os.getenv("ROLE_ID", "0")
LOG_CHANNEL_ID: Final[int] = int(os.getenv("LOG_CHANNEL_ID", "0"))
