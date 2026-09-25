import asyncio
import json
import time
import urllib.request
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/patients/P001"

async def run_ws_stream_capture(mode_name: str, fallback_setting: bool):
    print(f"\n==================================================")
    print(f"STARTING REAL WEBSOCKET STREAM MEASUREMENT: [{mode_name.upper()}]")
    print(f"==================================================")
    
    events = []
    t0 = time.time()
    last_t = t0

    async with websockets.connect(WS_URL) as ws:
        loop = asyncio.get_running_loop()
        
        def trigger():
            url = f"{BASE_URL}/api/patients/P001/cycle?fallback={str(fallback_setting).lower()}"
            req = urllib.request.Request(url, data=b'{}', headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as res:
                return json.loads(res.read().decode('utf-8'))

        future = loop.run_in_executor(None, trigger)

        while True:
            try:
                msg_str = await asyncio.wait_for(ws.recv(), timeout=0.2)
                now = time.time()
                elapsed = now - t0
                delta = now - last_t
                last_t = now

                msg = json.loads(msg_str)
                mtype = msg.get("type")
                payload = msg.get("payload", {})
                
                events.append((elapsed, delta, mtype, payload))

                if mtype == "twin_update":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: twin_update (Patient={payload.get('patient_id')}, Day={payload.get('profile', {}).get('post_op_day')})")
                elif mtype == "agent_status":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: agent_status -> Agent={payload.get('agent'):<13} Status={payload.get('status'):<10} Role={payload.get('role'):<10} Rec='{payload.get('recommendation')}'")
                elif mtype == "debate_message":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: debate_message -> Round={payload.get('round')} Agent={payload.get('agent'):<13} Status={payload.get('status'):<12} Msg='{payload.get('message')}'")
                elif mtype == "safety":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: safety -> Result={payload.get('result')} TriggeredRules={payload.get('rules_triggered')}")
                elif mtype == "escalation":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: escalation -> Summary='{payload.get('summary')}'")
                elif mtype == "plan":
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: plan -> Horizon={payload.get('horizon_hours')}h StepsTarget={payload.get('steps_target')}")
                else:
                    print(f"[{elapsed:6.3f}s | +{delta:6.3f}s] WS EVENT: {mtype}")

            except asyncio.TimeoutError:
                if future.done():
                    break

        cycle_res = await future
        total_time = time.time() - t0
        print(f"\n[{mode_name.upper()}] CYCLE COMPLETED in {total_time:.3f}s. Total WS Events Received: {len(events)}")
        return events, total_time

async def main():
    # 1. Reset patient state
    reset_req = urllib.request.Request(f"{BASE_URL}/api/simulator/reset", data=b'{"patient_id": "P001"}', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(reset_req) as res:
        res.read()

    # 2. Run Fallback Mode
    await run_ws_stream_capture("Fallback Mode (Rule-based)", fallback_setting=True)

    # 3. Reset patient state
    with urllib.request.urlopen(reset_req) as res:
        res.read()

    # 4. Run LLM Mode (Real Gemini calls)
    await run_ws_stream_capture("LLM Mode (Real Gemini 3.5)", fallback_setting=False)

if __name__ == "__main__":
    asyncio.run(main())
