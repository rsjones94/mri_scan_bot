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
import zipfile
import shutil
import glob
import datetime

from imapclient import IMAPClient
import yagmail

import email_tools as et

creds = '/Users/skyjones/Documents/repositories/donahueprocessing_app_pw.txt'
home = os.path.dirname(os.path.dirname(__file__))
bin_folder = os.path.join(home,'bin')

dl_folder = os.path.join(bin_folder, 'temp_working') # neither dl_folder nor workspace should exist
workspace = os.path.join(bin_folder, 'workspace') #
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
        print(f'UID, sender, subject: {uid}, {sender}, {subj}')
        
        if 'process' in subj.lower():
            process_requests.append((uid,email_message))
        elif 'info' in subj.lower():
            info_requests.append((uid,email_message))
            
        all_uids.append(uid)
        
    print('\n')
        
    success_uids_info = []
    success_uids_jobs = []  

 
    
    for uid, email_message in info_requests:
        #email_message = email.message_from_bytes(message_data[b'RFC822'])
        sender = email_message.get('From')
        subj = email_message.get('Subject')
        
        sender_adr = re.findall(r'\<.*?\>', sender)[0][1:-1]
        
        print(f'Fulfilling info request from {sender} ({subj})')
        
        info = os.path.join(bin_folder, 'info.txt')    
        with open(info) as fp:
            # Create a text/plain message
            msg = fp.read()
        
        yag.send(sender_adr, 'Your DIP info request (re: {subj})', msg)
        
        success_uids_info.append(uid)
    
    #server.delete_messages(success_uids_info)
    
    #sys.exit()
    print('\n')
    queued_messages = []
    for uid, email_message in process_requests:
        #email_message = email.message_from_bytes(message_data[b'RFC822'])
        sender = email_message.get('From')
        subj = email_message.get('Subject')
        
        sender_adr = re.findall(r'\<.*?\>', sender)[0][1:-1]
        
        print(f'Acknowledging a request from {sender} ({subj})')
            
        acknowledgement = os.path.join(bin_folder, 'acknowledgement.txt')
        with open(acknowledgement) as fp:
            # Create a text/plain message
            msg = fp.read()
        
        yag.send(sender_adr, f'Processing request acknowledgement (re: {subj})', msg)
        
        queued_messages.append(email_message)
        
        
        
    print('\n')
    for message in queued_messages:
        
        problems = ''
        can_run = True
        
        sender = message.get('From')
        subj = message.get('Subject')
        
        sender_adr = re.findall(r'\<.*?\>', sender)[0][1:-1]
        
        print(f'Processing a request from {sender} ({subj})')
        
        body_parts = []
        for part in message.walk():
           if part.get_content_type() == "text/plain":
              #print(part)
              body_parts.append(str(part))
        body = '\n'.join(body_parts)
        job_params = et.extract_parameters_from_body(body)
        
        if os.path.exists(dl_folder):
            shutil.rmtree(dl_folder)
        os.mkdir(dl_folder)     
        
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        os.mkdir(workspace)
        acquired_folder = os.path.join(workspace, 'Acquired')
        os.mkdir(acquired_folder)
        
                
        process_trust = False
        process_asl = False
        
        if 'trust' in subj.lower():
            process_trust = True
        if 'asl' in subj.lower():
            process_asl = True
            
        if not any([process_trust, process_asl]):
            problems = problems + '\nYou requested processing (process is in your subject line) but did not specify a processing type (at least one of trust or asl must be in the subject line too)'
            can_run = False
            
        
        attachment = et.save_attachment(msg=message, download_folder=dl_folder)
        if attachment == 'No attachment found':
            problems = problems + '\nYou forgot to include a zipped folder of scans'
            can_run = False
        elif attachment[-4:] != '.zip':
            problems = problems + '\nYour only attachment should be a single zipped folder of scans - you either forgot to attach a file, or the file you attached is not a .zip file'
            can_run = False
        else:
            with zipfile.ZipFile(attachment, 'r') as zip_ref:
                zip_ref.extractall(dl_folder)
            unzipped_folder = attachment[:-4]
            file_names = os.listdir(unzipped_folder)
            for file_name in file_names:
                os.rename(os.path.join(unzipped_folder, file_name), os.path.join(acquired_folder, f'{os.path.basename(workspace)}_{file_name}'))
            shutil.rmtree(dl_folder)
            
        provided_file_names = os.listdir(acquired_folder)
        
        trust_source_pattern = '*SOURCE*TRUST*VEIN*'
        trust_pattern = '*TRUST*VEIN*'
        
        asl_m0_pattern = '*ASL*M0*'
        asl_source_pattern = '*SOURCE*ASL*PLD*LD*'
        asl_pattern = '*ASL*PLD*LD*'
        
        t1_pattern = '*T1*'
        
        if process_trust:
            trust_source_matches = glob.glob(os.path.join(acquired_folder, trust_source_pattern))
            trust_matches = glob.glob(os.path.join(acquired_folder, trust_pattern))
            
            if not all([len(trust_source_matches)==1, len(trust_matches)==2]):
                problems = problems + f'\nYou requested TRUST processing, but did not provide correctly named files - the patterns for the TRUST and TRUST source are {trust_pattern} and {trust_source_pattern} respectively, and only one file matching each pattern can exist'
                can_run = False
                
            if not job_params['artox']:
                problems = problems + '\nYou requested TRUST processing, but did not provide an arterial oxygenation level (in the body of your email, you need a line that ONLY contains "artox:[number from 0 to 1]")'
                can_run = False
            if not job_params['hct']:
                problems = problems + '\nYou requested TRUST processing, but did not provide a hematocrit (in the body of your email, you need a line that ONLY contains "hct:[number from 0 to 1]")'
                can_run = False  
            if not job_params['status']:
                problems = problems + '\nYou requested TRUST processing, but did not provide a status (in the body of your email, you need a line that ONLY contains "status:[one of control, scd or anemia]")'
                can_run = False
        
        if process_asl:
            asl_m0_matches = glob.glob(os.path.join(acquired_folder, asl_m0_pattern))
            asl_source_matches = glob.glob(os.path.join(acquired_folder, asl_source_pattern))
            asl_matches = glob.glob(os.path.join(acquired_folder, asl_pattern))
            
            if not all([len(asl_m0_matches)==1, len(asl_source_matches)==1, len(asl_matches)==2]):
                problems = problems + f'\nYou requested ASL processing, but did not provide correctly named ASL files - the patterns for the ASL, ASL source and ASL M0 are {asl_pattern}, {asl_source_pattern} and {asl_m0_pattern} respectively, and only one file matching each pattern can exist'
                can_run = False
                
            t1_matches = glob.glob(os.path.join(acquired_folder, t1_pattern))
            
            if not len(t1_matches)==1:
                problems = problems + f'\nYou requested ASL processing, but did not provide a correctly named T1 file - the patterns for the T1 is {t1_pattern}, and only one file matching this pattern can exist'
                can_run = False
                
        # need to check validity of age, artox, hct, status, and scantime    
        age = job_params['age']
        if age:
            try:
                float(age)
            except ValueError:
                problems = problems + f'\nThe age you specified ({age}) cannot be coerced to a float. Make sure this entry is a number.'
                can_run = False
                
        artox = job_params['artox']
        if artox:
            try:
                artox = float(artox)
            except ValueError:
                problems = problems + f'\nThe artox you specified ({artox}) cannot be coerced to a float. Make sure this entry is a number.'
                can_run = False
            if not (artox >= 0 and artox <= 1):
                problems = problems + f'\nThe artox you specified ({artox}) must be between 0 and 1.'
                can_run = False
                
        hct = job_params['hct']
        if artox:
            try:
                float(hct)
            except ValueError:
                problems = problems + f'\nThe hct you specified ({hct}) cannot be coerced to a float. Make sure this entry is a number.'
                can_run = False
            if not (artox >= 0 and artox <= 1):
                problems = problems + f'\nThe hct you specified ({hct}) must be between 0 and 1.'
                can_run = False
                
        valid_statuses = ['control', 'scd', 'anemia']
        status = job_params['status']
        if status:
            if status not in valid_statuses:
                problems = problems + f'\nThe status you specified ({status}) is not one of {valid_statuses}. Make sure this entry can be found in that list.'
                can_run = False
                
        format_str_scan = '%Y.%m.%d'
        scan_date = job_params['scandate']
        try:
            scan_dt_obj = datetime.datetime.strptime(scan_date, format_str_scan)
        except ValueError:
            problems = problems + f'\nThe scan date you specified ({scan_date}) must be formatted as YYYY.mm.dd'
            can_run = False
            
        
    
        
                
        if not can_run:
            incomplete = os.path.join(bin_folder, 'processing_incomplete.txt')
            with open(incomplete) as fp:
                # Create a text/plain message
                msg = fp.read()
                
            msg = msg.replace('<PROBLEMS>', problems)
            yag.send(sender_adr, f'Processing request - incomplete job specification (re: {subj})', msg)
            
        else:
            print('Parameterization correct - processing')
            started = os.path.join(bin_folder, 'processing_started.txt')
            
            with open(started) as fp:
                # Create a text/plain message
                msg = fp.read()
            
            processing_types = []
            if process_trust:
                processing_types.append('trust')
            if process_asl:
                processing_types.append('asl')
                
            process_str = ', '.join(processing_types)
            
            msg = msg.replace('<PROCESSING>', process_str)
            msg = msg.replace('<PARAMS>', str(job_params))
            
            if job_params['status'] == 'scd':
                job_params['status'] = 'sca'
                
            call_str = f'process_scd.py -i {workspace} -s 24'
            
            if job_params["status"]:
                call_str = call_str + f' -p {job_params["status"]}'            
            if job_params["hct"]:
                call_str = call_str + f' -h {job_params["hct"]}'            
            if job_params["artox"]:
                call_str = call_str + f' -a {job_params["artox"]}'
            
            if not process_asl:
                call_str = call_str + ' -e vol,asl'
            if not process_trust:
                call_str = call_str + ' -e trust'
                
            # need to add these to process_scd.py
            if job_params["age"]:
                call_str = call_str + f' -y {job_params["age"]}'                
            if job_params["gender"]:
                call_str = call_str + f' -s {job_params["gender"]}'                
            if job_params["scandate"]:
                call_str = call_str + f' -t {job_params["scandate"]}'                
            if job_params["mrid"]:
                call_str = call_str + f' -m {job_params["mrid"]}'                
            if job_params["studyid"]:
                call_str = call_str + f' -x {job_params["studyid"]}'
                
            
            msg = msg.replace('<CALL>', call_str)
            
            yag.send(sender_adr, f'Processing request - update (re: {subj})', msg)
        
        
        
        
        
        
    # wrap up
    server.add_flags(all_uids, ['SEEN'])
    
    old_messages = server.search(f'BEFORE {before_date}')
    server.delete_messages(old_messages)



