#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

email tools

"""

import email
import imaplib
import os

from appscript import app, k
from mactypes import Alias
from pathlib import Path

subject = 'this is a test'
body = 'thanks for playing'
to_recip = ['rsajones94@gmail.com']
attachments = ['/Users/manusdonahue/Documents/Sky/repositories/mri_scan_bot/checkout.txt', '/Users/manusdonahue/Documents/Sky/repositories/mri_scan_bot/bot_alert.txt']


def send_message_with_attachment(subject, body, to_recip, attachment_paths=[]):

    msg = Message(subject=subject, body=body, to_recip=to_recip)

    for l in attachment_paths:
        p = Path(l)
        msg.add_attachment(p)

    #msg.show()
    msg.send()

class Outlook(object):
    def __init__(self):
        self.client = app('Microsoft Outlook')

class Message(object):
    def __init__(self, parent=None, subject='', body='', to_recip=[], cc_recip=[], show_=False):

        if parent is None: parent = Outlook()
        client = parent.client

        self.msg = client.make(
            new=k.outgoing_message,
            with_properties={k.subject: subject, k.content: body})

        self.add_recipients(emails=to_recip, type_='to')
        self.add_recipients(emails=cc_recip, type_='cc')

        if show_: self.show()

    def show(self):
        self.msg.open()
        self.msg.activate()

    def add_attachment(self, p):
        # p is a Path() obj, could also pass string

        p = Alias(str(p)) # convert string/path obj to POSIX/mactypes path

        attach = self.msg.make(new=k.attachment, with_properties={k.file: p})

    def add_recipients(self, emails, type_='to'):
        if not isinstance(emails, list): emails = [emails]
        for email in emails:
            self.add_recipient(email=email, type_=type_)

    def add_recipient(self, email, type_='to'):
        msg = self.msg

        if type_ == 'to':
            recipient = k.to_recipient
        elif type_ == 'cc':
            recipient = k.cc_recipient

        msg.make(new=recipient, with_properties={k.email_address: {k.address: email}})
        
    def send(self):
        msg=self.msg
        msg.send()


###### old email-based bot stuff below

def save_attachment(msg, download_folder="/tmp"):
    """
    Given a message, save its attachments to the specified
    download folder (default is /tmp)

    return: file path to attachment    
    
    From John Paul Hayes on Stack Overflow
    """
    att_path = "No attachment found."
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            continue

        filename = part.get_filename()
        att_path = os.path.join(download_folder, filename)

        if not os.path.isfile(att_path):
            fp = open(att_path, 'wb')
            fp.write(part.get_payload(decode=True))
            fp.close()
    return att_path


def extract_parameters_from_body(body):
    
    the_dict = {'dob':None,
                'artox':None,
                'hct':None,
                'status':None,
                'gender':None,
                'scandate':None,
                'mrid':None,
                'studyid':None}
    
    no_spaces = body.replace(' ', '')
    lowered = no_spaces.lower()
    lines = lowered.split('\n')
    parts = [i.split(':') for i in lines]
    cleaner = [i for i in parts if len(i)==2]
    
    for key,val in cleaner:
        if key in the_dict:
            the_dict[key] = val
            
    return the_dict
    
    
def params_to_processing_call(params):
    pass    



