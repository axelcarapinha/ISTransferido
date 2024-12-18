# ISTransferido
Download the files of all your courses in a brief <br/>
Redoit it, and only the new ones will be added;<br/>
All new files will be in the inbox folder 📥 <br/>
Uses <a href="https://scrapy.org/">Scrapy's library</a>. <br/>
<br/>
Disclaimer: optimized for Fenix's pages, but easily customizable with other XPaths.

### Configuration
1. Prepare the virtual environment
```bash
bash install.sh
```
2. Create the file with credentials
```bash
touch istransferido/.env
echo USERNAME="istxxxxx" >> .env
echo PASSWORD="your_password" >> .env # have you heard about password managers?


# ⚠️ IMPORTANT ⚠️
# If this is used in another repo, create the .gitignore file with the content as follows:
*.env
venv/
```

3. Chose which courses to download
```bash
nano config.yaml # maintain the base URL as used (it's the main link from each course page)
```

### Running
Download ALL the files + organize the inbox
```bash
# Run spider, RUN!
cd istransferido/ && scrapy crawl ist_spider && cd ../ && bash filter-inbox.sh 
```
If the command fails for some reason (configuration, conflicts, ...), remember to go back the main directory of the project. <br/>
Otherwise, it won't work.


### Contributions
Feel free to change or contribute! <br/>
I leave some unimplemented ideas, for me or others :) <br/>
- Avoid repeated downloads without the files being in the folder (it uses bash for now because of the relatively small amount of files)
- An alternative for credentials in the .env


### Extra notes
- Please, do not change the download delay to something that can create too much requests to the servers
