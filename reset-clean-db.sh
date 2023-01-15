#!/bin/bash
docker-compose down
rm -rf backup
mkdir backup
docker-compose up --force-recreate --build -d