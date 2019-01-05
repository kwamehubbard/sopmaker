from __future__ import print_function
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import Error
from httplib2 import Http
from oauth2client import file, client, tools
from enum import Enum
from pathlib import Path
from jira import JIRA
from jira import JIRAError
from markdown2 import Markdown
import sopdocument
import requests
import pathlib
import json
import configparser
import pprint
import os
import subprocess
import uuid
import logging

class Sop(object):
    """description of class"""

    # map Jira custom field names to friendly names
    # customfield_10008 is the epic link field which contains the epic - ISSUE
    # customfield_10101 contains the link to the Google Drive project folder - EPIC
    # customfield_10005 is the epic name (project name) - EPIC
    # customfield_10095 is the orginzation (client). this is a dictionary - EPIC
    #  and the key to retrieve is "value"
    # customfield_10093 GanttPro start date - EPIC
    # customfield_10092 GanttPro end date - EPIC
    custom_fields = {
        "epic": "customfield_10008",
        "project_folder": "customfield_10101",
        "epic_name": "customfield_10005",
        "organization": "customfield_10095",
        "start_date": "customfield_10093",
        "end_date": "customfield_10092"
    }

    #project information
    project_info = {
        "project_name":  "",
        "project_start_date": "",
        "project_end_date": "",
        "project_description": "",
        "project_summary": "",
        "project_organization_name": "",
        "project_folder": "",
        "project_folder_id": ""
    }

    # markdown document structure with section titles as first item
    # TO DO: Move this to the config file or database
    markdown_document = {
        "header" :[],
        "title" :[],
        "project_info" :[], 
        "setup" :[],
        "sales" :[], 
        "project_management" :[], 
        "leads" :[], 
        "devinf" :[], 
        "qa" :[], 
        "implementor" :[], 
        "support" :[], 
        "footer" :[]
    }

    markdown_documents = []

    markdown_document_section_headers = {
        "header" :"GACS/Solutions",
        "title" :"# Standard Operating Procedure: ",
        "project_info" :"## Project Details ##\n", 
        "setup" :"## Initialization ##\n",
        "sales" :"## Sales/Product Management ##\n", 
        "project_management" :"## Project Management ##\n", 
        "leads" :"## Technical Leads ##\n", 
        "devinf" :"## Development & Infrastructure ##\n", 
        "qa" :"## Quality Assurance ##\n", 
        "implementor" :"## Delivery ##\n", 
        "support" :"## Support ##\n", 
        "footer" :""
    }


    # list of sops
    issue_sops = []

    
    # Get some configuration settings
    config = configparser.ConfigParser()
    config.sections()
    config.read('Config.ini')

    SCOPES = 'https://www.googleapis.com/auth/drive.file'
    

    def __init__(self):
        self.server = self.config.get('SETTINGS', 'Server')
        self.sop_url = self.config.get('SETTINGS', 'SopURL')
        self.user = self.config.get('SETTINGS', 'User')
        self.password = self.config.get('SETTINGS', 'Password')
        self.logfile = self.config.get('SETTINGS', 'LogFile')
        logging.basicConfig(level=logging.INFO, filename='sopmaker.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

    def get_issue(self, issue_number):
        # connect to the Jira server

        sop_subtasks = []

        try:
            jira = JIRA(self.server, basic_auth=(self.user, self.password))

            if jira is not None:
                logging.info('Connected to https://solutionsitw.atlassian.net/rest/api/2/issue/')
                # get the sop issues
                issue = jira.issue(issue_number)
                print('Getting subtasks for: {} --- {}' .format(issue.key, issue.fields.summary))
                sop_subtasks.append(issue)
                for sop_subtask in issue.fields.subtasks:
                    sop_subtasks.append(jira.issue(sop_subtask.key))
                    logging.info(issue.key + ':' + sop_subtask.key + '  ' + sop_subtask.fields.summary)
                
                self.issue_sops.append(sop_subtasks)
                print("Number of SOPs returned: " + str(len(self.issue_sops)))       
                logging.info('Number of SOPs returned: ' + str(len(self.issue_sops)))
            else:
                print("Nothing to see here")
        except JIRAError as je:
            print("Jira Exception: "+ str(je.status_code) + "\n", je.text)
            logging.error('Jira Exception: ' + je.status_code)
            logging.error('Jira Exception: ' + je.response)



    def get_sops(self):
        # connect to the Jira server
        try:
            jira = JIRA(self.server, basic_auth=(self.user, self.password))

            if jira is not None:
                logging.info('Connected to https://solutionsitw.atlassian.net/rest/api/2/issue/')
                # get the sop issues
                for issue in jira.search_issues('issuetype=SOP AND status in (\'To Do\', \'In Progress\')'):
                    logging.info('Retrieving SOP subtasks for: ' + issue.key)
                    sop_subtasks = []
                    for sop_subtask in issue.fields.subtasks:
                        sop_subtasks.append(jira.issue(sop_subtask.key))
                        logging.info(issue.key + ':' + sop_subtask.key + '  ' + sop_subtask.fields.summary)
                    
                    logging.info('Number of subtasks returned: ' + str(len(sop_subtasks)))
                    sop_subtasks.insert(0,issue)
                    self.issue_sops.append(sop_subtasks)

                print("Number of SOPs returned: " + str(len(self.issue_sops)))
                logging.info('Number of SOPs returned: ' + str(len(self.issue_sops)))
            else:
                print("Nothing to see here")
        except JIRAError as je:
            print("Jira Exception: "+ str(je.status_code) + "\n", je.text)
            logging.error('Jira Exception: ' + je.status_code)
            logging.error('Jira Exception: ' + je.response)

    def print_me(self):
        pprint.pprint(self.project_info)
        pprint.pprint(self.issue_sops)

    def set_project_info(self, epic=None, name="Not Provided", start_date="1/1/1900", end_date="1/1/1900", description="Not Provided", summary="Not Provided", folder="http://solutionsitw.com", org_name="Not Provided"):

        # epic name/project name
        self.project_info["project_name"] = name if epic is None \
            else epic.fields.customfield_10005
        
        # start date
        self.project_info["project_start_date"] = start_date if epic is None \
            else epic.fields.customfield_10093
        
        # end date
        self.project_info["project_end_date"] = end_date if epic is None \
            else epic.fields.customfield_10092

        # description
        self.project_info["project_description"] = description if epic is None \
            else epic.fields.description
        
        # summary
        self.project_info["project_summary"] = summary if epic is None \
            else epic.fields.summary

        # project folder
        self.project_info["project_folder"] = folder if epic is None \
            else epic.fields.customfield_10101

        # organization
        if epic is not None:
            if epic.fields.customfield_10095 is not None:
                self.project_info["project_organization_name"] = epic.fields.customfield_10095.value
            else:
                self.project_info["project_organization_name"] = org_name
      
        # not as elegant as a regex but it works as long as the url matches this
        # https://drive.google.com/drive/u/0/folders/1IampOt20ZtD_vVlfo4EwSf_m7eVSi331
        self.project_info["project_folder_id"] = "" if self.project_info["project_folder"] is None \
            else self.project_info["project_folder"][43:]

    def add_section(self,subtask, section_name):
        section = ""

        # format the section header
        section_header = "### " + subtask.fields.summary + " ###\n"
        section_detail = subtask.fields.description + "\n"

        section = section_header + section_detail

        section_name.append(section)

    def add_project_info_section(self, project_info, md_document):

        # start date
        project_info["project_start_date"] = "" if project_info["project_start_date"] is None \
            else project_info["project_start_date"]
        
        # end date
        project_info["project_end_date"] = "" if project_info["project_end_date"] is None \
            else project_info["project_end_date"]
        
        # orginization name
        project_info["project_organization_name"] = "" if project_info["project_organization_name"] is None \
            else project_info["project_organization_name"]
        
        # folder
        project_info["project_folder"] = "" if project_info["project_folder"] is None \
            else project_info["project_folder"]

        # summary
        project_info["project_summary"] = "" if project_info["project_summary"] is None \
            else project_info["project_summary"]

        # description
        project_info["project_description"] = "" if project_info["project_description"] is None \
            else project_info["project_description"]


        project_table = "| Project Name | Epic Name |\n"
        project_table += "| ------ | ------ |\n"
        project_table += "| **Client** | " + project_info["project_organization_name"] + " |\n"
        project_table += "| **Start Date** | " +  project_info["project_start_date"] + " |\n"
        project_table += "| **End Date** | " + project_info["project_end_date"] + " |\n"
        project_table += "| **Project Folder** | [" + project_info["project_folder"] +"]()|\n"
        project_table += "| **Summary** | " + project_info["project_summary"]  + " |\n"
        project_table += "---\n"
        project_table += "## Overview ##\n"
        project_table += project_info["project_description"]
        project_table += "\n\n---\n"

        md_document["project_info"].append(project_table)
    
    def add_title_section(self, title, md_document):
        section = title[0] + "\n"
        section += "```sh\n"
        section += "Date Created: " + title[1] + "\n"
        section += "Last Updated: " +title[2] + "\n"
        section += "```\n"
        section += "---\n"
        md_document["title"].append(section)
    
    def build_markdown_document(self):
        # the sop task is the parent containing all steps in the SOP
        # as subtasks. iterate through the SOP subtasks to buld the document
        #parent_sop = JIRA.issue
        sop = JIRA.issue
        key = ''
        for item in self.issue_sops:
            logging.info('Compiling SOPs into markdown structure')
            md_document = {"header" :[],"title" :[],"project_info" :[], "setup" :[], \
                            "sales" :[], "project_management" :[], "leads" :[], \
                            "devinf" :[], "qa" :[], "implementor" :[], "support" :[], \
                            "footer" :[]}
            
            google_drive_folder_id = None

            for sop in item:
                if sop.fields.issuetype.name == 'SOP':
                    key = sop.key
                    if sop.fields.customfield_10008 is not None:
                        # its a project
                        try:
                            jira = JIRA(self.server, basic_auth=(self.user, self.password))
                            logging.info('Successfully connnected to Jira to retrieve epic info: ' + sop.fields.customfield_10008)
                            epic = jira.issue(sop.fields.customfield_10008)
                            self.set_project_info(epic)
                            google_drive_folder_id = self.project_info["project_folder_id"]
                            title = (epic.fields.customfield_10005, epic.fields.created, epic.fields.updated)
                        except JIRAError as je:
                            print("Jira Exception: "+ str(je.status_code) + "\n", je.text)
                            logging.error('Jira Exception: ' + je.status_code)
                            logging.error('Jira Exception: ' + je.response)
                    else:
                        self.set_project_info(summary=sop.fields.summary, description=sop.fields.description,name=sop.fields.summary, org_name=sop.fields.customfield_10095)
                        title = (sop.fields.summary, sop.fields.created, sop.fields.updated)                        

                    self.add_project_info_section(self.project_info, md_document)
                    self.add_title_section(title, md_document)
                elif 'SOP 0' in sop.fields.summary:
                    self.add_section(sop, md_document["setup"])
                elif 'SOP 1' in sop.fields.summary:
                    self.add_section(sop, md_document["sales"])
                elif 'SOP 2' in sop.fields.summary:
                    self.add_section(sop, md_document["project_management"])
                elif 'SOP 3' in sop.fields.summary:
                    self.add_section(sop, md_document["leads"])
                elif 'SOP 4' in sop.fields.summary:
                    self.add_section(sop, md_document["devinf"])
                elif 'SOP 5' in sop.fields.summary:
                    self.add_section(sop, md_document["qa"])
                elif 'SOP 6' in sop.fields.summary:
                    self.add_section(sop, md_document["implementor"])
                elif 'SOP 7' in sop.fields.summary:
                    self.add_section(sop, md_document["support"])
                else:
                    None
            
            self.markdown_documents.append([key,md_document,google_drive_folder_id])
            
        self.__make_markdown_file()
    
    
    def __clear_markdown_document(self):
        for value in self.markdown_document:
            self.markdown_document[value] = []


    def __make_markdown_file(self):
        for sop_document in self.markdown_documents:
            md_file = sop_document[0] + ".md"
            md_file = Path(md_file)
            f = open(md_file, "a")
            document = sop_document[1]
            for section in document:
                header = self.markdown_document_section_headers[section]
                if len(document[section]) > 0:
                    sop_list = document[section].copy()
                    sop_list.insert(0,header)
                    for item in sop_list:
                        f.write(item)

        f.close()

        self.__markdown2_html()
        #self.__save_to_google_drive()

    def __save_to_google_drive(self):
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', self.SCOPES)
            creds = tools.run_flow(flow, store)
        #service = build('drive', 'v3', http=creds.authorize(Http()))

        #Now build our api object, thing
        drive_api = build('drive', 'v3', credentials=creds)

        # this is the id of the operations team drive'0APEvtclfvCwFUk9PVA'
        team_drive_id = '1I8S2iIpOjViQzqnXvi3noZEg_ib26YDO'  # this is the id of the Clients folder on the Operations teamdrive
        documents_saved = 0

        logging.info('Saving files to project folders...')
        for document in self.markdown_documents:
            logging.info('Number of documents to be sent: ' + str(len(self.markdown_documents)))
            for md_file in os.listdir("."):
                doc_name = document[0] + ".md"
                if md_file == doc_name:
                    print("Saving: " + os.path.join("./", md_file))

                    file_metadata = {'name': doc_name, 'parents': [document[2]]} 
                    request_id = str(uuid.uuid4())
                    media = MediaFileUpload(md_file, mimetype='text/plain')
                    try:
                        savefile = drive_api.files().create(body=file_metadata, media_body=media, supportsTeamDrives=True, fields='id').execute()
                        #savefile = drive_api.teamdrives().create(body=file_metadata, requestId=request_id, fields='id').execute()
                        documents_saved += 1
                        logging.info('Saved: ' + savefile.get('id'))
                        print("Created file id: '%s'." % (savefile.get('id')))
                    except Error as ge:
                        logging.error('Google Drive Exception: ' + ge)
                        print(ge)
                    finally:
                        logging.info('Saved ' + str(documents_saved) + ' of ' + str(len(self.markdown_documents)))

    def __markdown2_html(self):
        #markdowner = Markdown()
        for file in os.listdir("."):
            if file.endswith(".md"):
                print('Converting...' + file)
                fo = open(file, 'r')
                markdown = fo.read()
                fo.close()
                html_content = markdown.markdown(markdown, extras=["tables"])
                html_file = os.path.basename(file) + ".html"
                html_file = Path(html_file)
                f = open(html_file, "w")
                f.write(html_content)
                f.close()



    



        

            

        





