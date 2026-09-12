from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Paginación estándar de la API.

    El tope de 50 no es decorativo: sin él, `?page_size=100000` obliga a
    serializar la tabla entera y es una denegación de servicio de una línea.
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50


class CompactPagination(DefaultPagination):
    """Para listados densos como los rankings."""

    page_size = 20
    max_page_size = 50
