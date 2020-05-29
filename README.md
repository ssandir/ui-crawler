Repurposed from assigment 1 and 2 for class Web data search and extraction.
Credits for repository also go to Andraž Jelenc and Vid Križnar.

# ui-crawler
The solution runs in two Docker containers: postgres and crawler.
**Docker and Docker-compose packets are required to sucessfully run this project**


## How to use
1. Clone repository with `git clone git@github.com:vkriznar/IEPS-WebCrawler.git`
2. Go into cloned repository with `cd IEPS-WebCrawler/crawler`
2. Obtain necessary Docker images with `docker-compose build`
3. Run with `docker-compose up`

**Postgres data are stored INSIDE container. The data is safe if you restart container, but it will be lost if you recreate the Postgres container!**

## Developer's notes
### Restart with keeping stored data
(Any modification in source code are applied)
1. Run `docker-compose restart`

### Restart with clean database
1. Run `docker-compose down` to remove BOTH containers
2. Run `docker-compose up` to start new containers

## How to pass variable into code
1. All variables are specified in *docker-compose.yml* file. For each container there is *environment* section that contains all variables that will be pushed into container on its creation.
2. To capture this variables with Python there is intermediate file *config.conf* that is created from *config.tmpl* on container's creation. So every variable that we want to push into Python source must be defined inside *config.tmpl* file.
3. To simplify accessing config file there is *ConfigManager* class inside *crawler/crawler-src*. This class maps config file into dictionaries by sections.

**Mind that variables from docker-compose are pushed to container only on its creation!**
