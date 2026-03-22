"""Standalone monitor server. Run with: python -m src.server

This starts the monitor API server without running a pipeline.
Use the dashboard at http://localhost:3000 to start/stop pipeline runs.
"""
import asyncio
from .monitor import PipelineMonitor


async def main():
    monitor = PipelineMonitor(port=8585)
    await monitor.start()
    print("\n" + "=" * 60)
    print("Pipeline Monitor Server")
    print("  API:       http://localhost:8585")
    print("  Dashboard: http://localhost:3000")
    print("  Start a run from the dashboard or POST /api/pipeline/start")
    print("=" * 60 + "\n")

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[monitor] Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
