import pymysql
from tabulate import tabulate
import os
from getpass import getpass
import hashlib
import uuid

def display_logo():
    # Display the logo. For Windows, use 'type' instead of 'cat'
    try:
        os.system("type logo.txt")
    except Exception:
        try:
            with open("logo.txt", "r") as file:
                print(file.read())
        except Exception:
            print("Logo not available.")

def signup(cursor, conn):
    print("\n=== Signup ===")
    email = input("Enter your email: ").strip()
    # Check if the email already exists in the user table
    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    if cursor.fetchone() is not None:
        print("An account with this email already exists. Please log in instead, or use a different email.\n")
        return None

    password = getpass("Enter your password: ")
    confirm_password = getpass("Confirm your password: ")
    if password != confirm_password:
        print("Passwords do not match. Please try again.\n")
        return None

    first_name = input("Enter your first name: ").strip()
    last_name = input("Enter your last name: ").strip()
    phone = input("Enter your phone number: ").strip()

    # Generate a salt and hash the password
    salt = uuid.uuid4().hex
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    
    # Insert into user_auth table (using email as username)
    cursor.execute(
        "INSERT INTO user_auth (username, password_hash, salt) VALUES (%s, %s, %s)",
        (email, password_hash, salt)
    )
    auth_id = cursor.lastrowid

    # Insert the user record into the user table
    cursor.execute(
        "INSERT INTO user (auth_id, first_name, last_name, phone, email) VALUES (%s, %s, %s, %s, %s)",
        (auth_id, first_name, last_name, phone, email)
    )
    conn.commit()
    print("Signup successful! You can now log in.\n")
    return email

def login(cursor):
    print("\n=== Login ===")
    email = input("Enter your email: ").strip()
    password = getpass("Enter your password: ")
    
    # Retrieve user record by email
    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    user_record = cursor.fetchone()
    if user_record is None:
        print("No account found with that email. Please sign up first.\n")
        return None

    # user table columns: user_id, auth_id, first_name, last_name, phone, email
    auth_id = user_record[1]
    cursor.execute("SELECT * FROM user_auth WHERE auth_id = %s", (auth_id,))
    auth_record = cursor.fetchone()
    # user_auth columns: auth_id, username, password_hash, salt, ...
    stored_password_hash = auth_record[2]
    salt = auth_record[3]
    
    # Hash the provided password together with the salt retrieved from the database
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    if password_hash == stored_password_hash:
        print("Login successful!\n")
        return email
    else:
        print("Incorrect password. Please try again.\n")
        return None

# Start of the main script

# Display the logo
display_logo()

# Connect to the MySQL database (database: rental_system)
connected = False
while not connected:
    db_username = input('Enter username for MySQL server: ')
    db_pw = getpass('Enter the password for MySQL server: ')
    print('\n')
    try:
        conn = pymysql.connect(
            host='localhost',
            user=db_username,
            password=db_pw,
            db='rental_system',
        )
        connected = True
    except pymysql.Error as ex:
        print('Username or password is invalid, please enter again.\n')

cur = conn.cursor()

# User authentication: signup or login flow
authenticated_email = None
while authenticated_email is None:
    print("Welcome! Please select an option:")
    print("1. Signup")
    print("2. Login")
    option = input("Enter your choice (1 or 2): ").strip()
    if option == '1':
        authenticated_email = signup(cur, conn)
    elif option == '2':
        authenticated_email = login(cur)
    else:
        print("Invalid option. Please select 1 or 2.\n")

print(f"Welcome, {authenticated_email}!")

# After authentication, present the main rental system options
choice = 0
columns = ['street number', 'street name', 'city', 'state', 'zip', 'room number', 'square foot', 'price', 'bedrooms']

while choice != 3:
    usr_choice = input('1: View all listings\n' +
                       '2: Filter listings\n' +
                       '3: Disconnect from the database and close the application\n' +
                       'Please select your choice: ')
    
    if usr_choice == '3':
        conn.close()
        choice = 3
    elif usr_choice == '1':
        print('\n')
        cur.execute("SELECT * FROM property")
        output = cur.fetchall()
        table = [list(item) for item in output]
        term_columns = os.get_terminal_size().columns
        print(tabulate(table, headers=columns, tablefmt="grid", maxcolwidths=[None, None, term_columns // 3]))
        print('\n')
    elif usr_choice == '2':
        print('\n')
        filter_choice = ''
        while filter_choice not in ["1", "2"]:
            filter_choice = input('1. Sort by column\n2. Filter by value\nPlease select your filter: ')
            if filter_choice not in ["1", "2"]:
                print('Please enter a valid value!\n')
        if filter_choice == '1':
            print('\n')
            col = ''
            asc = ''
            while col not in columns:
                col = input('Name of columns: street number, street name, city, state, zip, room number, square foot, price, bedrooms\nSelect column you want to sort by: ').lower()
                if col not in columns:
                    print('Column does not exist, please enter a valid value!\n')
            print('\n')
            while asc not in ['1', '2']:
                asc = input('1. low to high\n2. high to low\nPlease select how you want to sort: ')
            asc = 'asc' if asc == '1' else 'desc'
            print('\n')
            cur.execute(f"SELECT * FROM property ORDER BY {col} {asc}")
            output = cur.fetchall()
            table = [list(item) for item in output]
            term_columns = os.get_terminal_size().columns
            print(tabulate(table, headers=columns, tablefmt="grid", maxcolwidths=[None, None, term_columns // 3]))
            print('\n')
    else:
        print("Error! Please enter a valid choice!\n")
