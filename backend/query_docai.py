import sys
import os
import json
sys.path.append('/app')

from core_engine.services.chat_service import AgenticInvestigator

def run_query():
    case_id = 6
    question = "Cate persoane au fost instruite de toti cei 3 instructori?"
    
    print(f"[*] Running agentic query on case {case_id}...", flush=True)
    print(f"[QUESTION]: {question}\n", flush=True)
    
    agent = AgenticInvestigator(case_id, question)
    
    for chunk_json in agent.run():
        chunk = json.loads(chunk_json)
        c_type = chunk.get("type")
        c_data = chunk.get("data")
        
        if c_type == "step":
            print(f"\n[AGENT] {c_data}", flush=True)
        elif c_type == "tool_call":
            print(f"  TOOL CALL: {chunk.get('tool')}({chunk.get('params')})", flush=True)
        elif c_type == "observation":
            obs = str(c_data)
            if "Thinking:" in obs:
                print(f"  Thinking: {obs[:300]}...", flush=True)
            else:
                print(f"  OBSERVATION: {obs[:300]}...", flush=True)
        elif c_type == "final":
            print("\n" + "="*50, flush=True)
            print("[FINAL RESPONSE]:", flush=True)
            print(c_data, flush=True)
            print("="*50, flush=True)

if __name__ == "__main__":
    run_query()
