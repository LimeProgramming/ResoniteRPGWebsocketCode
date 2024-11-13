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

    return

async def aprint(message):
    """Try to force our safe print off to another thread to avoid any blocking"""

    if not isinstance(message, str):
        message = str(message)

    await asyncio.to_thread(safe_print, message)

    return


async def lprint(message):
    """Poor mans log message"""

    if not isinstance(message, str):
        message = str(message)

    await asyncio.to_thread(safe_print, f"[LOG] {message}")

    return

async def dprint(message):
    """Poor mans debug message"""

    if not isinstance(message, str):
        message = str(message)

    await asyncio.to_thread(safe_print, f"[DEBUG] {message}")

    return


async def eprint(message):
    """Poor mans Error message"""

    if not isinstance(message, str):
        message = str(message)

    await asyncio.to_thread(safe_print, f"[ERROR] {message}")

    return