# -*- coding: utf-8 -*-
"""
Spyder Editor

EMAILMANAGER

(c) Ferdi Ploeger 2020-03-07




make an .exe-file from these scripts with:

	pyinstaller -w -F -i "EmailManager.ico" emailmanager.py

"""
import pathlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from zipfile import ZipFile

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QIcon
from archive_emails import ArchiveEmails
from EmailManagerConstants import constants

#from pandas import read_sql




# Parameters
FolderOfTheScriptBeingRun = str(pathlib.Path(__file__).parent.absolute())

version = constants['version']
DEVELOPING = constants['DEVELOPING']
EmailManagerStartFolder = constants['EmailManagerStartFolder']
LogFile = constants['LogFile']
EmailDBFName = constants['EmailDBFName']






class EmailManager():

    """
    Methods to handle saved .eml-files that are stored locally
    routines to write parameters of .eml-files into SQLite database
    """


    def __init__(self, dlg):

        """
        1. read the file: C:/EmailManager/EmailManager.json if it exists

           If this file doesn't exist: create one with default folder C:/
           and number of restarts = 1

        2. sets as default folder the folder mentioned in EmailManager.info

        3. read the number of restarts, add 1 to it and write this back to
           the file

        """

        # init defaults by reading 'c:/EmailManager/EmailManager.json'
        try:
            with open(EmailManagerStartFolder+'/EmailManager.json', 'r') as file:
                self.defaults = json.load(file)
        except:
            try:
                os.mkdir(EmailManagerStartFolder)
            except:
                pass
            self.defaults = {'DefaultFolder':'C:/', 'NrOfRestarts':1}

            with open(EmailManagerStartFolder+'/EmailManager.json', 'w') as file:
                json.dump(self.defaults, file)


        self.dlg = dlg

        self.LogEntry()
        self.LogEntry('started EmailManager version ' + version)

        self.dlg.listWidget.hide()
        self.dlg.closeButton.hide()
        self.dlg.CSVButton.hide()
        self.dlg.tableWidget.hide()
        self.dlg.textEdit.hide()
        self.dlg.OKButton.hide()
        self.dlg.cancelButton.hide()
        # see : https://pythonspot.com/pyqt5-table/




    def LogEntry(self, entry=''):
        """
        writes an entry into LogFile
        creates a new logfile if LogFile doesn't exist
        """
        with open(LogFile, 'at') as log:
            if entry == '':
                log.write('\n')
            else:
                log.write(str(datetime.now())+ '   '  + entry+'\n')
                self.giveNotice(entry)




    def GetAllFiles(self, rootdir, ext='.eml'):
        """
        returns a list of all files with given extension in rootdir and its
        subfolders
        """
        ext = ext.lower()
        length = len(ext)

        allfiles = []

        for subdir, _, files in os.walk(rootdir):
            for file in files:
                if file[-length:] == ext:
                    allfiles.append(os.path.join(subdir, file))

        return allfiles




    def RenameAllFiles(self, rootdir, ext='.eml'):

        """
        renames all files with given extension in rootdir and its subfolders
        to a series FILE1.ext, FILE2.ext, FILE3.ext, ...
        """

        files = self.GetAllFiles(rootdir)

        NrRestarts = str(self.defaults['NrOfRestarts'])
        FileNo = 0

        for file in files:
            FileNo += 1
            FName = '/TEMPFILE-'+NrRestarts+'-'+str(FileNo)+ext
            os.rename(file, rootdir+FName)

            if FileNo % 500 == 0:
                self.LogEntry(str(FileNo) + ' files renamed to TEMPFILEs')

        self.LogEntry(str(FileNo) + ' files renamed to TEMPFILEs')

        files = self.GetAllFiles(rootdir)
        FileNo = self.localdefaults['LastFileNr']
        FileNo_0 = FileNo

        for file in files:
            FileNo += 1
            FName = '/FILE'+str(FileNo)+ext
            os.rename(file, rootdir+FName)

            if (FileNo-FileNo_0) % 500 == 0:
                self.LogEntry(str(FileNo-FileNo_0)+' TEMPFILEs renamed to FILEs')


        self.LogEntry(str(FileNo - FileNo_0)+ ' TEMPFILEs renamed to FILEs')

        self.localdefaults['LastFileNr'] = FileNo

        entry = 'Renamed files FILE' + str(FileNo_0+1) + '.eml through FILE' + \
            str(FileNo)+'.eml'
        self.LogEntry(entry)

        self.localdefaults['LastFileNr'] = FileNo
        self.defaults['NrOfRestarts'] += 1
        with open(rootdir+'/localEmailManager.json', 'w') as file:
            json.dump(self.localdefaults, file)
        with open(EmailManagerStartFolder+'/EmailManager.json', 'w') as file:
            json.dump(self.defaults, file)

        nr_renamed = FileNo-FileNo_0
        return nr_renamed








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
            return current_time


        if msg == '':
            self.dlg.listWidget.addItem(' ')
        else:
            self.dlg.listWidget.addItem(currentTime()+'   ' + msg)

        self.dlg.listWidget.scrollToBottom()
        app.processEvents()






    def resetListBox(self, initialise=''):
        self.dlg.tableWidget.hide()
        self.dlg.listWidget.clear()
        self.dlg.listWidget.show()
        self.dlg.CSVButton.hide()
        self.dlg.textEdit.hide()
        self.dlg.closeButton.show()
        self.LogEntry(initialise)







    def actionArchiveEmails(self):

        """
        Gets it DefaultFolder from dict defaults in
           C:/EmailManager/EmailManager.json
        Asks confirmation of defaultfolder with QFileDialog
        processes all the .eml-files in the defaultfolder AND its subfolders
        writes results into SQLite database
           emails.db (see ArchiveEmails.py)
        """

        fname = QFileDialog.getOpenFileName(
            directory=self.defaults['DefaultFolder'],
            filter='Email Files (*.eml)')


        # check whether the user wants to parse the DefaultFolder or another one
        if fname[0] != '': # QFileDialog is NOT cancelled
            Path = os.path.split(fname[0])[0]

            # start with a clean listbox:
            self.resetListBox('Archiving starts...')

            try:
                with open(Path+'/localEmailManager.json', 'r') as file:
                    self.localdefaults = json.load(file)
            except Exception as exc:
                self.LogEntry(str(exc))
                self.localdefaults = {'LastFileNr': 0}
                with open(Path+'/localEmailManager.json', 'w') as file:
                    json.dump(self.localdefaults, file)
                    self.LogEntry('Created new '+Path+'/localEmailManager.json')


            self.LogEntry('processing .eml-files in "'+Path+'/*.eml"')
            FilesRenamed = self.RenameAllFiles(Path)
            self.LogEntry(str(FilesRenamed)+' .eml-files renamed')

            fp = ArchiveEmails(Path, app, dlg, Path+'/Emails.db')

            FilesProcessed, filelist = fp.ParseEmails()

            self.LogEntry(str(FilesProcessed)+' .eml-files processed and zipped')

            # now the files from filelist are processed, but they are still
            # there: delete them!
            for file in filelist:
                os.remove(file)
            self.LogEntry(str(FilesProcessed)+' .eml-files deleted')










    def SetDefaultFolder(self):

        """
        Select a folder that the program will use as 'default-folder'
        In this folder the .eml-files are processed into Email.db,
        Email.zip and LocalEmail.json
        """

        folder = '-'

        while folder != '':
            folder = str(QtWidgets.QFileDialog.getExistingDirectory())
            if folder != '':
                self.defaults['DefaultFolder'] = folder

            with open(EmailManagerStartFolder+'/EmailManager.json', 'w') as file:
                json.dump(self.defaults, file)

            self.LogEntry('Default folder set to "' + \
                          self.defaults['DefaultFolder']+'"')
            break





    def DeleteLogfile(self):

        """
        Deletes logfile and hides the listWidget of the LogFile
        """
        os.remove(LogFile)
        self.LogEntry('New Logfile created')




    def ResetNrOfRestarts(self):

        """
        sets defaults['NrOfRestarts'] to 0 and writes defaults back to:
           C:/EmailManager/EmailManager.json
        """

        self.defaults['NrOfRestarts'] = 0

        with open('c:/EmailManager/EmailManager.json', 'w') as file:
            json.dump(self.defaults, file)

        self.LogEntry('Reset nr of restarts to 1')




    def OpenFile(self):

        """
        shows (any) file with its default application
        """
        fname = QFileDialog.getOpenFileName(
            directory=self.defaults['DefaultFolder'],
            filter='Any File (*.*)')

        if fname[0] != '':
            path = os.path.split(fname[0])[0]
            FName = os.path.split(fname[0])[1]

            os.chdir(path)
            os.startfile(FName)

            self.LogEntry('opened "'+path+'/'+FName+'" in its default app')



    def LogFile(self):
        """
        Shows LogFile   (c:/emailamanger/EmailManager.log)
        """
        self.HideWidgets()
        self.dlg.listWidget.clear()
        self.dlg.listWidget.show()
        self.dlg.closeButton.show()
        self.LogEntry('Opened LogFile on screen')

        with open(LogFile, 'r') as File:
            Lines = File.readlines()

        for line in Lines:
            self.dlg.listWidget.addItem(line.strip('\n'))

        self.dlg.listWidget.scrollToBottom()



    def HideWidgets(self):
        """
        Hides LogFile, listWidget and tableWidget
        """
        self.dlg.listWidget.hide()
        self.dlg.tableWidget.hide()
        self.dlg.closeButton.hide()
        self.dlg.CSVButton.hide()
        self.dlg.textEdit.hide()
        self.dlg.OKButton.hide()
        self.dlg.cancelButton.hide()
        self.LogEntry('closed screens')










    def actionHow_the_program_works(self):
        """
        Displays help
        """
        self.dlg.listWidget.clear()
        directory = FolderOfTheScriptBeingRun+'/EmailManagerHelp'
        os.chdir(directory)
        os.startfile('UserGuide.pdf')
        self.LogEntry('used: EmailManagerHelp')

        if DEVELOPING:
            print('WARNING: actionHow_the_program_works needs to be adapted')




    def actionSQL_examples(self):
        """
        Displays some simple examples of the use of SQL
        """
        self.dlg.listWidget.clear()
        directory = FolderOfTheScriptBeingRun+'/EmailManagerHelp'
        os.chdir(directory)
        os.startfile('SQL-Examples.pdf')
        self.LogEntry('used: SQL-examples')




    def SQLite_Tutorial(self):
        """
        Displays the SQLite Tutorial
        """
        self.dlg.listWidget.clear()
        directory = FolderOfTheScriptBeingRun+'/EmailManagerHelp'
        os.chdir(directory)
        os.startfile('SQLite Tutorial.pdf')
        self.LogEntry('used: SQLite Tutorial')




    def actionAbout(self):
        """
        displays name, version and author of this script
        """
        self.dlg.listWidget.clear()
        directory = FolderOfTheScriptBeingRun+'/EmailManagerHelp'
        os.chdir(directory)
        os.startfile('About.pdf')
        self.LogEntry('used: actionAbout')

        if DEVELOPING:
            print('WARNING: actionAbout needs to be adapted')



    def actionOpen_zipped_emailfile(self):
        """
        Opens Emails.zip
        """

        self.dlg.listWidget.clear()
        self.dlg.listWidget.show()
        self.dlg.closeButton.show()

        directory = self.defaults['DefaultFolder']
        os.chdir(directory)
        os.startfile('Emails.zip')
        self.LogEntry('used: actionOpen_zipped_emailfile')




    def actionOpen_emails_db(self):
        """
        Opens Emails.db in SQLite Studio

        """
        directory = self.defaults['DefaultFolder']
        os.chdir(directory)
        self.dlg.listWidget.clear()
        self.dlg.listWidget.show()
        self.dlg.closeButton.show()

        try:
            os.startfile('Emails.db')
            self.LogEntry('opened: Emails.db in SQLiteStudio')
        except:
            self.LogEntry('Could not open Emails.db in SQLiteStudio')




    def actionSelect_Emails(self):

        """
        This function reads a list of filenames of files that are stored
        in the emails.zip-file, retrieves them from the emails.zip-file
        and writes them into a folder with the same name as the name of the
        listfile. The files in this folders will be renamed FILE0001.eml,
        FILE0002.eml, ... according to their position on the listfile.
        The new folder will be written in the same folder where the list
        was read

        EXAMPLE:
            The listfile has the name 'list.txt' (it should be a .txt-file)
            it has the content of:
                FILE8977.eml
                FILE3.eml
                FILE789.eml
            which is the result of a SQL-selection from Emails.db

            written into the folder list wil be the files:
                FILE0001.eml (= FILE8977.eml)
                FILE0002.eml (= FILE3.eml)
                FILE0003.eml (= FILE789.eml)
        """



        def zfill4(x):
            """
            local function supplies leading zeroes
            """
            return ('0000'+str(x))[-5:]



        # def delete(folder):
        #     """
        #     local delete funcion
        #     """
        #     try:
        #         os.chdir(folder)
        #     except:
        #         pass # folder didn't exist




        fname = QFileDialog.getOpenFileName(
            directory=self.defaults['DefaultFolder'],
            filter='Text Files (*.txt)')

        if fname[0] != '':
            msg = 'selected "'+fname[0]+'" for retrieving emails'
            self.resetListBox()
            self.LogEntry(msg)

            path = os.path.split(fname[0])[0]
            FName = os.path.split(fname[0])[1]
            ResultsFolder = path + '/'+ os.path.splitext(FName)[0]

            os.chdir(path)

            with open(fname[0], 'rt') as file:
                ZippedFiles = file.readlines()

            folder = self.defaults['DefaultFolder']
            os.chdir(folder)


            zipObj = ZipFile(self.defaults['DefaultFolder']+'/Emails.zip', 'r')

            shutil.rmtree(ResultsFolder, ignore_errors=True)
            msg = 'Deleted folder ' + ResultsFolder + ' (if existed)'
            self.LogEntry(msg)

            NewFileNr = 0
            for n in range(len(ZippedFiles)):
                NewFileNr += 1
                ZippedFile = ZippedFiles[n].strip('\n')
                zipObj.extract(ZippedFile, ResultsFolder)

                NewFName = ResultsFolder + '/FILE' + zfill4(NewFileNr) + '.eml'
                OldFName = ResultsFolder + '/' + ZippedFile

                os.rename(OldFName, NewFName)

            msg = 'Put FILE0001.eml - FILE' + zfill4(NewFileNr) + '.eml' \
             + ' into the folder ' + ResultsFolder
            self.LogEntry(msg)
            self.LogEntry(str(NewFileNr) + ' Emails extracted from ' + \
               self.defaults['DefaultFolder']  + '/Emails.zip')






    def actionSelect_Emails_with_SQL(self):
        """
        asks for an edited SQL-file (from NotePad) anywhere on the system
        performs SQL query on Emails.db in default folder
        displays result in self.dlg.tableWidget
        sets self.defaults['ResultsFolder'] to the folder where the SQL-file
           was in: this will be used by self.ShowEmail
        """

        fname = QFileDialog.getOpenFileName(
            directory=self.defaults['DefaultFolder'],
            filter='SQL Files (*.sql)')

        if fname[0] != '':
            msg = 'selected "'+fname[0]+'" for retrieving emails'
            self.resetListBox(msg)
