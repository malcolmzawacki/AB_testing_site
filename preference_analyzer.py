import pandas as pd
import json
from collections import defaultdict, Counter
import numpy as np


class PreferenceAnalyzer:
    def __init__(self):
        self.metadata = None
        self.preferences = None

    def load_data(self, metadata_path, preferences_path):
        """
        Load both metadata and preference results

        Expected preferences.csv format with rich feedback:
        timestamp,test_type,image_a,image_b,chosen,liked_features,disliked_features,additional_feedback,session_id
        """
        # Load image metadata
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)

        # Load preference results
        self.preferences = pd.read_csv(preferences_path)

        # Parse JSON strings back to lists
        self.preferences['liked_features'] = self.preferences['liked_features'].apply(
            lambda x: json.loads(x) if pd.notna(x) and x != '[]' else []
        )
        self.preferences['disliked_features'] = self.preferences['disliked_features'].apply(
            lambda x: json.loads(x) if pd.notna(x) and x != '[]' else []
        )

    def get_available_features(self):
        """Get list of all features in metadata"""
        all_features = set()
        for image_data in self.metadata.values():
            if 'tags' in image_data:
                all_features.update(image_data['tags'].keys())
        return list(all_features)

    def analyze_feature_sentiment(self):
        """Analyze which features are most liked vs disliked"""
        liked_counts = Counter()
        disliked_counts = Counter()

        for _, row in self.preferences.iterrows():
            for feature in row['liked_features']:
                liked_counts[feature] += 1
            for feature in row['disliked_features']:
                disliked_counts[feature] += 1

        # Create sentiment analysis
        all_features = set(list(liked_counts.keys()) + list(disliked_counts.keys()))

        sentiment_data = []
        for feature in all_features:
            likes = liked_counts[feature]
            dislikes = disliked_counts[feature]
            total = likes + dislikes

            if total > 0:
                sentiment_score = (likes - dislikes) / total  # Range: -1 to 1
                sentiment_data.append({
                    'feature': feature,
                    'likes': likes,
                    'dislikes': dislikes,
                    'total_mentions': total,
                    'sentiment_score': sentiment_score,
                    'net_preference': likes - dislikes
                })

        return pd.DataFrame(sentiment_data).sort_values('sentiment_score', ascending=False)

    def analyze_feature_preferences(self, feature):
        """Enhanced analysis including sentiment data"""
        # Original win rate analysis
        results = defaultdict(lambda: {'wins': 0, 'appearances': 0})

        for _, row in self.preferences.iterrows():
            # Get metadata for both images
            image_a_meta = self.metadata[row['image_a']]['tags']
            image_b_meta = self.metadata[row['image_b']]['tags']

            if feature not in image_a_meta or feature not in image_b_meta:
                continue

            # Count appearances
            results[image_a_meta[feature]]['appearances'] += 1
            results[image_b_meta[feature]]['appearances'] += 1

            # Count wins
            chosen_meta = self.metadata[row['chosen']]['tags']
            if feature in chosen_meta:
                results[chosen_meta[feature]]['wins'] += 1

        # Add sentiment analysis
        sentiment_df = self.analyze_feature_sentiment()

        analysis_results = []
        for feature_value, data in results.items():
            win_rate = data['wins'] / data['appearances'] if data['appearances'] > 0 else 0

            # Get sentiment data for this specific feature:value combination
            feature_key = f"{feature}:{feature_value}"
            sentiment_row = sentiment_df[sentiment_df['feature'] == feature_key]

            sentiment_score = sentiment_row['sentiment_score'].iloc[0] if len(sentiment_row) > 0 else 0
            likes = sentiment_row['likes'].iloc[0] if len(sentiment_row) > 0 else 0
            dislikes = sentiment_row['dislikes'].iloc[0] if len(sentiment_row) > 0 else 0

            analysis_results.append({
                'feature_value': feature_value,
                'win_rate': win_rate,
                'total_appearances': data['appearances'],
                'sentiment_score': f"{sentiment_score:.2f}",
                'explicit_likes': likes,
                'explicit_dislikes': dislikes,
                'combined_score': (win_rate * 0.7) + (sentiment_score * 0.3)  # Weighted score
            })

        return pd.DataFrame(analysis_results).sort_values('combined_score', ascending=False)

    def calculate_elo_rankings(self, k_factor=32, initial_rating=1500):
        """
        Calculate Elo ratings for all images based on comparisons

        Args:
            k_factor: How much ratings change per game (32 is standard)
            initial_rating: Starting rating for all images (1500 is standard)
        """
        # Initialize all images with starting Elo rating
        elo_ratings = {}
        for image_name in self.metadata.keys():
            elo_ratings[image_name] = initial_rating

        # Process each comparison in chronological order
        for _, row in self.preferences.iterrows():
            image_a = row['image_a']
            image_b = row['image_b']
            chosen = row['chosen']

            # Skip if either image not in our metadata
            if image_a not in elo_ratings or image_b not in elo_ratings:
                continue

            # Get current ratings
            rating_a = elo_ratings[image_a]
            rating_b = elo_ratings[image_b]

            # Calculate expected scores (probability of winning)
            expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
            expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))

            # Actual scores (1 for win, 0 for loss)
            if chosen == image_a:
                actual_a, actual_b = 1, 0
            else:
                actual_a, actual_b = 0, 1

            # Update ratings
            elo_ratings[image_a] = rating_a + k_factor * (actual_a - expected_a)
            elo_ratings[image_b] = rating_b + k_factor * (actual_b - expected_b)

        # Create results DataFrame with additional info
        elo_results = []
        for image_name, rating in elo_ratings.items():
            # Count total comparisons for this image
            comparisons = len(self.preferences[
                                  (self.preferences['image_a'] == image_name) |
                                  (self.preferences['image_b'] == image_name)
                                  ])

            # Count wins
            wins = len(self.preferences[self.preferences['chosen'] == image_name])

            # Get image tags for context
            tags = self.metadata.get(image_name, {}).get('tags', {})

            elo_results.append({
                'image': image_name,
                'elo_rating': round(rating, 1),
                'total_comparisons': comparisons,
                'wins': wins,
                'win_rate': wins / comparisons if comparisons > 0 else 0,
                'rating_change': round(rating - initial_rating, 1),
                'tags': tags
            })

        return pd.DataFrame(elo_results).sort_values('elo_rating', ascending=False)

    def get_top_images_by_elo(self, top_n=10):
        """Get the top N images by Elo rating with their characteristics"""
        elo_df = self.calculate_elo_rankings()
        top_images = elo_df.head(top_n)

        print(f"=== TOP {top_n} IMAGES BY ELO RATING ===")
        for _, row in top_images.iterrows():
            print(f"\n{row['image']} - Elo: {row['elo_rating']}")
            print(f"  Win Rate: {row['win_rate']:.1%} ({row['wins']}/{row['total_comparisons']})")
            print(f"  Rating Change: {row['rating_change']:+.1f}")

            # Show key features
            tags = row['tags']
            if tags:
                key_features = [f"{k}: {v}" for k, v in tags.items()]
                print(f"  Features: {', '.join(key_features)}")

        return top_images

    def analyze_elo_by_feature(self, feature):
        """Analyze how different feature values perform in Elo rankings"""
        elo_df = self.calculate_elo_rankings()

        feature_performance = defaultdict(list)

        for _, row in elo_df.iterrows():
            tags = row['tags']
            if feature in tags:
                feature_value = tags[feature]
                feature_performance[feature_value].append(row['elo_rating'])

        # Calculate statistics for each feature value
        feature_stats = []
        for feature_value, ratings in feature_performance.items():
            feature_stats.append({
                'feature_value': feature_value,
                'avg_elo': np.mean(ratings),
                'max_elo': np.max(ratings),
                'min_elo': np.min(ratings),
                'count': len(ratings),
                'std_elo': np.std(ratings)
            })

        return pd.DataFrame(feature_stats).sort_values('avg_elo', ascending=False)

    def get_comprehensive_summary(self):
        """Get a complete analysis summary"""
        sentiment_df = self.analyze_feature_sentiment()
        elo_df = self.calculate_elo_rankings()

        summary = {
            'total_comparisons': len(self.preferences),
            'total_images': len(elo_df),
            'top_liked_features': sentiment_df.head(5)[['feature', 'sentiment_score', 'likes']].to_dict('records'),
            'top_disliked_features': sentiment_df.tail(5)[['feature', 'sentiment_score', 'dislikes']].to_dict(
                'records'),
            'top_elo_images': elo_df.head(5)[['image', 'elo_rating', 'win_rate']].to_dict('records'),
            'bottom_elo_images': elo_df.tail(5)[['image', 'elo_rating', 'win_rate']].to_dict('records')
        }

        return summary


