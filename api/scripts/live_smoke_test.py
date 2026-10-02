import os
import json
import asyncio
from store import store
from main import run_stage, STAGES

async def test():
    with open('../ai/test-ideas.json', 'r') as f:
        ideas = json.load(f)
    
    for idea in ideas:
        print(f"Testing idea: {idea}")
        session = store.create(idea=idea)
        
        for stage in STAGES:
            print(f"  Running {stage}...")
            output = await run_stage(stage, session)
            print(f"  {stage} Done.")
        
        deliver = session.stage_outputs.get("Deliver")
        print(f"  Result Brand: {deliver.get('brand_name')} - {deliver.get('tagline')}")
        
        cc = session.stage_outputs.get("ConsistencyCheck")
        print(f"  Consistency Score: {cc.get('overall_score')}, Is Consistent: {cc.get('is_consistent')}")
        print("  ---\n")

if __name__ == "__main__":
    os.environ["USE_MOCK_LLM"] = "false"
    asyncio.run(test())
