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


import re
import requests
import smtplib
import ssl
import sqlite3


### User Configurations ###
#
# Your customer id / account number with Mediacom
#mediacomCustomerId = '1234567890'
# SMTP server address 
smtpServerUrl = 'smtp.example.com'
# SMTP server port number
smtpServerPort = '465'
# Username for SMTP server
smtpUsername = 'user'
# Password for SMTP server
smtpPassword = 'password'
# Email address that should receive alerts
emailAddress = 'user@example.com'

def create_db_connection():
    conn = sqlite3.connect('MediacomUsage.db')
    return conn


def read_previous_usage_from_database(conn):
    cur = conn.cursor()
    cur.execute('SELECT MAX(DATETIME), TOTAL, UPLOAD, DOWNLOAD FROM USAGE ')
    result = cur.fetchall()
    if result.count == 0:
        return {
            'datetime': '',
            'total': 0,
            'upload': 0,
            'download': 0
        }
    else:
        return {
            'datetime': result[0][0],
            'total': result[0][1],
            'upload': result[0][2],
            'download': result[0][3]
        }


def write_new_usage_to_database(conn, usage):
    cur = conn.cursor()
    sql = 'INSERT INTO USAGE (DATETIME, TOTAL, UPLOAD, DOWNLOAD) VALUES (?,?,?,?)'
    values = (usage['datetime'], usage['total'], usage['upload'], usage['download'])
    cur.execute(sql, values)
    conn.commit()
    return cur.lastrowid

def pad_with_zero_to_two_characters(text):
    if len(text) == 1:
        return '0' + text
    else:
        return text


def retrieve_current_usage_from_mediacom():
    result = requests.get('http://50.19.209.155/um/usage.action?custId=' + mediacomCustomerId)
    datetimeMatche = re.search('by Mediacom as of ([0-9]{1,2})\/([0-9]{1,2})\/([0-9]{4}) ([0-9]{1,2}):([0-9]{2}). Note', result.text)
    month = pad_with_zero_to_two_characters(datetimeMatche.group(1))
    day = pad_with_zero_to_two_characters(datetimeMatche.group(2))
    year = datetimeMatche.group(3)
    hour = pad_with_zero_to_two_characters(datetimeMatche.group(4))
    minute = pad_with_zero_to_two_characters(datetimeMatche.group(5))
    total = re.search('usageCurrentData.push\((.+?)\)', result.text).group(1)
    upload = re.search('usageCurrentUpData.push\((.+?)\)', result.text).group(1)
    download = re.search('usageCurrentDnData.push\((.+?)\)', result.text).group(1)
    return {
        'datetime': year + '-' + month + '-' + day + ' ' + hour + ':' + minute + ':00',
        'total': float(total),
        'upload': float(upload),
        'download': float(download)
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

