# birdnest_backend

## Background

This is the backend component of assignment provided by company Reaktor.
The information about the assignment can be understood read here https://assignments.reaktor.com/birdnest/
This backend components creates a python program which perform query on the drone and pilot data before sanitising it
and put it into the postgresql database.
The docker-compose.yml spin up both the program and postgresql.
Currently, the mount volume code is written in docker-compose but not used due to not enough time for testing.

The data query and update is performed every 3 seconds because the drone data is updated at about every 2 seconds.

## Potential Improvement

1. Current usage of upsert one by one for each record is inefficient.
    1. This is limitation of using ORM provided by SQLAlchemy
    2. It would be better to write SQL statement to handle this.
2. Write proper tests
    1. Only Integration and run through tests is performed on playground notebook.
    2. Proper tests for parser and fetcher should be written.
3. Make it so that the postgresql is backup by mounting it to
    1. There was a challenge that faced here but turns out the bug is in another area, will come back and check this
       later.
    2. the code has already been written in docker-compose.

## Challenges Faced

1. Writing docker-compose.yml is quite a challenge since environment injection is a pain, hence the docker-compose up
   commands has to be run as seen in the commands.txt
2. SQLAlchemy's upsert on conflict only allows for single record update and is hence not that great. (write own sql is
   better)

## How to deploy
1. install docker on your host machine 
2. docker-compose up -d
3. open the incoming port to your host machine for the postgresql the port used here is default (data is not sensitive since it's publicly available, probably)