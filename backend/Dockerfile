FROM python:3.12.10-alpine3.22

RUN apk add --no-cache postgresql-dev

RUN adduser -D backend

WORKDIR /backend

COPY ./requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY django django
COPY ./start.sh .

RUN chown -R backend:backend /backend
RUN chmod +x start.sh

USER backend

CMD [ "./start.sh" ]
