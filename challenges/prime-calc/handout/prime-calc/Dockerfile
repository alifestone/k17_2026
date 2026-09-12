FROM python:3.13-slim AS dmtcp-builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gcc g++ make \
 && rm -rf /var/lib/apt/lists/*

ARG DMTCP_VERSION=4.2.0
RUN curl -fsSL "https://github.com/dmtcp/dmtcp/archive/refs/tags/v${DMTCP_VERSION}.tar.gz" \
      -o /tmp/dmtcp.tar.gz \
 && mkdir /tmp/dmtcp-src \
 && tar -xzf /tmp/dmtcp.tar.gz -C /tmp/dmtcp-src --strip-components=1 \
 && cd /tmp/dmtcp-src \
 && ./configure --prefix=/opt/dmtcp \
 && make -j"$(nproc)" \
 && make install

FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends gzip libatomic1 libstdc++6 tini \
 && rm -rf /var/lib/apt/lists/*

COPY --from=dmtcp-builder /opt/dmtcp /opt/dmtcp

WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/app.py src/generator.py src/worker.py src/entrypoint.sh ./
COPY src/templates ./templates
COPY flag.txt /flag
RUN chmod 0755 /app/entrypoint.sh \
 && groupadd --system prime \
 && useradd --system --gid prime --home-dir /app --no-create-home prime \
 && chown root:prime /flag \
 && chmod 0440 /flag \
 && mkdir -p /app/data/configs /app/data/runtime /app/data/output \
 && chown -R prime:prime /app/data

ENV DATA_DIR=/app/data \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/dmtcp/bin:$PATH
EXPOSE 8000
USER prime
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
