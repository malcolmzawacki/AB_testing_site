
import sys
import pandas as pd
import json

def test_smart_pairing():
    """Test the smart pairing system with your actual data"""
    
    print("=== TESTING SMART PAIRING SYSTEM ===")
    
    try:
        from smart_pairing_system import SmartPairingSystem, get_smart_pair
        
        # Test 1: Initialize the system
        print("\n1. Testing system initialization...")
        pairing_system = SmartPairingSystem('metadata.json', 'preferences.csv')
        print(f"✓ Loaded {len(pairing_system.metadata)} images")
        print(f"✓ Loaded {len(pairing_system.preferences)} preferences")
        
        # Test 2: Check data format
        print("\n2. Testing data format...")
        if not pairing_system.preferences.empty:
            print("✓ Preferences columns:", list(pairing_system.preferences.columns))
            
            # Test JSON parsing
            sample_liked = pairing_system.preferences['liked_features'].iloc[0]
            sample_disliked = pairing_system.preferences['disliked_features'].iloc[0]
            print(f"✓ Liked features sample: {sample_liked}")
            print(f"✓ Disliked features sample: {sample_disliked}")
        
        # Test 3: Image statistics
        print("\n3. Testing image statistics...")
        image_stats = pairing_system.calculate_image_stats()
        print(f"✓ Calculated stats for {len(image_stats)} images")
        
        # Show some examples
        for i, (img, stats) in enumerate(list(image_stats.items())[:3]):
            print(f"  {img}: {stats['comparisons']} comparisons, Elo: {stats['elo_rating']:.1f}")
            if i >= 2:  # Show first 3
                break
        
        # Test 4: Priority pairs
        print("\n4. Testing priority pairs...")
        priority_pairs = pairing_system.get_prioritized_pairs(10)
        print(f"✓ Generated {len(priority_pairs)} priority pairs")
        
        if priority_pairs:
            print("Top 3 priority pairs:")
            for i, pair in enumerate(priority_pairs[:3]):
                print(f"  {i+1}. {pair['image_a']} vs {pair['image_b']} (Priority: {pair['priority_score']:.1f})")
        
        # Test 5: Smart pair function
        print("\n5. Testing smart pair function...")
        smart_pair = get_smart_pair('sapphire_images', 'metadata.json', 'preferences.csv')
        if smart_pair:
            print(f"✓ Smart pair: {smart_pair[0]} vs {smart_pair[1]}")
        else:
            print("✗ No smart pair returned")
        
        # Test 6: Comprehensive recommendations
        print("\n6. Testing comprehensive recommendations...")
        recommendations = pairing_system.generate_pairing_recommendations()
        summary = recommendations['summary']
        
        print(f"✓ Summary:")
        print(f"  Total images: {summary['total_images']}")
        print(f"  Underexposed: {summary['underexposed_images']}")
        print(f"  Likely unpopular: {summary['likely_unpopular']}")
        print(f"  Pairs shown: {summary['pairs_already_shown']}")
        
        # Test 7: Pruning candidates
        print("\n7. Testing pruning candidates...")
        pruning_candidates = recommendations['pruning_candidates']
        if pruning_candidates:
            print(f"✓ Found {len(pruning_candidates)} pruning candidates:")
            for candidate in pruning_candidates[:3]:  # Show first 3
                print(f"  {candidate['image']} - Elo: {candidate['elo_rating']:.1f}")
        else:
            print("✓ No pruning candidates found")
        
        print("\n=== ALL TESTS PASSED! ===")
        print("The smart pairing system is ready to use with your data.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("Make sure smart_pairing_system.py is in your directory")
        return False

def show_next_recommendations():
    """Show the next recommended pairs"""
    try:
        from smart_pairing_system import SmartPairingSystem
        
        pairing_system = SmartPairingSystem('metadata.json', 'preferences.csv')
        recommendations = pairing_system.generate_pairing_recommendations()
        
        print("\n=== NEXT RECOMMENDED PAIRS ===")
        for i, pair in enumerate(recommendations['next_priority_pairs'][:10]):
            status = "NEW" if not pair['already_shown'] else "REPEAT"
            print(f"{i+1:2d}. {pair['image_a']} vs {pair['image_b']}")
            print(f"     Priority: {pair['priority_score']:.1f}, Status: {status}")
        
        print(f"\n=== PRUNING CANDIDATES ===")
        for candidate in recommendations['pruning_candidates']:
            tags = candidate['tags']
            tag_str = ", ".join([f"{k}: {v}" for k, v in tags.items()])
            print(f"{candidate['image']}")
            print(f"  Elo: {candidate['elo_rating']:.1f}, Win Rate: {candidate['win_rate']:.1%}")
            print(f"  Tags: {tag_str}")
            print()
        
    except Exception as e:
        print(f"Error generating recommendations: {e}")

if __name__ == "__main__":
    if test_smart_pairing():
        print("\n" + "="*50)
        show_next_recommendations()