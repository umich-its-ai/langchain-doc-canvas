FROM python:3.11

COPY ./requirements.txt .
COPY ./requirements-dev.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements-dev.txt

COPY ./canvas_langchain/ ./canvas_langchain/
COPY ./canvas-test.py .
COPY ./.env .

CMD [ "python", "./canvas-test.py" ]
