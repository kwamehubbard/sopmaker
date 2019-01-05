# SOP Maker Notes #
## JQL ##
returns the sop and it the subtasks
'(parent=' + issue.key + ' AND type=Sub-task) OR key='+ issue.key + ' ORDER BY key'

## To Do ##
1. ~~Add support for Google Drive access~~
2. If possible allow for SOP Maker to run as job that conntinually updates SOP documentation
3. ~~Move configuration outside of the application~~
4. ~~Allow for script to discover new SOPs and create the document~~
5. ~~Script needs to get a list of all client folders and their id. A mapping will be necessary so that when the SOP is created it is saved to the correct folder.~~ Link to folder is in the SOP. The script is able to parse the link to get the folder id.
6. Add logging
    1. ~~Log the number of epics/projects scanned~~
    2. ~~The number of SOPs created~~
    3. count of open items
7. Reporting
    1. For each SOP report on who owes what
8.  Add method to retrieve issue properties (checklits)
