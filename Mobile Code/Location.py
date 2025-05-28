import androidhelper
import time
import requests
import json

# Initialize Android helper
droid = androidhelper.Android()

# Supabase configuration - using your actual project
SUPABASE_URL = "https://wngqbymqpbrcpgtuqetr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InduZ3FieW1xcGJyY3BndHVxZXRyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDIwMDM3MiwiZXhwIjoyMDQ5Nzc2MzcyfQ.9hTOd76a0rjjiZOZy8Hb6GKP0JXWCz6qyx4lQtoFgFU"
TABLE_NAME = "Location"  # Your exact table name

# Headers for Supabase API
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def check_get_status():
    """Check if any record has GET=1"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=GET&GET=eq.1"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return len(data) > 0  # Returns True if any record has GET=1
    except Exception as e:
        print(f"Error checking GET status: {str(e)}")
        return False

def get_current_location():
    """Get current device location with retries"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            droid.startLocating()
            time.sleep(5)
            location = droid.readLocation().result
            droid.stopLocating()
            
            if location and ('gps' in location or 'network' in location):
                source = 'gps' if 'gps' in location else 'network'
                return {
                    'latitude': location[source]['latitude'],
                    'longitude': location[source]['longitude']
                }
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(2)
    return None




def save_to_supabase(location_data):
    """Save location data and reset GET flag"""
    try:
        # 1. Find the record with GET=1
        query_url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=*&GET=eq.1"
        print(f"🔍 Checking for GET=1 record: {query_url}")
        
        response = requests.get(query_url, headers=headers)
        print(f"🔹 GET Response: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        records = response.json()
        
        if not records:
            print("❌ No records with GET=1 found")
            return False
            
        # Get the first record with GET=1 (assuming there's only one)
        record = records[0]
        print(f"📝 Found record to update: {record}")
        
        # 2. Prepare PATCH request
        # Since your table doesn't have an 'id' column, we need to identify records differently
        # We'll use the GET=1 filter again in the update URL
        update_url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?GET=eq.1"
        
        payload = {
            "Latitude": float(location_data['latitude']),
            "Longitude": float(location_data['longitude']),
            "GET": 0  # Reset the GET flag
        }
        
        print(f"🔄 Update payload: {payload}")
        
        # 3. Execute PATCH request
        update_response = requests.patch(
            update_url,
            headers=headers,
            json=payload
        )
        
        print(f"🔹 PATCH Response: {update_response.status_code} - {update_response.text}")
        
        if update_response.status_code in (200, 204):  # Success
            print("✅ Successfully updated record!")
            return True
        else:
            error_msg = update_response.json().get("message", update_response.text)
            print(f"❌ Update failed: {error_msg}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main_loop():
    """Continuous polling loop"""
    while True:
        try:
            print("Checking for GET=1...")
            if check_get_status():
                print("GET=1 detected, getting location...")
                location = get_current_location()
                
                if location:
                    print(f"Obtained location: {location}")
                    if save_to_supabase(location):
                        print("Update successful")
                    else:
                        print("Failed to update record")
                else:
                    print("Failed to get location after multiple attempts")
            
            # Wait before checking again
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nScript stopped by user")
            break
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            time.sleep(10)  # Wait longer after errors

if __name__ == "__main__":
    print("Starting Location Tracker...")
    main_loop()