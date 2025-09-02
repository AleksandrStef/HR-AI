#!/usr/bin/env python3
"""Test detailed query results."""

import asyncio
import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hr_ai.api.query_processor import QueryProcessor

async def test_detailed_query():
    processor = QueryProcessor()
    
    print("Testing detailed query: 'что вызывает дискомфорт у сотрудников?'")
    print("=" * 60)
    
    try:
        result = await processor.process_query("что вызывает дискомфорт у сотрудников?")
        
        print(f"Success: {result.get('success')}")
        print(f"Total results: {result.get('total_results')}")
        print(f"Summary: {result.get('summary')}")
        
        if result.get('results'):
            print(f"\nFound {len(result['results'])} results:")
            for i, res in enumerate(result['results'], 1):
                print(f"\n{i}. Employee: {res.get('employee_name')}")
                print(f"   Type: {res.get('type')}")
                print(f"   Date: {res.get('date')}")
                print(f"   Content: {res.get('content')}")
                print(f"   Context: {res.get('context', 'N/A')}")
                print(f"   Document: {res.get('document_link')}")
        else:
            print("\nNo results found")
        
        # Also test some alternative queries
        print("\n" + "="*60)
        print("Testing alternative queries:")
        
        alternative_queries = [
            "проблемы сотрудников",
            "недовольство",
            "feedback",
            "отношение к работе"
        ]
        
        for query in alternative_queries:
            print(f"\nQuery: '{query}'")
            try:
                alt_result = await processor.process_query(query)
                print(f"  Results: {alt_result.get('total_results')}")
                if alt_result.get('total_results', 0) > 0:
                    print(f"  Summary: {alt_result.get('summary')}")
            except Exception as e:
                print(f"  Error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.close()

if __name__ == "__main__":
    asyncio.run(test_detailed_query())