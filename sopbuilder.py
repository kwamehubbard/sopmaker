from enum import Enum
from jira import JIRA
from jira import Issue
from pathlib import Path
import configparser
import logging
import pprint
import os
import markdown2
import requests
import json


class SopDocument(object):
    """ Builds a SOP from subtasks """

    class Document_Section(Enum):
        HEADER = "header"
        TITLE = "title "
        PROJECT_INFO = "project_info"
        SETUP = "setup"
        SALES = "sales"
        PROJECT_MANAGEMENT = "project_management" 
        LEADS = "leads"
        DEVINF = "devinf"
        QA = "qa"
        IMPLEMENTOR = "implementor"
        SUPPORT = "support"
        FOOTER = "footer"

    # map Jira custom field names to friendly names
    # customfield_10008 is the epic link field which contains the epic - ISSUE
    # customfield_10101 contains the link to the Google Drive project folder - EPIC
    # customfield_10005 is the epic name (project name) - EPIC
    # customfield_10095 is the orginzation (client). this is a dictionary - EPIC
    #  and the key to retrieve is "value"
    # customfield_10093 GanttPro start date - EPIC
    # customfield_10092 GanttPro end date - EPIC
    # custom_field_10102 checklist - ISSUE
    class Custom_Fields(Enum):
        EPIC_LINK = "customfield_10008"    
        PROJECT_FOLDER = "customfield_10101"
        EPIC_NAME = "customfield_10005"
        ORGANIZATION = "customfield_10095"
        START_DATE = "customfield_10093"
        END_DATE = "customfield_10092"
        CHECKLIST = "customfield_10102"


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

    # the sections that make a completed SOP document
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


    jira_project = {
        "epic": {},
        "sop": {},
        "subtasks": [],
        "issue_key":'',
        "folder_id":'',
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

    md_section_header = {
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


    # Get some configuration settings
    config = configparser.ConfigParser()
    config.sections()
    config.read('Config.ini')

    def __init__(self, jira_issue=None):
        self.jira_project = jira_issue
        self.issue_sops = []
        self.sop_path = self.config.get('SETTINGS', 'DocumentPath')
        logging.basicConfig(level=logging.INFO, filename='sopmaker.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

    def build_documents(self):
        """ Creates the the SOP document

        Utilizing the content contained in the Jira issues that comprise the SOP this function compiles it
        into a finished SOP document. This function drives the entire process.

        Args:

        Returns:
            file: the finished SOP document as a PDF

        """
        self.markdown_document = {"header" :[],"title" :[],"project_info" :[], "setup" :[], \
                "sales" :[], "project_management" :[], "leads" :[], \
                "devinf" :[], "qa" :[], "implementor" :[], "support" :[], \
                "footer" :[]}

       
        # get the project info
        if self.jira_project['epic']:
            self.set_project_info(epic=self.jira_project['epic'])
            title = (self.jira_project['epic'].fields.customfield_10005, self.jira_project['epic'].fields.created, self.jira_project['epic'].fields.updated)
            self.jira_project['issue_key'] = self.jira_project['epic'].key
        else:
            self.set_project_info(sop=self.jira_project['sop'])
            title = (self.jira_project['sop'].fields.summary, self.jira_project['sop'].fields.created, self.jira_project['sop'].fields.updated)
            self.jira_project['issue_key'] = self.jira_project['sop'].key
        
        # add the title
        self.add_title_section(title)

        # build the individual sections of the sop
        for subtask in self.jira_project['subtasks']:
            if 'SOP 0' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.SETUP.value)
            elif 'SOP 1' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.SALES.value)
            elif 'SOP 2' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.PROJECT_MANAGEMENT.value)
            elif 'SOP 3' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.LEADS.value)
            elif 'SOP 4' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.DEVINF.value)
            elif 'SOP 5' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.QA.value)
            elif 'SOP 6' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.IMPLEMENTOR.value)
            elif 'SOP 7' in subtask.fields.summary:
                self.add_section(subtask, self.Document_Section.SUPPORT.value)
            else:
                None
    
        self.__make_mardownfile()
        #self.__convert_markdown2HTML()
        myfile = self.__make_PDF('no sched')

        return myfile

    def __make_mardownfile(self):
        """ Creates a markdown file that represents the entire SOP

        Using content from all of the SOP subtasks the SOP document is created
        and marked up with markdown symbols.

        Args:

        Returns:
            file: the SOP as a markdown file
        """
        md_file = self.jira_project['issue_key'] + ".md"

        # try:
        #     if not os.path.exists(self.sop_path):
        #         os.makedirs(self.sop_path)
        # except OSError as oe:
        #     print(oe)

        os.chdir(self.sop_path)
        md_file = Path(md_file)
        f = open(md_file, "a")
        for section in self.markdown_document:
            header = self.md_section_header[section]
            if len(self.markdown_document[section]) > 0:
                sop_list = self.markdown_document[section].copy()
                sop_list.insert(0,header)
                for item in sop_list:
                    f.write(item)

        f.close()

        return md_file

    def __convert_markdown2HTML(self):
        """ Converts markdown to HTML

        Converts a markdown file to a HTML file for use by other PDF generators

        Todo: Consider passing in the file name as an argument

        Args:
            file: not passed directly but pickes up the appropriate markdown file from the subdirectory

        Returns:
            file: Returns the HTML file
        """

        # markdown2 does not return a complete html document. use the strings below to
        # wrap the html returned from markdown2 to create a complete html document
        html_header = '<!doctype html>\n\t<html>\n\t\t<head>\n\t\t\t<meta charset=\"utf-8\">\n\t\t\t<title>Page Title</title>\n\t\t\t <meta name=\"description\" content=\"Webpage for xxxx\">\n\t\t\t<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/2.10.0/github-markdown.min.css\">\n\t\t</head>\n\t\t<body><article class="markdown-body">\n\t\t\t\t'
        html_tail = '\n\t\t\t\t</article>\n\t\t\t</body></html>'

        os.chdir(self.sop_path)
        md_document = Path(self.jira_project['issue_key'] + ".md")

        try:
            # get the content of the markdown file
            md_reader = open(md_document, 'r')
            md_content = md_reader.read()
            md_reader.close()            

            # create the html
            html_file =  self.jira_project['issue_key'] + ".html"
            html_file = Path(self.sop_path + html_file)
            f = open(html_file, 'w')
            html_content = html_header + markdown2.markdown(md_content, extras=["tables", "fenced-code-blocks"],html4tags='true') + html_tail

            # set column widths for pdf writer
            html_content = html_content.replace('<table>', '<table width=\"70%\">', 1)
            html_content = html_content.replace('<th>', '<th width=\"30%\">', 1)
            html_content = html_content.replace('<th>', '<th width=\"70%\">', 1)

            f.write(html_content)
            f.close()
        except OSError as oe:
            print(oe)
            logging.error(oe)

        return html_file

    def __make_PDF(self, schedule):
        """ Converts a markdown document into a PDF

        This uses MarkdowntoPDF.com to convert the markdown files to PDF.
        MarkdowntoPDF does not have an API so instead this function makes a
        POST to the web form on their home page.

        Args:
            markdown (file): the file is not passed to this function directly instead the file
            is picked up from a subdirectory from which this script executed. When this was 
            written other options were being considered. This will be moved to outside of the
            class so that the PDF creation can be throttled so as not to abuse the free service.

        Returns:
            file: PDF of the SOP

        """
        pdf_download_location = self.config.get('SETTINGS','MarkdowntoPDFDownloadURL')
        pdf_upload_location = self.config.get('SETTINGS', 'MarkdowntoPDFUploadURL')

        #os.chdir('./' + self.config.get('SETTINGS','DocumentPath'))
        print(os.getcwd())

        file_name = self.jira_project['issue_key'] + ".md"   

        md_doc = self.jira_project['issue_key'] + ".md"
        #md_doc = Path(md_doc)

        try:
            multipart_form_data = {
                'file': (file_name, open(md_doc, 'rb'))
            }

            response = requests.post(pdf_upload_location, files=multipart_form_data)

            # transform response into jason
            file_location = json.loads(response.text)
                                
            if response.status_code == 200:
                foldername = file_location['foldername']
                filename = file_location['filename']
                pdf_download_location += foldername + "/" + filename
                my_pdf_file =  filename + ".pdf"
                my_pdf_file = Path(my_pdf_file)
                my_pdf = requests.get(pdf_download_location, allow_redirects=True)
                open(my_pdf_file, 'wb').write(my_pdf.content)

        except requests.exceptions.RequestException as req_err:
            logging.error("__make_pdf: " + req_err)
        except IOError as io_err:
            logging.error("__make_pdf: " + io_err)

        return my_pdf_file

    def __checklist2gfm(self, checklist):
        """ Converts a Smart Checklist to GFM (Github Flavored Markdown)

        Smart Checklist uses its own markdown syntax to create the checklist within a Jira issue.
        This function transform the markdown to GFM which should be easier to read when
        rendered in the final SOP document. Note: GFM does not have an indication for 'in progress'
        so to keep things uniform [*] is used to indicate in pogress in the final document.

        Smart Checklist Markdown 
            '-' = to do, '+' = done, '~' = in progress
        Github Flavored Markdown
            [ ] = to do, [x] = done, [*] = in progress

        Args:
            checklist (str): a string containing markdown.

        Returns:
            string: string containing the transformed markdown

        """

        cl = checklist.replace('\r\n+', '\r\n[x]')
        cl = cl.replace('\r\n-', '\r\n[ ]')
        cl = cl.replace('\r\n~', '\r\n[*]')
        if cl.startswith('-'):
            cl = cl.replace('-','[ ]',1)
        elif cl.startswith('+'):
            cl = cl.replace('+','[x]',1)
        elif cl.startswith('~'):
            cl = cl.replace('~','[*]',1)
        else:
            None 
        
        return cl
            
        
    def add_section(self, subtask, section_name):
        """ Adds the text from the sop subtasks to the SOP document.

        These sections are fairly generic and do not require specil formatting. This function
        also handles appending any checklists contained with the subtasks
        to the detail that will be included in the SOP document.

        Args:
            subtask (issue): This is a Jira subtask that contains the specific activities and outputs
            associated with this step in the SOP process.

            section_name (str): The section of the SOP that will contain the subtask's content

        Returns: None

        """
        section = ""
        checklist = ''

        # check for a checklist
        if subtask.fields.customfield_10102 is not None:
            checklist = self.__checklist2gfm(subtask.fields.customfield_10102)

        # format the section header
        section_header = "### " + subtask.fields.summary + " ###\n"
        section_detail = subtask.fields.description + '\n' if subtask.fields.description is not None else 'summary not provided' + '\n'

        section = section_header + section_detail + checklist

        self.markdown_document[section_name].append(section)
    
    def add_title_section(self, title):
        """ Create and adds the documents title section

        The title section contains the name of the project, the date the SOP was created
        and the date that it was last edited. This section appears at the top of the
        SOP document.

        """
        section = title[0] + "\n"
        section += "```sh\n"
        section += "Date Created: " + title[1] + "\n"
        section += "Last Updated: " +title[2] + "\n"
        section += "```\n"
        section += "---\n"

        self.markdown_document["title"].append(section)


    def add_project_info_section(self):
        """ Creates the project information section of the SOP document

        This will appear as a table at the top of the SOP document once rendered.
        It is created from the project info 

        """
        project_table = "| Project Name | Epic Name |\n"
        project_table += "| ------ | ------ |\n"
        project_table += "| **Client** | " + self.project_info["project_organization_name"] + " |\n"
        project_table += "| **Start Date** | " +  self.project_info["project_start_date"] + " |\n"
        project_table += "| **End Date** | " + self.project_info["project_end_date"] + " |\n"
        project_table += "| **Project Folder** | [" + self.project_info["project_folder"] +"]()|\n"
        project_table += "| **Summary** | " + self.project_info["project_summary"]  + " |\n"
        project_table += "---\n"
        project_table += "## Overview ##\n"
        project_table += self.project_info["project_description"]
        project_table += "\n\n---\n"

        self.markdown_document['project_info'].append(project_table)

    
    def set_project_info(self, epic=None, sop=None, name="Not Provided", start_date="1/1/1900", end_date="1/1/1900", description="Not Provided", summary="Not Provided", folder="http://solutionsitw.com", org_name="Not Provided"):
        """ Sets the meta data for the project

        Using a mix of custom fields and built in fields all of the key information about the project
        is established.

        Args:
            epic (issue): Jira epic isssue
            sop (issue): Jira SOP issue
            name (str): the name of the project
            start_date (date): the date that the project started or that the SOP was initiated
            end_date (date): the date that the project or SOP is scheduled to complete
            description (str): details about what needs to be accomplished by the project or SOP
            summary (str): a short description of the project or SOP
            folder (str): the url to the Google team drive folder for this 
            org_name (str): the name of the client that sommissioned the project

        """
        
        if epic:
            # epic name/project name
            self.project_info["project_name"] = name if epic.fields.customfield_10005 is None else epic.fields.customfield_10005
            
            # start date
            self.project_info["project_start_date"] = start_date if epic.fields.customfield_10093 is None else epic.fields.customfield_10093
            
            # end date
            self.project_info["project_end_date"] = end_date if epic.fields.customfield_10092 is None else epic.fields.customfield_10092

            # description
            self.project_info["project_description"] = description if epic.fields.description is None else epic.fields.description
            
            # summary
            self.project_info["project_summary"] = summary if epic.fields.summary is None else epic.fields.summary

            # project folder
            self.project_info["project_folder"] = folder if epic.fields.customfield_10101 else epic.fields.customfield_10101

            # organization
            self.project_info["project_organization_name"] = org_name if epic.fields.customfield_10095 is None else epic.fields.customfield_10095.value
        elif sop and not epic:
            # sop name/project name
            self.project_info["project_name"] = name if sop.fields.summary is None else sop.fields.summary
            
            # start date
            self.project_info["project_start_date"] = start_date if sop.fields.customfield_10093 is None else sop.fields.customfield_10093
            
            # end date
            self.project_info["project_end_date"] = end_date if sop.fields.customfield_10092 is None else sop.fields.customfield_10092

            # description
            self.project_info["project_description"] = description if sop.fields.description is None else sop.fields.description
            
            # summary
            self.project_info["project_summary"] = summary if sop.fields.summary is None else sop.fields.summary

            # project folder
            self.project_info["project_folder"] = folder if sop.fields.customfield_10101 else sop.fields.customfield_10101

            # organization
            self.project_info["project_organization_name"] = org_name if sop.fields.customfield_10095 is None else sop.fields.customfield_10095.value
        else:
            # default name/project name
            self.project_info["project_name"] = name
            
            # start date
            self.project_info["project_start_date"] = start_date
            
            # end date
            self.project_info["project_end_date"] = end_date

            # description
            self.project_info["project_description"] = description
            
            # summary
            self.project_info["project_summary"] = summary

            # project folder
            self.project_info["project_folder"] = folder

            # organization
            self.project_info["project_organization_name"] = org_name


        # not as elegant as a regex but it works as long as the url matches this
        # https://drive.google.com/drive/u/0/folders/1IampOt20ZtD_vVlfo4EwSf_m7eVSi331
        self.project_info["project_folder_id"] = "" if self.project_info["project_folder"] is None \
            else self.project_info["project_folder"][43:]

        self.jira_project['folder_id'] = self.project_info["project_folder_id"]

    