FROM python:3.8

RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

RUN apt-get update -y && apt-get update \
  && apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev libssl-dev python3-venv python3-pip python3-setuptools

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /usr/src/app

EXPOSE 5000
#ENTRYPOINT ["flask", "run"]
CMD ["python","/usr/src/app/run.py"]
