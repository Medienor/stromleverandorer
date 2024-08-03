import requests
from datetime import datetime
import json
from weds import webflow_bearer_token

# Strompris API credentials
STROMPRIS_USERNAME = 'josef@medienor.no'
STROMPRIS_PASSWORD = '3mXKRl0xVP'

# Get today's date in the required format
today = datetime.now().strftime("%d-%m-%Y")

# Strompris API call
strompris_url = f"https://www.strompris.no/strom-product-ms/feeds/{today}.json"
strompris_response = requests.get(strompris_url, auth=(STROMPRIS_USERNAME, STROMPRIS_PASSWORD))

if strompris_response.status_code != 200:
    print(f"Error accessing Strompris API: {strompris_response.status_code}")
    exit()

strompris_data = strompris_response.json()

# Webflow API call
webflow_url = "https://api.webflow.com/v2/collections/667c332ea80584f74f272d0b/items"
webflow_headers = {
    "accept": "application/json",
    "authorization": f"Bearer {webflow_bearer_token}"
}

webflow_response = requests.get(webflow_url, headers=webflow_headers)

if webflow_response.status_code != 200:
    print(f"Error accessing Webflow API: {webflow_response.status_code}")
    exit()

webflow_data = webflow_response.json()

def update_webflow_item(item_id, update_data):
    update_url = f"https://api.webflow.com/v2/collections/667c332ea80584f74f272d0b/items/{item_id}/live"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    
    # Prepare the payload
    payload = {
        "isArchived": False,
        "isDraft": False,
        "fieldData": update_data['fields']
    }
    
    print(f"Updating item {item_id} with data: {json.dumps(payload, indent=2)}")
    update_response = requests.patch(update_url, json=payload, headers=headers)
    print(f"Update response status: {update_response.status_code}")
    print(f"Update response content: {update_response.text}")
    
    if update_response.status_code != 200:
        print(f"Error updating Webflow item: {update_response.status_code}")
    else:
        print(f"Successfully updated Webflow item: {item_id}")

def get_zones_and_municipalities_from_company(company):
    zones = set()
    municipalities = set()
    for product in company['products']:
        if 'productArea' in product:
            for area in product['productArea']:
                if 'region' in area:
                    region = area['region']
                    zone_number = region[-1]  # Extract the number from regionNOX
                    zones.add(zone_number)
                elif 'municipality' in area:
                    municipalities.add(area['municipality'])
    return zones, municipalities

def get_zone_name(zone):
    zone_names = {
        "1": "Øst-Norge",
        "2": "Sør-Norge",
        "3": "Midt-Norge",
        "4": "Nord-Norge",
        "5": "Vest-Norge"
    }
    return zone_names.get(zone, "")

def format_locations(locations):
    if len(locations) == 1:
        return locations[0]
    elif len(locations) == 2:
        return f"{locations[0]} og {locations[1]}"
    else:
        return ", ".join(locations[:-1]) + f", og {locations[-1]}"

# Process each company from Strompris
for company in strompris_data:
    company_name = company['companyName']
    print(f"Processing company: {company_name}")
    
    # Find matching company in Webflow data
    matching_item = next((item for item in webflow_data['items'] if item['fieldData']['companyname'] == company_name), None)
    
    if matching_item:
        print(f"Found matching item in Webflow: {matching_item['id']}")
        # Get all unique zones and municipalities for this company
        company_zones, company_municipalities = get_zones_and_municipalities_from_company(company)
        print(f"Company zones: {company_zones}")
        print(f"Company municipalities: {company_municipalities}")
        
        # Prepare update data
        update_data = {
            "fields": {
                "name": matching_item['fieldData']['name'],
                "slug": matching_item['fieldData']['slug']
            }
        }
        
        for i in range(1, 6):
            field_name = f"soneno{i}"
            if str(i) in company_zones:
                update_data['fields'][field_name] = f"NO{i}"
            else:
                update_data['fields'][field_name] = ""
        
        # Prepare tilbyrstrom text
        if company_zones:
            zone_names = [get_zone_name(zone) for zone in company_zones]
            locations = format_locations(zone_names)
            tilbyrstrom_text = f"{company_name} tilbyr strømavtaler i {locations}"
        elif company_municipalities:
            municipalities = format_locations(list(company_municipalities))
            tilbyrstrom_text = f"{company_name} tilbyr strømavtaler i {municipalities}"
        else:
            tilbyrstrom_text = f"{company_name} tilbyr strømavtaler"
        
        update_data['fields']['tilbyrstrom'] = tilbyrstrom_text
        
        # Update Webflow item
        update_webflow_item(matching_item['id'], update_data)
    else:
        print(f"No matching company found in Webflow for: {company_name}")

print("Processing complete.")