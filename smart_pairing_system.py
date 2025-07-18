import pandas as pd
import numpy as np
import json
import random
from collections import defaultdict

class SmartPairingSystem:
    def __init__(self, metadata_file, preferences_file, images_dir='./sapphire_images'):
        self.metadata_file = metadata_file
        self.preferences_file = preferences_file
        self.images_dir = images_dir
        self.load_data()
        
    def load_data(self):
        """Load metadata and existing preferences, filtering out non-existent images"""
        with open(self.metadata_file, 'r') as f:
            all_metadata = json.load(f)
        
        # Filter metadata to only include images that actually exist
        import os
        self.metadata = {}
        for image_name, image_data in all_metadata.items():
            image_path = os.path.join(self.images_dir, image_name)
            if os.path.exists(image_path):
                self.metadata[image_name] = image_data
            else:
                print(f"Warning: {image_name} in metadata but not found in {self.images_dir}")
        
        try:
            self.preferences = pd.read_csv(self.preferences_file)
            # Parse JSON strings back to lists (matching your format)
            if 'liked_features' in self.preferences.columns:
                self.preferences['liked_features'] = self.preferences['liked_features'].apply(
                    lambda x: json.loads(x) if pd.notna(x) and x != '[]' else []
                )
            if 'disliked_features' in self.preferences.columns:
                self.preferences['disliked_features'] = self.preferences['disliked_features'].apply(
                    lambda x: json.loads(x) if pd.notna(x) and x != '[]' else []
                )
        except FileNotFoundError:
            # Create empty DataFrame if no preferences yet
            self.preferences = pd.DataFrame(columns=[
                'timestamp', 'image_a', 'image_b', 'chosen',
                'liked_features', 'disliked_features', 'general_feedback', 'session_id', 'not_chosen'
            ])
    
    def calculate_image_stats(self):
        """Calculate stats for each image"""
        image_stats = {}
        
        for image_name in self.metadata.keys():
            # Count total comparisons
            comparisons = len(self.preferences[
                (self.preferences['image_a'] == image_name) | 
                (self.preferences['image_b'] == image_name)
            ])
            
            # Count wins
            wins = len(self.preferences[self.preferences['chosen'] == image_name])
            
            # Calculate win rate
            win_rate = wins / comparisons if comparisons > 0 else 0.5  # Default to neutral
            
            # Calculate Elo (simplified version)
            elo_rating = self.calculate_simple_elo(image_name)
            
            image_stats[image_name] = {
                'comparisons': comparisons,
                'wins': wins,
                'win_rate': win_rate,
                'elo_rating': elo_rating,
                'needs_more_data': comparisons < 5,  # Flag for underexposed images
                'likely_unpopular': comparisons >= 8 and elo_rating < 1450  # Flag for pruning
            }
        
        return image_stats
    
    def calculate_simple_elo(self, image_name):
        """Calculate current Elo rating for a specific image"""
        current_rating = 1500
        
        for _, row in self.preferences.iterrows():
            if row['image_a'] == image_name:
                opponent = row['image_b']
                won = row['chosen'] == image_name
            elif row['image_b'] == image_name:
                opponent = row['image_a']
                won = row['chosen'] == image_name
            else:
                continue
            
            # Get opponent's current rating (simplified - would need recursive calculation for accuracy)
            opponent_rating = 1500  # Simplified assumption
            
            # Calculate Elo change
            expected = 1 / (1 + 10**((opponent_rating - current_rating) / 400))
            actual = 1 if won else 0
            current_rating += 32 * (actual - expected)
        
        return current_rating
    
    def get_prioritized_pairs(self, n_pairs=20, exclude_unpopular=True):
        """Get prioritized pairs based on exposure and performance"""
        image_stats = self.calculate_image_stats()
        
        # Filter out unpopular images if requested
        available_images = []
        for image_name, stats in image_stats.items():
            if exclude_unpopular and stats['likely_unpopular']:
                continue
            available_images.append(image_name)
        
        if len(available_images) < 2:
            return []
        
        # Generate all possible pairs
        all_pairs = []
        for i in range(len(available_images)):
            for j in range(i + 1, len(available_images)):
                img_a, img_b = available_images[i], available_images[j]
                
                # Check if this pair has been shown before
                pair_shown = len(self.preferences[
                    ((self.preferences['image_a'] == img_a) & (self.preferences['image_b'] == img_b)) |
                    ((self.preferences['image_a'] == img_b) & (self.preferences['image_b'] == img_a))
                ]) > 0
                
                # Calculate priority score
                priority_score = self.calculate_pair_priority(img_a, img_b, image_stats, pair_shown)
                
                all_pairs.append({
                    'image_a': img_a,
                    'image_b': img_b,
                    'priority_score': priority_score,
                    'already_shown': pair_shown,
                    'combined_comparisons': image_stats[img_a]['comparisons'] + image_stats[img_b]['comparisons']
                })
        
        # Sort by priority and return top pairs
        sorted_pairs = sorted(all_pairs, key=lambda x: x['priority_score'], reverse=True)
        return sorted_pairs[:n_pairs]
    
    def calculate_pair_priority(self, img_a, img_b, image_stats, pair_shown):
        """Calculate priority score for showing this pair"""
        stats_a = image_stats[img_a]
        stats_b = image_stats[img_b]
        
        priority = 0
        
        # Higher priority for images with less data
        if stats_a['needs_more_data']:
            priority += 50
        if stats_b['needs_more_data']:
            priority += 50
        
        # Higher priority for unshown pairs
        if not pair_shown:
            priority += 30
        
        # Higher priority for similar Elo ratings (more informative comparisons)
        elo_diff = abs(stats_a['elo_rating'] - stats_b['elo_rating'])
        priority += max(0, 20 - (elo_diff / 10))  # Bonus for close matches
        
        # Slight bonus for images with moderate exposure (not too little, not too much)
        avg_comparisons = (stats_a['comparisons'] + stats_b['comparisons']) / 2
        if 3 <= avg_comparisons <= 10:
            priority += 10
        
        # Small random factor to avoid always showing the same "optimal" pairs
        priority += random.uniform(0, 5)
        
        return priority
    
    def get_images_for_pruning(self):
        """Get list of images that could be considered for removal"""
        image_stats = self.calculate_image_stats()
        
        pruning_candidates = []
        for image_name, stats in image_stats.items():
            if stats['likely_unpopular']:
                pruning_candidates.append({
                    'image': image_name,
                    'elo_rating': stats['elo_rating'],
                    'win_rate': stats['win_rate'],
                    'comparisons': stats['comparisons'],
                    'tags': self.metadata[image_name].get('tags', {})
                })
        
        return sorted(pruning_candidates, key=lambda x: x['elo_rating'])
    
    def generate_pairing_recommendations(self):
        """Generate comprehensive pairing recommendations"""
        image_stats = self.calculate_image_stats()
        prioritized_pairs = self.get_prioritized_pairs(20)
        pruning_candidates = self.get_images_for_pruning()
        
        # Statistics
        total_images = len(image_stats)
        underexposed = sum(1 for stats in image_stats.values() if stats['needs_more_data'])
        likely_unpopular = len(pruning_candidates)
        
        recommendations = {
            'summary': {
                'total_images': total_images,
                'underexposed_images': underexposed,
                'likely_unpopular': likely_unpopular,
                'total_possible_pairs': total_images * (total_images - 1) // 2,
                'pairs_already_shown': len(self.preferences)
            },
            'next_priority_pairs': prioritized_pairs,
            'pruning_candidates': pruning_candidates,
            'underexposed_images': [
                img for img, stats in image_stats.items() 
                if stats['needs_more_data']
            ]
        }
        
        return recommendations
    
    def save_pairing_strategy(self, filename='pairing_strategy.json'):
        """Save the current pairing strategy to a file"""
        recommendations = self.generate_pairing_recommendations()
        
        with open(filename, 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        print(f"Pairing strategy saved to {filename}")
        return recommendations

# Integration function for the Streamlit app
def get_smart_pair(images_dir='./sapphire_images', metadata_file='metadata.json', 
                   preferences_file='preferences.csv', test_type=None):
    """
    Function to be called by the Streamlit app to get the next best pair
    """
    try:
        pairing_system = SmartPairingSystem(metadata_file, preferences_file, images_dir)
        prioritized_pairs = pairing_system.get_prioritized_pairs(10)  # Get top 10 options
        
        if not prioritized_pairs:
            return None
        
        # Filter by test type if specified
        if test_type and test_type != "general":
            filtered_pairs = []
            for pair in prioritized_pairs:
                img_a_tags = pairing_system.metadata.get(pair['image_a'], {}).get('tags', {})
                img_b_tags = pairing_system.metadata.get(pair['image_b'], {}).get('tags', {})
                
                # Check if both images have the specified feature
                if test_type in img_a_tags and test_type in img_b_tags:
                    filtered_pairs.append(pair)
            
            if filtered_pairs:
                prioritized_pairs = filtered_pairs
        
        # Return the highest priority pair
        best_pair = prioritized_pairs[0]
        return [best_pair['image_a'], best_pair['image_b']]
        
    except Exception as e:
        print(f"Error in smart pairing: {e}")
        return None

# Usage example
if __name__ == "__main__":
    # Generate recommendations
    pairing_system = SmartPairingSystem('metadata.json', 'preferences.csv', './sapphire_images')
    recommendations = pairing_system.generate_pairing_recommendations()
    
    print("=== PAIRING RECOMMENDATIONS ===")
    print(f"Total images: {recommendations['summary']['total_images']}")
    print(f"Underexposed images: {recommendations['summary']['underexposed_images']}")
    print(f"Likely unpopular: {recommendations['summary']['likely_unpopular']}")
    
    print("\n=== NEXT PRIORITY PAIRS ===")
    for i, pair in enumerate(recommendations['next_priority_pairs'][:5]):
        print(f"{i+1}. {pair['image_a']} vs {pair['image_b']} (Priority: {pair['priority_score']:.1f})")
        print(f"   Already shown: {pair['already_shown']}, Combined comparisons: {pair['combined_comparisons']}")
    
    print("\n=== PRUNING CANDIDATES ===")
    for candidate in recommendations['pruning_candidates']:
        print(f"{candidate['image']} - Elo: {candidate['elo_rating']:.1f}, Win Rate: {candidate['win_rate']:.1%}")
    
    # Save strategy
    pairing_system.save_pairing_strategy()