#            self.LogEntry(msg+'------')

            path = os.path.split(fname[0])[0]
            FName = os.path.split(fname[0])[1]
            ResultsFolder = path + '/'+ os.path.splitext(FName)[0]
            self.defaults['ResultsFolder'] = ResultsFolder

            shutil.rmtree(ResultsFolder, ignore_errors=True)
            msg = 'Deleted folder ' + ResultsFolder + ' (if existed)'
            self.LogEntry(msg)

            self.LogEntry('processing SQL in ' + fname[0])

            with open(fname[0], 'rt') as file:
                SQLstatements = file.read()

            self.LogEntry('SQL statements were:\n\n'+SQLstatements+'\n')

            EmailDBFName = self.defaults['DefaultFolder'] + \
                 constants['EmailDBFName']

            con = sqlite3.connect(EmailDBFName)
            cur = con.cursor()

            try:
                cur.execute(SQLstatements)
                names = list(map(lambda x: x[0], cur.description))

                # try to find a column with the name 'fname' for later
                # highlighting
                try:
                    fname_column = names.index('fname')
                except:
                    fname_column = -1

                rows = cur.fetchall()

                rowcount = len(rows)
                columncount = len(rows[0])
                self.LogEntry(str(rowcount) + ' records found')
                self.HideWidgets()
                self.dlg.tableWidget.setRowCount(rowcount)
                self.dlg.tableWidget.setColumnCount(columncount)
                self.dlg.tableWidget.setHorizontalHeaderLabels(names)

                self.dlg.tableWidget.show()
                self.dlg.closeButton.show()

                # here is an attempt to display the column 'fname' different
                # maybe give it another font or another color ?
                for rw in range(rowcount):
                    row = rows[rw]
                    for cl in range(columncount):
                        item = row[cl]
                        if cl == fname_column:  # here is the column 'fname'
                            # how to give this display a different look?
                            self.dlg.tableWidget.setItem(rw, cl, \
                                QTableWidgetItem(str(item)))
                        else:  # other columns
                            self.dlg.tableWidget.setItem(rw, cl, \
                                QTableWidgetItem(str(item)))

                self.LogEntry('SQL-statements executed')
            except:
                self.LogEntry('SQL-statements NOT executed or no records found')






    def ShowEmail(self):
        """
        when clicked on a filename in the displayed self.dlg.tableWidget
        it will extract the file from Emails.zip in the defaultfolder
          ( self.defaults['DefaultFolder'])
        and it will display the email on screen
        """
        col = self.dlg.tableWidget.currentColumn()
        row = self.dlg.tableWidget.currentRow()
        item = self.dlg.tableWidget.item(row, col).text()
        ResultsFolder = self.defaults['ResultsFolder']

        archive = ZipFile(self.defaults['DefaultFolder']+'/Emails.zip', 'r')
        try:
            archive.extract(item, ResultsFolder)
            os.chdir(ResultsFolder)
            os.startfile(item)
            self.LogEntry('Extracted, saved and showed ' + item)
        except:
            if DEVELOPING:
                print(item, 'is not a file')




    def exec_SQL(self):
        """
        Executes SQL-statement and writes its result into self.tableWidget
        sets the resultsfolder to constants['DefaultResults']
        """
        SQLstatements = self.sql
        EmailDBFName = self.defaults['DefaultFolder'] + \
              constants['EmailDBFName']
        con = sqlite3.connect(EmailDBFName)
        cur = con.cursor()
        ResultsFolder = constants['DefaultResults']
        self.defaults['ResultsFolder'] = ResultsFolder
        shutil.rmtree(ResultsFolder, ignore_errors=True)
        msg = 'Deleted folder ' + ResultsFolder + ' (if existed)'
        self.LogEntry(msg)


        try:
            cur.execute(SQLstatements)
            names = list(map(lambda x: x[0], cur.description))
            rows = cur.fetchall()

            rowcount = len(rows)
            self.LogEntry(str(rowcount) + ' records found')
            columncount = len(rows[0])
            self.HideWidgets()
            self.dlg.tableWidget.setRowCount(rowcount)
            self.dlg.tableWidget.setColumnCount(columncount)
            self.dlg.tableWidget.setHorizontalHeaderLabels(names)

            self.dlg.tableWidget.show()
            self.dlg.closeButton.show()
            self.dlg.CSVButton.hide()

            for rw in range(rowcount):
                row = rows[rw]
                for cl in range(columncount):
                    item = row[cl]
                    self.dlg.tableWidget.setItem(rw, cl, \
                        QTableWidgetItem(str(item)))

            self.LogEntry('SQL-statements executed')
        except:
            self.LogEntry('SQL-statements NOT executed or no records found')

        con.close()




    def emails_from_last_month(self):
        """
        assembles an sql to select all emails of last month
        sql is then executed by self.exec_SQL
        """
        today = datetime.now()
        month_ago = today - timedelta(days=31)
        today = today.strftime("%Y-%m-%d")
        month_ago = month_ago.strftime("%Y-%m-%d")

        sql = "SELECT * FROM emails WHERE date <= '{}' AND date >= '{}' " \
            + " ORDER BY date, time"
        self.sql = sql.format(today, month_ago)

        self.OutFName = today +', last month.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed all emails of last month (" + month_ago +"  -  " \
                      +today+')')



    def emails_from_today(self):
        """
        assembles an sql to select all emails of today
        sql is then executed by self.exec_SQL
        """
        today = datetime.now().strftime("%Y-%m-%d")

        sql = "SELECT * FROM emails WHERE date = '{}' ORDER BY time"
        self.sql = sql.format(today,)

        self.OutFName = today +', today.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed all emails from today ({})".format(today))



    def emails_from_last_week(self):
        """
        assembles sql to select all emails of last week
        sql is then executed by self.exec_SQL
        """
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        today = today.strftime("%Y-%m-%d")
        week_ago = week_ago.strftime("%Y-%m-%d")

        sql = "SELECT * FROM emails WHERE date <= '{}' AND date >= '{}'" \
            + " ORDER BY date, time"
        self.sql = sql.format(today, week_ago)

        self.OutFName = today +', last week.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed all emails of last week ({} - {})" \
                      .format(week_ago, today))




    def actionfrom_today_no_spam(self):
        """
        assembles an sql to select all emails of today (spam excluded)
        sql is then executed by self.exec_SQL
        """
        today = datetime.now().strftime("%Y-%m-%d")

        sql = """SELECT * FROM emails
                  WHERE (spam <> 'YES' OR spam IS NULL) and
                  date = '{}'
                 ORDER BY time"""
        self.sql = sql.format(today,)

        self.OutFName = today +', today.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed emails from today ({}), spam excluded".format(today))



    def actionfrom_last_week_no_spam(self):
        """
        assembles sql to select all emails of last week (spam excluded)
        sql is then executed by self.exec_SQL
        """
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        today = today.strftime("%Y-%m-%d")
        week_ago = week_ago.strftime("%Y-%m-%d")

        sql = """SELECT * FROM emails
                  WHERE (spam <> 'YES' OR spam IS NULL) and
                  date <= '{}' AND date >= '{}'
                 ORDER BY date, time"""
        self.sql = sql.format(today, week_ago)

        self.OutFName = today +', last week.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed emails of last week ({} - {}), spam excluded" \
                      .format(week_ago, today))



    def actionfrom_last_month_no_spam(self):
        """
        assembles an sql to select all emails of last month (spam excluded)
        sql is then executed by self.exec_SQL
        """
        today = datetime.now()
        month_ago = today - timedelta(days=31)
        today = today.strftime("%Y-%m-%d")
        month_ago = month_ago.strftime("%Y-%m-%d")

        sql = """SELECT * FROM emails
                  WHERE (spam <> 'YES' OR spam IS NULL) and
                  date <= '{}' AND date >= '{}'
                 ORDER BY date, time"""
        self.sql = sql.format(today, month_ago)

        self.OutFName = today +', last month.csv'
        self.exec_SQL()
        self.dlg.CSVButton.hide()
        self.LogEntry("Showed emails of last month (" + month_ago +"  -  " \
                      +today+'), spam excluded')




    # def MakeCSV(self):
    #     """
    #     """
    #     # EmailDBFName = self.defaults['DefaultFolder'] + \
    #     #     constants['EmailDBFName']
    #     # ResultsFolder = self.defaults['ResultsFolder']
    #     # os.mkdir(ResultsFolder)

    #     # con = sqlite3.connect(EmailDBFName)

    #     # result = read_sql(self.sql, con)
    #     # result.to_csv(ResultsFolder + '/' + self.OutFName)
    #     # dlg.CSVButton.hide()
    #     # self.dlg.tableWidget.hide()
    #     # self.dlg.listWidget.show()
    #     # self.LogEntry('created ' + ResultsFolder+ '/' + self.OutFName)
    #     # con.close()
    #     pass


    def showTextEdit(self):
        self.HideWidgets()
        dlg.textEdit.show()
        dlg.OKButton.show()
        dlg.cancelButton.show()




    def actionwith_SQL(self):
        """
        Description
        -----------
        presents a bare SQL-statement in dlg.textEdit to be editted by the
        end-user to search for movies
        When the enduser is satisfied with the editted sql statement the
        method self.execSQL() tries to execute this statement. If the statement
        contains errors or doesn't have any result self.execSQL() adds an
        errormessage to dlg.textEdit

        Returns
        -------
        None.
        although self.textEdit is made available for self.execSQL()

        """

        today = datetime.now().strftime("%Y-%m-%d")

        self.sql = ''
        dlg.textEdit.clear()
        dlg.textEdit.append(
            """/* Modify this rump SQL-statement */

            SELECT *
              FROM emails
             WHERE sender LIKE '%---%' AND
                   receiver LIKE '%---%' AND
                   subject LIKE '%---%' AND
                   (spam <> 'YES' OR spam IS NULL) AND
                   date >= '{}' AND
                   date <= '{}'
             ORDER BY date,
                      time;

            """.format(today, today))
        self.showTextEdit()





    def exec_inner_SQL(self):
        """
        Executes SQL-statement and writes its result into self.tableWidget
        if the SQL-statement doesn't execute (errors) or doesn't have a
        result it adds a warning to dlg.textEdit.

        if the SQL-statement results in records being found it shows them by
        invoking self.showTableWidget
        """

        EmailDBFName = self.defaults['DefaultFolder'] + constants['EmailDBFName']

        con = sqlite3.connect(EmailDBFName, timeout=10)
        cur = con.cursor()

        try:
            self.sql = dlg.textEdit.toPlainText()
            cur.execute(self.sql)
        except:
            dlg.textEdit.append('\n /* Syntax error */')
            return None

        names = list(map(lambda x: x[0], cur.description))
        rows = cur.fetchall()
        if rows == []:
            dlg.textEdit.append('\n /* No records found */')
            return None

        # try:
        #     self.pathColumn = names.index('fname')
        # except:
        #     dlg.textEdit.append(
        #         '\n /* fname should be in the query %/')
        #     return None

        rowcount = len(rows)
        columncount = len(rows[0])
        self.HideWidgets()
        dlg.tableWidget.setRowCount(rowcount)
        dlg.tableWidget.setColumnCount(columncount)
        dlg.tableWidget.setHorizontalHeaderLabels(names)

        for rw in range(rowcount):
            row = rows[rw]
            for cl in range(columncount):
                item = row[cl]
                dlg.tableWidget.setItem(rw, cl, \
                    QTableWidgetItem(str(item)))

        self.dlg.tableWidget.show()
        self.dlg.closeButton.show()
        self.dlg.CSVButton.hide()


        # except:
        #     dlg.textEdit.append(
        #         '\n /* SQL statement contains errors or has no results*/')
        con.close()








