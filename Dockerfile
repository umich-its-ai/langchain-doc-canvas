FROM python:3.10

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY ./canvas_langchain/ ./canvas_langchain/
COPY ./canvas-test.py .

CMD [ "python", "./canvas-test.py" ]
