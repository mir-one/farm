FROM influxdb:latest

RUN mkdir -pv /var/influxdb/data

ADD docker/influxdb/run.sh /run.sh
RUN chmod +x /*.sh

ENV PRE_CREATE_DB farm_db
ENV ADMIN_USER farm
ENV PASS mmdu77sj3nIoiajjs

EXPOSE 8086

CMD /run.sh
