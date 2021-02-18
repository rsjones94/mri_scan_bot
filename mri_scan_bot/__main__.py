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
import subprocess
import requests

import pandas as pd
from imapclient import IMAPClient
import yagmail
import redcap

import email_tools as et

"""
with open('/Users/manusdonahue/Desktop/cronjob_check.txt', 'rw') as f:
    f.write('yes hello this is to see if the cronjob is triggering\n')
    f.write(f'__file__ is {__file__}\n')
    f.write(f'dirname is {os.path.dirname(__file__)}\n')
"""
    



print('Running scheduled check for processing requests')


#creds = '/Users/skyjones/Documents/repositories/donahueprocessing_app_pw.txt'
cred_name = 'donahueprocessing_app_token.txt'

home = os.path.dirname(os.path.dirname(__file__))
creds = os.path.join(os.path.dirname(home), cred_name)

bin_folder = os.path.join(home,'bin')
scd_data_folder = '/Users/manusdonahue/Desktop/Projects/SCD/Data/'

# because we're running this as a cron job, we need to prevent concurrent
# instances otherwise we'll have trouble with redcap pulls disagreeing
checkout_file = os.path.join(home, 'checkout.txt')
if not os.path.exists(checkout_file):
    with open(checkout_file, 'w') as f:
        f.close()
        
with open(checkout_file, 'r+') as f: # if the checkout doesn't exist, or if the last line is 'free' then we can begin processing
    lines = f.readlines()
    if len(lines) == 0 or lines[-1] == 'free':
        f.write(f'\noccupado ({datetime.datetime.now()})')
    else:
        f.write(f'\nchecked, but was occupado')
        f.write(f'\noccupado')
        sys.exit()

