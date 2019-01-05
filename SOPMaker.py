from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from enum import Enum
from pathlib import Path
from jira import JIRA
from jira import JIRAError
from sopbuilder import SopDocument
from teamdrive import TeamDrive
import requests
import pathlib
import json
import configparser
import httplib2
import os
import logging
import pprint
#from sopdocument import Sop



def main():
    config = configparser.ConfigParser()
    config.sections()
    config.read('Config.ini')
    user = config.get('SETTINGS', 'User')
    password = config.get('SETTINGS', 'Password')
    server = config.get('SETTINGS', 'Server')
    
    jira_project = {
        "epic": {},
        "sop": {},
        "subtasks": [],
        "issue_key":'',
        "folder_id":'',
    }

    logging.basicConfig(level=logging.INFO, filename='sopmaker.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()

    td = TeamDrive(file_name='C:\\Users\\kwame\\source\\repos\\SOPMaker\\SOPMaker\\DGMS-2267.pdf',folder_id='1xBtsxIJzXw40047SqPb4tZiZUsa8gKZ8')

    jira_issues = []
    jira = JIRA(server, basic_auth=(user, password))


    #jira = JIRA(server, basic_auth=(user, password))
    #issue = jira.issue('DGMS-1993')
    #props = jira.application_properties()
    
    # changing things up a bit to provide more abstraction in the sopdocument
    # moving the data fetching from the class and into the main body of the script
    # this should make debugging easier and means the class is doing the one
    # thing that it was designed to do. be a document engine. 


    logger.info('******************************  Starting Session  ******************************')
    try:
        if jira is not None:
            logging.info('Connected to https://solutionsitw.atlassian.net/rest/api/2/issue/')

            # get the sop issues
            for sop in jira.search_issues('issuetype=SOP AND status in (\'To Do\', \'In Progress\')'):
                jira_project = {"epic": {},"sop": {},"subtasks": [], "issue_key":'', "folder_id":'',}
                jira_project['sop'] = sop
                logging.info('Retrieving SOP subtasks for: ' + sop.key)
                
                for sop_subtask in sop.fields.subtasks:
                    jira_project['subtasks'].append(jira.issue(sop_subtask.key))

                logging.info('Number of subtasks returned: ' + str(len(jira_project['subtasks'])))

                if sop.fields.customfield_10008 is not None:
                    jira_project['epic'] = jira.issue(sop.fields.customfield_10008)
                jira_issues.append(jira_project)

            print("Number of SOPs returned: " + str(len(jira_issues)))
            logging.info('Number of SOPs returned: ' + str(len(jira_issues)))
        else:
            print("Nothing to see here")
    except JIRAError as je:
        print("Jira Exception: "+ str(je.status_code) + "\n", je.text)
        logging.error('Jira Exception: ' + je.status_code)
        logging.error('Jira Exception: ' + je.response)
    
    logger.info('******************************  Start PDF Creation ******************************')
    try:
        if not os.path.exists(config.get('SETTINGS','DocumentPath')):
            os.makedirs(config.get('SETTINGS','DocumentPath'))
    except OSError as oe:
        logging.error(oe)


    # start build ing the documents
    for sop in jira_issues:
        sop_doc = SopDocument(sop)
        doc = sop_doc.build_documents()
        pprint.pprint(doc)
        del sop_doc
  
     
    logger.info('******************************  Session Complete  ******************************')

    
if __name__ == '__main__':
    main()

