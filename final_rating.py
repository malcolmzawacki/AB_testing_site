import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from PIL import Image
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io

# Configuration
IMAGES_DIR = './sapphire_images'
METADATA_FILE = 'metadata.json'
FINAL_RATINGS_FILE = 'final_ratings.csv'

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': st.secrets["email"]["smtp_server"],
    'smtp_port': st.secrets["email"]["smtp_port"],
    'sender_email': st.secrets["email"]["sender_email"],
    'sender_password': st.secrets["email"]["sender_password"],
    'recipient_email': st.secrets["email"]["recipient_email"]
}

def load_metadata():
    """Load metadata with tags"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_top_images():
    """Get the top performing images (you'll need to specify which 10)"""
    # For now, just get all available images - you can modify this list
    # to only include your top 10 finalists
    if not os.path.exists(IMAGES_DIR):
        return []
    
    files = []
    for filename in os.listdir(IMAGES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            files.append(filename)
    
    # You can replace this with your specific top 10 list:
    # files = ['ring1.jpg', 'ring2.jpg', 'ring3.jpg', ...etc]
    
    return sorted(files)

def send_final_ratings_email(ratings_data):
    """Send final ratings via email"""
    try:
        # Create DataFrame and CSV
        df = pd.DataFrame(ratings_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = f"Final Ring Ratings - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Email body
        body = f"""
Hi! Here are the final detailed ratings for the top ring candidates.

Rating Summary:
- Total rings rated: {len(ratings_data)}
- Session completed: {ratings_data[-1]['timestamp'] if ratings_data else 'N/A'}

The detailed ratings are attached as a CSV file.

Time to make the final decision! 💎💍

Love,
Your Ring Rating Bot
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach CSV
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(csv_data.encode())
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename=final_ring_ratings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        msg.attach(attachment)
        
        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['recipient_email'], text)
        server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def save_rating(image_name, liked_features, disliked_features, overall_rating, comments):
    """Save individual image rating"""
    rating = {
        'timestamp': datetime.now().isoformat(),
        'image': image_name,
        'liked_features': json.dumps(liked_features),
        'disliked_features': json.dumps(disliked_features),
        'overall_rating': overall_rating,
        'comments': comments,
        'session_id': st.session_state.get('session_id', 'final_rating')
    }
    
    # Store in session state
    if 'all_final_ratings' not in st.session_state:
        st.session_state.all_final_ratings = []
    
    # Check if we already have a rating for this image and update it
    existing_index = None
    for i, existing_rating in enumerate(st.session_state.all_final_ratings):
        if existing_rating['image'] == image_name:
            existing_index = i
            break
    
    if existing_index is not None:
        st.session_state.all_final_ratings[existing_index] = rating
    else:
        st.session_state.all_final_ratings.append(rating)

def main():
    st.title("💎 Final Ring Rating")
    st.subheader("Rate each ring individually on its specific features")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"final_rating_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    
    # Load data
    metadata = load_metadata()
    top_images = get_top_images()
    
    if not top_images:
        st.error("No images found for final rating!")
        return
    
    # Navigation
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_image_index == 0):
            st.session_state.current_image_index -= 1
            st.rerun()
    
    with col2:
        st.write(f"Ring {st.session_state.current_image_index + 1} of {len(top_images)}")
    
    with col3:
        if st.button("Next ➡️", disabled=st.session_state.current_image_index == len(top_images) - 1):
            st.session_state.current_image_index += 1
            st.rerun()
    
    with col4:
        if st.button("📧 Send All Ratings"):
            if 'all_final_ratings' in st.session_state and st.session_state.all_final_ratings:
                if send_final_ratings_email(st.session_state.all_final_ratings):
                    st.success("Final ratings sent!")
                else:
                    st.error("Failed to send email")
            else:
                st.warning("No ratings to send yet!")
    
    # Current image
    current_image = top_images[st.session_state.current_image_index]
    current_tags = metadata.get(current_image, {}).get('tags', {})
    
    # Get existing rating if any
    existing_rating = None
    if 'all_final_ratings' in st.session_state:
        for rating in st.session_state.all_final_ratings:
            if rating['image'] == current_image:
                existing_rating = rating
                break
    
    # Display image
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader(f"Rating: {current_image}")
        try:
            image_path = os.path.join(IMAGES_DIR, current_image)
            image = Image.open(image_path)
            st.image(image, caption=current_image, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading image: {e}")
    
    with col2:
        st.subheader("Rate This Ring")
        
        # Overall Rating
        overall_rating = st.select_slider(
            "Overall Rating",
            options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            value=existing_rating['overall_rating'] if existing_rating else 5,
            key=f"overall_{current_image}"
        )
        
        # Feature rating
        if current_tags:
            st.write("**Feature Analysis:**")
            st.write("Click on features you like or dislike about this ring:")
            
            liked_features = []
            disliked_features = []
            
            # Initialize with existing ratings if available
            if existing_rating:
                existing_liked = json.loads(existing_rating['liked_features'])
                existing_disliked = json.loads(existing_rating['disliked_features'])
            else:
                existing_liked = []
                existing_disliked = []
            
            for feature, value in current_tags.items():
                st.write(f"**{feature.replace('_', ' ').title()}: {value}**")
                
                col_like, col_dislike, col_neutral = st.columns(3)
                
                feature_key = f"{feature}:{value}"
                
                with col_like:
                    if st.button(f"👍 Like", key=f"like_{feature}_{current_image}"):
                        if feature_key not in liked_features:
                            liked_features.append(feature_key)
                        # Remove from disliked if it was there
                        if feature_key in disliked_features:
                            disliked_features.remove(feature_key)
                
                with col_dislike:
                    if st.button(f"👎 Dislike", key=f"dislike_{feature}_{current_image}"):
                        if feature_key not in disliked_features:
                            disliked_features.append(feature_key)
                        # Remove from liked if it was there
                        if feature_key in liked_features:
                            liked_features.remove(feature_key)
                
                with col_neutral:
                    if st.button(f"😐 Neutral", key=f"neutral_{feature}_{current_image}"):
                        # Remove from both lists
                        if feature_key in liked_features:
                            liked_features.remove(feature_key)
                        if feature_key in disliked_features:
                            disliked_features.remove(feature_key)
                
                # Show current status
                if feature_key in existing_liked:
                    st.write("✅ Currently: LIKED")
                elif feature_key in existing_disliked:
                    st.write("❌ Currently: DISLIKED")
                else:
                    st.write("😐 Currently: NEUTRAL")
            
            # Update session state with current selections
            if 'current_liked' not in st.session_state:
                st.session_state.current_liked = existing_liked.copy()
            if 'current_disliked' not in st.session_state:
                st.session_state.current_disliked = existing_disliked.copy()
            
            # Update with new selections
            for feature in liked_features:
                if feature not in st.session_state.current_liked:
                    st.session_state.current_liked.append(feature)
                if feature in st.session_state.current_disliked:
                    st.session_state.current_disliked.remove(feature)
            
            for feature in disliked_features:
                if feature not in st.session_state.current_disliked:
                    st.session_state.current_disliked.append(feature)
                if feature in st.session_state.current_liked:
                    st.session_state.current_liked.remove(feature)
        
        # Comments
        comments = st.text_area(
            "Additional Comments",
            value=existing_rating['comments'] if existing_rating else "",
            key=f"comments_{current_image}"
        )
        
        # Save rating
        if st.button("💾 Save Rating", type="primary"):
            final_liked = st.session_state.get('current_liked', [])
            final_disliked = st.session_state.get('current_disliked', [])
            
            save_rating(current_image, final_liked, final_disliked, overall_rating, comments)
            st.success("Rating saved!")
            
            # Reset for next image
            st.session_state.current_liked = []
            st.session_state.current_disliked = []
    
    # Show progress
    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if 'all_final_ratings' in st.session_state:
            completed = len(st.session_state.all_final_ratings)
            st.metric("Rings Rated", f"{completed}/{len(top_images)}")
    
    with col2:
        if 'all_final_ratings' in st.session_state and st.session_state.all_final_ratings:
            avg_rating = sum(r['overall_rating'] for r in st.session_state.all_final_ratings) / len(st.session_state.all_final_ratings)
            st.metric("Average Rating", f"{avg_rating:.1f}/10")

if __name__ == "__main__":
    main()