import streamlit as st
import json
import os
import random
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
PREFERENCES_FILE = 'preferences.csv'

# Email configuration - you'll need to set these up
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

def get_tagged_images():
    """Get list of images that have been tagged"""
    metadata = load_metadata()
    tagged_images = []
    
    for filename, data in metadata.items():
        if data.get('tags') and any(data['tags'].values()):  # Has at least one tag
            image_path = os.path.join(IMAGES_DIR, filename)
            if os.path.exists(image_path):
                tagged_images.append(filename)
    
    return tagged_images

def send_results_email(preferences_data):
    """Send preference results via email"""
    try:
        # Create DataFrame and CSV
        df = pd.DataFrame(preferences_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = f"Ring Preference Results - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Email body
        body = f"""
Hi! Here are the latest ring preference results.

Session Summary:
- Total comparisons: {len(preferences_data)}
- Session started: {preferences_data[0]['timestamp'] if preferences_data else 'N/A'}
- Session ended: {preferences_data[-1]['timestamp'] if preferences_data else 'N/A'}

The detailed results are attached as a CSV file.

Love,
Your Ring Preference Bot 💎
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach CSV
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(csv_data.encode())
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename=ring_preferences_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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

def save_preference_result(image_a, image_b, chosen, 
                           liked_features, disliked_features,general_feedback):
    """Save AB test result in session state"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'image_a': image_a,
        'image_b': image_b,
        'chosen': chosen,
        'liked_features': json.dumps(liked_features),
        'disliked_features': json.dumps(disliked_features),
        'general_feedback': general_feedback,
        'session_id': st.session_state.get('session_id', 'default')
    }
    
    # Store in session state
    if 'all_preferences' not in st.session_state:
        st.session_state.all_preferences = []
    
    st.session_state.all_preferences.append(result)
    
    # Auto-send email every 10 comparisons
    if len(st.session_state.all_preferences) % 10 == 0:
        if send_results_email(st.session_state.all_preferences):
            st.success("✅ Results automatically sent!")
    
    # Also save a backup locally if possible (for development)
    try:
        df = pd.DataFrame(st.session_state.all_preferences)
        df.to_csv('preferences_backup.csv', index=False)
    except:
        pass  # Fail silently in deployed environment

def get_random_pair(images, test_type=None):
    """Get a random pair of images, optionally filtered by test type"""
    metadata = load_metadata()
    
    if test_type and test_type != "general":
        # Filter images that have the specific feature tagged
        filtered_images = []
        for img in images:
            tags = metadata.get(img, {}).get('tags', {})
            if test_type in tags:
                filtered_images.append(img)
        
        if len(filtered_images) >= 2:
            return random.sample(filtered_images, 2)
    
    # Default: random pair from all images
    if len(images) >= 2:
        return random.sample(images, 2)
    
    return None

