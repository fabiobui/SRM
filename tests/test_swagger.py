# Imports
from http import HTTPStatus

import pytest
from django.urls import reverse

# Nota: solo "schema-swagger-ui" è effettivamente registrato in config/urls.py
# (`schema_view.with_ui('swagger', ...)`). Redoc e uno schema JSON separato
# non sono mai stati aggiunti a config/urls.py, quindi non c'è nulla da
# testare per quelle varianti finché non vengono davvero registrate.


# Function to check if swagger UI is accessible by admin
def test_swagger_ui_accessible_by_admin(admin_client):
    url = reverse("schema-swagger-ui")
    response = admin_client.get(url)
    assert response.status_code == HTTPStatus.OK


# Function to check if swagger UI is accessible by normal user
@pytest.mark.django_db()
def test_swagger_ui_accessible_by_normal_user(client):
    url = reverse("schema-swagger-ui")
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK
