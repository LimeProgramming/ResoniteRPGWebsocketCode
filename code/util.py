"""
Lime is a paranoid moron so here are his paranoid moron util functions
"""

import sys
import asyncio


# ======================================== Stupid Helper Functions ========================================

def safe_print(content, *, end='\n', flush=True):
    """Custom function to allow printing to console with less issues from asyncio"""

    sys.stdout.buffer.write((content + end).encode('utf-8', 'replace'))
    if flush:
        sys.stdout.flush()

async def aprint(message):
    """Try to force our safe print off to another thread to avoid any blocking"""

    if not isinstance(message, str):
        message = str(message)

    await asyncio.to_thread(safe_print, message)