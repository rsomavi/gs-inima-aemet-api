"""URL routes for the weather app."""

from django.urls import path

from .views import AntarcticaDataView

urlpatterns = [
    path(
        "antartida/datos/fechaini/<str:fecha_ini_str>/fechafin/<str:fecha_fin_str>/estacion/<str:identificacion>",
        AntarcticaDataView.as_view(),
        name="antartida-datos",
    ),
]