# big try block will be used to make sure we append 'free' to the checkout file no matter what
try:
    
    alert_file = os.path.join(home, 'bot_alert.txt')
    with open(alert_file, 'a+') as f:
        f.write(f'\n\nBot scanning for requests. Time is {datetime.datetime.now()}')
    
    print('\nContacting the REDCap database...')
        
    
    api_url = 'https://redcap.vanderbilt.edu/api/'
    
    with open(creds) as c:
        token = c.read()
        
    project = redcap.Project(api_url, token)
    project_data_raw = project.export_records()
    project_data = pd.DataFrame(project_data_raw)
    
    n_complete = 0
    for i, row in project_data.iterrows():
        
        stage = row['processing_stage']
        if stage not in ('', '0'):
            continue
        
        email = row['contact_email']
        print(f'Processing scans for {email}')
        
        with open(alert_file, 'a+') as f:
            f.write(f'\n\tRequest for {email} ({row["mr_id"]}): ')
        
        row['processing_stage'] = '1'
        
        # update redcap to mark that processing has begun
        import_row = {}
        for key, val in row.items():
            import_row[key] = val
        np = project.import_records([import_row])
        
        record = row['record_id']
        
        if row['filetype'] == '1':
            exts_match = ['nii'] #.nii.gz
            exts = ['.nii.gz']
        elif row['filetype'] == '2':
            exts_match = ['par', 'rec'] # PARREC
            exts = ['.PAR', '.REC'] # PARREC
        
        job_params = {'dob':None,
                    'art_ox':None,
                    'hct':None,
                    'subject_status':None,
                    'gender':None,
                    'scan_Date':None,
                    'mr_id':None,
                    'study_id':None}
        
        process_asl = int(row['asl_requested'])
        process_trust = int(row['trust_requested'])
        
        if process_asl:
            pld_val = row['pld']
            ld_val = row['ld']
        else:
            pld_val = 0
            ld_val = 0
        
        date_params = ['dob', 'scan_date']
        for dp in date_params:
            if row[dp] == '':
                pass
            else:
                dt = datetime.datetime.strptime(row[dp], '%Y-%m-%d')
                job_params[dp] = datetime.datetime.strftime(dt, '%Y.%m.%d')
                
        float_params = ['hct', 'art_ox']
        for fp in float_params:
            if row[fp] == '':
                pass
            else:
                job_params[fp] = float(row[fp])
                
        str_params = ['mr_id', 'study_id']
        for sp in str_params:
            if row[sp] == '':
                pass
            else:
                job_params[sp] = row[sp]
            
        gen = row['gender']
        if gen == '':
            pass
        elif gen == '1':
            job_params['gender'] = 'male'
        elif gen == '2':
            job_params['gender'] = 'female'
        else:
            job_params['gender'] = 'n/a'
            
        stat = row['subject_status']
        if stat == '1':
            job_params['subject_status'] = 'control'
        elif stat == '2':
            job_params['subject_status'] = 'scd'
        elif gen == '3':
            job_params['subject_status'] = 'anemia'
            
        dl_fields = {'t1':'3DT1_scan',
                     'asl_m0':'ASL_M0_scan',
                     'asl_source':f'SOURCE_ASL_PLD{pld_val}_LD{ld_val}_scan',
                     'asl':f'ASL_PLD{pld_val}_LD{ld_val}_scan',
                     'trust_source':'SOURCE_TRUST_VEIN_scan',
                     'trust':'TRUST_VEIN_scan'}
        dl_fields_real = {}
        for f, pattern in dl_fields.items():
            for e,r in zip(exts_match, exts):
                dl_fields_real[(f'{f}_{e}')] = f'{pattern}{r}'
                
        
        workspace_name = f"PROCESSING_BOT_{row['mr_id']}"
        #workspace = os.path.join(bin_folder, workspace_name)
        workspace = os.path.join(scd_data_folder, workspace_name)
        acquired_folder = os.path.join(workspace, 'Acquired')
        
        if os.path.exists(workspace):
            shutil.rmtree(workspace)
        
        os.mkdir(workspace)
        os.mkdir(acquired_folder)
        
        for field, filename in dl_fields_real.items():
            real_name = f'{workspace_name}_{filename}'
            try:
                file_contents, headers = project.export_file(record, field)
                outname = os.path.join(acquired_folder, real_name)
                with open(outname, 'wb') as f: #arg2 might need to be w, not wb, in production?
                    f.write(file_contents)
            except requests.HTTPError: # happens if there is not file to download
                pass
            
            
        processing_types = []
        if process_trust:
            processing_types.append('trust')
        if process_asl:
            processing_types.append('asl')
            
        process_str = ', '.join(processing_types)
        
        if job_params['subject_status'] == 'scd':
            job_params['subject_status'] = 'sca'
            
        call_str = f'process_scd.py --infolder {workspace} --steps 24 --auto 1 --redcap 0'
        
        if job_params["subject_status"]:
            call_str = call_str + f' -p {job_params["subject_status"]}'            
        if job_params["hct"]:
            call_str = call_str + f' -h {job_params["hct"]}'            
        if job_params["art_ox"]:
            call_str = call_str + f' -a {job_params["art_ox"]}'
        
        if not process_asl:
            call_str = call_str + ' -e vol,asl'
        if not process_trust:
            call_str = call_str + ' -e trust'
            
        # need to add these to process_scd.py
        if job_params["dob"]:
            call_str = call_str + f' -b {job_params["dob"]}'                
        if job_params["gender"]:
            call_str = call_str + f' -u {job_params["gender"]}'                
        if job_params["scan_date"]:
            call_str = call_str + f' -t {job_params["scan_date"]}'
        if job_params["study_id"]:
            call_str = call_str + f' -x {job_params["study_id"]}'
        
        max_time_mins = 20
        max_time_secs = max_time_mins*60
        
        print(f'Call string: {call_str}')
        
        
        try:
            subprocess.call(call_str, timeout=max_time_secs, shell=True)
            processing_status = '2'
            
            with open(alert_file, 'a+') as f:
                f.write(f' complete')
            
        except subprocess.TimeoutExpired:
            print('Process timed out')
            processing_status = '4'
            with open(alert_file, 'a+') as f:
                f.write(f' !!!!! timed out !!!!!')
            
        except Exception as e:
            with open(alert_file, 'a+') as f:
                f.write(f' ????? Unknown exception ?????')
                f.write(f'\n\t\t{e}')
        
        
            
        print('Cleaning up')
        
        # update redcap
        row['processing_stage'] = processing_status
        
        import_row = {}
        for key, val in row.items():
            import_row[key] = val
        np = project.import_records([import_row])
        
        n_complete += 1
        
    
    with open(alert_file, 'a+') as f:
        f.write(f'\nSuccessfully finished. {n_complete} request(s) completed.')
        
except Exception:
    pass

finally:
    with open(checkout_file, 'r+') as f: # if the checkout doesn't exist, or if the last line is 'free' then we can begin processing
        f.write(f'\nfree')
    
    
