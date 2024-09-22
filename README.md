This is a Python script that uses the Gmail API to fetch emails from a specified folder and store the sender information in a SQLite database. 
The script also includes functionality to block specific senders and update the database accordingly.
Sender_get.py
•	Authenticate and return the Gmail service
•	Define the Database Structure
•	Fetch the information from the folder(s)
•	Parse the Sender Information: Sender: Google Calendar <mailto:calendar-notification@google.com>, Count: 4
•	Store Data in SQLite Database
•	Regular Updates and De-Duplication: Implement logic to update the database whenever new emails are fetched
Use the DB browser for SQLite
•	Querying and Viewing the Data
•	Create a new database with the blocked sender list
Blocked.py
•	Upload this new database into blocked.py
•	Authenticate and return the Gmail service
•	Fetch from database
•	Select senders to block: Displays senders numbered and allows user to select which ones to block via terminal, e.g. ‘Enter the numbers of the senders you want to block (comma-separated): 170, 111, 112.’
•	Create Gmail filter: Creates a Gmail filter to automatically delete emails from a specific sender
•	Move all selected emails to trash: Separate function that moves all existing emails from the specified sender to Trash.
The question now is selecting from the terminal which ones to delete or selecting from the database the most efficient approach. Perhaps doing analysis on the content of the emails by isolating keywords or going deeper and using machine learning for analysis for the identification of spam. Well, I do have a very good model I can use for this exact purpose which uses machine learning.
What Next?
Instead of entering the numbers in the terminal and moving all duplicates together. Create a python list in the block.py script and add your own email addresses copy and pasted from Gmail inbox folder. Pull all senders from the spam folder to start this list. This will be the most efficient and correct method. This list will be the an input for the filter function.
