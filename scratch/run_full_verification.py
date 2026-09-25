import asyncio
import json
import urllib.request
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/patients/P001"

def http_post(endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req_data = json.dumps(data if data is not None else {}).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode('utf-8'))

async def test_escalation_scenario():
    print("\n--- TEST: Escalation Scenario (Pain Spike) ---")
    # 1. Reset
    http_post("/api/simulator/reset", {"patient_id": "P001"})
    
    # 2. Inject pain spike
    http_post("/api/simulator/inject", {"patient_id": "P001", "scenario": "pain_spike"})
    
    # 3. Advance time 180 min to raise pain to 8.2
    http_post("/api/simulator/advance", {"patient_id": "P001", "minutes": 180})
    
    # 4. Connect WS and run cycle
    events = []
    async with websockets.connect(WS_URL) as ws:
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, lambda: http_post("/api/patients/P001/cycle"))
        
        while True:
            try:
                msg_str = await asyncio.wait_for(ws.recv(), timeout=0.3)
                msg = json.loads(msg_str)
                events.append(msg)
                print(f"[WS EVENT] type={msg.get('type')}")
                if msg.get('type') == 'safety':
                    print(f"   Safety Result: {msg.get('payload', {}).get('result')}")
                elif msg.get('type') == 'escalation':
                    print(f"   ESCALATION EVENT: {msg.get('payload', {}).get('summary')}")
            except asyncio.TimeoutError:
                if future.done():
                    break
        
        cycle_res = await future
        print(f"HTTP Cycle Response: Escalated={cycle_res.get('escalated')}, Safety Result={cycle_res.get('safety', {}).get('result')}")
        
        escalation_events = [e for e in events if e.get('type') == 'escalation']
        assert len(escalation_events) > 0 or cycle_res.get('escalated'), "Escalation event/status must be set!"
        print("PASSED: Escalation scenario test successful.")

def test_http_fallback():
    print("\n--- TEST: WS Disconnect Fallback (Pure REST Endpoint) ---")
    # Reset
    http_post("/api/simulator/reset", {"patient_id": "P001"})
    # Call post cycle directly without WS connection (mimicking WS disconnect)
    res = http_post("/api/patients/P001/cycle")
    assert "cycle_id" in res, "Cycle ID missing in response!"
    assert "priority" in res, "Priority missing in response!"
    assert "proposals" in res, "Proposals missing in response!"
    assert "safety" in res, "Safety missing in response!"
    assert "plan" in res, "Plan missing in response!"
    print(f"HTTP Fallback Cycle Success: cycle_id={res['cycle_id']}, plan_horizon={res['plan']['horizon_hours'] if res.get('plan') else None}")
    print("PASSED: HTTP Fallback test successful.")

async def main():
    print("==================================================")
    print("RUNNING RECOVERY-SWARM REAL STREAM & FALLBACK TESTS")
    print("==================================================")
    await test_escalation_scenario()
    test_http_fallback()
    print("\n==================================================")
    print("ALL VERIFICATION SUITES COMPLETED SUCCESSFULLY")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
