FROM httpd:2.4.49

COPY apache/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY apache/htdocs/ /usr/local/apache2/htdocs/

COPY proxy /app/proxy
COPY getflag /getflag

RUN chmod 755 /app/proxy \
    && chown root:root /getflag \
    && chmod 111 /getflag

EXPOSE 8080

CMD ["sh", "-c", "httpd -DFOREGROUND & exec /app/proxy"]