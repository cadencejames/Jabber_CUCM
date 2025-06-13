import requests
import warnings
import os
import sys
import re
import time
import csv
import getpass
import base64
from lxml import etree

# --- Configuration ---
csv_input = "./csv_input.csv"
url = "https://192.168.1.1/axl"

ns = {
    "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
    "ns": "http://www.cisco.com/AXL/API/14.0"
}
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)
dirgroups = [
    "<group 1 pkid here>",
    "<group 2 pkid here>",
    "<group 3 pkid here>",
    "<group 4 pkid here>",
    "<group 5 pkid here>",
    "<group 6 pkid here>",
    "<group 7 pkid here>"
]

# --- Helper Functions ---

def login():
    # Prompts user for credentials and returns a complete headers dictionary for AXL.
    print("--- CUCM AXL Login ---")
    username = input("CUCM Username: ")
    password = getpass.getpass("CUCM Password: ")
    credentials = f"{username}:{password}"
    credentials_bytes = credentials.encode('utf-8')
    base64_bytes = base64.b64encode(credentials_bytes)
    base64_string = base64_bytes.decode('utf-8')
    login_headers = {
        'Authorization': f'Basic {base64_string}',
        'Content-Type': 'text/plain'
    }
    print("Credentials encoded successfully.")
    return login_headers

def sanitize_userid(userid):
    # Checks if the userid is safe. Returns the userid if it exists, but exits the script if the input is invalid.
    clean_userid = userid.strip()
    if not re.match(r'^[a-zA-Z0-9]+$', clean_userid):
        print(f"Error: Invalid User ID format '{userid}'. Skipping this user.")
        return None
    return clean_userid