def main():

    st.title("💎 Ring Preference A/B Testing")
    if 'all_preferences' in st.session_state and st.session_state.all_preferences:
        
        # Manual send button
        if st.button("📧 Send Results Now"):
            if send_results_email(st.session_state.all_preferences):
                st.success("Email sent!")
            else:
                st.error("Failed to send email")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if 'current_pair' not in st.session_state:
        st.session_state.current_pair = None
    
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    
    if 'chosen_image' not in st.session_state:
        st.session_state.chosen_image = None
    
    # Load images
    tagged_images = get_tagged_images()
    
    if len(tagged_images) < 2:
        st.error("Need at least 2 tagged images to run A/B testing. Please tag some images first!")
        return
    
    # Test type selectio
    test_type = "general"
    
    # Generate new pair button
    if st.sidebar.button("🎲 Get New Pair") or st.session_state.current_pair is None:
        pair = get_random_pair(tagged_images, test_type)
        if pair:
            st.session_state.current_pair = pair
            st.session_state.show_feedback = False
            st.session_state.chosen_image = None
            st.rerun()
        else:
            st.error("Couldn't find a suitable pair for this test type.")
            return
    
    if not st.session_state.current_pair:
        return
    
    image_a, image_b = st.session_state.current_pair
    metadata = load_metadata()

    try:
        img_path_a = os.path.join(IMAGES_DIR, image_a)
        img_a = Image.open(img_path_a)   
    except Exception as e:
        st.error(f"Error loading image A: {e}")
    
    try:
        img_path_b = os.path.join(IMAGES_DIR, image_b)
        img_b = Image.open(img_path_b)
    except Exception as e:
        st.error(f"Error loading image B: {e}")
    
    # Display images side by side
    if not st.session_state.show_feedback:
        st.subheader("Which do you prefer?")
        
        
        col1, col2 = st.columns(2)
        with col1:
     
            if st.button("👍 Choose Option A", key="choose_a", type="primary"):
                st.session_state.chosen_image = image_a
                st.session_state.show_feedback = True
                st.rerun()

            st.image(img_a, caption="Option A", use_container_width=True)

        
        with col2:
 
            if st.button("👍 Choose Option B", key="choose_b", type="primary"):
                st.session_state.chosen_image = image_b
                st.session_state.show_feedback = True
                st.rerun()

            st.image(img_b, caption="Option B", use_container_width=True)  
            
    # Feature feedback section
    if st.session_state.show_feedback and st.session_state.chosen_image:
        chosen = st.session_state.chosen_image
        not_chosen = image_b if chosen == image_a else image_a
        chosen_img = img_a if chosen == image_a else img_b
        not_chosen_img = img_b if chosen == image_a else img_a

        st.subheader("What influenced your decision?")
        st.write("Click on the features you liked or disliked about each option:")
        
        # Get all available features from both images
        tags_a = metadata.get(image_a, {}).get('tags', {})
        tags_b = metadata.get(image_b, {}).get('tags', {})
        all_features = set(list(tags_a.keys()) + list(tags_b.keys()))
        
        if all_features:
            col1, col2 = st.columns(2)
            
            liked_features = []
            disliked_features = []
            
            with col1:
                st.write("**(Your Choice)**")
                st.write("✅ Click features you LIKED:")
                
                chosen_tags = metadata.get(chosen, {}).get('tags', {})
                for feature in sorted(all_features):
                    if feature in chosen_tags:
                        feature_value = chosen_tags[feature]
                        if st.checkbox(f"👍 {feature}", key=f"like_{feature}"):
                            liked_features.append(f"{feature}:{feature_value}")
                st.image(chosen_img)
            
            with col2:
                st.write("**(Not Chosen)**")
                st.write("❌ Click features you DISLIKED:")
                
                not_chosen_tags = metadata.get(not_chosen, {}).get('tags', {})
                for feature in sorted(all_features):
                    if feature in not_chosen_tags:
                        feature_value = not_chosen_tags[feature]
                        if st.checkbox(f"👎 {feature}", key=f"dislike_{feature}"):
                            disliked_features.append(f"{feature}:{feature_value}")
                st.image(not_chosen_img)

            # Session state to track selections
            if 'liked_features' not in st.session_state:
                st.session_state.liked_features = []
            if 'disliked_features' not in st.session_state:
                st.session_state.disliked_features = []
            
            # Update selections
            st.session_state.liked_features.extend(liked_features)
            st.session_state.disliked_features.extend(disliked_features)
            
            # Show current selections
            if st.session_state.liked_features or st.session_state.disliked_features:
                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.session_state.liked_features:
                        st.write("**Liked Features:**")
                        for feature in st.session_state.liked_features:
                            st.write(f"✅ {feature}")
                
                with col2:
                    if st.session_state.disliked_features:
                        st.write("**Disliked Features:**")
                        for feature in st.session_state.disliked_features:
                            st.write(f"❌ {feature}")
        general_feedback = st.text_area("General Feedback")
         # Finish and save
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save & Continue", type="primary",key="save1"):
                save_preference_result(
                    image_a, image_b, chosen,
                    st.session_state.get('liked_features', []),
                    st.session_state.get('disliked_features', []),
                    general_feedback
                )
                
                # Reset for next round
                st.session_state.current_pair = None
                st.session_state.show_feedback = False
                st.session_state.chosen_image = None
                st.session_state.liked_features = []
                st.session_state.disliked_features = []
                
                st.success("Saved! Getting next pair...")
                st.rerun()
        
        with col2:
            if st.button("⏭️ Skip Feedback",key="skip1"):
                save_preference_result(image_a, image_b, chosen, [], [],"")
                
                # Reset for next round
                st.session_state.current_pair = None
                st.session_state.show_feedback = False
                st.session_state.chosen_image = None
                st.session_state.liked_features = []
                st.session_state.disliked_features = []
                
                st.rerun()
    # Sidebar stats
    if os.path.exists(PREFERENCES_FILE):
        df = pd.read_csv(PREFERENCES_FILE)
        st.sidebar.write("---")
        st.sidebar.write("**Session Stats:**")
        st.sidebar.metric("Total Comparisons", len(df))
        st.sidebar.metric("This Session", len(df[df['session_id'] == st.session_state.session_id]))

if __name__ == "__main__":
    main()