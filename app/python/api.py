import requests
import json
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_text(field):
    """Extract _text field from nested objects"""
    if isinstance(field, dict) and "_text" in field:
        return field["_text"].strip()
    return str(field).strip() if field else "N/A"

def format_key(key):
    """Convert camelCase to Title Case"""
    key = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
    return key.replace('_', ' ').title()

def api1_lookup(meter_number):
    """API 1: Get meter data and extract consumer number"""
    try:
        clean_meter = str(meter_number).strip()
        url = "http://web.bpdbprepaid.gov.bd/bn/token-check"
        
        headers = {
            'Accept': 'text/x-component',
            'Content-Type': 'text/plain;charset=UTF-8',
            'Next-Action': '29e85b2c55c9142822fe8da82a577612d9e58bb2',
            'Origin': 'http://web.bpdbprepaid.gov.bd',
            'Referer': 'http://web.bpdbprepaid.gov.bd/bn/token-check',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        request_data = '[{"meterNo":"' + clean_meter + '"}]'
        response = requests.post(url, headers=headers, data=request_data, verify=False, timeout=30)
        
        if response.status_code == 200:
            response_text = response.text
            lines = response_text.split('\n')
            json_line = None
            
            for line in lines:
                if line.startswith('1:'):
                    json_line = line[2:]
                    break
            
            if json_line:
                api1_data = json.loads(json_line)
                consumer_number = extract_consumer_number(api1_data)
                return consumer_number, api1_data
            else:
                return None, {"error": "No valid response data found"}
        else:
            return None, {"error": f"HTTP Error: {response.status_code}"}
            
    except Exception as e:
        return None, {"error": f"API 1 Error: {str(e)}"}

def extract_consumer_number(api1_data):
    """Extract consumer number from API 1 response"""
    try:
        if "mCustomerData" in api1_data and "result" in api1_data["mCustomerData"]:
            customer_data = api1_data["mCustomerData"]["result"]
            if "customerAccountNo" in customer_data:
                customer_no = get_text(customer_data["customerAccountNo"])
                if customer_no and customer_no != "N/A":
                    return customer_no
        
        if "mOrderData" in api1_data and "result" in api1_data["mOrderData"]:
            order_data = api1_data["mOrderData"]["result"]
            if "orders" in order_data and "order" in order_data["orders"]:
                orders = order_data["orders"]["order"]
                if isinstance(orders, list) and len(orders) > 0:
                    first_order = orders[0]
                    if "customerNo" in first_order:
                        customer_no = get_text(first_order["customerNo"])
                        if customer_no and customer_no != "N/A":
                            return customer_no
                elif isinstance(orders, dict) and "customerNo" in orders:
                    customer_no = get_text(orders["customerNo"])
                    if customer_no and customer_no != "N/A":
                        return customer_no
        
        return None
        
    except Exception as e:
        return None

def api3_lookup(customer_number):
    """API 3: Get pre-customer information"""
    try:
        url = f"https://miscbillapi.bpdb.gov.bd/api/v1/get-pre-customer_info/{customer_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            api3_data = response.json()
            if api3_data and api3_data.get("customerNumber"):
                return api3_data
            else:
                return None
        else:
            return None
            
    except Exception as e:
        return None

def api2_lookup(account_number):
    """API 2: Get detailed postpaid consumer information with balance"""
    try:
        url = f"https://billonwebapi.bpdb.gov.bd/api/CustomerInformation/{account_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP Error: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"API 2 Error: {str(e)}"}

def fetch_prepaid_data(meter_number):
    """Complete prepaid lookup: API 1 → API 3 → API 2"""
    consumer_number, api1_data = api1_lookup(meter_number)
    
    result = {
        "meter_number": meter_number,
        "api1_data": api1_data,
        "consumer_number": consumer_number,
        "api3_data": None,
        "api2_data": None
    }
    
    if consumer_number and "error" not in api1_data:
        api3_data = api3_lookup(consumer_number)
        result["api3_data"] = api3_data
        
        if api3_data:
            account_number = api3_data.get("customerNumber")
            if account_number:
                api2_data = api2_lookup(account_number)
                result["api2_data"] = api2_data
            else:
                api2_data = api2_lookup(consumer_number)
                result["api2_data"] = api2_data
        else:
            api2_data = api2_lookup(consumer_number)
            result["api2_data"] = api2_data
    
    return result

def fetch_postpaid_data(meter_number):
    """Postpaid lookup: API 3 → API 2"""
    result = {
        "meter_number": meter_number,
        "api3_data": None,
        "api2_data": None
    }
    
    api3_data = api3_lookup(meter_number)
    result["api3_data"] = api3_data
    
    if api3_data:
        account_number = api3_data.get("customerNumber")
        if account_number:
            api2_data = api2_lookup(account_number)
            result["api2_data"] = api2_data
        else:
            api2_data = api2_lookup(meter_number)
            result["api2_data"] = api2_data
    else:
        api2_data = api2_lookup(meter_number)
        result["api2_data"] = api2_data
    
    return result

def clean_api1_data(api1_data):
    """Extract useful information from API 1 for prepaid customers"""
    if not api1_data or "error" in api1_data:
        return api1_data

    cleaned = {}

    if "mCustomerData" in api1_data and "result" in api1_data["mCustomerData"]:
        customer_data = api1_data["mCustomerData"]["result"]
        
        cleaned["customer_info"] = {
            "Consumer Number": get_text(customer_data.get("customerAccountNo")),
            "Name": get_text(customer_data.get("customerName")),
            "Address": get_text(customer_data.get("customerAddress")),
            "Phone": get_text(customer_data.get("customerPhone")),
            "Division": get_text(customer_data.get("division")),
            "Sub Division": get_text(customer_data.get("sndDivision")),
            "Tariff Category": get_text(customer_data.get("tariffCategory")),
            "Connection Category": get_text(customer_data.get("connectionCategory")),
            "Account Type": get_text(customer_data.get("accountType")),
            "Meter Type": get_text(customer_data.get("meterType")),
            "Sanctioned Load": get_text(customer_data.get("sanctionLoad")),
            "Meter Number": get_text(customer_data.get("meterNumber")),
            "Last Recharge Amount": get_text(customer_data.get("lastRechargeAmount")),
            "Last Recharge Time": get_text(customer_data.get("lastRechargeTime")),
            "Installation Date": get_text(customer_data.get("installationDate")),
            "Lock Status": get_text(customer_data.get("lockStatus")),
            "Total Recharge This Month": get_text(customer_data.get("totalRechargeThisMonth"))
        }

    if "mOrderData" in api1_data and "result" in api1_data["mOrderData"]:
        order_data = api1_data["mOrderData"]["result"]
        
        if "orders" in order_data and "order" in order_data["orders"]:
            orders = order_data["orders"]["order"]
            transactions = []
            
            if isinstance(orders, dict):
                orders = [orders]
            
            for order in orders[:3]:
                transaction = {
                    "Date": get_text(order.get("date")),
                    "Order Number": get_text(order.get("orderNo")),
                    "Amount": f"৳{get_text(order.get('grossAmount'))}",
                    "Energy Cost": f"৳{get_text(order.get('energyCost'))}",
                    "Tokens": get_text(order.get("tokens")),
                    "Operator": get_text(order.get("operator")),
                    "Sequence": get_text(order.get("sequence"))
                }
                
                if "tariffFees" in order and "tariffFee" in order["tariffFees"]:
                    tariff_fees = order["tariffFees"]["tariffFee"]
                    if isinstance(tariff_fees, list):
                        for fee in tariff_fees:
                            item_name = get_text(fee.get("itemName"))
                            charge_amount = get_text(fee.get("chargeAmount"))
                            if item_name and charge_amount and charge_amount != "0":
                                transaction[item_name] = f"৳{charge_amount}"
                    elif isinstance(tariff_fees, dict):
                        item_name = get_text(tariff_fees.get("itemName"))
                        charge_amount = get_text(tariff_fees.get("chargeAmount"))
                        if item_name and charge_amount and charge_amount != "0":
                            transaction[item_name] = f"৳{charge_amount}"
                
                transactions.append(transaction)
            
            cleaned["recent_transactions"] = transactions

    cleaned = remove_empty_fields(cleaned)
    return cleaned

def clean_api2_data(api2_data):
    """Extract useful information from API 2"""
    if not api2_data or "error" in api2_data:
        return api2_data

    cleaned = {}

    if "customerInfo" in api2_data and api2_data["customerInfo"]:
        if api2_data["customerInfo"][0] and len(api2_data["customerInfo"][0]) > 0:
            first_customer = api2_data["customerInfo"][0][0]
            cleaned["customer_info"] = {
                "Customer Number": first_customer.get("CUSTOMER_NUMBER"),
                "Customer Name": first_customer.get("CUSTOMER_NAME"),
                "Address": first_customer.get("ADDRESS"),
                "Tariff": first_customer.get("TARIFF"),
                "Location Code": first_customer.get("LOCATION_CODE"),
                "Bill Group": first_customer.get("BILL_GROUP"),
                "Book": first_customer.get("BOOK"),
                "Walking Sequence": first_customer.get("WALKING_SEQUENCE"),
                "Meter Number": first_customer.get("METER_NUM"),
                "Meter Status": get_meter_status(first_customer.get("METER_STATUS")),
                "Connection Date": format_date(first_customer.get("METER_CONNECT_DATE")),
                "Description": first_customer.get("DESCR"),
                "Account_Number": first_customer.get("CONS_EXTG_NUM"),
            }
    
    balance_info = {}
    
    if "finalBalanceInfo" in api2_data and api2_data["finalBalanceInfo"]:
        balance_info = extract_balance_info(api2_data["finalBalanceInfo"])
    
    elif "balanceInfo" in api2_data and "Result" in api2_data["balanceInfo"]:
        balance_result = api2_data["balanceInfo"]["Result"]
        if balance_result and len(balance_result) > 0:
            first_balance = balance_result[0]
            balance_info = {
                "Total Balance": f"{first_balance.get('BALANCE', 0):.0f}",
                "Current Bill": f"{first_balance.get('CURRENT_BILL', 0):.0f}",
                "Arrear Bill": f"{first_balance.get('ARREAR_BILL', 0):.0f}",
                "Paid Amount": f"{first_balance.get('PAID_AMT', 0):.0f}"
            }
    
    if balance_info:
        cleaned["balance_info"] = balance_info
    
    cleaned = remove_empty_fields(cleaned)
    return cleaned

def clean_api3_data(api3_data):
    """Extract useful information from API 3 with consistent field names"""
    if not api3_data:
        return {}

    cleaned = {}

    cleaned["customer_info"] = {
        "Customer Number": api3_data.get("customerNumber"),
        "Customer Name": api3_data.get("customerName"),
        "Customer Address": api3_data.get("customerAddr"),
        "Father Name": api3_data.get("fatherName"),
        "Location Code": api3_data.get("locationCode"),
        "Area Code": api3_data.get("areaCode"),
        "Book Number": api3_data.get("bookNumber"),
        "Bill Group": api3_data.get("billGroup"),
        "Meter Number": api3_data.get("meterNum"),
        "Meter Condition": api3_data.get("meterConditionDesc"),
        "Sanctioned Load": api3_data.get("sanctionedLoad"),
        "Tariff Description": api3_data.get("tariffDesc"),
        "Walk Order": api3_data.get("walkOrder"),
        "Arrear Amount": api3_data.get("arrearAmount"),
        "Last Bill Reading SR": api3_data.get("lastBillReadingSr"),
        "Last Bill Reading OF PK": api3_data.get("lastBillReadingOfPk"),
        "Last Bill Reading PK": api3_data.get("lastBillReadingPk")
    }

    if api3_data.get("arrearAmount") is not None:
        cleaned["balance_info"] = {
            "Total Balance": str(api3_data.get("arrearAmount", 0)),
            "Arrear Amount": str(api3_data.get("arrearAmount", 0))
        }

    cleaned = remove_empty_fields(cleaned)
    return cleaned

def merge_api_data(result):
    """Merge API 3 and API 2 data, removing duplicates"""
    api3_data = result.get('api3_data')
    api2_data = result.get('api2_data', {})
    
    if not api3_data and "error" in api2_data:
        return None
    
    merged = {}
    
    # Start with API 3 data as base
    if api3_data:
        cleaned_api3 = clean_api3_data(api3_data)
        if "customer_info" in cleaned_api3:
            merged["customer_info"] = cleaned_api3["customer_info"].copy()
        if "balance_info" in cleaned_api3:
            merged["balance_info"] = cleaned_api3["balance_info"].copy()
    
    # If API 3 has no data but API 2 has data, use API 2
    elif "error" not in api2_data:
        cleaned_api2 = clean_api2_data(api2_data)
        if "customer_info" in cleaned_api2:
            merged["customer_info"] = cleaned_api2["customer_info"].copy()
        if "balance_info" in cleaned_api2:
            merged["balance_info"] = cleaned_api2["balance_info"].copy()
    
    # Supplement with unique data from API 2
    if "error" not in api2_data:
        cleaned_api2 = clean_api2_data(api2_data)
        
        if "customer_info" in cleaned_api2:
            if "customer_info" not in merged:
                merged["customer_info"] = {}
            
            api2_customer = cleaned_api2["customer_info"]
            
            # Add only unique fields from API 2
            unique_fields = {
                "Meter Status": api2_customer.get("Meter Status"),
                "Connection Date": api2_customer.get("Connection Date"),
                "Description": api2_customer.get("Description"),
                "Account_Number": api2_customer.get("Account_Number")
            }
            
            for key, value in unique_fields.items():
                if value and value != "N/A":
                    merged["customer_info"][key] = value
        
        # Use API 2 balance info if it has more detailed breakdown
        if "balance_info" in cleaned_api2:
            api2_balance = cleaned_api2["balance_info"]
            if api2_balance and len(api2_balance) > 1:  # If API 2 has detailed breakdown
                merged["balance_info"] = api2_balance
    
    return remove_empty_fields(merged)

def format_merged_display(merged_data):
    """Format merged data for nice display without duplicates"""
    if not merged_data:
        return "No data available"
    
    output = []
    
    # Customer Info Section
    if "customer_info" in merged_data:
        output.append("👤 CUSTOMER INFORMATION")
        output.append("=" * 35)
        
        customer_info = merged_data["customer_info"]
        
        # Display in logical order
        key_order = [
            "Customer Number", "Customer Name", "Customer Address", 
            "Location Code", "Area Code", "Bill Group", "Book Number",
            "Tariff Description", "Sanctioned Load", "Meter Number",
            "Meter Condition", "Meter Status", "Walk Order", "Walking Sequence",
            "Connection Date", "Description", "Account_Number", "Father Name",
            "Arrear Amount", "Last Bill Reading SR", "Last Bill Reading OF PK", "Last Bill Reading PK"
        ]
        
        for key in key_order:
            if key in customer_info and customer_info[key] and customer_info[key] != "N/A":
                output.append(f"📌 {key}: {customer_info[key]}")
        
        # Add any remaining fields not in the ordered list
        for key, value in customer_info.items():
            if key not in key_order and value and value != "N/A":
                output.append(f"📌 {key}: {value}")
        
        output.append("")
    
    # Balance Information Section
    if "balance_info" in merged_data:
        output.append("💰 OUTSTANDING BALANCE")
        output.append("=" * 35)
        
        balance_info = merged_data["balance_info"]
        
        # Display balance in logical order
        balance_order = ["Total Balance", "Arrear Amount", "Current Bill", "PRN", "LPS", "VAT", "Paid Amount"]
        
        for key in balance_order:
            if key in balance_info and balance_info[key]:
                value = str(balance_info[key]).replace('৳', '').strip()
                output.append(f"💵 {key}: ৳{value}")
        
        # Add any remaining balance fields
        for key, value in balance_info.items():
            if key not in balance_order and value:
                value = str(value).replace('৳', '').strip()
                output.append(f"💵 {key}: ৳{value}")
    
    return "\n".join(output)

def format_prepaid_display(cleaned_data):
    """Format cleaned API 1 data for nice display"""
    if not cleaned_data:
        return "No data available"
    
    output = []
    
    if "customer_info" in cleaned_data:
        output.append("👤 PREPAID CUSTOMER INFORMATION")
        output.append("=" * 35)
        for key, value in cleaned_data["customer_info"].items():
            if value and value != "N/A":
                output.append(f"📌 {key}: {value}")
        output.append("")
    
    if "recent_transactions" in cleaned_data:
        output.append("💳 RECENT TRANSACTIONS")
        output.append("=" * 35)
        for i, transaction in enumerate(cleaned_data["recent_transactions"], 1):
            output.append(f"#{i} - {transaction['Date']}")
            output.append(f"   💰 Amount: {transaction['Amount']}")
            output.append(f"   ⚡ Energy Cost: {transaction['Energy Cost']}")
            if transaction.get('Tokens') and transaction['Tokens'] != 'N/A':
                output.append(f"   🔑 Tokens: {transaction['Tokens']}")
            output.append(f"   👨‍💼 Operator: {transaction['Operator']}")
            
            for key, value in transaction.items():
                if key not in ['Date', 'Amount', 'Energy Cost', 'Tokens', 'Operator', 'Sequence', 'Order Number']:
                    output.append(f"   📊 {key}: {value}")
            output.append("")
    
    return "\n".join(output)

def get_meter_status(status_code):
    """Convert meter status code to readable text"""
    status_map = {
        "1": "Active",
        "2": "Inactive", 
        "3": "Disconnected"
    }
    return status_map.get(str(status_code), f"Unknown ({status_code})")

def format_date(date_string):
    """Format date from API response"""
    if not date_string:
        return "N/A"
    try:
        if "T" in date_string:
            return date_string.split("T")[0]
        return date_string
    except:
        return date_string

def extract_balance_info(balance_string):
    """Extract balance components from the string"""
    if not balance_string:
        return {}
    
    balance_info = {}
    
    try:
        parts = balance_string.split(',')
        
        main_balance = parts[0].strip()
        balance_info["Total Balance"] = main_balance.split('(')[0].strip()
        
        for part in parts[1:]:
            if ':' in part:
                key, value = part.split(':', 1)
                balance_info[key.strip()] = value.strip()
                
    except Exception as e:
        balance_info["Raw Balance Info"] = balance_string
    
    return balance_info

def remove_empty_fields(data):
    """Recursively remove empty fields and N/A values"""
    if isinstance(data, dict):
        return {k: remove_empty_fields(v) for k, v in data.items() 
                if v not in [None, "", "N/A", {}] and remove_empty_fields(v)}
    elif isinstance(data, list):
        return [remove_empty_fields(item) for item in data 
                if item not in [None, "", "N/A", {}] and remove_empty_fields(item)]
    else:
        return data

def validate_meter(meter_number, bill_type):
    """Validate meter number based on bill type"""
    meter_str = str(meter_number).strip()
    
    if not meter_str.isdigit():
        return False, "Meter number must contain only digits"
    
    if bill_type == "prepaid":
        if len(meter_str) != 12:
            return False, "Prepaid meter must be exactly 12 digits"
        return True, "Valid"
    else:
        if len(meter_str) == 0:
            return False, "Please enter meter number"
        return True, "Valid"

def display_result(result, bill_type):
    """Display results in clean format - merged without duplicates"""
    print("\n" + "="*50)
    print(f"📊 {bill_type.upper()} LOOKUP RESULTS")
    print("="*50)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"🔢 Meter Number: {result.get('meter_number', 'N/A')}")
    
    if bill_type == "prepaid":
        if result.get('consumer_number'):
            print(f"👤 Consumer Number: {result['consumer_number']}")
        
        # Show prepaid details from API 1
        api1_data = result.get('api1_data', {})
        cleaned_data = clean_api1_data(api1_data)
        
        if "error" not in api1_data:
            display_text = format_prepaid_display(cleaned_data)
            if display_text.strip():
                print("\n" + "="*30)
                print("📋 PREPAID CUSTOMER DETAILS")
                print("="*30)
                print(display_text)
        
        # Show merged API 3 + API 2 data
        merged_data = merge_api_data(result)
        if merged_data:
            print("\n" + "="*30)
            print("📋 CUSTOMER INFORMATION")
            print("="*30)
            display_text = format_merged_display(merged_data)
            print(display_text)
    
    elif bill_type == "postpaid":
        # Show merged API 3 + API 2 data for postpaid
        merged_data = merge_api_data(result)
        if merged_data:
            print("\n" + "="*30)
            print("📋 CUSTOMER INFORMATION")
            print("="*30)
            display_text = format_merged_display(merged_data)
            print(display_text)
        else:
            print("❌ No customer data found")

def main():
    """Main interactive interface"""
    print("🚀 BPDB METER INFORMATION CHECKER")
    print("="*40)
    
    while True:
        print("\n🔧 Select Bill Type:")
        print("1. Prepaid (12-digit meter)")
        print("2. Postpaid (any digit meter)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "3":
            print("👋 Goodbye!")
            break
            
        if choice not in ["1", "2"]:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
            continue
        
        bill_type = "prepaid" if choice == "1" else "postpaid"
        
        print(f"\n📝 Enter {bill_type.upper()} Meter Number:")
        meter_number = input("Meter Number: ").strip()
        
        is_valid, message = validate_meter(meter_number, bill_type)
        if not is_valid:
            print(f"❌ {message}")
            continue
        
        print(f"\n🔄 Processing {bill_type.upper()} lookup...")
        
        try:
            if bill_type == "prepaid":
                result = fetch_prepaid_data(meter_number)
            else:
                result = fetch_postpaid_data(meter_number)
            
            display_result(result, bill_type)
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        continue_test = input("\n🔄 Test another meter? (y/n): ").strip().lower()
        if continue_test != 'y':
            print("👋 Goodbye!")
            break

if __name__ == "__main__":
    main()
