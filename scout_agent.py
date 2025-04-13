import pandas as pd

EXPIRY_THRESHOLDS = {
    "Dairy": (2, 5, 7),
    "Meat": (1, 3, 5),
    "Seafood": (0, 1, 2),
    "Fruits": (2, 5, 10),   
    "Vegetables": (1, 4, 7),
    "Confectionery": (7, 30, 90),
    "Bakery": (0, 2, 4),
    "Packaged": (30, 180, 365),
    "Beverages": (7, 30, 180),
    "Frozen": (30, 90, 365),
    "Canned": (180, 365, 730)
}

def assign_zone(row, expiry_thresholds):
    category = row['food_category']
    days = row['days_to_expiry']
    
    if category in expiry_thresholds:
        red, warn, safe = expiry_thresholds[category]
        if days <= red:
            return 'red_alert'
        elif days <= warn:
            return 'warning'
        elif days <= safe:
            return 'safe'
        else:
            return None
    return None

def classify_items_by_expiry(df, location, expiry_thresholds=EXPIRY_THRESHOLDS):
    store_data = df[df['store_name'] == location].copy()
    store_data['todays_date'] = pd.to_datetime(store_data['todays_date'])
    store_data['expiry_date'] = pd.to_datetime(store_data['expiry_date'])
    store_data['days_to_expiry'] = (store_data['expiry_date'] - store_data['todays_date']).dt.days
    store_data['expiry_zone'] = store_data.apply(lambda row: assign_zone(row, expiry_thresholds), axis=1)
    alert_data = store_data[store_data['expiry_zone'].notna()]
    red_alert_items = alert_data[alert_data['expiry_zone'] == 'red_alert']
    warning_items = alert_data[alert_data['expiry_zone'] == 'warning']
    safe_items = alert_data[alert_data['expiry_zone'] == 'safe']
    return {
        'red_alert': red_alert_items,
        'warning': warning_items,
        'safe': safe_items
    }

def print_zone(zone_name, items_df):
        print(f"--- {zone_name.capitalize()} Items ---")
        if items_df.empty:
            print(f"No items in the {zone_name} zone.\n")
        else:
            for idx, row in items_df.iterrows():
                expiry_date = row['expiry_date'].strftime("%Y-%m-%d")
                print(f"{row['food_category']} - {row['food_item']} | Quantity: {row['quantity']} {row['unit']} | Expiry Date: {expiry_date} (in {row['days_to_expiry']} days)")
            print() 

def main():
    df = pd.read_csv("./data/merged_dataset.csv")
    location = input("Enter the store name: ")
    results = classify_items_by_expiry(df, location)
    print_zone("red_alert", results['red_alert'])
    print_zone("warning", results['warning'])
    print_zone("safe", results['safe'])

if __name__ == '__main__':
    main()