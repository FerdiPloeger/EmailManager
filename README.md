# EmailManager
archives emails in .zip-files and keeps track of them in a SQLite Database

Python script
EmailManager reads and processes .eml-files (emails) in a 'default'-folder. 
EmailManager can handle more then one 'default'-folders

Of each email a record with date, time, sender, receiver, subject, spam, size, cc's, bcc's is written as table 'emails' into SQLite database
In a table 'addresses' are kept all the addresses given in sender, receiver, cc's and bcc's

then emails are stored in a .zip-file and the .eml-files in the folder are deleted. 

EmailManager is able to produce tables (emails today, last week, last month (with or without spam) or offers a rump-sql
statement to be amended to do a special query

Clicking on the FileName of the email in the table makes EmailManager retrieve the email from the .zipfile and display it on screen whilst
saving this email in a dedicated folder for later use


