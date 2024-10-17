# git
git rm -r --cached .


# Material Icons
https://fonts.google.com/icons

sudo apt-get install python3-venv
python3 -m venv venv
source venv/bin/activate


# freeze dependences to reqs.txt  && executable file
pip freeze > requirements.txt

pip install -r requirements.txt

pip install djangorestframework
pip install djangorestframework-simplejwt

# super user
py manage.py createsuperuser
username: admin
password: AdminPos@123

# Make emails unique
python manage.py dbshell
CREATE UNIQUE INDEX unique_email ON auth_user(email);

# make migrations in pyinstaller
./ngomahardware migrate

#local exe
pyinstaller ngomahardware.spec
.\ngomahardware.exe

# for images, create d tempalatetags for handling blob

QRCODE
npm install --save qrious

#Seeding
py manage.py seed

#delete
python manage.py dbshell  
DELETE FROM posApp_salesitems
.exit

# For backing up to google drive
pip install google-api-python-client google-auth google-auth-oauthlib
