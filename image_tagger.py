import streamlit as st
import json
import os
from PIL import Image

# Configuration
IMAGES_DIR = './sapphire_images'
METADATA_FILE = 'metadata.json'

# Tag categories
TAG_OPTIONS = {
    'stone_shape': ['Oval', 'Round', 'Cushion', 'Emerald', 'Pear', 'Marquise'],
    'color_intensity': ['Light Blue', 'Medium Blue', 'Dark Blue', 'Royal Blue'],
    'setting_style': ['Solitaire', 'Halo', 'Three Stone', 'Vintage', 'Modern'],
    'metal_type': ['White Gold', 'Yellow Gold', 'Rose Gold', 'Platinum'],
    'overall_style': ['Classic', 'Vintage', 'Modern', 'Art Deco', 'Nature Inspired']
}

def load_metadata():
    """Load existing metadata"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save metadata to file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_image_files():
    """Get list of image files in directory"""
    if not os.path.exists(IMAGES_DIR):
        return []
    
    files = []
    for filename in os.listdir(IMAGES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            files.append(filename)
    return sorted(files)

def main():
    st.set_page_config(page_title="Image Tagging Interface", layout="wide")
    st.title("🏷️ Image Tagging Interface")
    
    # Load data
    metadata = load_metadata()
    image_files = get_image_files()
    
    if not image_files:
        st.error(f"No images found in {IMAGES_DIR}")
        return
    
    # Initialize session state
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_index == 0):
            st.session_state.current_index -= 1
            st.rerun()
    
    with col2:
        st.write(f"Image {st.session_state.current_index + 1} of {len(image_files)}")
    
    with col3:
        if st.button("Next ➡️", disabled=st.session_state.current_index == len(image_files) - 1):
            st.session_state.current_index += 1
            st.rerun()
    
    # Current image
    current_image = image_files[st.session_state.current_index]
    current_tags = metadata.get(current_image, {}).get('tags', {})
    
    # Display image
    st.subheader(f"Current Image: {current_image}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        try:
            image_path = os.path.join(IMAGES_DIR, current_image)
            image = Image.open(image_path)
            st.image(image, caption=current_image, use_column_width=True)
        except Exception as e:
            st.error(f"Error loading image: {e}")
    
    with col2:
        st.subheader("Tags")
        
        # Tag interface
        updated_tags = current_tags.copy()
        
        for category, options in TAG_OPTIONS.items():
            st.write(f"**{category.replace('_', ' ').title()}**")
            
            # Create columns for tag buttons
            cols = st.columns(len(options))
            current_value = current_tags.get(category)
            
            for i, option in enumerate(options):
                with cols[i]:
                    is_selected = current_value == option
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(
                        option, 
                        key=f"{category}_{option}_{st.session_state.current_index}",
                        type=button_type
                    ):
                        updated_tags[category] = option
                        
                        # Update metadata
                        if current_image not in metadata:
                            metadata[current_image] = {'tags': {}}
                        metadata[current_image]['tags'] = updated_tags
                        
                        # Save immediately
                        save_metadata(metadata)
                        st.success(f"Tagged as {option}")
                        st.rerun()
        
        # Clear tag option
        st.write("---")
        if st.button("🗑️ Clear All Tags for This Image"):
            if current_image in metadata:
                metadata[current_image]['tags'] = {}
                save_metadata(metadata)
                st.success("Tags cleared!")
                st.rerun()
    
    # Progress and summary
    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        tagged_count = sum(1 for img in image_files if metadata.get(img, {}).get('tags'))
        st.metric("Tagged Images", f"{tagged_count}/{len(image_files)}")
    
    with col2:
        if st.button("📊 View All Tags Summary"):
            st.subheader("Tagging Summary")
            for img in image_files:
                tags = metadata.get(img, {}).get('tags', {})
                if tags:
                    st.write(f"**{img}**: {tags}")
                else:
                    st.write(f"**{img}**: No tags")

if __name__ == "__main__":
    main()