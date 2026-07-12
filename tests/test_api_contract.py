"""Pruebas rápidas que no requieren una base PostgreSQL activa."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import CuentaUpdate, SimularFallo, UsuarioCreate


client = TestClient(app)


def test_openapi_expone_modulos_obligatorios():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/usuarios/" in paths
    assert "/api/publicaciones/likes" in paths
    assert "/api/publicaciones/citaciones" in paths
    assert "/api/fotografias/{id_foto}/archivo" in paths
    assert "/api/fotografias/{id_foto}/miniatura" in paths
    assert "/api/admin/concurrencia" in paths


def test_paginacion_rechaza_limites_excesivos():
    response = client.get("/api/usuarios/?limit=101")
    assert response.status_code == 422


def test_modelos_rechazan_valores_fuera_del_dominio():
    for constructor, data in (
        (UsuarioCreate, {"cedula": "1234567890", "apellidos": "A", "nombres": "B", "cargo": "estudiante"}),
        (CuentaUpdate, {"estado": "borrado"}),
        (SimularFallo, {"id_usuario_origen": 1, "id_usuario_destino": 2, "monto": 0}),
    ):
        try:
            constructor(**data)
        except ValueError:
            continue
        raise AssertionError(f"{constructor.__name__} aceptó datos inválidos")
