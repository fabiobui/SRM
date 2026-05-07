"""URL del portale fornitore.

Tutte le rotte qui sono inserite in `config/urls.py` sotto il prefisso `/portale/`
con `namespace='portal'`. I `name=` sono usati con il prefisso `portal:` (es.
`{% url 'portal:dashboard' %}`).
"""

from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    # Home portale
    path("", views.PortalDashboardView.as_view(), name="dashboard"),

    # I miei documenti — i Document sono pre-creati dal BO (vedi DocumentInline
    # in vendors/admin.py); il fornitore carica il file sul singolo Document
    # identificato dal pk in URL.
    path("documenti/", views.MyDocumentsView.as_view(), name="my-documents"),
    path("documenti/<str:pk>/", views.MyDocumentDetailView.as_view(), name="my-document-detail"),
    path("documenti/<str:pk>/upload/", views.MyDocumentUploadView.as_view(), name="my-document-upload"),

    # Anagrafica
    path("anagrafica/", views.MyVendorProfileView.as_view(), name="my-profile"),
    path("anagrafica/modifica/", views.VendorChangeRequestCreateView.as_view(),
         name="my-profile-change"),
    path("anagrafica/richieste/", views.VendorChangeRequestListView.as_view(),
         name="my-change-requests"),

    # Qualifica
    path("qualifica/", views.MyQualificationView.as_view(), name="my-qualification"),

    # Area BO — gestione richieste anagrafica
    path("backoffice/anagrafica-richieste/",
         views.BoChangeRequestListView.as_view(), name="bo-change-requests"),
    path("backoffice/anagrafica-richieste/<uuid:pk>/",
         views.BoChangeRequestDetailView.as_view(),
         name="bo-change-request-detail"),
    path("backoffice/anagrafica-richieste/<uuid:pk>/review/",
         views.BoChangeRequestReviewView.as_view(),
         name="bo-change-request-review"),
]
