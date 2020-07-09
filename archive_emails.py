#!/usr/bin/env python
# coding: utf-8


from PyQt5 import QtWidgets, uic
from email import policy
from email.parser import BytesParser
import glob
import sqlite3
import os, sys
from zipfile import ZipFile
import zipfile
from EmailManagerConstants import constants
from datetime import datetime


version = constants['version']
DEVELOPING = constants['DEVELOPING']
EmailDBFName = constants['EmailDBFName']




class ArchiveEmails():

    """
    This class reads the .eml-files in the [emailfolder] and writes its contents
    ((idx, date, from, subject, spam, to, cc, bcc, path) into a sqlite DB
    as [EmailDBFName]

    a typical session with ArchiveEmails will be:

        from EmailManager import ArchiveEmails
        f = ArchiveEmails()
        f.ParseEMLs()

    In the [EmailDBFName] there are two tables:

    1. [EmailsTableName] for each .eml-file in [emailfolder]
       the attributes:
           idx (primary key)
           date
           time
           timezone
           sender
           subject
           spam
           fname
           receiver
           cc
           bcc
           path

    2. [EmailAddressesTableName]
       sender addresses and indication if this sender sends spam
           address (primary key)
           spam
           count
    """


    def __init__(self, emailfolder, app, dlg, EmailDBFName = EmailDBFName):

        """
        assigns values to the class variables:
        """

        self.EmailsTableName = constants['EmailsTableName']
        self.EmailAddressesTableName = constants['EmailAddressesTableName']
        self.emailfolder = emailfolder
        self.emails = emailfolder + '/*.eml'
        self.EmailZIPFName = emailfolder + '/Emails.zip'
        self.EmailDBFName = EmailDBFName
        self.ZipFile = ZipFile(self.EmailZIPFName, mode ='a',
                               compression = zipfile.ZIP_DEFLATED)
        self.LogFile = constants['LogFile']
        self.app = app    # needed for making EmaqilManager look multithreading
        self.dlg = dlg    # needed for being able to write to listWidget




    def OpenDB(self):

        """
        1. opens [EmailDBFName]
        2. creates a new [EmailsTableName] (SQLite)
        3. creates a new [EmailAddressesTableName] if doesn't exists (SQLIte)
        """

        self.con = sqlite3.connect(self.EmailDBFName)
        self.cursor = self.con.cursor()

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS """ + self.EmailsTableName + """ (
                date     TEXT,
                time     TEXT,
                timezone TEXT,
                sender   TEXT,
                subject  TEXT,
                spam     TEXT,
                fname    TEXT PRIMARY KEY,
                fsize    FLOAT,
                receiver TEXT,
                cc       TEXT,
                bcc      TEXT
                );
            """)


        self.con.execute("""
            CREATE TABLE IF NOT EXISTS """ + self.EmailAddressesTableName +
            """ (
            [address]   TEXT PRIMARY KEY,
            [spam]      TEXT,
            [count]     INT DEFAULT 1)
            """)






    def StringToList(self, s):
        """
        1. makes a list from comma separated items in a string
        2. strips the surrounding blanks of the itemns in the list

        EXAMPLE:
            >>> s = "mail1@mail.com,mail2@mail.com, mail3@mail.com"

            >>> StringToLIst(s)
            ['mail1@mail.com', 'mail2@mail.com', 'mail3@mail.com']
        """

        if s != None:
            lst = s.split(',')
        else:
            lst = []

        for i in range(len(lst)):
            lst[i] = lst[i].strip()

        return lst


    def ConvertDate(self, d):
        """

        converts a d:
                 10        20        30
        ....+....|....+....|....+....|.
        Wed, 01 Jan 2020 17:39:35 +0000

        into

        2020-01-01 17:39:35 +0000
        """
        try:
            if len(d) < 31:
                return(d, '', '' )
        except:
            return('None', 'None', 'None')

#       Months abrvs in english, dutch and french
        Months={'jan':'01','feb':'02','fev':'02','mar':'03','apr':'04', \
                'avr':'04','may':'05','mei':'05','mai':'05','jun':'06', \
                'jul':'07','aug':'08','sep':'09','oct':'10','okt':'10', \
                'nov':'11','dec':'12'}

        year = d[12:16]
        month = d[8:11].lower()
        try:
            month = Months[month]
        except:
            month = 'XX'
        day = d[5:7]
        date = year+'-'+month+'-'+day
        time = d[17:25]
        timezone = d[26:]
        return(date, time, timezone)



    def GetSize(self, fileobject):
        """
        gives the size of fileobject in bytes
        """
        fileobject.seek(0,2) # move the cursor to the end of the file
        size = fileobject.tell()
        return size



    def Mitigate(self, text):
#        print(text)
        self.closeDB()
        os.remove(self.EmailDBFName)
        os.remove(self.EmailZIPFName)
        sys.exit()



    def LogEntry(self, entry=''):
        """
        writes an entry into LogFile
        creates a new logfile if LogFile doesn't exist

        I am not happy with this function, but is used in bulk porcessing only
        """
        with open(self.LogFile, 'at') as log:
            if entry == '':
                log.write('\n')
            else:
                log.write(str(datetime.now())+ '   '  + entry+'\n')
#                print(str(datetime.now())+ '   '  + entry)
                self.giveNotice(entry)




    def giveNotice(self, msg=''):

        """
        writes current time and msg in the listWidget
        scrolls to the bottom of the list
        displays list again (with app.processEvents())

        an empty message causes a blank line in the listWidget
        """

        def currentTime():
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            return(current_time)


        if msg == '':
            self.dlg.listWidget.addItem(' ')
        else:
            self.dlg.listWidget.addItem(currentTime()+'   ' + msg)

        self.dlg.listWidget.scrollToBottom()




    def ParseEMLs(self):

        """
        Routine ParseEMLs:

        1. opens [EmailDBFName]
        2. parses the [emailfolder]
        3. adds an entry for every .eml in the [EmailsTableName]
        4. adds an entry for each NEW emailaddres in [EmailAddressesTableName]
        5. informs user of progress made
        6. commits changes and closes [EmailDBFName]
        """


        def add_zip_flat(zip, filename):
            """
            zips files without a path
            """
            dir, base_filename = os.path.split(filename)
            os.chdir(dir)
            zip.write(base_filename)



        self.OpenDB()
        emails = self.emailfolder + '/*.eml'
        filelist = glob.glob(emails)
        filecounter = 0

        for file in filelist:
            self.app.processEvents()
            with open(file, 'rb') as fp:
                file = file.replace('\\','/')

                try:  # just to prevent writing when the ZIPfile is open
                    add_zip_flat(self.ZipFile, file)
                except:
                    self.closeDB()
                    self.LogEntry('Program had difficulties with zipping ' + \
                          'files in archive_emails.py')
                    sys.exit()

                msg = BytesParser(policy=policy.default).parse(fp)
                filesize = round(self.GetSize(fp)/1024/1024, 2) # in Mb's
                filecounter += 1


                if filecounter % 500 == 0:
                    self.LogEntry('processed ' + str(filecounter) +'.eml-files')

                FullFName = os.path.split(file)

                FName = FullFName[1]
#                Path = FullFName[0]
                try:
                    Date, Time, TimeZone = self.ConvertDate(msg['date'])
                except:
                    Date='Invalid'
                    Time='Invalid'
                    TimeZone ='Invalid'

                self.con.execute("""
                    INSERT INTO """ + self.EmailsTableName + """
                    (
                    fname,
                    fsize,
                    sender,
                    receiver,
                    date,
                    time,
                    timezone,
                    subject,
                    cc,
                    bcc,
                    spam
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                    FName,
                    filesize,
                    msg['from'],
                    msg['to'],
                    Date,Time, TimeZone,
                    msg['subject'],
                    msg['cc'],
                    msg['bcc'],
                    msg['X-XS4ALL-Spam']
                    ))



                # add (possible new) addresses to addressbook and spam-indication
                address = msg['from']

                try:
                    self.con.execute("""
                    INSERT INTO """ + self.EmailAddressesTableName +
                    """ (address, spam) VALUES (?, ?)
                    ON CONFLICT(address) DO UPDATE SET spam = ?""",
                    (address, msg['X-XS4ALL-Spam'], msg['X-XS4ALL-Spam']))
                except:
                    self.Mitigate('Updating '+ self.EmailAddressesTableName + \
                                  '(1) went wrong\n' + 'FileName ='+FName)


                AllAddresses = self.StringToList(msg['to']) + \
                self.StringToList(msg['cc']) + self.StringToList(msg['bcc'])

                try:
                    for address in AllAddresses:
                        self.con.execute("""
                        INSERT INTO """ + self.EmailAddressesTableName +
                        """ (address) VALUES (?)
                        ON CONFLICT(address) DO UPDATE SET count = ?""",
                        (address, 1))
                except:
                    self.Mitigate('Updating '+ self.EmailAddressesTableName + \
                                  '(1) went wrong\n' + 'FileName ='+FName)

        self.closeDB()

        return filecounter, filelist



    def ParseEmails(self):
        """
        Calls ParseEMLs, so is functional the same
        """
        n = self.ParseEMLs()
        return n


    def closeDB(self):
        """
        1. commits changes to EmailDBFName
        2. closes the DB-file
        """
        self.con.commit()
        self.con.close()
        self.ZipFile.close()




    def ExecuteSQLstatements(self, SQL):

        try:
            self.con.execute(SQL)
            msg = 'SQL executed'
        except:
            msg = 'Could not execute SQL'

        return msg














