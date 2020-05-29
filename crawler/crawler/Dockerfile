FROM ubuntu:19.10

ENV DEBIAN_FRONTEND noninteractive
ENV CHROMEDRIVER_PATH /usr/bin/chromedriver

RUN apt-get update && \
    apt-get install -y apt-utils && \
    apt-get install -y \
      curl \
      unzip \
      xvfb \
      libxi6 \
      libgconf-2-4 \
      libpq-dev \
      gnupg2 \
      python3.8 \
      python3-pip \
      python3.8-dev

# Selenium/Chrome/Chromedriver requirements: curl unzip xvfb libxi6 libgconf-2-4
# PG lib: libpq-dev 
# Python: python python-pip 

COPY requirements.txt requirements.txt
RUN python3.8 -m pip install -r requirements.txt

# Chrome
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
	echo "deb [arch=amd64]  http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
	apt-get -y update && \
	apt-get -y install google-chrome-stable
	
# Chromedriver
RUN wget https://chromedriver.storage.googleapis.com/2.41/chromedriver_linux64.zip && \
	unzip chromedriver_linux64.zip && \
	mv chromedriver $CHROMEDRIVER_PATH && \
	chmod +x $CHROMEDRIVER_PATH

# For creating config from template
ENV DOCKERIZE_VERSION v0.6.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz
