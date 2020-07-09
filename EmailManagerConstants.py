# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 09:07:52 2020

@author: Ferdi


WORTH LOOKING AT:
    https://www.youtube.com/watch?v=e-OZeAHFpkw
    http://www.silx.org/doc/silx/0.6.1/index.html


2020-03-22
Replaced the print-statements that showed progress when testing the program
with self.LogEntry statements.

Fear is that, although the .eml-files are saved, the images are not. Maybe even
the attachments are not saved. Is quite complicated to find out and to mitigate
where needed.

2020-03-30
Responded to 'static code analysis' (F8)
Didn't change isues around snake-case naming and UPPER_CASE naming (tricky)
program still seems to work. Keep situation as in 2020-03-29 for safety in
zip-file

2020-05-20
Added extra option 'with SQL' allowing to adapt a basic SQL-statement, rather then
allowing just executing SQL from a seperate file as now is the option 'with SQL from file'.
"""

DEVELOPING = True
EmailManagerStartFolder = 'C:/EmailManager'
DefaultResultsFolder = 'C:/EmailManagerResults'
LogFile = EmailManagerStartFolder + '/PythonEmailManager.log'
SQLiteStudio = 'C:/Program Files/SQLiteStudio/SQLiteStudio.exe'
EmailDBFName = '/Emails.db'


constants = \
    {'DEVELOPING' : False,
     'version' : '2020-07-09',
     'EmailManagerStartFolder' : EmailManagerStartFolder,
     'LogFile' : LogFile,
     'SQLiteStudio' : SQLiteStudio,
     'EmailDBFName' : EmailDBFName,
     'EmailsTableName' : 'emails',
     'EmailAddressesTableName' : 'addresses',
     'DefaultResults' : DefaultResultsFolder
     }
