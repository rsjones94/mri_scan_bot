#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Main sequence for the scan bot

"""

import os
import sys
import ssl
import email
import smtplib
import re
import datetime

from imapclient import IMAPClient
import yagmail

from email_tools import save_attachment

creds = '/Users/skyjones/Documents/repositories/donahueprocessing_app_pw.txt'
home = os.path.dirname(os.path.dirname(__file__))
bin_folder = os.path.join(home,'bin')

dl_folder = bin_folder
#dl_folder = '/Users/skyjones/Documents/repositories'


with open(creds) as c:
    words = c.read()
    lines = words.split('\n')
    
#HOST = 'imap-mail.outlook.com'
HOST = 'imap.gmail.com'

#ssl_context = ssl.create_default_context()
#ssl_context.load_cert_chain("/path/to/ssl_certificate.crt")

USERNAME = lines[0]
PASSWORD = lines[1]

yag = yagmail.SMTP(USERNAME,PASSWORD)

days_before = 14 # messages more than days_before days old will be deleted after processing
before_date = (datetime.date.today() - datetime.timedelta(days_before)).strftime("%d-%b-%Y")

#with IMAPClient(HOST, ssl_context=ssl_context) as server:
with IMAPClient(HOST, ssl=True) as server:
    server.login(USERNAME, PASSWORD)
    server.select_folder('INBOX', readonly=False)

    
    #messages = server.search('NOT DELETED')
    messages = server.search('NOT SEEN')
    process_requests, info_requests = [], []
    all_uids = []
    for uid, message_data in server.fetch(messages, 'RFC822').items():
        email_message = email.message_from_bytes(message_data[b'RFC822'])
        subj = email_message.get('Subject')
        sender = email_message.get('From')
        print(uid, sender, subj)
        
        if 'process' in subj.lower():
            process_requests.append((uid,email_message))
        elif 'info' in subj.lower():
            info_requests.append((uid,email_message))
            
        all_uids.append(uid)
        

        
    success_uids_info = []
    success_uids_jobs = []  
    
    acknowledgement = os.path.join(bin_folder, 'acknowledgement.txt')
    info = os.path.join(bin_folder, 'info.txt')     
    
    for uid, email_message in info_requests:
        #email_message = email.message_from_bytes(message_data[b'RFC822'])
        sender = email_message.get('From')
        subj = email_message.get('Subject')
        
        sender_adr = re.findall(r'\<.*?\>', sender)[0][1:-1]
        
        print(f'Fulfilling info request from {sender} ({subj})')
        
        with open(info) as fp:
            # Create a text/plain message
            msg = fp.read()
        
        yag.send(sender_adr, 'Your DIP info request', msg)
        
        success_uids_info.append(uid)
    
    #server.delete_messages(success_uids_info)
    
    #sys.exit()
    
    queued_senders, queued_jobs = [], []
    for uid, email_message in process_requests:
        #email_message = email.message_from_bytes(message_data[b'RFC822'])
        sender = email_message.get('From')
        subj = email_message.get('Subject')
        
        sender_adr = re.findall(r'\<.*?\>', sender)[0][1:-1]
        
        print(f'Processing a request from {sender} ({subj})')
        
        body_parts = []
        for part in email_message.walk():
           if part.get_content_type() == "text/plain":
              #print(part)
              body_parts.append(str(part))
        body = '\n'.join(body_parts)
        
        save_attachment(msg=email_message, download_folder=dl_folder)
        
        with open(acknowledgement) as fp:
            # Create a text/plain message
            msg = fp.read()
        
        yag.send(sender_adr, f'Processing request acknowledgement (re:{subj})', msg)
        
        job_params = None
        
        queued_senders.append(sender_adr)
        queued_senders.append(job_params)
        
    # wrap up
    server.add_flags(all_uids, ['SEEN'])
    
    old_messages = server.search(f'BEFORE {before_date}')
    server.delete_messages(old_messages)



