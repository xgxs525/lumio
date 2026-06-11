import asyncio
import os
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
import uvicorn.loops.asyncio


if sys.platform == 'win32':
    uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop


if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', '8000')),
        loop='asyncio',
        reload=os.getenv('RELOAD', 'false').lower() == 'true',
    )
