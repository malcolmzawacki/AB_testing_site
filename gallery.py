import streamlit as st
import os
import json
from PIL import Image

# Configuration
IMAGES_DIR = './sapphire_images'
METADATA_FILE = 'metadata.json'

def load_metadata():
    """Load existing metadata"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_image_files():
    """Get list of image files that actually exist"""
    if not os.path.exists(IMAGES_DIR):
        return []
    
    files = []
    for filename in os.listdir(IMAGES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            files.append(filename)
    return sorted(files)

def get_image_stats(image_name):
    """Get basic stats for an image from preferences if available"""
    try:
        import pandas as pd
        if os.path.exists('preferences.csv'):
            prefs = pd.read_csv('preferences.csv')
            
            # Count comparisons
            comparisons = len(prefs[
                (prefs['image_a'] == image_name) | 
                (prefs['image_b'] == image_name)
            ])
            
            # Count wins
            wins = len(prefs[prefs['chosen'] == image_name])
            
            return {
                'comparisons': comparisons,
                'wins': wins,
                'win_rate': wins / comparisons if comparisons > 0 else 0
            }
    except:
        pass
    
    return {'comparisons': 0, 'wins': 0, 'win_rate': 0}

def main():
    st.title("🖼️ Image Gallery")
    
    # Load data
    metadata = load_metadata()
    image_files = get_image_files()
    
    if not image_files:
        st.error(f"No images found in {IMAGES_DIR}")
        return
    
    # Gallery options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_stats = st.checkbox("Show Performance Stats", value=True)
    
    with col2:
        show_tags = st.checkbox("Show Tags", value=True)
    
    with col3:
        images_per_row = st.selectbox("Images per row", [2, 3, 4, 5], index=2)
    
    st.write(f"**Total Images: {len(image_files)}**")
    st.write("---")
    
    # Create image grid
    for i in range(0, len(image_files), images_per_row):
        cols = st.columns(images_per_row,vertical_alignment='top')
        
        for j in range(images_per_row):
            if i + j < len(image_files):
                image_name = image_files[i + j]
                
                with cols[j]:
                    try:
                        # Display image
                        image_path = os.path.join(IMAGES_DIR, image_name)
                        image = Image.open(image_path)
                        st.image(image, caption=image_name, use_container_width=True)
                        
                        # Show stats if requested
                        if show_stats:
                            stats = get_image_stats(image_name)
                            if stats['comparisons'] > 0:
                                st.write(f"📊 {stats['wins']}/{stats['comparisons']} wins ({stats['win_rate']:.1%})")
                            else:
                                st.write("📊 No comparisons yet")
                        
                        # Show tags if requested
                        if show_tags:
                            image_meta = metadata.get(image_name, {})
                            tags = image_meta.get('tags', {})
                            
                            if tags:
                                tag_display = []
                                for key, value in tags.items():
                                    # Shorten tag names for display
                                    short_key = key.replace('_', ' ').title()
                                    if len(short_key) > 12:
                                        short_key = short_key[:12] + "..."
                                    tag_display.append(f"**{short_key}:** {value}")
                                
                                st.write("🏷️ " + " | ".join(tag_display[:3]))  # Show first 3 tags
                                
                                if len(tags) > 3:
                                    with st.expander("More tags..."):
                                        for key, value in list(tags.items())[3:]:
                                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.write("🏷️ No tags")
                        
                    except Exception as e:
                        st.error(f"Error loading {image_name}: {e}")
    

if __name__ == "__main__":
    main()