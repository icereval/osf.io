FROM python:2.7-slim

# Install dependancies
RUN apt-get update \
    && apt-get install -y \
        git \
        libev4 \
        libev-dev \
        libevent-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        # matplotlib
        libfreetype6-dev \
        libxft-dev \
        # scipy
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        # cryptography
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# grab gosu for easy step-down from root
ENV GOSU_VERSION 1.4
RUN apt-get update \
    && apt-get install -y \
        curl \
    && gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture)" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture).asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && apt-get clean \
    && apt-get autoremove -y \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Node : https://registry.hub.docker.com/u/library/node/
ENV NODE_VERSION 0.12.4
ENV NPM_VERSION 2.10.1
RUN apt-get update \
    && apt-get install -y \
        curl \
    && gpg --keyserver pool.sks-keyservers.net --recv-keys 7937DFD2AB06298B2293C3187D33FF9D0246406D 114F43EE0176B71C7BC219DD50A3051F888C628D \
    && curl -SLO "http://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz" \
    && curl -SLO "http://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
    && gpg --verify SHASUMS256.txt.asc \
    && grep " node-v$NODE_VERSION-linux-x64.tar.gz\$" SHASUMS256.txt.asc | sha256sum -c - \
    && tar -xzf "node-v$NODE_VERSION-linux-x64.tar.gz" -C /usr/local --strip-components=1 \
    && rm "node-v$NODE_VERSION-linux-x64.tar.gz" SHASUMS256.txt.asc \
    && npm install -g npm@"$NPM_VERSION" \
    && npm cache clear \
    && apt-get clean \
    && apt-get autoremove -y \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /code
WORKDIR /code

RUN pip install -U pip

# RUN git clone -b master --single-branch https://github.com/CenterForOpenScience/osf.io.git /code
# RUN cp /code/website/settings/local-dist.py /code/website/settings/local.py

# RUN pip install --no-cache-dir numpy==1.8.0
# RUN invoke requirements --metrics --addons
# RUN invoke assets --allow-root

COPY ./requirements.txt /code/
COPY ./requirements/ /code/requirements/
# RUN pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/requirements/metrics.txt

# COPY ./website/addons/badges/requirements.txt /code/website/addons/badges/
# RUN pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/badges/requirements.txt
COPY ./website/addons/box/requirements.txt /code/website/addons/box/
COPY ./website/addons/dataverse/requirements.txt /code/website/addons/dataverse/
COPY ./website/addons/dropbox/requirements.txt /code/website/addons/dropbox/
COPY ./website/addons/zotero/requirements.txt /code/website/addons/zotero/
COPY ./website/addons/github/requirements.txt /code/website/addons/github/
COPY ./website/addons/mendeley/requirements.txt /code/website/addons/mendeley/
COPY ./website/addons/s3/requirements.txt /code/website/addons/s3/
COPY ./website/addons/twofactor/requirements.txt /code/website/addons/twofactor/

RUN pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/dropbox/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/github/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/mendeley/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/s3/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/twofactor/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/box/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/dataverse/requirements.txt && \
  pip install --no-cache-dir -c /code/requirements/constraints.txt -r /code/website/addons/zotero/requirements.txt

COPY ./package.json /code/
RUN npm install --production

COPY ./.bowerrc /code/
COPY ./bower.json /code/
RUN ./node_modules/bower/bin/bower install --allow-root

COPY ./ /code/
RUN mv /code/website/settings/local-dist.py /code/website/settings/local.py && \
  mv /code/api/base/settings/local-dist.py /code/api/base/settings/local.py

RUN pip install invoke && \
  invoke requirements --release && \
  invoke requirements --base --addons && \
  (pip uninstall uritemplate.py --yes || true) && \
  pip install uritemplate.py==0.3.0

RUN  mkdir -p /code/website/static/built/ && \
    invoke build_js_config_files && \
  node ./node_modules/webpack/bin/webpack.js --config webpack.prod.config.js

# RUN apt-get clean \
#   && apt-get autoremove -y \
#     build-essential \
#   && rm -rf \
RUN rm -rf \
  /tmp \
  /root/.npm \
  /root/.cache \
  /code/node_modules \
  /code/website/static/vendor/bower_components

RUN npm install list-of-licenses

CMD ["gosu", "nobody", "invoke", "--list"]
