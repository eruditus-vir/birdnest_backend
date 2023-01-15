FROM python:3.8

RUN apt-get update && apt-get install -y libpq-dev

COPY . /app

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "app.py"]
