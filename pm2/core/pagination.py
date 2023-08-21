from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """
        CustomPagination class used to handle the pagination
    """
    def paginate_queryset(self, queryset, request, view=None):
        """
            method used to paginate the query set
        """
        self.page_size_query_param = 'page_size'
        return super(CustomPagination, self).paginate_queryset(queryset, request, view)
