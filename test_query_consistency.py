#!/usr/bin/env python3
"""Test query analysis using the server environment."""

import asyncio
import json

async def test_query_consistency():
    # Test multiple requests to the same endpoint
    import aiohttp
    
    query = "что вызывает дискомфорт у сотрудников?"
    url = "http://127.0.0.1:8000/api/query"
    
    print(f"Testing query consistency for: '{query}'")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        for i in range(5):
            print(f"\n--- Request {i+1} ---")
            try:
                async with session.post(url, json={"query": query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"Intent: {data['query_analysis'].get('intent')}")
                        print(f"Total results: {data.get('total_results')}")
                        print(f"Categories: {data['query_analysis'].get('categories')}")
                        print(f"Keywords: {data['query_analysis'].get('keywords')}")
                        print(f"Summary: {data.get('summary')[:100]}...")
                    else:
                        print(f"Error: HTTP {resp.status}")
                        text = await resp.text()
                        print(f"Response: {text}")
            except Exception as e:
                print(f"Request failed: {e}")
    
    print(f"\n--- Testing related queries ---")
    related_queries = [
        "проблемы сотрудников",
        "недовольство работников", 
        "что беспокоит команду",
        "employee discomfort",
        "staff problems"
    ]
    
    async with aiohttp.ClientSession() as session:
        for query in related_queries:
            print(f"\nQuery: '{query}'")
            try:
                async with session.post(url, json={"query": query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  Intent: {data['query_analysis'].get('intent')}, Results: {data.get('total_results')}")
                    else:
                        print(f"  Error: HTTP {resp.status}")
            except Exception as e:
                print(f"  Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_query_consistency())