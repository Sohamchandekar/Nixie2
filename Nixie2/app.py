from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management


# Function to convert Excel to JSON
def excel_to_json(excel_path, json_path):
    df = pd.read_excel(excel_path)

    json_data = []
    for index, row in df.iterrows():
        entry = {
            "name": row['name'],
            "user_id": row['user id'],
            "password": row['password']
        }
        json_data.append(entry)

    with open(json_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


# Function to generate JSON from Excel/CSV for client data
def json_generator(input_file, output_file):
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")

    json_data = {}
    for index, row in df.iterrows():
        project_name = row['project_name']
        json_data[project_name] = {
            "rera": row['rera'],
            "client": row['client_name'],
            "email": row['email'],
            "phone": row['phone'],
            "user": row['user_id'],
            "password": row['password'],
            "admin_access": row['admin_access'],
            "general_access": row['general_access']
        }

    with open(output_file, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


# Convert login_credentials.xlsx to login_credentials.json
login_excel_path = 'uploads/logincredi/login_credentials.xlsx'
login_json_path = 'uploads/logincredi/login_credentials.json'
excel_to_json(login_excel_path, login_json_path)

# Convert client_data.xlsx to ProjectsCheckData.json
client_excel_path = 'uploads/clientdata/client_data.xlsx'
client_json_path = 'uploads/clientdata/ProjectsCheckData.json'
json_generator(client_excel_path, client_json_path)

# Load user data from login_credentials.json
with open(login_json_path, 'r') as f:
    user_data = json.load(f)

# Load client data from ProjectsCheckData.json
with open(client_json_path, 'r') as f:
    client_data = json.load(f)


# Route for handling search requests
@app.route('/search')
def search():
    query = request.args.get('query').lower().strip()

    filtered_data = {}
    for project_name, details in client_data.items():
        if query in project_name.lower():
            filtered_data[project_name] = details

    return jsonify(filtered_data)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['user_id']
    user_password = request.form['user_password']

    for user in user_data:
        if user['user_id'] == user_id and user['password'] == user_password:
            session['user_id'] = user_id
            session['user_password'] = user_password
            session['logged_in_user'] = user['name']
            return redirect(url_for('data_viewing'))

    flash('Invalid Credentials')
    return redirect(url_for('index'))


@app.route('/dataviewing')
def data_viewing():
    logged_in_user = session.get('logged_in_user')

    filtered_data = {}
    for project_name, details in client_data.items():
        admin_access = details.get('admin_access', [])
        general_access = details.get('general_access', [])

        if logged_in_user in admin_access or logged_in_user in general_access:
            filtered_data[project_name] = details

    num_visible_projects = len(filtered_data)

    return render_template('dataviewing.html', client_data=filtered_data, num_projects=num_visible_projects)


@app.route('/filter_projects', methods=['POST'])
def filter_projects():
    selected_project = request.form.get('selected_project')
    filtered_data = {name: details for name, details in client_data.items() if name.lower() == selected_project.lower()}

    table_rows = ''
    for project_name, details in filtered_data.items():
        table_rows += f'''
        <tr>
            <td>{project_name}</td>
            <td>{details['rera']}</td>
            <td>{details['client']}</td>
            <td>{details['email']}</td>
            <td>{details['phone']}</td>
            <td>{details['user']}</td>
            <td class="masked">*******</td>
            <td><button class="auto-login-btn" data-user="{details['user']}" data-password="{details['password']}">Auto Login</button></td>
        </tr>
        '''
    return table_rows


@app.route('/auto_login', methods=['POST'])
def auto_login():
    user_id = request.form['user_id']
    password = request.form['password']

    login_to_maharerait(user_id, password)

    return jsonify({'status': 'success'})


def login_to_maharerait(user_id, password):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Disable password saving
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver_path = 'static/chromedriver.exe'
    service = Service(driver_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get("https://maharerait.mahaonline.gov.in/")

        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="UserName"]'))
        )
        username_field.send_keys(user_id)

        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Password"]'))
        )
        password_field.send_keys(password)

        print("User ID and Password entered. Please complete the CAPTCHA and login manually.")

        WebDriverWait(driver, 600).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="non_existent_element"]'))
        )

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        driver.quit()


# Helper function to classify and save the file
def classify_and_save_file(file):
    df = pd.read_excel(file)
    if set(['name', 'user id', 'password']).issubset(df.columns):
        file_path = 'uploads/logincredi/login_credentials.xlsx'
        df.to_excel(file_path, index=False)
        excel_to_json(file_path, 'uploads/logincredi/login_credentials.json')
    elif set(['rera', 'project_name', 'client_name', 'email', 'phone', 'user_id', 'password', 'admin_access',
              'general_access']).issubset(df.columns):
        file_path = 'uploads/clientdata/client_data.xlsx'
        df.to_excel(file_path, index=False)
        json_generator(file_path, 'uploads/clientdata/ProjectsCheckData.json')
    else:
        raise ValueError("File format not recognized")


@app.route('/adminupload', methods=['GET', 'POST'])
def admin_upload():
    if session.get('logged_in_user') != 'admin':
        flash('Only admin users are allowed to upload files.')
        return redirect(url_for('data_viewing'))

    if request.method == 'POST':
        # Check if the file is present in the request
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        # If the user does not select a file, browser submits an empty file without a filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        try:
            classify_and_save_file(file)
            flash('File uploaded and processed successfully')
        except ValueError as e:
            flash(str(e))

        return redirect(url_for('data_viewing'))

    return render_template('adminupload.html')