# Example usage with Elo analysis:
if __name__ == "__main__":
    analyzer = PreferenceAnalyzer()
    analyzer.load_data('metadata.json', 'preferences.csv')

    # Comprehensive analysis
    summary = analyzer.get_comprehensive_summary()
    print("=== PREFERENCE ANALYSIS SUMMARY ===")
    print(f"Total comparisons: {summary['total_comparisons']}")
    print(f"Total images analyzed: {summary['total_images']}")

    print("\n=== TOP LIKED FEATURES ===")
    for feature in summary['top_liked_features']:
        print(f"{feature['feature']}: {feature['sentiment_score']:.2f} (liked {feature['likes']} times)")

    print("\n=== TOP DISLIKED FEATURES ===")
    for feature in summary['top_disliked_features']:
        print(f"{feature['feature']}: {feature['sentiment_score']:.2f} (disliked {feature['dislikes']} times)")

    # Elo ranking analysis
    print("\n=== TOP IMAGES BY ELO ===")
    top_images = analyzer.get_top_images_by_elo(10)

    print("\n=== ELO PERFORMANCE BY FEATURE ===")
    for feature in analyzer.get_available_features():
        print(f"\n--- {feature.replace('_', ' ').title()} Elo Performance ---")
        feature_elo = analyzer.analyze_elo_by_feature(feature)
        if not feature_elo.empty:
            print(feature_elo.round(1))
        else:
            print("No data available")

    # Feature-specific traditional analysis
    print("\n=== DETAILED FEATURE ANALYSIS ===")
    for feature in analyzer.get_available_features():
        print(f"\n--- {feature.replace('_', ' ').title()} Analysis ---")
        try:
            feature_analysis = analyzer.analyze_feature_preferences(feature)
            if not feature_analysis.empty:
                print(feature_analysis.round(3))
            else:
                print("No sufficient data")
        except Exception as e:
            print(f"Error analyzing {feature}: {e}")
