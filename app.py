import cv2
import yfinance as yf
from pyzbar.pyzbar import decode
from flask import Flask
import threading
import numpy as np
import requests  # You need this import for lookup_openfoodfacts

app = Flask("greenwashing")

# ========== BARCODE SCANNER FUNCTION ==========
def scan_barcode():
    # Try to open the default camera (index 0 is usually the default camera)
    cap = cv2.VideoCapture(0)
    
    # Check if the camera opened successfully
    if not cap.isOpened():
        print("ERROR: Could not open webcam. Try a different camera index.")
        return None
    
    barcode_data = None
    
    while True:
        # Read a frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame - stream may have ended")
            break
            
        decoded_objects = decode(frame)
        
        # Process each detected barcode
        for obj in decoded_objects:
            # Get the barcode data
            barcode_data = obj.data.decode('utf-8')
            barcode_type = obj.type
            
            print("=" * 40)
            print(f"BARCODE NUMBER: {barcode_data}")
            print(f"Barcode Type: {barcode_type}")
            print("=" * 40)
            
            x, y, w, h = obj.rect
            
            # Draw a simple rectangle instead of using polygon points
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
            # Draw the barcode data
            cv2.putText(frame, f"{barcode_data}", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Show the frame with detection for 2 seconds
            cv2.imshow('Barcode Scanner', frame)
            cv2.waitKey(2000)
            break  # Exit the for loop after first detection
                       
        # Display the frame
        cv2.imshow('Barcode Scanner', frame)
        
        # If we detected a barcode or user pressed 'q', exit
        if barcode_data is not None or (cv2.waitKey(1) & 0xFF == ord('q')):
            break
            
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print("Barcode scanning complete")
    
    return barcode_data  # Return the detected barcode

def lookup_openfoodfacts(barcode_data):
    if barcode_data is None:
        print("No barcode data provided")
        return None, None
        
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_data}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 1:
            product = data['product']
            brand = product.get('brands', 'Unknown')
            name = product.get('product_name', 'Unknown')
            return name, brand
    return None, None

# ========== ESG FETCH FUNCTION ==========
def get_esg_data(company_ticker):
    try:
        stock = yf.Ticker(company_ticker)
        esg_data = stock.sustainability

        if esg_data is not None and 'totalEsg' in esg_data.index:
            total_esg_score = esg_data.loc['totalEsg'][0]
            return f"<h2>Total ESG Score for {company_ticker}: {total_esg_score}</h2>"
        else:
            return f"<h2>No ESG data available for {company_ticker}.</h2>"
    except Exception as e:
        return f"<h2>Error fetching ESG data for {company_ticker}:</h2><p>{e}</p>"


# ========== MAIN ==========
if __name__ == "__main__":
    detected_barcode = scan_barcode()
    if detected_barcode:
        product_name, brand = lookup_openfoodfacts(detected_barcode)
        if product_name and brand:
            print(f"Found product: {product_name} by {brand}")
        else:
            print("Product not found in OpenFoodFacts database")
