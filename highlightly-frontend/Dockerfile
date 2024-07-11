# Start from a node image since both node and NPM is required.
FROM node:16

WORKDIR /usr/src/app

COPY package* ./

ENV NODE_ENV development

# Install the dependencies in the copied package.json.
RUN npm install
