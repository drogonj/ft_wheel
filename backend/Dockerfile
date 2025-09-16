FROM python:3.12.10-alpine3.22

RUN apk add --no-cache postgresql-dev

RUN adduser -D -u 4242 backend

WORKDIR /backend

COPY ./requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY django django
COPY ./start.sh .

RUN chown -R backend:backend /backend
RUN chmod +x start.sh

RUN mkdir -p /var/log/ft_wheel && chown -R backend:backend /var/log/ft_wheel

USER backend

CMD [ "./start.sh" ]