# main
app = QtWidgets.QApplication([])
dlg = uic.loadUi(FolderOfTheScriptBeingRun+"/emailmanager.ui")
dlg.setWindowTitle('EmailManager (version ' + version + ')')
dlg.setWindowIcon(QIcon(FolderOfTheScriptBeingRun+'/EmailManager.ico'))
f = EmailManager(dlg)


# Actions:

# Menuheader Actions
dlg.actionArchiveEmails.triggered.connect(f.actionArchiveEmails)
dlg.actionSelect_Emails.triggered.connect(f.actionSelect_Emails)
dlg.actionSelect_Emails_with_SQL.triggered.connect(f.actionSelect_Emails_with_SQL)
dlg.actionwith_SQL.triggered.connect(f.actionwith_SQL)

# Get Emails
dlg.emails_from_today.triggered.connect(f.emails_from_today)
dlg.emails_from_last_week.triggered.connect(f.emails_from_last_week)
dlg.emails_from_last_month.triggered.connect(f.emails_from_last_month)

dlg.actionfrom_today_no_spam.triggered.connect(f.actionfrom_today_no_spam)
dlg.actionfrom_last_week_no_spam.triggered.connect(f.actionfrom_last_week_no_spam)
dlg.actionfrom_last_month_no_spam.triggered.connect(f.actionfrom_last_month_no_spam)

