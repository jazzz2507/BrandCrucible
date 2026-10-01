import httpx
import asyncio
import json

async def test_golden():
    async with httpx.AsyncClient() as client:
        # Start the stream
        async with client.stream('GET', 'http://127.0.0.1:8000/api/pipeline/stream/golden-demo') as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

if __name__ == "__main__":
    asyncio.run(test_golden())
