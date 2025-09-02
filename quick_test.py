#!/usr/bin/env python3
"""
Quick test script to verify HR AI system functionality
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hr_ai.analyzers.hr_analyzer import HRAnalyzer

def main():
    print("🧪 Quick HR AI Test")
    print("==================")
    
    analyzer = HRAnalyzer()
    
    try:
        print("\n📊 Running analysis with force_reanalyze=False...")
        results_normal = analyzer.analyze_all_documents(force_reanalyze=False)
        
        print(f"  Total files: {results_normal['total_files']}")
        print(f"  Processed: {results_normal['processed']}")
        print(f"  Skipped: {results_normal.get('skipped', 'N/A')}")
        print(f"  Errors: {results_normal['errors']}")
        
        print("\n📊 Running analysis with force_reanalyze=True...")
        results_force = analyzer.analyze_all_documents(force_reanalyze=True)
        
        print(f"  Total files: {results_force['total_files']}")
        print(f"  Processed: {results_force['processed']}")
        print(f"  Skipped: {results_force.get('skipped', 'N/A')}")
        print(f"  Errors: {results_force['errors']}")
        print(f"  Meetings detected: {results_force['meetings_detected']}")
        print(f"  Meetings missed: {results_force['meetings_missed']}")
        print(f"  HR attention required: {len(results_force['hr_attention_required'])}")
        
        if results_force['hr_attention_required']:
            print("\n⚠️ Cases requiring HR attention:")
            for case in results_force['hr_attention_required']:
                print(f"  • {case['employee']}: {case['reason']}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return 1
    finally:
        analyzer.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())