import asyncio
import json
import time
import urllib.request
import websockets

async def listen_and_trigger():
    uri = 'ws://localhost:8000/ws/patients/P001'
    async with websockets.connect(uri) as ws:
        print('CONNECTED TO WS:', uri)
        t0 = time.time()

        def post():
            req = urllib.request.Request('http://localhost:8000/api/patients/P001/cycle', data=b'{}', headers={'Content-Type': 'application/json'})
            res = urllib.request.urlopen(req)
            return res.read()

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, post)

        messages = []
        while True:
            try:
                msg_str = await asyncio.wait_for(ws.recv(), timeout=0.2)
                dt = time.time() - t0
                msg = json.loads(msg_str)
                mtype = msg.get('type')
                print(f'[{dt:.3f}s] WS EVENT RECEIVED: type={mtype}')
                if mtype == 'agent_status':
                    payload = msg.get('payload', {})
                    print(f'         agent={payload.get("agent")}, status={payload.get("status")}, role={payload.get("role")}, rec={payload.get("recommendation")}')
                elif mtype == 'debate_message':
                    payload = msg.get('payload', {})
                    print(f'         round={payload.get("round")}, agent={payload.get("agent")}, status={payload.get("status")}, msg="{payload.get("message")}"')
                elif mtype == 'safety':
                    print(f'         safety_result={msg.get("payload", {}).get("result")}')
                elif mtype == 'plan':
                    print('         plan_horizon=', msg.get("payload", {}).get("horizon_hours"))
                messages.append(msg)
            except asyncio.TimeoutError:
                if future.done():
                    break

        await future
        print(f'TOTAL WS EVENTS RECEIVED: {len(messages)}')

if __name__ == '__main__':
    asyncio.run(listen_and_trigger())
