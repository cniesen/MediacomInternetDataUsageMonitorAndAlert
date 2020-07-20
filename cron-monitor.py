#!/usr/bin/env python3

#  Mediacom Internet Data Usage Monitor & Alert

#  Copyright (C) 2020  Claus Niesen
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.


import smtplib
import ssl
import sqlite3
import json
import time
import datetime

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import logging
logging.basicConfig(level=logging.ERROR)

### User Configurations ###
#
# Your username and password at Mediacom
username = 'username'
password = 'password'
# SMTP server address
smtpServerUrl = 'smtp.example.com'
# SMTP server port number
smtpServerPort = '465'
# Username for SMTP server
smtpUsername = 'username'
# Password for SMTP server
smtpPassword = 'password'
# Email address that should receive alerts
emailAddress = 'user@example.com'
# Location of chromedriver
chromedriver = '/usr/bin/chromedriver'


def create_db_connection():
    conn = sqlite3.connect('MediacomUsage.db')
    return conn


def read_previous_usage_from_database(conn):
    cur = conn.cursor()
    cur.execute('SELECT MAX(DATETIME), TOTAL, UPLOAD, DOWNLOAD, ALLOWANCE, BILLING_PERIOD_START, BILLING_PERIOD_END, ALLOWANCE_TO_DAY FROM USAGE')
    result = cur.fetchone()
    if result is None:
        return {
            'datetime': '',
            'total': 0,
            'upload': 0,
            'download': 0,
            'allowance': 0,
            'billing_period_start': '',
            'billing_period_end': '',
            'allowance_to_day': 0
        }
    else:
        return {
            'datetime': result[0],
            'total': result[1],
            'upload': result[2],
            'download': result[3],
            'allowance': result[4],
            'billing_period_start': result[5],
            'billing_period_end': result[6],
            'allowance_to_day': result[7]
        }


def write_new_usage_to_database(conn, usage):
    cur = conn.cursor()
    sql = 'INSERT INTO USAGE (DATETIME, TOTAL, UPLOAD, DOWNLOAD, ALLOWANCE, BILLING_PERIOD_START, BILLING_PERIOD_END, ALLOWANCE_TO_DAY) VALUES (?,?,?,?,?,?,?,?)'
    values = (usage['datetime'], usage['total'], usage['upload'], usage['download'], usage['allowance'], usage['billing_period_start'], usage['billing_period_end'], usage['allowance_to_day'])
    cur.execute(sql, values)
    conn.commit()
    return cur.lastrowid


def pad_with_zero_to_two_characters(text):
    if len(text) == 1:
        return '0' + text
    else:
        return text

# octet (aka bytes) to GB: 1GB = 1024 * 1024 * 1024 bytes
def octets_to_gb(text):
    return float(text) / 1073741824


def retrieve_current_usage_from_mediacom():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1440, 900')
    chrome_options.add_argument('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36')
    driver = webdriver.Chrome(options = chrome_options, executable_path = chromedriver)

    driver.get('https://support.mediacomcable.com')
    login_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//button[text()="MEDIACOM ID"]'))
    )
    time.sleep(1)
    login_button.click()

    # Login Page
    if not (driver.current_url.startswith("https://sso.mediacomcable.com")):
        print("Unexpected website: " + driver.current_url)
        exit(-5)
    username_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//input[@name="pf.username"]'))
    )
    username_input.clear()
    username_input.send_keys(username)

    password_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//input[@name="pf.pass"]'))
    )
    password_input.clear()
    password_input.send_keys(password)
    login_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//button[text()="Sign In"]'))
    )
    time.sleep(1)
    login_button.click()

    # Wait for request that we're interested in
    request = driver.wait_for_request('/api/api/InternetUsage/50014', 120)

    body = json.loads(request.response.body)

    print("Debug: Billing Periods received (using last one)")
    periods = body['PeriodUsages']
    for period in periods:
        print("  " + period['BillingPeriod'])

    usage = periods[len(periods) - 1]
    driver.quit()

    as_of_datetime = datetime.datetime.strptime(usage['AsOfDate'], '%m/%d/%Y %H:%M')
    billing_period_start = datetime.datetime.strptime(usage['BillingPeriod'].split(' - ')[0], '%b %d, %Y')
    billing_period_end = datetime.datetime.strptime(usage['BillingPeriod'].split(' - ')[1], '%b %d, %Y')
    days_in_billing_period = (billing_period_end.date() - billing_period_start.date()).days + 1
    days_into_billing_period = (as_of_datetime.date() - billing_period_start.date()).days + 1
    allowance = octets_to_gb(usage['Quota'])
    allowance_to_day = allowance / days_in_billing_period * days_into_billing_period
    return {
        'datetime': as_of_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'total': round(octets_to_gb(usage['TotalOctets']), 1),
        'upload': round(octets_to_gb(usage['TotalUpOctets']), 1),
        'download': round(octets_to_gb(usage['TotalDnOctets']), 1),
        'allowance': round(allowance, 1),
        'billing_period_start': billing_period_start.strftime('%Y-%m-%d'),
        'billing_period_end': billing_period_end.strftime('%Y-%m-%d'),
        'allowance_to_day': round(allowance_to_day)
    }


def email_high_usage_alert(currentUsage, previousUsage):
    message = 'Subject: Mediacom Data Usage Warning\n' \
              + 'Data usage is higher than expected\n\n' \
              + 'Previous usage: ' + str(previousUsage) + '\n'\
              + 'Current usage : ' + str(currentUsage) + '\n'
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtpServerUrl, smtpServerPort, context=context) as server:
        server.login(smtpUsername, smtpPassword)
        server.sendmail(emailAddress, emailAddress, message)


con = create_db_connection()
previousUsage = read_previous_usage_from_database(con)
currentUsage = retrieve_current_usage_from_mediacom()
print("Debug previous usage: ", previousUsage)
print("Debug current usage: ", currentUsage)
if currentUsage['datetime'] == previousUsage['datetime']:
    print('Debug Old data retrieved')
else:
    write_new_usage_to_database(con, currentUsage)
    email_high_usage_alert(currentUsage, previousUsage)