def build_payload(body_content):
    # Wraps the given XML content in a standard SOAP envelope.
    return f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://www.cisco.com/AXL/API/14.0">
        <soapenv:Header/>
        <soapenv:Body>
            {body_content}
        </soapenv:Body>
    </soapenv:Envelope>
    """

def APICall(payload, headers):
    # Makes the API call and handles SOAP Faults (errors) from CUCM.
    try:
        response = requests.request("POST", url, headers=headers, data=payload, verify=False, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        root = etree.fromstring(response.content) # Use response.content for bytes

        # Check for a SOAP Fault in the response from CUCM
        fault = root.find(".//faultstring") # No namespace needed for this standard tag
        if fault is not None:
            print(f"AXL API Error: {fault.text}")
            return None # Indicate failure
        return root
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request Error: {e}")
        return None
    except etree.XMLSyntaxError as e:
        print(f"XML Parsing Error: Could not parse response. Details: {e}")
        return None

def process_single_user(userid, headers):
    # Performs all provisioning steps for a single, sanitized User ID.
    # Returns True on sucess and False on fatal error for this user
    fullname, phonenumber, userpkid = GetUserInfo(userid, headers)
    if not userpkid: # Stop if user wasn't found
        return False
        
    print(f"\nProcessing user: {fullname} ({userid})")
    print(f"Phone Number: {phonenumber}")
    print(f"User PKID: {userpkid}")

    csfpkid = CheckCSFExistence(userid, headers)
    if not csfpkid:
        csfpkid = CreateDevice(userid, fullname, phonenumber, headers)
        if csfpkid:
            print("\nPausing for 2 seconds to allow system to sync...")
            time.sleep(2)
    
    if not csfpkid:
        print(f"FATAL: Could not find or create a CSF device for {userid}. Aborting this user.")
        return False

    current_dir_groups = GetUserDirGroups(userpkid, headers)
    print(f"\nUser is currently in {len(current_dir_groups)} directory group(s).")
    UpdateUserDirGroups(userpkid, userid, dirgroups, current_dir_groups, headers)
    UpdateUserDeviceMap(userpkid, csfpkid, userid, headers)
    return True

# --- AXL Action Functions ---

def GetUserInfo(userid, headers):
    axl_body = f"<ns:executeSQLQuery><sql>SELECT * FROM enduser WHERE userid = '{userid}'</sql></ns:executeSQLQuery>"
    root = APICall(build_payload(axl_body), headers)
    if root is None or not root.xpath("//ns:executeSQLQueryResponse/return/row", namespaces=ns):
        print(f"There was an error finding user: {userid}")
        return None, None, None
    
    firstname = root.xpath("//row/firstname/text()", namespaces=ns)[0]
    lastname = root.xpath("//row/lastname/text()", namespaces=ns)[0]
    phonenumber = root.xpath("//row/telephonenumber/text()", namespaces=ns)[0]
    userpkid = root.xpath("//row/pkid/text()", namespaces=ns)[0]
    fullname = f"{firstname} {lastname}"
    return fullname, phonenumber, userpkid

def CheckCSFExistence(userid, headers):
    axl_body = f"<ns:executeSQLQuery><sql>SELECT pkid FROM device WHERE name = 'CSF{userid}'</sql></ns:executeSQLQuery>"
    root = APICall(build_payload(axl_body), headers)
    if root is not None:
        csfpkid_list = root.xpath("//row/pkid/text()", namespaces=ns)
        if csfpkid_list:
            print(f"CSF device for {userid} already exists. Skipping creation...")
            return csfpkid_list[0] # Return the first pkid found
    print(f"CSF device for {userid} does NOT exist. Proceeding with creation...")
    return None

def CreateDevice(userid, fullname, phonenumber, headers):
    axl_body = f"""
    <ns:addPhone>
        <phone>
            <name>CSF{userid}</name><description>{fullname}</description>
            <product>Cisco Unified Client Services Framework</product><model>Cisco Unified Client Services Framework</model>
            <class>Phone</class><protocol>SIP</protocol><devicePoolName>Device Pool</devicePoolName>
            <phoneTemplateName>Standard Client Services Framework</phoneTemplateName>
            <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
            <securityProfileName>Cisco Unified Client Services Framework - Standard SIP Non-Secure Profile</securityProfileName>
            <sipProfileName>Standard SIP Profile</sipProfileName>
            <lines><line><index>1</index><label>{fullname}</label><display>{fullname}</display>
            <dirn><pattern>{phonenumber}</pattern></dirn></line></lines>
            <ownerUserName>{userid}</ownerUserName>
        </phone>
    </ns:addPhone>
    """
    root = APICall(build_payload(axl_body), headers)
    if root is not None:
        csfpkid_list = root.xpath("//ns:addPhoneResponse/return/text()", namespaces=ns)
        if csfpkid_list:
            csfpkid = csfpkid_list[0].strip('{}')
            print(f"CSF for {userid} created successfully.")
            return csfpkid
    print(f"Failed to create CSF device for {userid}.")
    return None

def GetUserDirGroups(userpkid, headers):
    axl_body = f"""
    <ns:executeSQLQuery><sql>
        SELECT fkdirgroup FROM enduserdirgroupmap WHERE fkenduser = '{userpkid}'
    </sql></ns:executeSQLQuery>
    """
    root = APICall(build_payload(axl_body), headers)
    if root is not None:
        return root.xpath("//row/fkdirgroup/text()", namespaces=ns)
    return []

def UpdateUserDirGroups(userpkid, userid, required_groups, current_groups, headers):
    print(f"\nUpdating directory groups for {userid}...")
    for group_pkid in required_groups:
        if group_pkid in current_groups:
            print(f"User already in group: {group_pkid}")
            continue
        axl_body = f"""
        <ns:executeSQLUpdate>
            <sql>
                INSERT INTO enduserdirgroupmap (fkenduser, fkdirgroup)
                VALUES ('{userpkid}', '{group_pkid}')
            </sql>
        </ns:executeSQLUpdate>
        """
        root = APICall(build_payload(axl_body), headers)
        if root is not None and root.xpath("//ns:executeSQLUpdateResponse/return/rowsUpdated/text()", namespaces=ns)[0] == "1":
            print(f"Successfully added group {group_pkid} to {userid}")
        else:
            print(f"Failed to add group {group_pkid} to {userid}")

def UpdateUserDeviceMap(userpkid, csfpkid, userid, headers):
    print(f"\nAssociating device for {userid}...")
    axl_body = f"""
    <ns:executeSQLUpdate>
        <sql>
            INSERT INTO enduserdevicemap (fkenduser, fkdevice, tkuserassociation)
            VALUES ('{userpkid}', '{csfpkid}', '1')
        </sql>
    </ns:executeSQLUpdate>
    """
    root = APICall(build_payload(axl_body), headers)
    if root is not None and root.xpath("//ns:executeSQLUpdateResponse/return/rowsUpdated/text()", namespaces=ns)[0] == "1":
        print(f"Successfully associated device {csfpkid} with {userid}")
    else:
        # This could fail if the association already exists, which is often okay.
        print(f"Could not associate device {csfpkid} with {userid}. (Note: It may already be associated).")

# --- Main Execution Logic ---

if __name__ == "__main__":
    try:
        auth_headers = login()
    except Exception as e:
        print(f"An error occurred during login: {e}")
        sys.exit(1) # Exit if login fails
    while True:
        os.system('cls')
        print("1. Single User Provisioning")
        print("2. Bulk User Provisioning (from CSV)")
        print("3. Quit")
        choice = input("Select option: ")

        if choice == "1":
            os.system('cls')
            userid_input = input("Enter User ID: ")
            userid = sanitize_userid(userid_input)
            if userid:
                process_single_user(userid, auth_headers)
            input("\nPress enter to return to the menu...")

        elif choice == "2":
            os.system('cls')
            try:
                with open(csv_input, mode='r', newline='') as infile:
                    reader = csv.DictReader(infile)
                    user_ids_to_process = [row['userid'] for row in reader]
            except FileNotFoundError:
                print(f"Error: The input file '{csv_input}' was not found.")
                input("\nPress enter to continue...")
                continue
            except KeyError:
                print(f"Error: CSV file must have a column header named 'userid'.")
                input("\nPress enter to continue...")
                continue
            total_users = len(user_ids_to_process)
            success_count = 0
            fail_count = 0

            print(f"Found {total_users} user(s) to process. Starting bulk run...")
            print("-" * 50)

            for i, userid_input in enumerate(user_ids_to_process):
                print(f"--- Processing user {i+1} of {total_users}: '{userid_input.strip()}' ---")
                userid = sanitize_userid(userid_input)
                if not userid:
                    fail_count += 1
                    print("-" * 50)
                    continue
                if process_single_user(userid, auth_headers):
                    success_count += 1
                else:
                    fail_count += 1
                print("-" * 50)

            print("Bulk processing complete.")
            print(f"Summary: {success_count} succeeded, {fail_count} failed.")
            input("\nPress enter to return to the menu...")

        elif choice == "3":
            os.system('cls')
            break
        
        else:
            print("Invalid options, please try again.")
            input("Press enter to continue...")
