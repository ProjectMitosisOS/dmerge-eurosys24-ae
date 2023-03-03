FROM python:3.9

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt && \
       mkdir tmp

EXPOSE 8080

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]
