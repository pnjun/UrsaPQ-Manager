#!/usr/bin/env python3
from context import lam_dl
import asyncio
import sys

if __name__ == '__main__':
    target = float(sys.argv[1])
    asyncio.run(lam_dl(target))