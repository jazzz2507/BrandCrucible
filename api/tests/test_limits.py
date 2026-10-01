import httpx
import asyncio

async def test_limits():
    async with httpx.AsyncClient(timeout=None) as client:
        # 1. 501-char idea
        long_idea = "A" * 501
        res = await client.post('http://127.0.0.1:8000/api/interview/start', json={"idea": long_idea})
        print(f"501-char idea status: {res.status_code}")
        
        # 2. Rate limit: 5 sessions per hour.
        # We already created 1 in test_simultaneous.py, let's create 5 more.
        for i in range(5):
            res = await client.post('http://127.0.0.1:8000/api/interview/start', json={"idea": "A valid idea string here"})
            print(f"Rate limit test {i+1} status: {res.status_code}")
            
        # 3. golden-demo works despite rate limit
        res_golden = await client.get('http://127.0.0.1:8000/api/trace/golden-demo')
        print(f"Golden-demo trace status: {res_golden.status_code}")

if __name__ == "__main__":
    asyncio.run(test_limits())
