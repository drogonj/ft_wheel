FROM postgres:14.18-alpine3.21

COPY ./export_credentials.sh /usr/local/bin/export_credentials.sh
RUN chmod +x /usr/local/bin/export_credentials.sh

ENTRYPOINT ["/usr/local/bin/export_credentials.sh"]
CMD ["postgres"]