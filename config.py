# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import os
from dotenv import load_dotenv
from typing import Final

load_dotenv()

TOKEN: Final[str] = os.getenv("DISCORD_TOKEN", "")
