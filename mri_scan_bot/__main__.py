#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Main sequence for the scan bot

"""

import os
import sys
import ssl



from imapclient import IMAPClient

HOST = 'imap-mail.outlook.com'

ssl_context = ssl.create_default_context()
#ssl_context.load_cert_chain("/path/to/ssl_certificate.crt")

#USERNAME = ''
#PASSWORD = ''

#with IMAPClient(HOST, ssl_context=ssl_context) as server:
with IMAPClient(HOST, ssl=False) as server:
    server.login(USERNAME, PASSWORD)
    #server.select_folder('INBOX', readonly=True)

    #messages = server.search('UNSEEN')
    #for uid, message_data in server.fetch(messages, 'RFC822').items():
        #email_message = email.message_from_bytes(message_data[b'RFC822'])
        #print(uid, email_message.get('From'), email_message.get('Subject'))