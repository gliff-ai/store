import os

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.contrib.staticfiles import finders

from api.endpoints import api

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    path("api/", api.urls),
]


if settings.DEBUG:

    def serve_static(request, path):
        filename = finders.find(path)
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)

        return serve(request, basename, dirname)

    urlpatterns += [re_path(r"^static/(?P<path>.*)$", serve_static)]
