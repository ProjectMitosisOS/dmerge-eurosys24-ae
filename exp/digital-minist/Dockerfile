FROM val01:5000/dmerge-base

WORKDIR /app

RUN pip install tensorflow==2.4.0 keras==2.4.3
COPY . .
RUN pip install -r requirements.txt && \
       mkdir tmp

EXPOSE 8080

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]
