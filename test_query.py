#!/usr/bin/env python3
"""Test the query processor directly."""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hr_ai.api.query_processor import QueryProcessor

async def test_query():
    processor = QueryProcessor()
    
    print("Testing query: 'что вызывает дискомфорт у сотрудников?'")
    print("=" * 60)
    
    try:
        result = await processor.process_query("что вызывает дискомфорт у сотрудников?")
        
        print(f"Success: {result.get('success')}")
        print(f"Total results: {result.get('total_results')}")
        print(f"Query analysis: {result.get('query_analysis')}")
        print(f"Summary: {result.get('summary')}")
        
        if result.get('results'):
            print("\nResults:")
            for i, res in enumerate(result['results'][:3], 1):  # Show first 3 results
                print(f"{i}. {res.get('employee_name')} - {res.get('type')}")
                print(f"   Content: {res.get('content', '')[:100]}...")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.close()

if __name__ == "__main__":
    asyncio.run(test_query())