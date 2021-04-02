#!/bin/bash
while IFS="" read -r p || [ -n "$p" ]
do
  pip3 install --target "./package" $p
done < requirements.txt
cd package
zip -r ../deployment-package.zip .
cd ..
zip -g deployment-package.zip *.py