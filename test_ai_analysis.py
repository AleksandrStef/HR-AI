#!/usr/bin/env python3
"""Test AI query analysis directly."""

import asyncio
import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hr_ai.api.query_processor import QueryProcessor

async def test_ai_analysis():
    processor = QueryProcessor()
    
    query = "что вызывает дискомфорт у сотрудников?"
    
    print(f"Testing AI analysis for: '{query}'")
    print("=" * 60)
    
    try:
        # Test the analysis multiple times to check consistency
        for i in range(3):
            print(f"\n--- Run {i+1} ---")
            analysis = await processor._analyze_query(query)
            print(f"Intent: {analysis.get('intent')}")
            print(f"Categories: {analysis.get('categories')}")
            print(f"Keywords: {analysis.get('keywords')}")
            print(f"Confidence: {analysis.get('confidence')}")
            if analysis.get('specific_request'):
                print(f"Specific request: {analysis.get('specific_request')}")
            if analysis.get('search_strategy'):
                print(f"Search strategy: {analysis.get('search_strategy')}")
        
        # Test without AI enhancement
        print(f"\n--- Without AI Enhancement ---")
        processor.client = None  # Disable AI
        analysis_basic = await processor._analyze_query(query)
        print(f"Intent: {analysis_basic.get('intent')}")
        print(f"Categories: {analysis_basic.get('categories')}")
        print(f"Keywords: {analysis_basic.get('keywords')}")
        print(f"Confidence: {analysis_basic.get('confidence')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.close()

if __name__ == "__main__":
    asyncio.run(test_ai_analysis())