FROM debian:bookworm

RUN apt-get -qq update && apt-get -qqy dist-upgrade && apt-get -qqy --no-install-recommends install \
  gearman-job-server && \
  apt-get clean && \
  rm -rf /var/lib/apt

EXPOSE 4730

ENTRYPOINT [ "gearmand" ]
