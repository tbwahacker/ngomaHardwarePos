# # runserver.py
# import os
# import sys
#
# from django.core.management import execute_from_command_line
#
# # Adjust BASE_DIR for frozen executables
# if getattr(sys, 'frozen', False):
#     os.environ['DJANGO_SETTINGS_MODULE'] = 'pos.settings'
#     sys.path.append(sys._MEIPASS)
#     os.chdir(sys._MEIPASS)
# execute_from_command_line([sys.argv[0], 'runserver', '0.0.0.0:8000', '--noreload'])


# runserver.py
import os
import sys
import django
from django.core.management import execute_from_command_line

# Adjust BASE_DIR for frozen executables
if getattr(sys, 'frozen', False):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'pos.settings'
    django.setup()  # Ensures Django is fully initialized
    sys.path.append(sys._MEIPASS)
    os.chdir(sys._MEIPASS)

# Check command-line arguments for custom commands
if len(sys.argv) > 1:
    if sys.argv[1] == 'migrate':
        # First run makemigrations
        execute_from_command_line([sys.argv[0], 'makemigrations'])
        # Then run migrate
        execute_from_command_line([sys.argv[0], 'migrate'])
    else:
        # For other commands, run them directly
        execute_from_command_line(sys.argv)
else:
    # Default to running the server
    execute_from_command_line([sys.argv[0], 'runserver', '0.0.0.0:8000', '--noreload'])
