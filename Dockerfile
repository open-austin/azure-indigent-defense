FROM  --platform=linux/amd64 python:3.8-slim-bullseye
WORKDIR /app

# Install Azure CLI and Azure Func Tools v4
# https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4
RUN apt-get -y update
RUN apt-get -y install ca-certificates curl apt-transport-https lsb-release gnupg

RUN mkdir -p /etc/apt/keyrings
RUN curl -sLS https://packages.microsoft.com/keys/microsoft.asc \
  | gpg --dearmor \
  | tee /etc/apt/keyrings/microsoft.gpg > /dev/null
RUN chmod go+r /etc/apt/keyrings/microsoft.gpg

RUN echo "deb [arch=`dpkg --print-architecture` signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" \
  | tee /etc/apt/sources.list.d/azure-cli.list
RUN echo "deb [arch=`dpkg --print-architecture` signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f 1)/prod $(lsb_release -cs) main" \
  | tee /etc/apt/sources.list.d/dotnetdev.list

RUN cat /etc/apt/sources.list.d/dotnetdev.list
RUN apt-get -y update && apt-get -y install azure-cli azure-functions-core-tools-4

# Install Python dependencies, then copy the rest of the project in
RUN python -m pip install --upgrade pip
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./
