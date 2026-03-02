import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def listen_sse():
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", f"{BASE_URL}/tickets/stream") as response:
            print("Connected to SSE")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "heartbeat":
                            continue
                        
                        serving = data.get("data", {}).get("serving", [])
                        waiting = data.get("data", {}).get("waiting", [])
                        print(f"Update: Serving Count={len(serving)}, Waiting Count={len(waiting)}")
                        if len(serving) > 0:
                            print(f"  Serving: {[t.get('number') for t in serving]}")
                        
                        if len(serving) == 0 and len(waiting) == 0:
                            print("Queue is empty!")
                            
                    except json.JSONDecodeError:
                        pass

async def simulate_flow():
    async with httpx.AsyncClient() as client:
        # Give SSE time to connect
        await asyncio.sleep(2)
        
        # 1. Create Ticket
        print("Creating ticket...")
        res = await client.post(f"{BASE_URL}/tickets/", json={"queue_id": 1})
        ticket = res.json()
        print(f"Created ticket: {ticket['number']}")
        await asyncio.sleep(2)
        
        # 2. Call Ticket
        print("Calling ticket...")
        res = await client.get(f"{BASE_URL}/tickets/next?module_id=1&queue_ids=1")
        print(f"Called ticket status: {res.status_code}")
        await asyncio.sleep(2)
        
        # 3. Complete Ticket
        print("Completing ticket...")
        res = await client.post(f"{BASE_URL}/tickets/{ticket['id']}/complete")
        print(f"Completed ticket status: {res.status_code}")
        await asyncio.sleep(2)
        
        print("Simulation done.")

async def main():
    # Run listener and simulator concurrently
    listener = asyncio.create_task(listen_sse())
    simulator = asyncio.create_task(simulate_flow())
    
    await simulator
    # Wait a bit for final event
    await asyncio.sleep(2)
    listener.cancel()

if __name__ == "__main__":
    asyncio.run(main())