# Menuheader Options
dlg.actionSet_default_folder.triggered.connect(f.SetDefaultFolder)
dlg.actionDelete_logfile.triggered.connect(f.DeleteLogfile)
dlg.actionReset_nr_of_restarts.triggered.connect(f.ResetNrOfRestarts)
dlg.actionOpen_a_file.triggered.connect(f.OpenFile)
dlg.actionLogFile.triggered.connect(f.LogFile)
dlg.actionOpen_zipped_emailfile.triggered.connect(f.actionOpen_zipped_emailfile)
dlg.actionOpen_emails_db.triggered.connect(f.actionOpen_emails_db)

# Menuheader Help
dlg.actionHow_the_program_works.triggered.connect(f.actionHow_the_program_works)
dlg.actionAbout_2.triggered.connect(f.actionAbout)
dlg.actionSQLite_Tutorial.triggered.connect(f.SQLite_Tutorial)
dlg.actionSQL_examples.triggered.connect(f.actionSQL_examples)

# miscs actions
dlg.closeButton.clicked.connect(f.HideWidgets)
dlg.tableWidget.clicked.connect(f.ShowEmail)
dlg.cancelButton.clicked.connect(f.HideWidgets)
dlg.OKButton.clicked.connect(f.exec_inner_SQL)

#dlg.CSVButton.clicked.connect(f.MakeCSV)


dlg.show()
app.exec()
