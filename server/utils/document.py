import pandas as pd
from loguru import logger
from typing import List
from model.model import User
import os

def read_xlsx_file(file_path: str) -> List[User]:
    """
    Read Excel file and extract user data (name, email, phone number)
    Returns a list of User objects
    """
    try:
        # Read the Excel file
        raw_data = pd.read_excel(file_path)
        logger.info(f"Successfully read xlsx file: {file_path}")
        
        # List to store User objects
        users = []
        
        # Expected column names (case-insensitive)
        name_columns = ['name', 'full_name', 'fullname', 'user_name', 'username']
        first_name_columns = ['first_name', 'firstname', 'fname', 'first']
        last_name_columns = ['last_name', 'lastname', 'lname', 'last']
        email_columns = ['email', 'email_address', 'e_mail']
        phone_columns = ['phone', 'phone_number', 'mobile', 'mobile_number', 'contact']
        
        # Find the actual column names (case-insensitive)
        name_col = None
        first_name_col = None
        last_name_col = None
        email_col = None
        phone_col = None
        
        for col in raw_data.columns:
            col_lower = col.lower().strip()
            if col_lower in name_columns and name_col is None:
                name_col = col
            elif col_lower in first_name_columns and first_name_col is None:
                first_name_col = col
            elif col_lower in last_name_columns and last_name_col is None:
                last_name_col = col
            elif col_lower in email_columns and email_col is None:
                email_col = col
            elif col_lower in phone_columns and phone_col is None:
                phone_col = col
        
        # Check if we found required columns
        missing_columns = []
        if name_col is None and (first_name_col is None or last_name_col is None):
            missing_columns.append("name (or first_name + last_name)")
        if email_col is None:
            missing_columns.append("email")
        if phone_col is None:
            missing_columns.append("phone")
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}. Available columns: {list(raw_data.columns)}")
        
        # Process each row
        for index, row in raw_data.iterrows():
            try:
                # Extract data and clean it
                if name_col:
                    # Single name column
                    name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                else:
                    # Separate first and last name columns
                    first_name = str(row[first_name_col]).strip() if pd.notna(row[first_name_col]) else ""
                    last_name = str(row[last_name_col]).strip() if pd.notna(row[last_name_col]) else ""
                    name = f"{first_name} {last_name}".strip()
                
                email = str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
                phone = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
                
                # Format phone number with +91 prefix
                if phone:
                    # Check if +91 is already present
                    if phone.startswith('+91'):
                        # Already has +91, just clean up any extra characters
                        phone = '+91' + phone[3:].replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                    else:
                        # Remove any existing country code or special characters
                        phone_clean = phone.replace('+91', '').replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                        
                        # Add +91 prefix if not already present
                        if not phone_clean.startswith('91') and len(phone_clean) == 10:
                            phone = f"+91{phone_clean}"
                        elif phone_clean.startswith('91') and len(phone_clean) == 12:
                            phone = f"+{phone_clean}"
                        else:
                            phone = phone_clean  # Keep original if doesn't match expected format
                
                # Skip rows with empty required fields
                if not name or not email or not phone:
                    logger.warning(f"Skipping row {index + 1}: Missing required data (name: {name}, email: {email}, phone: {phone})")
                    continue
                
                # Create User object
                user = User(
                    name=name,
                    email=email,
                    phone=phone
                )
                users.append(user)
                
            except Exception as e:
                logger.error(f"Error processing row {index + 1}: {e}")
                continue
        if os.path.exists(file_path):
            logger.info(f"Removing file: {file_path}")
            os.remove(file_path)
        logger.info(f"Successfully extracted {len(users)} users from Excel file")
        return users
        
    except Exception as e:
        logger.error(f"Error reading xlsx file: {e}")
        raise e


