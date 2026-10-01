import httpx
import asyncio

async def listen(session_id, listener_id):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream('GET', f'http://127.0.0.1:8000/api/pipeline/stream/{session_id}') as response:
            count = 0
            async for line in response.aiter_lines():
                if line.startswith('event:'):
                    count += 1
            print(f"Listener {listener_id} received {count} events")

async def test():
    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post('http://127.0.0.1:8000/api/interview/start', json={"idea": "A neighborhood tool library test idea with enough length"})
        session_id = res.json()["sessionId"]
        print(f"Created session {session_id}")
        
    await asyncio.gather(
        listen(session_id, 1),
        listen(session_id, 2)
    )
    
    async with httpx.AsyncClient() as client:
        res = await client.get(f'http://127.0.0.1:8000/api/trace/{session_id}')
        trace = res.json()["trace"]
        print(f"Trace length: {len(trace)}")

if __name__ == "__main__":
    asyncio.run(test())
