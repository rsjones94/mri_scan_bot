#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

email tools

"""

import email
import imaplib
import os


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
