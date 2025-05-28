#!/bin/bash

# Remove all migration files except the initial one
for file in store/migrations/*; do
    if [[ $file != "store/migrations/0001_initial.py" ]]; then
        rm "$file"
    fi
done

# Reset migrations
python manage.py makemigrations --empty store --name initial

# Apply migrations
python manage.py migrate store
