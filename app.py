import cv2
import yfinance as yf
from pyzbar.pyzbar import decode
import numpy as np
import requests
import json
import time

# ========== BARCODE SCANNER FUNCTION ==========
def scan_barcode():
    
    # Try to open the default camera (index 1 as specified in your code)
    cap = cv2.VideoCapture(1)
    
    # Check if the camera opened successfully
    if not cap.isOpened():
        print("ERROR: Could not open webcam. Try a different camera index.")
        return None
    
    last_barcode_data = None
    stable_barcode_time = 0
    required_stable_time = 0.8  # Seconds the barcode must remain stable
    
    while True:
        # Read a frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame - stream may have ended")
            break
        
        # Make a copy of the frame for display
        display_frame = frame.copy()
        
        decoded_objects = decode(frame)
        current_time = time.time()
        current_barcode = None
        
        # Process each detected barcode
        for obj in decoded_objects:
            # Get the barcode data
            current_barcode = obj.data.decode('utf-8')
            barcode_type = obj.type
            
            # Draw rectangle around barcode
            x, y, w, h = obj.rect
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw the barcode data
            cv2.putText(display_frame, f"{current_barcode}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Print barcode information
            print(f"DETECTED: {current_barcode} ({barcode_type})")
            
            # Only use the first barcode if multiple are detected
            break
        
        # Check if the barcode is stable
        if current_barcode == last_barcode_data and current_barcode is not None:
            # If this is the first time we've seen this stable barcode, record the time
            if stable_barcode_time == 0:
                stable_barcode_time = current_time
                
            # Check if the barcode has been stable for the required time
            if current_time - stable_barcode_time >= required_stable_time:
                print("=" * 40)
                print(f"CONFIRMED BARCODE: {current_barcode}")
                print(f"Barcode was stable for {current_time - stable_barcode_time:.1f} seconds")
                print("=" * 40)
                
                # Show the final frame with confirmed detection
                cv2.putText(display_frame, "CONFIRMED", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('Barcode Scanner', display_frame)
                cv2.waitKey(2000)  # Show the confirmed frame for 2 seconds
                break
        else:
            # Reset the stable time if the barcode changed or disappeared
            stable_barcode_time = 0
            
        # Update the last seen barcode
        last_barcode_data = current_barcode
        
        # Add status information to the display frame
        if current_barcode is not None:
            if stable_barcode_time > 0:
                elapsed = current_time - stable_barcode_time
                remaining = max(0, required_stable_time - elapsed)
                cv2.putText(display_frame, f"Confirming: {remaining:.1f}s left", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                cv2.putText(display_frame, "Detected - waiting for stable read", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(display_frame, "Scanning...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Display the frame
        cv2.imshow('Barcode Scanner', display_frame)
        
        # Exit if user presses 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("User terminated scanning")
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print("Barcode scanning complete")
    
    return last_barcode_data  # Return the confirmed barcode

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

with open("parent_companies.json", "r") as f:
    parent_companies = json.load(f)

# ========== PARENT COMPANY MAPPING FUNCTION ==========
with open("parent_companies.json", "r") as f:
    parent_companies = json.load(f)

def get_parent_company_ticker(brand_name):
    # Convert to lowercase for case-insensitive matching
    brand_lower = brand_name.lower()

    # Try exact match
    if brand_lower in parent_companies:
        return brand_lower, parent_companies[brand_lower]

    # Try partial match
    for known_brand, ticker in parent_companies.items():
        if known_brand in brand_lower or brand_lower in known_brand:
            return known_brand, ticker

    # No match found
    return brand_name, None

# ========== ESG FETCH FUNCTION ==========
def get_esg_data(company_ticker):
    try:
        stock = yf.Ticker(company_ticker)
        esg_data = stock.sustainability
        
        if esg_data is not None and 'totalEsg' in esg_data.index:
            total_esg_score = esg_data.loc['totalEsg'].iloc[0]
            return f"Total ESG Score for {company_ticker}: {total_esg_score}"
        else:
            return f"No ESG data available for {company_ticker}."
    except Exception as e:
        return f"Error fetching ESG data for {company_ticker}: {e}"

# ========== MAIN ==========
if __name__ == "__main__":
    # Step 1: Scan barcode

    detected_barcode = scan_barcode()
    
    if detected_barcode:
        # Step 2: Look up product information
        product_name, brand = lookup_openfoodfacts(detected_barcode)
        
        if product_name and brand:
            print(f"Found product: {product_name} by {brand}")
            
            # Step 3: Find parent company and ticker
            parent_company, ticker = get_parent_company_ticker(brand)
            
            if ticker:
                print(f"Parent company: {parent_company} (Ticker: {ticker})")
                
                # Step 4: Get ESG data for parent company
                esg_result = get_esg_data(ticker)
                print(esg_result)
            else:
                print(f"Could not determine parent company ticker for {brand}")
        else:
            print("Product not found in OpenFoodFacts database")
    else:
        print("No barcode detected or scanning was cancelled")
