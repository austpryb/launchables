FROM python:3.8

RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

RUN apt-get update -y && apt-get update \
  && apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev libssl-dev python3-venv python3-pip python3-setuptools

RUN apt-get update -y --allow-releaseinfo-change

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash -

RUN apt-get install -y nodejs

#RUN npm install -g openzeppelin-contracts@4.4.0

#RUN npm install -g chainlink-brownie-contracts@0.2.2

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN pip install eth-brownie

#COPY . /usr/src/app

EXPOSE 5000

CMD ["python", "/usr/src/app/run.py"]
