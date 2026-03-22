"""Standalone memory server entrypoint for Docker.

Starts the memory monitor (FastAPI at :8686) which includes:
- Memory query API (POST /api/query)
- Episode browsing (GET /api/episodes)
- Real-time monitoring (GET /api/events SSE)
- Statistics (GET /api/stats)
"""
import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.monitor import get_monitor


async def main():
    monitor = get_monitor(port=8686)
    await monitor.start()
    print("\n" + "=" * 60)
    print("Jarvis Memory Server")
    print("  API:       http://localhost:8686")
    print("  Dashboard: http://localhost:3001")
    print("  Query:     POST /api/query")
    print("  Episodes:  GET /api/episodes")
    print("=" * 60 + "\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[memory] Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
