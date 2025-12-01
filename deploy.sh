#!/bin/bash
set -e

rm Archive.zip

zip -r Archive.zip .

az functionapp deployment source config-zip \
  --resource-group jfrog-budget-test \
  --name jfrog-slack-notification-function \
  --src Archive.zip
