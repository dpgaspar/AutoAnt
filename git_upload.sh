git add docs/*
git add *.rst
git add *.py
git add MANIFEST.in
git add LICENSE
git add requirements.txt
git add git_upload.sh
git add .gitignore
git add autoant/*.py
git commit -a -m "$1"
git push origin $2

