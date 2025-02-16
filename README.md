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
