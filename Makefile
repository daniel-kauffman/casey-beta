SOURCE = client.c
OBJECT = $(HOME)/casey
KEY := $(shell echo $$RANDOM | sha512sum | cut -d " " -f 1)
KEY_FILE = key.txt
DOMAIN = $(shell hostname)
PORT = 5005
SERVER_NAME = casey
N_PROCS = 10


all: clean key compile serve
key:
	@echo $(KEY) > $(KEY_FILE);
	@chmod 600 $(KEY_FILE);
compile:
	@gcc $(SOURCE) \
		 -std=gnu11 \
		 -Wall \
		 -Werror \
		 -O3 \
		 -D DOMAIN=\"$(DOMAIN)\" \
		 -D PORT=\"$(PORT)\" \
		 -D KEY=\"$(KEY)\" \
		 -lcrypto \
		 -o $(OBJECT);
	@chmod 711 $(OBJECT);
clean:
	@rm -f $(KEY_FILE) $(OBJECT);
	@if [ -z "$1" ]; \
	then \
		printf "#/bin/bash\necho" > $(OBJECT); \
		chmod 755 $(OBJECT); \
	fi
serve: shutdown
	@gunicorn --name $(SERVER_NAME) \
        	  --bind 0.0.0.0:$(PORT) flaskapp:app \
        	  --workers $(N_PROCS) \
        	  --max-requests 1 \
        	  --timeout 900 \
        	  --preload \
        	  --daemon;
shutdown:
	@for pid in $$(pgrep -f "gunicorn --name $(SERVER_NAME) "); \
	do \
		command=$$(ps --no-headers -o %c $$pid); \
		if [[ $$command != "" && $$command != sh ]]; \
		then \
			kill -s 9 $$pid; \
		fi \
	done
	@rm -f ~/inbox/*/*/*/.lock
