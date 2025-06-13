# CUCM Jabber/CSF Provisioning Tool

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/github/license/cadencejames/Jabber_CUCM)
![Last Commit](https://img.shields.io/github/last-commit/cadencejames/Jabber_CUCM)
![Contributors](https://img.shields.io/github/contributors/cadencejames/Jabber_CUCM)

---

This repository contains a Python script designed to automate the provisioning of Cisco Jabber Client Services Framework (CSF) devices for users in a Cisco Unified Communications Manager (CUCM) environment. The tool uses the AXL SOAP API to perform administrative tasks, reducing manual effort and ensuring consistency.

It supports both single-user provisioning and bulk provisioning from a CSV file.

## Key Features

-   **Secure Credential Entry**: Prompts for a username and password at runtime using a hidden password field, avoiding the need to store credentials in the script.
-   **User Information Retrieval**: Fetches user details like full name and phone number from CUCM.
-   **Automated CSF Device Management**:
    -   Checks if a CSF device already exists for a user.
    -   Creates a new CSF device (`Cisco Unified Client Services Framework`) if one does not exist.
-   **Directory Group Management**: Ensures users are added to a predefined list of essential directory groups.
-   **Device Association**: Associates the newly created or existing CSF device with the end user account.
-   **Two Modes of Operation**:
    -   **Single User Mode**: Provision one user at a time via an interactive prompt.
    -   **Bulk Mode**: Provision multiple users automatically by reading from a CSV file.

---

## Prerequisites

Before running this script, ensure you have the following:

1.  **Python 3.7+**: The script uses f-strings and other modern Python features.
2.  **CUCM AXL API Access**: An Application User must be configured in CUCM with a role that has AXL API access rights. At a minimum, the role needs permissions to read and update end users, and read/write/update phones. The "Standard AXL API Access" role is often sufficient.
3.  **Network Connectivity**: The machine running the script must have network access to the CUCM publisher's AXL port (typically TCP/8443).

---

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/cadencejames/Jabber_CUCM.git
    cd Jabber_CUCM
    ```

2.  **Create a Python virtual environment (recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the required Python libraries:**
    The script depends on the `requests` and `lxml` libraries. Install them using pip:
    ```bash
    pip install -r requirements.txt
    ```
    *(If a `requirements.txt` file is not present, create one with the following content or install manually)*
    ```
    # requirements.txt
    requests
    lxml
    ```
    Manual install: `pip install requests lxml`

---

## Configuration

Before running the script, you must edit the main Python file (`provision_csf.py`) to configure a few variables at the top:

-   **`url`**: Set this to the AXL endpoint of your CUCM publisher.
    ```python
    # Example
    url = "https://cucm-pub.your-domain.com:8443/axl/"
    ```

-   **`csv_input`**: The name of the CSV file for bulk operations. The default is `csv_input.csv`.

-   **`dirgroups`**: This is a critical step. You must replace the placeholder text with the actual **pkid** values of the directory groups you want users to be added to.
    > **How to find the pkid?** A pkid is a unique identifier (UUID) for an object in the CUCM database. You can find it by using an AXL query tool like Postman or by carefully inspecting the URL when viewing an object in the CUCM admin interface.

    ```python
    # Replace these placeholder UUIDs with real ones from your CUCM
    dirgroups = [
        "c3d9b4a1-0e9f-4b1a-8c8a-7f1b2c3d4e5f", # Standard End User Group pkid
        "d4e0c5b2-1f0a-5c2b-9d9b-8g2c3d4e5f6g", # Another Group pkid
        # ... add all required group pkids here
    ]
    ```

---

## Usage

Run the script from your terminal:

```bash
python provision_csf.py
```

You will be prompted to log in with your CUCM Application User credentials. After a successful login, you will see the main menu:

```
1. Single User Provisioning
2. Bulk User Provisioning (from CSV)
3. Quit
Select option:
```

### Option 1: Single User Provisioning

-   Select `1` and press Enter.
-   Enter the User ID of the user you wish to provision.
-   The script will perform all the necessary actions for that user and display the results.

### Option 2: Bulk User Provisioning

-   Select `2` and press Enter.
-   The script will automatically read the user IDs from the configured CSV file (`csv_input.csv` by default) and process each one sequentially.
-   A summary of successful and failed users will be displayed at the end.

#### CSV File Format

For bulk mode, create a CSV file with the name specified in the `csv_input` variable. The file **must** contain a header row with the column name `userid`.

**Example `csv_input.csv`:**

```csv
userid
jdoe
ssmith
mjones
```

---

## Disclaimer

This script makes direct changes to your Cisco Unified Communications Manager environment via the AXL API. It is highly recommended to **test this script in a non-production lab environment** before using it in a live production system. The author of this script is not responsible for any damage, data loss, or service interruption caused by its use. **Use at your own risk.**
