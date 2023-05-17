FROM python:alpine
LABEL made="with_love"
ADD . /summus/
WORKDIR /summus
RUN ls
RUN pip install -r ./requirements.txt
CMD python3 -m src ./src/__main__.py