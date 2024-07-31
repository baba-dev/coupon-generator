import streamlit as st
import sqlite3
import pandas as pd
import random
import string
import smtplib
import qrcode
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from PIL import Image, ImageDraw, ImageFont

# Security variables
SMTP_SERVER = st.secrets["smtp_server"]
SMTP_PORT = st.secrets["smtp_port"]
SMTP_USERNAME = st.secrets["smtp_username"]
SMTP_PASSWORD = st.secrets["smtp_password"]
DATA_ENTRY_PASSWORD = st.secrets["data_entry_password"]

# Function to generate a unique ticket number
def generate_ticket_number():
    return random.randint(100000, 999999)

# Function to generate a unique 20 alphanumeric identifier
def generate_unique_identifier():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

# Function to save data to SQLite database
def save_to_database(name, phone, email, ticket_number, unique_id, discount):
    conn = sqlite3.connect('coupons.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS coupons
                 (name TEXT, phone TEXT, email TEXT, ticket_number INTEGER, unique_id TEXT, discount INTEGER)''')
    c.execute('INSERT INTO coupons (name, phone, email, ticket_number, unique_id, discount) VALUES (?, ?, ?, ?, ?, ?)', 
              (name, phone, email, ticket_number, unique_id, discount))
    conn.commit()
    conn.close()

# Function to get last 10 entries from SQLite database
def get_last_entries():
    conn = sqlite3.connect('coupons.db')
    df = pd.read_sql_query('SELECT * FROM coupons ORDER BY rowid DESC LIMIT 10', conn)
    conn.close()
    return df

# Function to download all entries from SQLite database as CSV
def download_all_entries():
    conn = sqlite3.connect('coupons.db')
    df = pd.read_sql_query('SELECT * FROM coupons', conn)
    conn.close()
    return df.to_csv(index=False).encode('utf-8')

# Function to clear all entries in the SQLite database
def clear_database():
    conn = sqlite3.connect('coupons.db')
    c = conn.cursor()
    c.execute('DELETE FROM coupons')
    conn.commit()
    conn.close()
    st.success("Database cleared successfully!")

# Function to display coupon details in a printable manner
def display_coupon(name, phone, email, ticket_number, discount):
    st.write(f"""
    <div style="border: 2px solid black; padding: 10px; margin: 10px;">
        <h2>Coupon</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Discount:</strong> {discount} OMR</p>
        <p><strong>Ticket Number:</strong> {ticket_number}</p>
    </div>
    """, unsafe_allow_html=True)

# Function to generate QR code
def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    return img

# Function to create coupon image
def create_coupon_image(name, phone, email, ticket_number, discount):
    # Load the blank ticket template
    template = Image.open('ticket_template.png')
    draw = ImageDraw.Draw(template)
    
    # Define font and size
    font_path = "Arial.ttf"
    try:
        font = ImageFont.truetype(font_path, 35)
    except IOError:
        font = ImageFont.load_default()

    # Add text to template (right side)
    text_x = 630
    text_y = 130
    line_height = 50
    
    draw.text((text_x, text_y), f"Name: {name}", fill="black", font=font)
    draw.text((text_x, text_y + line_height), f"Phone: {phone}", fill="black", font=font)
    draw.text((text_x, text_y + 2 * line_height), f"Email: {email}", fill="black", font=font)
    draw.text((text_x, text_y + 3 * line_height), f"Discount: {discount} OMR", fill="black", font=font)

    # Generate and add QR code to template (left side)
    qr_code_data = f"Name: {name}\nPhone: {phone}\nEmail: {email}\nTicket Number: {ticket_number}\nDiscount: {discount} OMR"
    qr_img = generate_qr_code(qr_code_data)
    qr_img = qr_img.resize((300, 300))
    template.paste(qr_img, (90, 230))

    # Add ticket number to the bottom center
    ticket_number_text = f"Ticket No: {ticket_number}"
    text_bbox = draw.textbbox((0, 0), ticket_number_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_position = ((template.width - text_width) // 2 - 10, template.height - text_height - 100)
    draw.text(text_position, ticket_number_text, fill="black", font=font)

    return template

# Function to send email
def send_email(to_email, subject, body, attachment=None):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= coupon.png")
        msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, to_email, text)

# Streamlit app
st.title("Coupon Generator")

# Sidebar to show last 10 entries and download all entries
with st.sidebar:
    st.header("Welcome to Coupon Generator Application.",divider=True)
    st.write("Please enter customer information on the provided form to generate coupons for Taiseer Electronics.")
    st.text(" \n")
    st.text(" \n")

    st.write("You can view the last 10 generated coupons here.")
    with st.expander("Last 10 Entries"):
        last_entries = get_last_entries()
        st.write(last_entries)

    a,b = st.columns(2)    
    
    with a:
        if st.button('Download CSV'):
            csv = download_all_entries()
            st.download_button(label='Download CSV', data=csv, file_name='coupons.csv', mime='text/csv')
    
    with b:
        # Clear DB button
        if st.button('Clear Database'):
            st.warning("Are You sure? This will delete all entries in database.")
            clear_database()

# Data entry form
with st.form(key='data_entry_form'):
    name = st.text_input('Client Name')
    phone = st.text_input('Phone Number')
    email = st.text_input('Email Address')
    discount = st.selectbox('Select Discount in OMR', [5, 10, 20])
    password = st.text_input('Enter Staff Password', type='password')
    submit_button = st.form_submit_button(label='Generate Coupon')

    if submit_button:
        if not name or not phone or not email or not password:
            st.warning('Please fill in all fields.')
            st.stop()

        if password != DATA_ENTRY_PASSWORD:
            st.warning('Incorrect password.')
            st.stop()

        ticket_number = generate_ticket_number()
        unique_id = generate_unique_identifier()

        save_to_database(name, phone, email, ticket_number, unique_id, discount)

        st.session_state['coupon_details'] = (name, phone, email, ticket_number, unique_id, discount)

# Display coupon details and image if they exist in session state
if 'coupon_details' in st.session_state:
    name, phone, email, ticket_number, unique_id, discount = st.session_state['coupon_details']

    display_coupon(name, phone, email, ticket_number, discount)
    
    coupon_img = create_coupon_image(name, phone, email, ticket_number, discount)
    img_buffer = BytesIO()
    coupon_img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    st.image(img_buffer, caption="Coupon", use_column_width=True)

    # 3-column layout for buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        # Share via email button
        if st.button('Share via Email', key='email_button', type='primary'):
            email_subject = "Your Discount Coupon From Taiseer Electronics"
            email_body = f"Dear {name},\n\nThank you for shopping at Taiseer Electronics. As a value customer, please find your discount coupon attached below:\n\nTicket Number: {ticket_number}\nDiscount: {discount} OMR\n\nThank you for choosing at Taiseer Electronics"
            img_buffer.seek(0)  # Reset buffer position before sending
            send_email(email, email_subject, email_body, img_buffer)
            st.success('Coupon sent via email!')

    with col2:
        # Share via WhatsApp button
        whatsapp_message = f"Your discount coupon For Taiseer Electronics:\nTicket Number: {ticket_number}\nDiscount: {discount} OMR"
        whatsapp_url = f"https://wa.me/{phone}?text={whatsapp_message.replace(' ', '%20')}"
        st.markdown(f'<a href="{whatsapp_url}" target="_blank">Share via WhatsApp</a>', unsafe_allow_html=True)

    with col3:
        if st.button('Clear'):
            st.session_state.pop('coupon_details', None)
            st.rerun()
