# Using Sidecar from a Psion

This guide illustrates how to access the Sidecar from a Psion browser,
download software, and prepare a Guardian crossword for use with a compatible
Psion crossword program.

## 1. Open the Sidecar homepage

1. Start the Sidecar server on the Raspberry Pi.
2. Connect the Psion to the same network, or establish your usual supported
   connection to the Pi.
3. Open Opera or another compatible browser on the Psion.
4. Enter `http://<raspberry-pi-address>:8081/`, replacing the placeholder with
   the hostname or IP address of your Raspberry Pi.

## 2. Browse files on the Sidecar

Use the homepage and its links to browse the locally stored crossword files
and other available resources.

![Psion file listing](images/File%20listing%201.png)

![Another view of the file listing](images/File%20listing%202.png)

## 3. Download software from Psion Community

1. Select the Psion Community software link on the Sidecar homepage.
2. Search the catalogue for the program you want.
3. Select the appropriate download link.
4. Wait for the download to finish and follow the browser's prompts to save
   the file.

The browser may initially use `Download.bin` as the filename. Follow the
save prompt and check the resulting filename before attempting to install
the package. The exact behaviour can vary with the browser and installer.

![Selecting a software download](images/Download%20sis%20file.png)

![Software download in progress](images/Download%20in%20progress.png)

Software availability depends on the external archive and the links in the
catalogue. Only download and use packages you are entitled to access.

## 4. Download a Guardian crossword

1. On the Sidecar homepage, choose the Quick or Cryptic crossword option.
2. Enter the crossword number and submit the request.
3. When the text file is available, select its link to download it to the
   Psion, or use the local archive to retrieve a crossword already stored
   on the Raspberry Pi.

Downloaded files have names such as `Quick_17028.txt` or
`Cryptic_30103.txt`.

## 5. Convert the crossword on the Psion

The downloaded text file must be converted using the separate Psion OPL
converter before it can be opened in a compatible RMR or FatCatz crossword
program.

1. Transfer the downloaded text file to a location accessible on the Psion.
2. Open and run the OPL converter.
3. Follow the converter's prompts to select and convert the crossword text
   file.
4. Open the converted crossword in the appropriate crossword application.

The screenshots below illustrate the import and conversion workflow.

![Selecting a crossword to import](images/Import%20crossword.png)

![Crossword conversion on the Psion](images/Crossword%20conversion.png)

![Cryptic crossword after import](images/Imported%20crossword%20-%20cryptic.png)

## Notes

- The Sidecar server must be running for the browser interface to be
  available.
- The Raspberry Pi and Psion must have a working network or other supported
  connection between them.
- Browser prompts and file-handling behaviour can vary by Psion model and
  browser version.
- The Guardian website and external software archives can change
  independently of the Sidecar project.
