import pymysql
from tabulate import tabulate
import os
from getpass import getpass
import hashlib
import uuid

def display_logo():
    # Display logo.txt. On Windows, 'type' is used (or fallback to Python file I/O).
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
    # Verify that the email is unique by checking the user table.
    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    if cursor.fetchone() is not None:
        print("An account with this email already exists. Please log in instead or use a different email.\n")
        return None

    password = getpass("Enter your password: ")
    confirm_password = getpass("Confirm your password: ")
    if password != confirm_password:
        print("Passwords do not match. Please try again.\n")
        return None

    first_name = input("Enter your first name: ").strip()
    last_name = input("Enter your last name: ").strip()
    phone = input("Enter your phone number: ").strip()

    # Generate a salt and hash the password using SHA-256.
    salt = uuid.uuid4().hex
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()

    # Insert authentication record into user_auth (using email as username).
    cursor.execute(
        "INSERT INTO user_auth (username, password_hash, salt) VALUES (%s, %s, %s)",
        (email, password_hash, salt)
    )
    auth_id = cursor.lastrowid

    # Insert into the user table.
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

    # Retrieve the user record using the email.
    cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
    user_record = cursor.fetchone()
    if user_record is None:
        print("No account found with that email. Please sign up first.\n")
        return None

    # The user table is expected to have: user_id, auth_id, first_name, last_name, phone, email.
    auth_id = user_record[1]
    cursor.execute("SELECT * FROM user_auth WHERE auth_id = %s", (auth_id,))
    auth_record = cursor.fetchone()
    stored_password_hash = auth_record[2]
    salt = auth_record[3]
    
    # Hash the provided password with the retrieved salt.
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    if password_hash == stored_password_hash:
        print("Login successful!\n")
        return email
    else:
        print("Incorrect password. Please try again.\n")
        return None

def main_menu(cursor, conn, authenticated_email):
    logged_in = True
    # These column headers are used when displaying listings.
    columns = ['street number', 'street name', 'city', 'state', 'zip', 
               'room number', 'square foot', 'price', 'bedrooms']
    while logged_in:
        print("\nMain Menu:")
        usr_choice = input(
            "1: View all listings\n" +
            "2: Filter listings\n" +
            "3: Logout\n" +
            "4: Disconnect and exit the application\n" +
            "Please select your choice: "
        ).strip()

        if usr_choice == '1':
            print('\nListings:')
            cursor.execute("SELECT * FROM property")
            output = cursor.fetchall()
            if output:
                table = [list(item) for item in output]
                term_columns = os.get_terminal_size().columns
                print(tabulate(table, headers=columns, tablefmt="grid", maxcolwidths=[None, None, term_columns // 3]))
            else:
                print("No listings available.\n")
        elif usr_choice == '2':
            print('\nFilter Listings:')
            filter_choice = ''
            while filter_choice not in ["1", "2"]:
                filter_choice = input("1: Sort by column\n2: Filter by value\nPlease select your filter: ").strip()
                if filter_choice not in ["1", "2"]:
                    print("Please enter a valid value!\n")
            if filter_choice == '1':
                col = ''
                while col not in columns:
                    col = input(
                        "Available columns: street number, street name, city, state, zip, room number, square foot, price, bedrooms\n" +
                        "Select column you want to sort by: "
                    ).lower()
                    if col not in columns:
                        print("Column does not exist, please enter a valid value!\n")
                sort_order = ''
                while sort_order not in ['1', '2']:
                    sort_order = input("1: low to high\n2: high to low\nPlease select sort order: ").strip()
                sort_order = 'asc' if sort_order == '1' else 'desc'
                cursor.execute(f"SELECT * FROM property ORDER BY {col} {sort_order}")
                output = cursor.fetchall()
                if output:
                    table = [list(item) for item in output]
                    term_columns = os.get_terminal_size().columns
                    print(tabulate(table, headers=columns, tablefmt="grid", maxcolwidths=[None, None, term_columns // 3]))
                else:
                    print("No listings available.\n")
            elif filter_choice == '2':
                # This branch can be extended to filter by custom values.
                print("Filter by value option not implemented yet.\n")
        elif usr_choice == '3':
            print("Logging out...\n")
            logged_in = False
        elif usr_choice == '4':
            print("Disconnecting from the database and closing the application...\n")
            conn.close()
            exit(0)
        else:
            print("Error! Please enter a valid choice!\n")
    return

def main():
    # Display the logo at the start.
    display_logo()

    # Database connection loop.
    connected = False
    while not connected:
        db_username = input("Enter username for MySQL server: ")
        db_pw = getpass("Enter the password for MySQL server: ")
        print()
        try:
            conn = pymysql.connect(
                host="localhost",
                user=db_username,
                password=db_pw,
                db="rental_system"
            )
            connected = True
        except pymysql.Error as ex:
            print("Username or password is invalid, please enter again.\n")
    cur = conn.cursor()
    
    # Outer loop for authentication, so a user can log out and a new user can log in.
    while True:
        authenticated_email = None
        while authenticated_email is None:
            print("Welcome! Please select an option:")
            print("1: Signup")
            print("2: Login")
            option = input("Enter your choice (1 or 2): ").strip()
            if option == '1':
                authenticated_email = signup(cur, conn)
            elif option == '2':
                authenticated_email = login(cur)
            else:
                print("Invalid option. Please select 1 or 2.\n")
        print(f"Welcome, {authenticated_email}!\n")
        main_menu(cur, conn, authenticated_email)
        # When main_menu returns, the user has logged out.
        print("You have been logged out.\n")

if __name__ == "__main__":
    main()
