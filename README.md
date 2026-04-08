# journal-bot Summary
A  chatbot based tool based to journal my life

### System dependencies
 * Install docker
 * Install docker-compose

### App dependencies
Telegram

### Setup using docker-compose
__**Step 1: Copy the env file from the backend folder**__
```
    cd backend
    cp .env.docker.example .env
```

__**Step 2: Insert environmental variable data**__

__**Step 3:  To build the application type the command in the console**__
```
docker-compose -f docker-compose.yml build
```

__**Step 4: To launch the application type the command in the console**__
```
docker-compose -f docker-compose.yml up
```

...or launch as a daemon:
```
docker-compose -f docker-compose.yml up -d
```

#### Create SQLlite DB
1) open python in terminal
2) Insert the following commands
```
from database import ( init_db )
init_db()
````

### Run Locally
`python bot.py`

### Media Uploads
The bot can save media you send in Telegram.

- Use `Upload Photo or Audio` from the keyboard, or just send the file directly.
- Supported uploads: photos, audio files, and Telegram voice notes.
- Uploaded media is stored in the configured Google Drive folder and logged in the daily journal record.

### Daily Journal Prompts
The bot can now send an automatic daily journal prompt.

- `/start` enables daily prompts for that chat.
- `Enable Daily Prompt` turns them on again if you paused them.
- `Disable Daily Prompt` or `/daily_off` turns them off.
- `/daily_on` turns them back on.

Optional env vars:

- `TIMEZONE=America/Bogota`
- `DAILY_PROMPT_TIME=18:00`

If `DAILY_PROMPT_TIME` is not set, the bot sends the prompt daily at `18:00`.
