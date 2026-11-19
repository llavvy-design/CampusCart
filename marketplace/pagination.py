from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ProductPagination(PageNumberPagination):
    """
    Paginate product listings.

    Default page size: 10 products.
    Maximum page size: 50 products.
    Clients can request a custom size using ?page_size=.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "products": data,
            }
        )
