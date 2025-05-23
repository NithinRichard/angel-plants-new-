from angels_plants.wsgi import application

def handler(request, context):
    return application(request)
